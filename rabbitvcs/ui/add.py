from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.vcs.status import Status
from rabbitvcs.util.log import Log
import rabbitvcs.vcs
from rabbitvcs.util.strings import S
import rabbitvcs.ui.action
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
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

import os
import six.moves._thread
from time import sleep
from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.add")

_ = gettext.gettext

helper.gobject_threads_init()


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/add.xml")
class AddWidget(Gtk.Box):
    __gtype_name__ = "AddWidget"

    select_all = Gtk.Template.Child()
    show_ignored = Gtk.Template.Child()
    files_table = Gtk.Template.Child()
    status = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)

class Add(GtkTemplateHelper, GtkContextMenuCaller):
    """
    Provides an interface for the user to add unversioned files to a
    repository.  Also, provides a context menu with some extra functionality.

    Send a list of paths to be added

    """

    TOGGLE_ALL = True

    def __init__(self, paths, base_dir=None):
        GtkTemplateHelper.__init__(self, "Add")

        self.widget = AddWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Add", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.select_all.connect("toggled", self.on_select_all_toggled)
        self.widget.show_ignored.connect("toggled", self.on_show_ignored_toggled)
        # set window properties
        self.window.set_default_size(450, 300)

        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.vcs = rabbitvcs.vcs.VCS()
        self.items = []
        self.show_ignored = False

        # TODO Remove this when there is svn support
        for path in paths:
            if rabbitvcs.vcs.guess(path)["vcs"] == rabbitvcs.vcs.VCS_SVN:
                self.widget.show_ignored.set_sensitive(False)

        columns = [
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
            ],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, "", _("Path"), _("Extension")],
        ]

        self.setup(self.window, columns)

        self.files_table = rabbitvcs.ui.widget.Table(
            self.widget.files_table,
            columns[0],
            columns[1],
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

    def setup(self, window, columns):
        self.statuses = self.vcs.statuses_for_add(self.paths)

    #
    # Helpers
    #

    def load(self):
        status = self.widget.status
        helper.run_in_main_thread(status.set_text, _("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.statuses)

        if self.show_ignored:
            for path in self.paths:
                # TODO Refactor
                # TODO SVN support
                # TODO Further fix ignore patterns
                if rabbitvcs.vcs.guess(path)["vcs"] == rabbitvcs.vcs.VCS_GIT:
                    git = self.vcs.git(path)
                    for ignored_path in git.client.get_all_ignore_file_paths(path):
                        should_add = True
                        for item in self.items:
                            if item.path == os.path.realpath(ignored_path):
                                should_add = False

                        if should_add:
                            self.items.append(
                                Status(os.path.realpath(ignored_path), "unversioned")
                            )

        self.populate_files_table()
        helper.run_in_main_thread(
            status.set_text, _("Found %d item(s)") % len(self.items)
        )

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append(
                [True, S(item.path), item.path, helper.get_file_extension(item.path)]
            )

    def toggle_ignored(self):
        self.show_ignored = not self.show_ignored
        self.initialize_items()

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

    def delete_items(self):
        paths = self.files_table.get_selected_row_items(1)
        if len(paths) > 0:
            proc = helper.launch_ui_window("delete", paths)
            self.rescan_after_process_exit(proc, paths)

    #
    # UI Signal Callbacks
    #

    def on_select_all_toggled(self, widget):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_show_ignored_toggled(self, widget):
        self.toggle_ignored()

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        helper.launch_diff_tool(*paths)

    def on_files_table_key_event(self, controller, keyval, keycode, state, pressed):
        if not pressed and Gdk.keyval_name(keyval) == "Delete":
            self.delete_items()

    def on_files_table_mouse_event(self, gesture, n_press, x, y, pressed):
        if gesture.get_current_button() == 3 and not pressed:
            # self.show_files_table_popup_menu(treeview, event) todo
            pass

    def show_files_table_popup_menu(self, treeview, event):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, event, self.base_dir, paths).show()


class SVNAdd(Add):
    def __init__(self, paths, base_dir=None):
        Add.__init__(self, paths, base_dir)

        self.svn = self.vcs.svn()

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        self.window.set_visible(False)

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn
        )
        self.action.append(self.action.set_header, _("Add"))
        self.action.append(self.action.set_status, _("Running Add Command..."))
        self.action.append(self.svn.add, items)
        self.action.append(self.action.set_status, _("Completed Add"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()


class GitAdd(Add):
    def __init__(self, paths, base_dir=None):
        Add.__init__(self, paths, base_dir)

        self.git = self.vcs.git(paths[0])

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        self.window.set_visible(False)

        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )
        self.action.append(self.action.set_header, _("Add"))
        self.action.append(self.action.set_status, _("Running Add Command..."))
        self.action.append(self.git.add, items)
        self.action.append(self.action.set_status, _("Completed Add"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNAdd, rabbitvcs.vcs.VCS_GIT: GitAdd}


def add_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)


class AddQuiet(object):
    def __init__(self, paths):
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
        self.action = rabbitvcs.ui.action.SVNAction(self.svn)

        self.action.append(self.svn.add, paths)
        self.action.schedule()


def on_activate(app):
    from rabbitvcs.ui import main, BASEDIR_OPT, QUIET_OPT

    (options, paths) = main(
        [BASEDIR_OPT, QUIET_OPT], usage="Usage: rabbitvcs add [path1] [path2] ..."
    )

    if options.quiet:
        AddQuiet(paths)
    else:
        # Add(paths, options.base_dir)
        widget = add_factory(paths, options.base_dir)
        app.add_window(widget.window)
        widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
