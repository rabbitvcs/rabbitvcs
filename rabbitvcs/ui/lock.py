from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.vcs
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
from rabbitvcs.ui.action import SVNAction
from rabbitvcs.ui import GtkTemplateHelper
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

import six.moves._thread
import os

from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.lock")

_ = gettext.gettext

helper.gobject_threads_init()


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/lock.xml")
class LockWidget(Gtk.Grid):
    __gtype_name__ = "LockWidget"

    files_table = Gtk.Template.Child()
    message = Gtk.Template.Child()
    previous_messages = Gtk.Template.Child()
    status = Gtk.Template.Child()
    steal_locks = Gtk.Template.Child()
    select_all = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

class SVNLock(GtkTemplateHelper, GtkContextMenuCaller):
    """
    Provides an interface to lock any number of files in a working copy.

    """

    def __init__(self, paths, base_dir):
        """
        @type:  paths: list
        @param: paths: A list of paths to search for versioned files

        """

        GtkTemplateHelper.__init__(self, "Lock")

        self.widget = LockWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Lock", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.select_all.connect("toggled", self.on_select_all_toggled)
        self.widget.previous_messages.connect("clicked", self.on_previous_messages_clicked)
        # set window properties
        self.window.set_default_size(600, -1)

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.widget.files_table,
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
            ],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), _("Locked")],
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.path_filter,
                    "user_data": {"base_dir": base_dir, "column": 2},
                }
            ],
            callbacks={"mouse-event": self.on_files_table_mouse_event},
        )

        self.message = rabbitvcs.ui.widget.TextView(self.widget.message)

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
        self.widget.status.set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths)
        self.populate_files_table()
        self.widget.status.set_text(_("Found %d item(s)") % len(self.items))

    def populate_files_table(self):
        for item in self.items:

            locked = ""
            if self.svn.is_locked(item.path):
                locked = _("Yes")
            if not self.svn.is_versioned(item.path):
                continue

            self.files_table.append(
                [
                    True,
                    S(item.path),
                    item.path,
                    helper.get_file_extension(item.path),
                    locked,
                ]
            )

    def show_files_table_popup_menu(self):
        paths = self.files_table.get_selected_row_items(1)
        # TODO GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    #
    # UI Signal Callbacks
    #

    def on_ok_clicked(self, widget, data=None):
        steal_locks = self.widget.steal_locks.get_active()
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.window.close()
            return

        message = self.message.get_text()

        self.window.set_visible(False)

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn
        )

        self.action.append(self.action.set_header, _("Get Lock"))
        self.action.append(self.action.set_status, _("Running Lock Command..."))
        self.action.append(helper.save_log_message, message)
        for path in items:
            self.action.append(self.svn.lock, path, message, force=steal_locks)
        self.action.append(self.action.set_status, _("Completed Lock"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def on_files_table_mouse_event(self, gesture, n_press, x, y, pressed):
        if gesture.get_current_button() == 3 and not pressed:
            self.show_files_table_popup_menu()

    def on_select_all_toggled(self, widget, data=None):
        for row in self.files_table.get_items():
            row[0] = self.widget.select_all.get_active()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages(self.window)
        dialog.run(self.on_previous_messages_response)

    def on_previous_messages_response(self, message):
        if message is not None:
            self.message.set_text(S(message).display())


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNLock}


def lock_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)


def on_activate(app):
    from rabbitvcs.ui import main, BASEDIR_OPT

    (options, paths) = main(
        [BASEDIR_OPT], usage="Usage: rabbitvcs lock [path1] [path2] ..."
    )

    widget = lock_factory(paths, options.base_dir)
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
