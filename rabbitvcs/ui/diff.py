from __future__ import absolute_import
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
from shutil import rmtree
import tempfile

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, Gdk, GLib
sa.restore()

from rabbitvcs import TEMP_DIR_PREFIX
from rabbitvcs.ui import InterfaceNonView
import rabbitvcs.vcs
from rabbitvcs.ui.action import SVNAction, GitAction
from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.diff")

from rabbitvcs import gettext
_ = gettext.gettext

class Diff(InterfaceNonView):
    def __init__(self, path1, revision1=None, path2=None, revision2=None,
            sidebyside=False):
        InterfaceNonView.__init__(self)

        self.vcs = rabbitvcs.vcs.VCS()

        self.path1 = path1
        self.path2 = path2
        self.sidebyside = sidebyside

        self.temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)

        if path2 is None:
            self.path2 = path1

        self.dialog = None

    def launch(self):
        try:
            if self.sidebyside:
                self.launch_sidebyside_diff()
            else:
                self.launch_unified_diff()
        finally:
            self.stop_loading()

    def _build_export_path(self, index, revision, path):
        dest = helper.get_tmp_path("rabbitvcs-%s-%s-%s" % (str(index), str(revision)[:5], os.path.basename(path)))
        if os.path.exists(dest):
            if os.path.isdir(dest):
                rmtree(dest, ignore_errors=True)
            else:
                os.remove(dest)

        return dest

    def start_loading(self):
        self.dialog = rabbitvcs.ui.dialog.Loading()
        self.dialog.run()

    def stop_loading(self):

        # Sometimes the launching will be too fast, and the dialog we're trusted with
        # cleaning up, may not even have been created!
        while self.dialog == None:
            # Wait for dialog's creation.
            pass

        self.dialog.close()
        self.dialog = None

class SVNDiff(Diff):
    def __init__(self, path1, revision1=None, path2=None, revision2=None,
            sidebyside=False):
        Diff.__init__(self, path1, revision1, path2, revision2, sidebyside)

        self.svn = self.vcs.svn()

        self.revision1 = self.get_revision_object(revision1, "base")
        self.revision2 = self.get_revision_object(revision2, "working")

        GLib.idle_add(self.launch)
        self.start_loading()

    def get_revision_object(self, value, default):
        # If value is a rabbitvcs Revision object, return it
        if hasattr(value, "is_revision_object"):
            return value

        # If value is None, use the default
        if value is None:
            return self.svn.revision(default)

        # If the value is an integer number, return a numerical revision object
        # otherwise, a string revision value has been passed, use that as "kind"
        try:
            value = int(value)
            return self.svn.revision("number", value)
        except ValueError:
            # triggered when passed a string
            return self.svn.revision(value)

    def launch_unified_diff(self):
        """
        Launch diff as a unified diff in a text editor or .diff viewer

        """

        action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )

        diff_text = action.run_single(
            self.svn.diff,
            self.temp_dir,
            self.path1,
            self.revision1,
            self.path2,
            self.revision2
        )
        if diff_text is None:
            diff_text = ""

        fh = tempfile.mkstemp("-rabbitvcs-" + str(self.revision1) + "-" + str(self.revision2) + ".diff")
        os.write(fh[0], S(diff_text).bytes())
        os.close(fh[0])
        helper.open_item(fh[1])

    def launch_sidebyside_diff(self):
        """
        Launch diff as a side-by-side comparison using our comparison tool

        """

        action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )

        if self.revision1.kind == "working":
            dest1 = self.path1
        else:
            dest1 = self._build_export_path(1, self.revision1, self.path1)
            action.run_single(
                self.svn.export,
                self.path1,
                dest1,
                self.revision1
            )
            action.stop_loader()

        if self.revision2.kind == "working":
            dest2 = self.path2
        else:
            dest2 = self._build_export_path(2, self.revision2, self.path2)
            action.run_single(
                self.svn.export,
                self.path2,
                dest2,
                self.revision2
            )
            action.stop_loader()

        helper.launch_diff_tool(dest1, dest2)

class GitDiff(Diff):
    def __init__(self, path1, revision1=None, path2=None, revision2=None,
            sidebyside=False):
        Diff.__init__(self, path1, revision1, path2, revision2, sidebyside)

        self.git = self.vcs.git(path1)

        self.revision1 = self.get_revision_object(revision1, "HEAD")
        self.revision2 = self.get_revision_object(revision2, "WORKING")

        GLib.idle_add(self.launch)
        self.start_loading()

    def get_revision_object(self, value, default):
        # If value is a rabbitvcs Revision object, return it
        if hasattr(value, "is_revision_object"):
            return value

        value_to_pass = value
        if not value_to_pass:
            value_to_pass = default

        # triggered when passed a string
        return self.git.revision(value_to_pass)

    def save_diff_to_file(self, path, data):
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        if not data:
            data = ""

        file = open(path, "wb")
        try:
            try:
                file.write(S(data).bytes())
            except Exception as e:
                log.exception(e)
        finally:
            file.close()

    def launch_unified_diff(self):
        """
        Launch diff as a unified diff in a text editor or .diff viewer

        """

        action = GitAction(
            self.git,
            notification=False,
            run_in_thread=False
        )

        diff_text = action.run_single(
            self.git.diff,
            self.path1,
            self.revision1,
            self.path2,
            self.revision2
        )
        if diff_text is None:
            diff_text = ""

        fh = tempfile.mkstemp("-rabbitvcs-" + str(self.revision1)[:5] + "-" + str(self.revision2)[:5] + ".diff")
        os.write(fh[0], S(diff_text).bytes())
        os.close(fh[0])
        helper.open_item(fh[1])

    def launch_sidebyside_diff(self):
        """
        Launch diff as a side-by-side comparison using our comparison tool

        """

        action = GitAction(
            self.git,
            notification=False,
            run_in_thread=False
        )

        if self.revision1.kind != "WORKING":
            dest1 = self._build_export_path(1, self.revision1, self.path1)
            self.save_diff_to_file(dest1, action.run_single(
                self.git.show,
                self.path1,
                self.revision1
            ))
        else:
            dest1 = self.path1

        if self.revision2.kind != "WORKING":
            dest2 = self._build_export_path(2, self.revision2, self.path2)
            self.save_diff_to_file(dest2, action.run_single(
                self.git.show,
                self.path2,
                self.revision2
            ))
        else:
            dest2 = self.path2

        helper.launch_diff_tool(dest1, dest2)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNDiff,
    rabbitvcs.vcs.VCS_GIT: GitDiff
}

def diff_factory(vcs, path1, revision_obj1, path2=None, revision_obj2=None, sidebyside=False):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path1)
        vcs = guess["vcs"]

    return classes_map[vcs](path1, revision_obj1, path2, revision_obj2, sidebyside)


if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT
    (options, args) = main([
        (["-s", "--sidebyside"], {
            "help":     _("View diff as side-by-side comparison"),
            "action":   "store_true",
            "default":  False
        }), VCS_OPT],
        usage="Usage: rabbitvcs diff [url1@rev1] [url2@rev2]"
    )

    pathrev1 = helper.parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = helper.parse_path_revision_string(args.pop(0))

    diff_factory(options.vcs, pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1], sidebyside=options.sidebyside)
