#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
#
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

"""
Very simple status checking class. Useful when you can't get any of the others
to work, or you need to prototype things.
"""
from __future__ import absolute_import
import os
from rabbitvcs.util.log import Log

import rabbitvcs.vcs
import rabbitvcs.vcs.status

from rabbitvcs import gettext

_ = gettext.gettext

log = Log("rabbitvcs.services.statuschecker")


class StatusChecker(object):
    """A class for performing status checks."""

    # All subclasses should override this! This is to be displayed in the
    # settings dialog
    CHECKER_NAME = _("Simple status checker")

    def __init__(self):
        """Initialises status checker. Obviously."""
        self.vcs_client = rabbitvcs.vcs.create_vcs_instance()
        self.conditions_dict_cache = {}

    def check_status(self, path, recurse, summary, invalidate):
        """Performs a status check, blocking until the check is done."""
        path_status = self.vcs_client.status(path, summary, invalidate)
        return path_status

    def generate_menu_conditions(self, paths, invalidate=False):
        from rabbitvcs.util.contextmenu import MainContextMenuConditions

        conditions = MainContextMenuConditions(self.vcs_client, paths)
        return conditions.path_dict
    # RABBITVCS_BATCHED_MENU_WARMUP_V8
    def _menu_paths_share_repository(self, base_dir, paths):
        if not paths:
            return False

        guesses = [self.vcs_client.guess(path) for path in paths]
        keys = {
            (guess.get("vcs"), guess.get("repo_path"))
            for guess in guesses
        }
        if len(keys) != 1:
            return False

        vcs_type, repo_path = next(iter(keys))
        if not vcs_type or not repo_path:
            return False

        try:
            base_real = os.path.normcase(
                os.path.realpath(os.fsdecode(base_dir))
            )
            repo_real = os.path.normcase(
                os.path.realpath(os.fsdecode(repo_path))
            )
            return os.path.commonpath([base_real, repo_real]) == repo_real
        except (OSError, TypeError, ValueError):
            return False

    def _menu_statuses_for_path(self, path, all_statuses):
        normalized_path = os.path.normcase(
            os.path.normpath(os.fsdecode(path))
        )
        directory_prefix = normalized_path.rstrip(os.sep) + os.sep
        path_is_directory = os.path.isdir(path)

        statuses = []
        seen_paths = set()

        for status in all_statuses:
            status_path = os.path.normcase(
                os.path.normpath(os.fsdecode(status.path))
            )

            # Preserve the exact semantics of the old per-path Git
            # calculation. Gittyup's ignored-file scan is repository-wide,
            # even when status() was requested for one file or subdirectory.
            # Consequently every old menu condition set included all ignored
            # statuses and could report has_ignored=True.
            include = status.simple_content_status() == "ignored"

            if status_path == normalized_path:
                include = True
            elif (
                path_is_directory
                and status_path.startswith(directory_prefix)
            ):
                # VCS.statuses() defaults to recurse=True, so a directory menu
                # receives its complete subtree, not only direct children.
                include = True

            if include and status_path not in seen_paths:
                statuses.append(status)
                seen_paths.add(status_path)

        return statuses

    def generate_menu_conditions_batch(self, base_dir, paths):
        from rabbitvcs.util.contextmenu import MainContextMenuConditions

        if not paths:
            return []

        # RABBITVCS_GROUPED_SPARSE_MENU_SNAPSHOT_V8G
        # One Nautilus/D-Bus batch can contain a nested repository. Group the
        # paths by their actual VCS and repository instead of falling back to
        # one old-style calculation per path.
        groups = {}
        group_order = []

        for path in paths:
            guess = self.vcs_client.guess(path)
            key = (guess.get("vcs"), guess.get("repo_path"))
            if key not in groups:
                groups[key] = []
                group_order.append(key)
            groups[key].append(path)

        path_dicts = {}

        for key in group_order:
            vcs_type, repo_path = key
            group_paths = groups[key]

            if not vcs_type or not repo_path:
                for path in group_paths:
                    path_dicts[path] = self.generate_menu_conditions([path])
                continue

            try:
                base_real = os.path.normcase(
                    os.path.realpath(os.fsdecode(base_dir))
                )
                repo_real = os.path.normcase(
                    os.path.realpath(os.fsdecode(repo_path))
                )
                if os.path.commonpath([base_real, repo_real]) == repo_real:
                    group_base = base_dir
                else:
                    # A direct child can itself be a nested repository root.
                    group_base = repo_path
            except (OSError, TypeError, ValueError):
                group_base = repo_path

            vcs_backend = self.vcs_client.client(group_base)

            if (
                vcs_type == "git"
                and hasattr(vcs_backend, "menu_statuses_batch")
            ):
                batches = vcs_backend.menu_statuses_batch(
                    group_base, group_paths
                )
                for path in group_paths:
                    path_statuses = batches.get(path, [])
                    if path_statuses:
                        conditions = MainContextMenuConditions(
                            self.vcs_client,
                            [path],
                            statuses=path_statuses,
                        )

                        # RABBITVCS_GROUPED_SPARSE_MENU_SNAPSHOT_V8G
                        # The batch already contains the exact status for this
                        # path. Derive is_versioned from it instead of asking
                        # the shared VCS facade again; that extra lookup can
                        # observe a different repository/cache generation when
                        # one Nautilus directory contains nested repositories.
                        normalized_path = os.path.normcase(
                            os.path.normpath(os.fsdecode(path))
                        )
                        exact_status = next(
                            (
                                status
                                for status in path_statuses
                                if os.path.normcase(
                                    os.path.normpath(
                                        os.fsdecode(status.path)
                                    )
                                )
                                == normalized_path
                            ),
                            None,
                        )
                        if exact_status is not None:
                            conditions.path_dict["is_versioned"] = (
                                exact_status.is_versioned()
                            )

                        path_dicts[path] = conditions.path_dict
                    else:
                        path_dicts[path] = (
                            self.generate_menu_conditions([path])
                        )
                continue

            # Preserve V8b's recursive grouped behaviour for other VCS
            # implementations.
            all_statuses = self.vcs_client.statuses(
                group_base, recurse=True, invalidate=True
            )
            for path in group_paths:
                path_statuses = self._menu_statuses_for_path(
                    path, all_statuses
                )
                if path_statuses:
                    conditions = MainContextMenuConditions(
                        self.vcs_client,
                        [path],
                        statuses=path_statuses,
                    )
                    path_dicts[path] = conditions.path_dict
                else:
                    path_dicts[path] = (
                        self.generate_menu_conditions([path])
                    )

        return [path_dicts[path] for path in paths]

    def extra_info(self):
        return None

    def get_memory_usage(self):
        """Returns any additional memory of any subprocesses used by this
        checker. In other words, DO NOT return the memory usage of THIS process!
        """
        return 0

    def quit(self):
        # We will exit when the main process does
        pass
