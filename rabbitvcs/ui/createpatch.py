from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.ui.commit import SVNCommit, GitCommit
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.util
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
from rabbitvcs.ui.action import SVNAction, GitAction
from rabbitvcs.ui import GtkTemplateHelper
from gi.repository import Gtk, GObject, Gio
from rabbitvcs.ui.commit import CommitWidget

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
import tempfile
import shutil
import six.moves._thread

from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.createpatch")

_ = gettext.gettext

helper.gobject_threads_init()


class CreatePatch(GtkTemplateHelper):
    """
    Provides a user interface for the user to create a Patch file

    """

    def __init__(self, paths, base_dir):
        """

        @type  paths:   list of strings
        @param paths:   A list of local paths.

        """

        GtkTemplateHelper.__init__(self, "Commit")

        # Modify the Commit window to what we need for Create Patch
        self.widget = CommitWidget()
        self.window = self.get_window(self.widget)
        self.window.set_title(_("Create Patch"))
        # add dialog buttons
        self.ok = self.add_dialog_button("Create Patch", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.toggle_show_unversioned.connect("toggled", self.on_toggle_show_unversioned_toggled)
        self.widget.toggle_show_all.connect("toggled", self.on_toggle_show_all_toggled)
        self.widget.refresh.connect("clicked", self.on_refresh_clicked)
        # set window properties
        self.window.set_default_size(640, 400)

        self.widget.commit_to_box.set_visible(False)
        self.widget.add_message_box.set_visible(False)

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.activated_cache = {}

        self.common = helper.get_common_directory(paths)

        if not self.vcs.is_versioned(self.common):
            rabbitvcs.ui.dialog.MessageBox(_("The given path is not a working copy"))
            raise SystemExit()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.widget.files_table,
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
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
            },
            flags={"sortable": True, "sort_on": 2},
        )
        self.files_table.allow_multiple()

        self.items = None
        self.initialize_items()

    #
    # Helper functions
    #

    def choose_patch_path(self, callback):
        dialog = Gtk.FileChooserNative.new(
            title=_("Create Patch"), parent=None, action=Gtk.FileChooserAction.SAVE
        )
        dir = helper.get_common_directory(self.paths).replace("file://", "")
        dialog.set_current_folder(
            Gio.File.new_for_path(dir)
        )
        dialog.connect("response", callback)
        dialog.show()


class SVNCreatePatch(CreatePatch, SVNCommit):
    def __init__(self, paths, base_dir=None):
        CreatePatch.__init__(self, paths, base_dir)

        self.svn = self.vcs.svn()

    #
    # Event handlers
    #

    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.window.set_visible(False)

        if len(items) == 0:
            self.window.close()
            return

        self.choose_patch_path(self.choose_patch_path_callback)

    def choose_patch_path_callback(self, dialog, response):
        if response != Gtk.ResponseType.ACCEPT:
            return
        
        path = dialog.get_file().get_path()
        if not path:
            self.window.close()
            return

        items = self.files_table.get_activated_rows(1)
        ticks = len(items) * 2
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Create Patch"))
        self.action.append(self.action.set_status, _("Creating Patch File..."))

        def create_patch_action(patch_path, patch_items, base_dir):
            fileObj = open(patch_path, "w")

            # PySVN takes a path to create its own temp files...
            temp_dir = tempfile.mkdtemp(prefix=rabbitvcs.TEMP_DIR_PREFIX)

            os.chdir(base_dir)

            # Add to the Patch file only the selected items
            for item in patch_items:
                rel_path = helper.get_relative_path(base_dir, item)
                diff_text = self.svn.diff(
                    temp_dir,
                    rel_path,
                    self.svn.revision("base"),
                    rel_path,
                    self.svn.revision("working"),
                )
                fileObj.write(diff_text)

            fileObj.close()

            # Note: if we don't want to ignore errors here, we could define a
            # function that logs failures.
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.action.append(create_patch_action, path, items, self.common)

        self.action.append(self.action.set_status, _("Patch File Created"))
        self.action.append(self.action.finish)
        self.action.schedule()

        # TODO: Open the diff file (meld is going to add support in a future version :()
        # helper.launch_diff_tool(path)

        self.window.close()


class GitCreatePatch(CreatePatch, GitCommit):
    def __init__(self, paths, base_dir=None):
        CreatePatch.__init__(self, paths, base_dir)

        self.git = self.vcs.git(paths[0])

    #
    # Event handlers
    #

    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.window.set_visible(False)

        if len(items) == 0:
            self.window.close()
            return

        self.choose_patch_path(self.choose_patch_path_callback)

    def choose_patch_path_callback(self, dialog, response):
        if response != Gtk.ResponseType.ACCEPT:
            return

        path = dialog.get_file().get_path()
        if not path:
            self.window.close()
            return

        items = self.files_table.get_activated_rows(1)
        ticks = len(items) * 2
        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Create Patch"))
        self.action.append(self.action.set_status, _("Creating Patch File..."))

        def create_patch_action(patch_path, patch_items, base_dir):
            fileObj = open(patch_path, "w")

            # PySVN takes a path to create its own temp files...
            temp_dir = tempfile.mkdtemp(prefix=rabbitvcs.TEMP_DIR_PREFIX)

            os.chdir(base_dir)

            # Add to the Patch file only the selected items
            for item in patch_items:
                rel_path = helper.get_relative_path(base_dir, item)
                diff_text = self.git.diff(
                    rel_path,
                    self.git.revision("HEAD"),
                    rel_path,
                    self.git.revision("WORKING"),
                )
                fileObj.write(diff_text)

            fileObj.close()

            # Note: if we don't want to ignore errors here, we could define a
            # function that logs failures.
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.action.append(create_patch_action, path, items, self.common)

        self.action.append(self.action.set_status, _("Patch File Created"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()


classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNCreatePatch,
    rabbitvcs.vcs.VCS_GIT: GitCreatePatch,
}


def createpatch_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)



def on_activate(app):
    from rabbitvcs.ui import main, BASEDIR_OPT

    (options, paths) = main(
        [BASEDIR_OPT], usage="Usage: rabbitvcs createpatch [path1] [path2] ..."
    )

    widget = createpatch_factory(paths, options.base_dir)
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)

