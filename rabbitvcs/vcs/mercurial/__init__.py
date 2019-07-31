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

"""
Concrete VCS implementation for Mercurial functionality.
"""
from __future__ import absolute_import

import os.path
from datetime import datetime

from mercurial import commands, ui, hg

from rabbitvcs.util.strings import S

import rabbitvcs.vcs
import rabbitvcs.vcs.status
import rabbitvcs.vcs.log
import rabbitvcs.vcs.mercurial.util
from rabbitvcs.vcs.branch import BranchEntry
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.vcs.mercurial")

from rabbitvcs import gettext
_ = gettext.gettext

class Revision:
    """
    Implements a simple revision object as a wrapper around the gittyup revision
    object.  This allows us to provide a standard interface to the object data.
    """

    def __init__(self, kind, value=None):
        self.kind = kind.upper()
        self.value = value

        if self.kind == "HEAD":
            self.value = "HEAD"

        self.is_revision_object = True

    def __str__(self):
        if self.value:
            return S(self.value)
        return S(self.kind)

    def __unicode__(self):
        return self.__str__().unicode()

    def short(self):
        if self.value:
            return S(self.value)[0:7]
        else:
            return self.kind

    def __repr__(self):
        return self.__str__()

    def primitive(self):
        return self.value

class Mercurial:
    STATUS = {
        "normal":       "C",
        "added":        "A",
        "removed":      "R",
        "modified":     "M",
        "untracked":    "?",
        "missing":      "!"
    }

    STATUS_REVERSE = {
        "C":       "normal",
        "A":        "added",
        "R":      "removed",
        "M":     "modified",
        "?":    "untracked",
        "!":      "missing"
    }

    STATUSES_FOR_REVERT = [
        "missing",
        "modified",
        "removed"
    ]

    STATUSES_FOR_COMMIT = [
        "untracked",
        "missing",
        "modified",
        "added",
        "removed"
    ]

    STATUSES_FOR_STAGE = [
        "untracked"
    ]

    STATUSES_FOR_UNSTAGE = [
        "added"
    ]

    def __init__(self, repo=None):
        self.vcs = rabbitvcs.vcs.VCS_MERCURIAL
        self.interface = "mercurial"

        self.ui = ui.ui()
        self.repository = None
        if repo:
            self.repository_path = repo
            self.repository = hg.repository(self.ui, self.repository_path)

        self.cache = rabbitvcs.vcs.status.StatusCache()

    def set_repository(self, path):
        self.repository_path = path
        self.repository = hg.repository(self.ui, self.repository_path)

    def get_repository(self):
        return self.repository_path

    def find_repository_path(self, path):
        path_to_check = path
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".hg")):
                return path_to_check

            path_to_check = os.path.split(path_to_check)[0]

        return None

    def get_relative_path(self, path):
        if path == self.repository_path:
            return ""

        return rabbitvcs.vcs.mercurial.util.relativepath(self.repository_path, path)

    def get_absolute_path(self, path):
        return os.path.join(self.repository_path, path).rstrip("/")

    def statuses(self, path, recurse=True, invalidate=False):
        mercurial_statuses = self.repository.status(clean=True, unknown=True)

        # the status method returns a series of tuples filled with files matching
        # the statuses below
        tuple_order = ["modified", "added", "removed", "missing", "unknown", "ignored", "clean"]

        # go through each tuple (each of which has a defined status), and
        # generate a flat list of rabbitvcs statuses
        statuses = []
        index = 0
        directories = {}
        for status_tuple in mercurial_statuses:
            content = tuple_order[index]
            for item in status_tuple:
                st_path = self.get_absolute_path(item)

                rabbitvcs_status = rabbitvcs.vcs.status.MercurialStatus({
                    "path": st_path,
                    "content": content
                })
                statuses.append(rabbitvcs_status)

                # determine the statuses of the parent folders
                dir_content = content
                if content in self.STATUSES_FOR_REVERT:
                    dir_content = "modified"

                path_to_check = os.path.dirname(st_path)
                while True:
                    if path_to_check not in directories or directories[path_to_check] not in self.STATUSES_FOR_COMMIT:
                        rabbitvcs_status = rabbitvcs.vcs.status.MercurialStatus({
                            "path": path_to_check,
                            "content": dir_content
                        })
                        statuses.append(rabbitvcs_status)
                        directories[path_to_check] = dir_content

                    if path_to_check == "" or path_to_check == self.repository_path:
                        break

                    path_to_check = os.path.split(path_to_check)[0]

            index += 1

        return statuses

    def status(self, path, summarize=True, invalidate=False):
        all_statuses = self.statuses(path, invalidate=invalidate)

        if summarize:
            path_status = None
            for st in all_statuses:
                if st.path == path:
                    path_status = st
                    break

            if path_status:
                path_status.summary = path_status.single
            else:
                path_status = rabbitvcs.vcs.status.Status.status_unknown(path)
        else:
            path_status = all_statuses[0]

        return path_status

    def is_working_copy(self, path):
        if (os.path.isdir(path) and
                os.path.isdir(os.path.join(path, ".hg"))):
            return True
        return False

    def is_in_a_or_a_working_copy(self, path):
        if self.is_working_copy(path):
            return True

        return (self.find_repository_path(os.path.split(path)[0]) != "")

    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True

        st = self.status(path)
        try:
            return st.is_versioned()
        except Exception as e:
            log.error(e)
            return False

        return False

    def is_locked(self, path):
        return False

    def get_items(self, paths, statuses=[]):
        if paths is None:
            return []

        items = []
        for path in paths:
            st = self.statuses(path, invalidate=True)
            for st_item in st:
                if st_item.content == "modified" and os.path.isdir(st_item.path):
                    continue

                if st_item.content in statuses or len(statuses) == 0:
                    items.append(st_item)

        return items

    #
    # Actions
    #
