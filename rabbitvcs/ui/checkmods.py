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
import threading

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceView
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, \
    GtkContextMenuCaller, GtkFilesContextMenuConditions, GtkContextMenu
from rabbitvcs.util.contextmenuitems import MenuItem, MenuUpdate, \
    MenuSeparator
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
from rabbitvcs.util.log import Log
from rabbitvcs.util.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.checkmods")

from rabbitvcs import gettext
_ = gettext.gettext

helper.gobject_threads_init()

class SVNCheckForModifications(InterfaceView):
    """
    Provides a way for the user to see what files have been changed on the
    repository.

    """

    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "checkmods", "CheckMods")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
        self.notebook = self.get_widget("notebook")

        self.local_mods = SVNCheckLocalModifications(self, \
                                                         self.vcs, \
                                                         self.paths, \
                                                         self.base_dir)
        self.remote_mods = SVNCheckRemoteModifications(self, \
                                                           self.vcs, \
                                                           self.paths, \
                                                           self.base_dir)

        self.remote_refreshed = False

        self.load()

    def on_refresh_clicked(self, widget):
        if self.notebook.get_current_page() == 0:
            self.local_mods.refresh()
        else:
            self.remote_mods.refresh()

    def on_notebook_switch_page(self, page, data, page_num):
        if page_num == 1 and self.remote_refreshed == False:
            self.remote_mods.refresh()
            self.remote_refreshed = True

    #
    # Helper methods
    #

    def load(self):
        self.local_mods.refresh()

class SVNCheckLocalModifications(GtkContextMenuCaller):
    def __init__(self, caller, vcs, paths, base_dir):
        self.caller = caller
        self.vcs = vcs
        self.svn = vcs.svn()
        self.items = None
        self.paths = paths
        self.base_dir = base_dir

        self.files_table = rabbitvcs.ui.widget.Table(
            self.caller.get_widget("local_files_table"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Path"), _("Status"), _("Extension")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 0
                }
            }],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event
            }
        )

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(0)
        self.diff_local(paths[0])

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            paths = self.files_table.get_selected_row_items(0)
            GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    def refresh(self):
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(self.svn.get_items, self.paths, self.svn.STATUSES_FOR_CHECK)
        self.action.append(self.populate_files_table)
        self.action.schedule()

    @gtk_unsafe
    def populate_files_table(self):
        self.files_table.clear()
        self.items = self.action.get_result(0)
        for item in self.items:
            self.files_table.append([
                item.path,
                item.simple_content_status(),
                helper.get_file_extension(item.path)
            ])

    def diff_local(self, path):
        helper.launch_diff_tool(path)

    def on_context_menu_command_finished(self):
        self.refresh()

class SVNCheckRemoteModifications(GtkContextMenuCaller):
    def __init__(self, caller, vcs, paths, base_dir):
        self.caller = caller
        self.vcs = vcs
        self.svn = vcs.svn()
        self.items = None
        self.paths = paths
        self.base_dir = base_dir

        self.files_table = rabbitvcs.ui.widget.Table(
            self.caller.get_widget("remote_files_table"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING,
                GObject.TYPE_STRING, GObject.TYPE_STRING,
                GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Path"), _("Extension"),
                _("Text Status"), _("Property Status"),
                _("Revision"), _("Author")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 0
                }
            }],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event
            }
        )

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(0)
        self.diff_remote(paths[0])

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            paths = self.files_table.get_selected_row_items(0)
            CheckRemoteModsContextMenu(self, data, self.base_dir, self.vcs, paths).show()

    def refresh(self):
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(self.svn.get_remote_updates, self.paths)
        self.action.append(self.populate_files_table)
        self.action.schedule()

    @gtk_unsafe
    def populate_files_table(self):
        self.files_table.clear()
        self.items = self.action.get_result(0)
        for item in self.items:
            revision = -1
            author = ""

            if item.revision is not None:
                revision = item.revision
            if item.author is not None:
                author = item.author

            self.files_table.append([
                item.path,
                helper.get_file_extension(item.path),
                item.remote_content,
                item.remote_metadata,
                str(revision),
                author
            ])

    def diff_remote(self, path):
        from rabbitvcs.ui.diff import SVNDiff

        path_local = path
        path_remote = self.svn.get_repo_url(path_local)

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local,
            None,
            path_remote,
            "HEAD"
        )
        self.action.schedule()

    def on_context_menu_command_finished(self):
        self.refresh()

class MenuViewDiff(MenuItem):
    identifier = "RabbitVCS::View_Diff"
    label = _("View unified diff")
    icon = "rabbitvcs-diff"

class MenuCompare(MenuItem):
    identifier = "RabbitVCS::Compare"
    label = _("Compare side by side")
    icon = "rabbitvcs-compare"

class CheckRemoteModsContextMenuConditions(GtkFilesContextMenuConditions):
    def __init__(self, vcs, paths=[]):
        GtkFilesContextMenuConditions.__init__(self, vcs, paths)

    def update(self, data=None):
        return True

    def view_diff(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

    def compare(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

class CheckRemoteModsContextMenuCallbacks:
    def __init__(self, caller, base_dir, vcs, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.paths = paths

    def update(self, data1=None, data2=None):
        proc = helper.launch_ui_window(
            "update",
            self.paths
        )
        self.caller.rescan_after_process_exit(proc, self.paths)

    def view_diff(self, data1=None, data2=None):
        self.caller.diff_remote(self.paths[0])

    def compare(self, data1=None, data2=None):
        from rabbitvcs.ui.diff import SVNDiff

        path_local = self.paths[0]
        path_remote = self.svn.get_repo_url(path_local)

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local,
            None,
            path_remote,
            "HEAD",
            sidebyside=True
        )
        self.action.schedule()

class CheckRemoteModsContextMenu:
    def __init__(self, caller, event, base_dir, vcs, paths=[]):

        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs = vcs

        self.conditions = CheckRemoteModsContextMenuConditions(self.vcs, paths)
        self.callbacks = CheckRemoteModsContextMenuCallbacks(
            self.caller,
            self.base_dir,
            self.vcs,
            paths
        )

        self.structure = [
            (MenuViewDiff, None),
            (MenuCompare, None),
            (MenuSeparator, None),
            (MenuUpdate, None)
        ]

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNCheckForModifications
}

def checkmods_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)


if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs checkmods [url_or_path]"
    )

    window = checkmods_factory(paths, options.base_dir)
    window.register_gtk_quit()
    Gtk.main()
