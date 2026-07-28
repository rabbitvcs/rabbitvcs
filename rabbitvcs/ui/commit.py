from __future__ import absolute_import
from rabbitvcs import gettext
import rabbitvcs.vcs.status
from rabbitvcs.util.decorators import gtk_unsafe
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.util
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
import rabbitvcs.ui.action
from rabbitvcs.util.contextmenu import (
    GtkFilesContextMenu,
    GtkFilesContextMenuCallbacks,
    GtkFilesContextMenuConditions,
    GtkContextMenuCaller,
    create_vcs_instance,
)
from rabbitvcs.ui import InterfaceView
from gi.repository import Gtk, GObject, Gdk, GLib

#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2010 by Adam Plumb <adamplumb@gmail.com>
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

import os
import six.moves._thread
from time import sleep

from rabbitvcs.util import helper

from gi import require_version

require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.commit")

_ = gettext.gettext

helper.gobject_threads_init()


class Commit(InterfaceView, GtkContextMenuCaller):
    """
    Provides a user interface for the user to commit working copy
    changes to a repository.  Pass it a list of local paths to commit.

    """

    SETTINGS = rabbitvcs.util.settings.SettingsManager()

    TOGGLE_ALL = False
    SHOW_UNVERSIONED = SETTINGS.get("general", "show_unversioned_files")

    # This keeps track of any changes that the user has made to the row
    # selections
    changes = {}

    def __init__(self, paths, base_dir=None, message=None):
        """

        @type  paths:   list of strings
        @param paths:   A list of local paths.

        """
        InterfaceView.__init__(self, "commit", "Commit")

        self.base_dir = base_dir

        # Set dialog title with folder name
        if base_dir:
            folder_name = os.path.basename(os.path.normpath(base_dir))
            self.get_widget("Commit").set_title(_("Commit - %s") % folder_name)
        self.vcs = rabbitvcs.vcs.VCS()
        self.items = []

        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_STATUS,
                GObject.TYPE_STRING,
            ],
            [
                rabbitvcs.ui.widget.TOGGLE_BUTTON,
                "",
                _("Path"),
                _("Extension"),
                _("Text Status"),
                _("Property Status"),
            ],
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.path_filter,
                    "user_data": {"base_dir": base_dir, "column": 2},
                }
            ],
            callbacks={
                "row-activated": self.on_files_table_row_activated,
                "mouse-event": self.on_files_table_mouse_event,
                "key-event": self.on_files_table_key_event,
                "row-toggled": self.on_files_table_toggle_event,
            },
            flags={"sortable": True, "sort_on": 2},
        )
        self.files_table.allow_multiple()
        self.get_widget("toggle_show_unversioned").set_active(self.SHOW_UNVERSIONED)
        if not message:
            message = self.SETTINGS.get_multiline("general", "default_commit_message")
        self.message = rabbitvcs.ui.widget.TextView(self.get_widget("message"), message)

        self.paths = []
        for path in paths:
            if self.vcs.is_in_a_or_a_working_copy(path):
                self.paths.append(S(path))

    #
    # Helper functions
    #

    def load(self):
        """
        - Gets a listing of file items that are valid for the commit window.
        - Determines which items should be "activated" by default
        - Populates the files table with the retrieved items
        - Updates the status area
        """

        self.get_widget("status").set_text(_("Loading..."))

        self.items = self.vcs.get_items(
            self.paths, self.vcs.statuses_for_commit(self.paths)
        )

        self.populate_files_table()

    # Overrides the GtkContextMenuCaller method
    def on_context_menu_command_finished(self):
        self.initialize_items()

    def should_item_be_activated(self, item):
        """
        Determines if a file should be activated or not
        """

        if (
            S(item.path) in self.paths
            or item.is_versioned()
            and item.simple_content_status() != rabbitvcs.vcs.status.status_missing
        ):
            return True

        return False

    def should_item_be_visible(self, item):
        show_unversioned = self.SHOW_UNVERSIONED

        if not show_unversioned:
            if not item.is_versioned():
                return False

        return True

    def initialize_items(self):
        """
        Initializes the activated cache and loads the file items in a new thread
        """

        GLib.idle_add(self.load)

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    def delete_items(self, widget, event):
        paths = self.files_table.get_selected_row_items(1)
        if len(paths) > 0:
            proc = helper.launch_ui_window("delete", paths)
            self.rescan_after_process_exit(proc, paths)

    #
    # Event handlers
    #
    def on_refresh_clicked(self, widget):
        self.initialize_items()

    def on_key_pressed(self, widget, event, *args):
        if InterfaceView.on_key_pressed(self, widget, event, *args):
            return True

        if Gdk.keyval_name(event.keyval) == "F5":
            self.initialize_items()
            return True

        if (
            event.state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(event.keyval) == "Return"
        ):
            self.on_ok_clicked(widget)
            return True

    def on_toggle_show_all_toggled(self, widget, data=None):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        self.changes.clear()
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL
            self.changes[row[1]] = self.TOGGLE_ALL

    def on_toggle_show_unversioned_toggled(self, widget, *args):
        self.SHOW_UNVERSIONED = widget.get_active()
        self.populate_files_table()

        # Save this preference for future commits.
        if (
            self.SETTINGS.get("general", "show_unversioned_files")
            != self.SHOW_UNVERSIONED
        ):
            self.SETTINGS.set(
                "general", "show_unversioned_files", self.SHOW_UNVERSIONED
            )
            self.SETTINGS.write()

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        pathrev1 = helper.create_path_revision_string(paths[0], "base")
        pathrev2 = helper.create_path_revision_string(paths[0], "working")
        proc = helper.launch_ui_window("diff", ["-s", pathrev1, pathrev2])
        self.rescan_after_process_exit(proc, paths)

    def on_files_table_key_event(self, treeview, event, *args):
        if Gdk.keyval_name(event.keyval) == "Delete":
            self.delete_items(treeview, event)

    def on_files_table_mouse_event(self, treeview, event, *args):
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.show_files_table_popup_menu(treeview, event)

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(S(message).display())

    def populate_files_table(self):
        """
        First clears and then populates the files table based on the items
        retrieved in self.load()

        """

        self.files_table.clear()
        n = 0
        m = 0
        for item in self.items:
            if item.path in self.changes:
                checked = self.changes[item.path]
            else:
                checked = self.should_item_be_activated(item)

            if item.is_versioned():
                n += 1
            else:
                m += 1

            if not self.should_item_be_visible(item):
                continue

            self.files_table.append(
                [
                    checked,
                    S(item.path),
                    item.path,
                    helper.get_file_extension(item.path),
                    item.simple_content_status(),
                    item.simple_metadata_status(),
                ]
            )
        self.get_widget("status").set_text(
            _("Found %(changed)d changed and %(unversioned)d unversioned item(s)")
            % {"changed": n, "unversioned": m}
        )


