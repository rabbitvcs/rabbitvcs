from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.vcs.status import Status
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.vcs
import rabbitvcs.ui.action
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
from rabbitvcs.ui import InterfaceView
from gi.repository import Gtk, GObject, Gdk

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

import gi

gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.revert")

_ = gettext.gettext

helper.gobject_threads_init()


log = Log("rabbitvcs.ui.revert")

_ = gettext.gettext


class Revert(InterfaceView, GtkContextMenuCaller):

    TOGGLE_ALL = True

    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "revert", "Revert")

        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.vcs = rabbitvcs.vcs.VCS()
        self.items = []

        self.statuses = self.vcs.statuses_for_revert(paths)
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
            ],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, "", _("Path"), _("Extension")],
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
        )

        self.initialize_items()

    def on_ok_clicked(self, widget):
        return True

    def load(self):
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.statuses)

        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append(
                [True, S(item.path), item.path, helper.get_file_extension(item.path)]
            )

    # Overrides the GtkContextMenuCaller method
    def on_context_menu_command_finished(self):
        self.initialize_items()

    def initialize_items(self):
        """
        Initializes the activated cache and loads the file items in a new thread
        """

        try:
            six.moves._thread.start_new_thread(self.load, ())
        except Exception as e:
            log.exception(e)

    def on_select_all_toggled(self, widget):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        helper.launch_diff_tool(*paths)

    def on_files_table_key_event(self, treeview, event, *args):
        if Gdk.keyval_name(event.keyval) == "Delete":
            self.delete_items(treeview, event)

    def on_files_table_mouse_event(self, treeview, event, *args):
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.show_files_table_popup_menu(treeview, event)

    def show_files_table_popup_menu(self, treeview, event):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, event, self.base_dir, paths).show()


class SVNRevert(Revert):
    def __init__(self, paths, base_dir=None):
        Revert.__init__(self, paths, base_dir)

        self.svn = self.vcs.svn()

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return
        self.hide()

        self.action = rabbitvcs.ui.action.SVNAction(
            self.vcs.svn(), register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Revert"))
        self.action.append(self.action.set_status, _("Running Revert Command..."))
        self.action.append(self.vcs.svn().revert, items, recurse=True)
        self.action.append(self.action.set_status, _("Completed Revert"))
        self.action.append(self.action.finish)
        self.action.schedule()


class GitRevert(Revert):
    def __init__(self, paths, base_dir=None):
        Revert.__init__(self, paths, base_dir)

        self.git = self.vcs.git(self.paths[0])

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return
        self.hide()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git, register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Revert"))
        self.action.append(self.action.set_status, _("Running Revert Command..."))
        self.action.append(self.git.checkout, items)
        self.action.append(self.action.set_status, _("Completed Revert"))
        self.action.append(self.action.finish)
        self.action.schedule()


class SVNRevertQuiet(object):
    def __init__(self, paths, base_dir=None):
        self.vcs = rabbitvcs.vcs.VCS()
        self.action = rabbitvcs.ui.action.SVNAction(self.vcs.svn(), run_in_thread=False)

        self.action.append(self.vcs.svn().revert, paths)
        self.action.schedule()


class GitRevertQuiet(object):
    def __init__(self, paths, base_dir=None):
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(paths[0])
        self.action = rabbitvcs.ui.action.GitAction(self.git, run_in_thread=False)

        self.action.append(self.git.checkout, paths)
        self.action.schedule()


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNRevert, rabbitvcs.vcs.VCS_GIT: GitRevert}

quiet_classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNRevertQuiet,
    rabbitvcs.vcs.VCS_GIT: GitRevertQuiet,
}


def revert_factory(classes_map, paths, base_dir=None):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)


if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT, QUIET_OPT

    (options, paths) = main(
        [BASEDIR_OPT, QUIET_OPT], usage="Usage: rabbitvcs revert [path1] [path2] ..."
    )

    if options.quiet:
        revert_factory(quiet_classes_map, paths)
    else:
        window = revert_factory(classes_map, paths, options.base_dir)
        window.register_gtk_quit()
        Gtk.main()
