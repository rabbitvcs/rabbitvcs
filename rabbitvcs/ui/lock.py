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

import six.moves._thread

import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import SVNAction
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.vcs
from rabbitvcs.util import helper
from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.lock")

from rabbitvcs import gettext
_ = gettext.gettext

helper.gobject_threads_init()

class SVNLock(InterfaceView, GtkContextMenuCaller):
    """
    Provides an interface to lock any number of files in a working copy.

    """

    def __init__(self, paths, base_dir):
        """
        @type:  paths: list
        @param: paths: A list of paths to search for versioned files

        """

        InterfaceView.__init__(self, "lock", "Lock")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [GObject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH, GObject.TYPE_STRING,
                GObject.TYPE_STRING],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"),
                _("Locked")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 1
                }
            }],
            callbacks={
                "mouse-event":   self.on_files_table_mouse_event
            }
        )

        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
        )

        self.items = None
        self.initialize_items()

    #
    # Helper functions
    #

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

    def load(self):
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths)
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))

    def populate_files_table(self):
        for item in self.items:

            locked = ""
            if self.svn.is_locked(item.path):
                locked = _("Yes")
            if not self.svn.is_versioned(item.path):
                continue

            self.files_table.append([
                True,
                item.path,
                helper.get_file_extension(item.path),
                locked
            ])

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    #
    # UI Signal Callbacks
    #

    def on_ok_clicked(self, widget, data=None):
        steal_locks = self.get_widget("steal_locks").get_active()
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        message = self.message.get_text()

        self.hide()

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Get Lock"))
        self.action.append(self.action.set_status, _("Running Lock Command..."))
        self.action.append(helper.save_log_message, message)
        for path in items:
            self.action.append(
                self.svn.lock,
                path,
                message,
                force=steal_locks
            )
        self.action.append(self.action.set_status, _("Completed Lock"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    def on_select_all_toggled(self, widget, data=None):
        for row in self.files_table.get_items():
            row[0] = self.get_widget("select_all").get_active()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(S(message).display())



classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNLock
}

def lock_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs lock [path1] [path2] ..."
    )

    window = lock_factory(paths, options.base_dir)
    window.register_gtk_quit()
    Gtk.main()