class SVNCommit(Commit):
    def __init__(self, paths, base_dir=None, message=None):
        Commit.__init__(self, paths, base_dir, message)

        self.get_widget("commit_to_box").show()

        self.get_widget("to").set_text(
            S(self.vcs.svn().get_repo_url(self.base_dir)).display()
        )

        self.items = None
        if len(self.paths):
            self.initialize_items()

    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.hide()

        if len(items) == 0:
            self.close()
            return

        added = 0
        recurse = False
        for item in items:
            status = self.vcs.status(item, summarize=False).simple_content_status()
            try:
                if status == rabbitvcs.vcs.status.status_unversioned:
                    self.vcs.svn().add(item)
                    added += 1
                elif status == rabbitvcs.vcs.status.status_deleted:
                    recurse = True
                elif status == rabbitvcs.vcs.status.status_missing:
                    self.vcs.svn().update(item)
                    self.vcs.svn().remove(item)
            except Exception as e:
                log.exception(e)

        ticks = added + len(items) * 2

        self.action = rabbitvcs.ui.action.SVNAction(
            self.vcs.svn(), register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Commit"))
        self.action.append(self.action.set_status, _("Running Commit Command..."))
        self.action.append(helper.save_log_message, self.message.get_text()),
        self.action.append(self.do_commit, items, recurse)
        self.action.append(self.action.finish)
        self.action.schedule()

    def do_commit(self, items, recurse):
        # pysvn.Revision
        revision = self.vcs.svn().commit(
            items, self.message.get_text(), recurse=recurse
        )

        self.action.set_status(
            _("Completed Commit") + " at Revision: " + str(revision.number)
        )

    def on_files_table_toggle_event(self, row, col):
        # Adds path: True/False to the dict
        self.changes[row[1]] = row[col]


class GitCommit(Commit):
    def __init__(self, paths, base_dir=None, message=None):
        Commit.__init__(self, paths, base_dir, message)

        self.git = self.vcs.git(paths[0])

        self.get_widget("commit_to_box").show()

        active_branch = self.git.get_active_branch()
        if active_branch:
            self.get_widget("to").set_text(S(active_branch.name).display())
        else:
            self.get_widget("to").set_text("No active branch")

        # Cache for last-known size/position (updated on configure-event)
        self._win_geometry = None
        self._pane_position = None

        # Restore saved window size and position
        window = self.get_widget("Commit")
        try:
            w = int(self.SETTINGS.get("commit_window", "width") or 0)
            h = int(self.SETTINGS.get("commit_window", "height") or 0)
            x = int(self.SETTINGS.get("commit_window", "x") or 0)
            y = int(self.SETTINGS.get("commit_window", "y") or 0)
            if w > 0 and h > 0:
                window.resize(w, h)
            if x != 0 or y != 0:
                window.move(x, y)
        except Exception:
            pass

        # Track geometry changes so we can save even after the window is hidden
        window.connect("configure-event", self._on_configure)

        # Restore pane position (deferred so initial layout doesn't override it)
        pane = self.get_widget("pane")
        try:
            pos = int(self.SETTINGS.get("commit_window", "pane_position") or 0)
            if pos > 0:
                GLib.idle_add(pane.set_position, pos)
        except Exception:
            pass

        self.items = None
        if len(self.paths):
            self.initialize_items()

    def _on_configure(self, window, event):
        """Cache window size and position on every move/resize."""
        self._win_geometry = (event.width, event.height, event.x, event.y)

    def on_destroy(self, widget):
        # Save the last-known geometry (captured while window was visible)
        if self._win_geometry:
            w, h, x, y = self._win_geometry
            self.SETTINGS.set("commit_window", "width", str(w))
            self.SETTINGS.set("commit_window", "height", str(h))
            self.SETTINGS.set("commit_window", "x", str(x))
            self.SETTINGS.set("commit_window", "y", str(y))
        # Save pane position (prefer value captured before hide() to avoid GTK layout drift)
        pane_pos = self._pane_position if self._pane_position is not None else self.get_widget("pane").get_position()
        if pane_pos > 0:
            self.SETTINGS.set("commit_window", "pane_position", str(pane_pos))
        self.SETTINGS.write()
        super().on_destroy(widget)

    def load(self):
        """
        Override base load() to merge last-commit files when amend is active.
        When amend is checked, use HEAD~1 as the diff base (TortoiseGit style)
        so that files from the last commit appear pre-checked in the list.
        """
        self.get_widget("status").set_text(_("Loading..."))
        amend = self.get_widget("amend_checkbox").get_active()
        if amend:
            self.items = self._get_amend_items()
        else:
            self.items = self.vcs.get_items(
                self.paths, self.vcs.statuses_for_commit(self.paths)
            )
        self.populate_files_table()

    def _get_amend_items(self):
        """
        Return status items showing what will be in the amended commit.
        Runs `git diff --name-status HEAD~1` (working tree vs HEAD~1) so that
        both the previous commit's files and any new modifications are listed.
        Falls back to normal status if HEAD~1 does not exist (initial commit).
        """
        import subprocess
        from rabbitvcs.vcs.git.gittyup.objects import (
            ModifiedStatus, AddedStatus, RemovedStatus, RenamedStatus
        )

        repo_root = self.git.client.repo.path

        git_to_identifier = {
            "M": ModifiedStatus,
            "A": AddedStatus,
            "D": RemovedStatus,
            "R": RenamedStatus,
            "C": ModifiedStatus,
            "U": ModifiedStatus,
        }

        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", "HEAD~1"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # HEAD~1 probably doesn't exist (initial commit); fall back
                raise RuntimeError(result.stderr.strip())

            seen_paths = set()
            items = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                git_flag = parts[0][0]  # 'M', 'A', 'D', 'R', etc.
                path = parts[-1]        # last field (new path for renames)
                abs_path = self.git.client.get_absolute_path(path)
                if abs_path in seen_paths:
                    continue
                seen_paths.add(abs_path)
                status_cls = git_to_identifier.get(git_flag, ModifiedStatus)
                gittyup_st = status_cls(abs_path)
                items.append(rabbitvcs.vcs.status.GitStatus(gittyup_st))
            return items
        except Exception as e:
            log.exception(e)
            return self.vcs.get_items(
                self.paths, self.vcs.statuses_for_commit(self.paths)
            )

    def on_new_branch_toggled(self, widget, *args):
        to_widget = self.get_widget("to")
        if widget.get_active():
            # Clear and make editable for new branch name
            to_widget.set_text("")
            to_widget.set_editable(True)
            to_widget.grab_focus()
        else:
            # Return to display mode with current branch
            to_widget.set_editable(False)
            active_branch = self.git.get_active_branch()
            if active_branch:
                to_widget.set_text(S(active_branch.name).display())

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        amend = self.get_widget("amend_checkbox").get_active()
        if amend:
            # Show diff from HEAD~1 to working dir (previous commit + current changes)
            pathrev1 = helper.create_path_revision_string(paths[0], "HEAD~1")
            pathrev2 = helper.create_path_revision_string(paths[0], "working")
        else:
            pathrev1 = helper.create_path_revision_string(paths[0], "base")
            pathrev2 = helper.create_path_revision_string(paths[0], "working")
        proc = helper.launch_ui_window("diff", ["-s", pathrev1, pathrev2])
        self.rescan_after_process_exit(proc, paths)

    def show_files_table_popup_menu(self, treeview, data):
        """Override to inject amend-aware revert: when amend is active,
        revert targets HEAD~1 (TortoiseGit style) instead of HEAD, and
        the Revert item is shown for all files in the amend list regardless
        of working-tree status (those files live in HEAD, not the work tree)."""
        paths = self.files_table.get_selected_row_items(1)
        amend = self.get_widget("amend_checkbox").get_active()
        revision = "HEAD~1" if amend else "HEAD"

        caller = self

        class AmendAwareCallbacks(GtkFilesContextMenuCallbacks):
            def revert(self, widget, data1=None, data2=None):
                proc = helper.launch_ui_window(
                    "revert", ["-q", "--revision", revision] + self.paths
                )
                caller.rescan_after_process_exit(proc, self.paths)

        class AmendAwareConditions(GtkFilesContextMenuConditions):
            def revert(self, data=None):
                # In amend mode every listed file can be reverted to HEAD~1
                if amend and self.path_dict["is_in_a_or_a_working_copy"]:
                    return True
                return super().revert(data)

        vcs_client = create_vcs_instance()
        conditions = AmendAwareConditions(vcs_client, paths)
        callbacks = AmendAwareCallbacks(self, self.base_dir, vcs_client, paths)
        GtkFilesContextMenu(
            self, data, self.base_dir, paths,
            conditions=conditions, callbacks=callbacks
        ).show()

    def on_amend_toggled(self, widget, *args):
        if widget.get_active():
            # Save the current message so we can restore it if unchecked
            self._pre_amend_message = self.message.get_text()
            # Pre-fill with the last commit message
            try:
                head_sha = self.git.client.head()
                commit_obj = self.git.client.repo[head_sha]
                last_message = commit_obj.message.decode("utf-8", errors="replace").strip()
                self.message.set_text(last_message)
            except Exception as e:
                log.exception(e)
        else:
            # Restore the message that was there before amend was checked
            saved = getattr(self, "_pre_amend_message", None)
            if saved is not None:
                self.message.set_text(saved)
                self._pre_amend_message = None
        self.initialize_items()

    def on_ok_clicked(self, widget, data=None):
        new_branch = self.get_widget("new_branch_checkbox").get_active()
        amend = self.get_widget("amend_checkbox").get_active()
        to_widget = self.get_widget("to")

        branch_name = None
        if new_branch:
            branch_name = to_widget.get_text().strip()
            if not branch_name:
                rabbitvcs.ui.dialog.MessageBox(
                    _("You must enter a branch name.")
                )
                return

        items = self.files_table.get_activated_rows(1)
        # Capture pane position while window is still visible (avoids GTK layout drift)
        pos = self.get_widget("pane").get_position()
        if pos > 0:
            self._pane_position = pos
        self.hide()

        if len(items) == 0:
            self.close()
            return

        staged = 0
        for item in items:
            try:
                status = self.vcs.status(item, summarize=False).simple_content_status()
                if status == rabbitvcs.vcs.status.status_missing:
                    self.git.checkout([item])
                    self.git.remove(item)
                else:
                    self.git.stage(item)
                    staged += 1
            except Exception as e:
                log.exception(e)

        ticks = staged + len(items) * 2

        self.action = rabbitvcs.ui.action.GitAction(
            self.git, register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Commit"))
        self.action.append(self.action.set_status, _("Running Commit Command..."))
        self.action.append(helper.save_log_message, self.message.get_text())
        if amend:
            self.action.append(self.git.amend, self.message.get_text())
        else:
            self.action.append(self.git.commit, self.message.get_text())
        if branch_name:
            # TortoiseGit style: create branch and switch to it after the commit
            self.action.append(self.git.branch, branch_name)
            self.action.append(self.git.checkout, [], self.git.revision(branch_name))
        self.action.append(self.action.set_status, _("Completed Commit"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_files_table_toggle_event(self, row, col):
        # Adds path: True/False to the dict
        self.changes[row[1]] = row[col]


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNCommit, rabbitvcs.vcs.VCS_GIT: GitCommit}


def commit_factory(paths, base_dir=None, message=None):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir, message)


if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT

    (options, paths) = main(
        [BASEDIR_OPT, (["-m", "--message"], {"help": "add a commit log message"})],
        usage="Usage: rabbitvcs commit [path1] [path2] ...",
    )

    window = commit_factory(paths, options.base_dir, message=options.message)
    window.register_gtk_quit()
    Gtk.main()
