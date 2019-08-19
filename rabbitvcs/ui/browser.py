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

import os.path
import six
import six.moves._thread
from datetime import datetime

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceView
from rabbitvcs.util.contextmenu import GtkContextMenu, GtkContextMenuCaller, \
    GtkFilesContextMenuConditions
from rabbitvcs.util.contextmenuitems import *
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.vcs
from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log
from rabbitvcs.util.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.browser")

from rabbitvcs import gettext
_ = gettext.gettext

helper.gobject_threads_init()

class SVNBrowser(InterfaceView, GtkContextMenuCaller):
    def __init__(self, url):
        InterfaceView.__init__(self, "browser", "Browser")

        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.url = ""
        if self.svn.is_in_a_or_a_working_copy(url):
            action = rabbitvcs.ui.action.SVNAction(self.svn, notification=False, run_in_thread=False)
            self.url = S(action.run_single(self.svn.get_repo_url, url))
        elif self.svn.is_path_repository_url(url):
            self.url = S(url)

        self.urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("urls"),
            helper.get_repository_paths()
        )
        if self.url:
            self.urls.set_child_text(helper.unquote_url(self.url))

        # We must set a signal handler for the Gtk.Entry inside the combobox
        # Because glade will not retain that information
        self.urls.set_child_signal(
            "key-release-event",
            self.on_urls_key_released
        )

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.svn,
            url_combobox=self.urls,
            expand=True
        )

        self.items = []
        self.list_table = rabbitvcs.ui.widget.Table(
            self.get_widget("list"),
            [rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH, GObject.TYPE_INT,
                GObject.TYPE_INT, GObject.TYPE_STRING, GObject.TYPE_FLOAT],
            ["", _("Path"), _("Revision"), _("Size"), _("Author"), _("Date")],
            filters=[{
                "callback": self.file_filter,
                "user_data": {
                    "column": 1
                }
            },{
                "callback": self.revision_filter,
                "user_data": {
                    "column": 2
                }
            },{
                "callback": self.size_filter,
                "user_data": {
                    "column": 3
                }
            },{
                "callback": self.date_filter,
                "user_data": {
                    "column": 5
                }
            }],
            filter_types=[GObject.TYPE_STRING, GObject.TYPE_STRING,
                GObject.TYPE_STRING, GObject.TYPE_STRING,
                GObject.TYPE_STRING, GObject.TYPE_STRING],
            callbacks={
                "file-column-callback": self.file_column_callback,
                "row-activated": self.on_row_activated,
                "mouse-event":   self.on_list_table_mouse_event
            },
            flags={
                "sortable": True
            }
        )

        self.url_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.repo_root_url = None

        if self.url:
            helper.save_repository_path(url)
            self.load()

    def load(self):
        self.url = self.urls.get_active_text()
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        revision = self.revision_selector.get_revision_object()
        self.action.append(
                        self.svn.list,
                        helper.quote_url(self.url),
                        revision=revision, recurse=False)
        self.action.append(self.init_repo_root_url)
        self.action.append(self.populate_table, 0)
        self.action.schedule()

    @gtk_unsafe
    def populate_table(self, item_index=0):
        self.list_table.clear()
        self.items = self.action.get_result(item_index)
        self.items.sort(key = self.sort_files_key)

        self.list_table.append([S(".."), "..", 0, 0, "", 0])
        for item,locked in self.items[1:]:
            self.list_table.append([
                S(item.path),
                item.path,
                item.created_rev.number,
                item.size,
                item.last_author,
                item.time
            ])

    def init_repo_root_url(self):
        if self.repo_root_url is None and self.svn.is_in_a_or_a_working_copy(self.url):
            action = rabbitvcs.ui.action.SVNAction(self.svn, notification=False, run_in_thread=False)
            self.repo_root_url = action.run_single(self.svn.get_repo_root_url, self.url)

    def on_refresh_clicked(self, widget):
        helper.save_repository_path(self.urls.get_active_text())
        self.load()

    def create_folder(self, where):
        from rabbitvcs.ui.dialog import NewFolder
        dialog = NewFolder()
        result = dialog.run()
        if result is None:
            return

        (folder_name, log_message) = result
        new_url = where.rstrip("/") + "/" + folder_name

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(self.svn.mkdir, new_url, log_message)
        self.action.append(self.svn.list, where, recurse=False)
        self.action.append(self.populate_table, 1)
        self.action.schedule()

    def on_create_folder_here_clicked(self, widget):
        self.create_folder(self.urls.get_active_text())

    def on_row_activated(self, treeview, data, col):
        path = self.list_table.get_selected_row_items(0)[0]
        if path == "..":
            path = self.url.split("/")[0:-1]
            self.url = "/".join(path)
        else:
            self.url = path

        if self.file_column_callback(self.url) == "dir" or self.url != path:
            self.urls.set_child_text(helper.unquote_url(self.url))
            self.load()
        else:
            self._open([self.url])

    def on_urls_key_released(self, widget, data, userdata):
        if Gdk.keyval_name(data.keyval) == "Return":
            helper.save_repository_path(self.urls.get_active_text())
            self.load()

    def file_column_callback(self, filename):
        """
        Determine the node kind (dir or file) from our retrieved items list
        """

        filename = S(filename).unicode()
        if filename == six.u(".."):
            return "dir"

        for item,locked in self.items:
            if S(item.path).unicode() == filename:
                return self.svn.NODE_KINDS_REVERSE[item.kind]
        return None

    def sort_files_key(self, x):
        """
        Return a key to sort the browser listing so that folders are
        on top and then sort alphabetically.
        """
        kind = self.svn.NODE_KINDS_REVERSE[x[0].kind] != "dir"
        return (kind, x[0].repos_path)

    def file_filter(self, row, column, user_data=None):
        """
        Table filter to just show the basename of the item path
        """

        if row[column]:
            return os.path.basename(row[column])

        return row[column]

    def size_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item size to a "pretty" filesize
        """

        if self.file_column_callback(row[0]) == "file":
            return helper.pretty_filesize(int(row[column]))

        return ""

    def revision_filter(self, row, column, user_data=None):
        """
        Table filter to convert revision to a desired format
        """

        if row[0] == "..":
            return ""

        return row[column]

    def date_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item date to something readable
        """

        if row[0] == "..":
            return ""

        if row[column]:
            change_time = datetime.fromtimestamp(float(row[column]))
            return helper.format_datetime(change_time)

        return str(row[column])

    def on_list_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_list_table_popup_menu(treeview, data)

    def show_list_table_popup_menu(self, treeview, data):
        paths = self.list_table.get_selected_row_items(0)
        if len(paths) == 0:
            paths.append(self.url)

        BrowserContextMenu(self, data, None, self.vcs, paths).show()

    def set_url_clipboard(self, url):
        self.url_clipboard.set_text(S(url).display(), -1)

    def get_repo_root_url(self):
        return self.repo_root_url

    def get_url(self):
        return self.urls.get_active_text()

    def _open(self, paths):
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )

        exported_paths = []
        for path in paths:
            export_path = helper.get_tmp_path(os.path.basename(paths[0]))
            exported_paths.append(export_path)
            self.action.append(self.svn.export, paths[0],
                export_path, revision=self.revision_selector.get_revision_object())

        for path in exported_paths:
            self.action.append(helper.open_item, path)

        self.action.schedule()

class SVNBrowserDialog(SVNBrowser):
    def __init__(self, path, callback=None):
        """
        Override the normal Browser class so that we can hide the window as we need.
        Also, provide a callback for when the close button is clicked so that we
        can get some desired data.
        """

        self.callback = callback

        SVNBrowser.__init__(self, path)

        self.change_button("close", _("_Select"), "rabbitvcs-ok")

    def on_destroy(self, widget):
        pass

    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.callback is not None:
            path = self.urls.get_active_text()
            selected = self.list_table.get_selected_row_items(0)
            if len(selected) > 0:
                path = selected[0]
            self.callback(path)




class MenuCreateRepositoryFolder(MenuItem):
    identifier = "RabbitVCS::Create_Repository_Folder"
    label = _("Create folder...")
    icon = "folder-new"

class MenuBrowserCopyTo(MenuItem):
    identifier = "RabbitVCS::Browser_Copy_To"
    label = _("Copy to...")
    icon = "edit-copy"

class MenuBrowserCopyUrlToClipboard(MenuItem):
    identifier = "RabbitVCS::Browser_Copy_Url_To_Clipboard"
    label = _("Copy URL to clipboard")
    icon = "rabbitvcs-asynchronous"

class MenuBrowserMoveTo(MenuItem):
    identifier = "RabbitVCS::Browser_Move_To"
    label = _("Move to...")
    icon = "document-save-as"


class BrowserContextMenuConditions(GtkFilesContextMenuConditions):
    def __init__(self, vcs, paths, caller):
        GtkFilesContextMenuConditions.__init__(self, vcs, paths)
        self.caller = caller

    def is_parent_selected(self):
        for path in self.paths:
            if os.path.split(path.rstrip("/"))[1] == "..":
                return True
        return False

    def _open(self, data1=None, data2=None):
        return True

    def show_log(self, data1=None, data2=None):
        return True

    def annotate(self, data1=None, data2=None):
        if self.path_dict["length"] == 1:
            return (self.caller.file_column_callback(self.paths[0]) == "file")

        return False

    def checkout(self, data1=None, data2=None):
        return True

    def export(self, data1=None, data2=None):
        return True

    def rename(self, data1=None):
        if self.path_dict["length"] > 1 or self.is_parent_selected():
            return False
        revision = self.caller.revision_selector.get_revision_object()
        return revision.kind == "head"

    def delete(self, data1=None, data2=None):
        revision = self.caller.revision_selector.get_revision_object()
        return revision.kind == "head" and not self.is_parent_selected()

    def create_repository_folder(self, data1=None):
        if self.path_dict["length"] == 1 and not self.is_parent_selected():
            return (self.caller.file_column_callback(self.paths[0]) == "dir")

        return (self.path_dict["length"] == 0)

    def browser_copy_to(self, data1=None, data2=None):
        return not self.is_parent_selected()

    def browser_copy_url_to_clipboard(self, data1=None, data2=None):
        return (self.path_dict["length"] == 1)

    def browser_move_to(self, data1=None, data2=None):
        revision = self.caller.revision_selector.get_revision_object()
        return revision.kind == "head" and not self.is_parent_selected()

class BrowserContextMenuCallbacks:
    def __init__(self, caller, base_dir, vcs, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.paths = paths
        self.guess = rabbitvcs.vcs.VCS_SVN

    def __update_browser_url(self, url):
        # Make sure the Browser variables are updated with the new path
        self.caller.urls.set_child_text(url)
        self.caller.url = url

    def __get_browser_revision(self):
        return self.caller.revision_selector.get_revision_object()

    def __generate_sources_list(self):
        # Generates a list of tuples where the first element is a path and the
        # second element is a primitive revision object
        # Used for the copy_to menu item
        sources = []
        for path in self.paths:
            sources.append((path,self.__get_browser_revision().primitive()))

        return sources

    def _open(self, data=None, user_data=None):
        self.caller._open(self.paths)

    def show_log(self, data=None, user_data=None):
        helper.launch_ui_window("log", ["--vcs=%s" % self.guess, self.paths[0]])

    def annotate(self, data=None, user_data=None):
        urlrev = self.paths[0]
        revision = self.__get_browser_revision()
        if revision.kind == "number":
            urlrev += "@" + revision.value
        helper.launch_ui_window("annotate", ["--vcs=%s" % self.guess, urlrev])

    def checkout(self, data=None, user_data=None):
        args = [self.paths[0]]
        revision = self.__get_browser_revision()
        if revision.kind == "number":
            args = ["-r", revision.value] + args
        helper.launch_ui_window("checkout", args)

    def export(self, data=None, user_data=None):
        args = [self.paths[0]]
        revision = self.__get_browser_revision()
        if revision.kind == "number":
            args = ["-r", revision.value] + args
        helper.launch_ui_window("export", args)

    def rename(self, data=None, user_data=None):
        (base, filename) = os.path.split(self.paths[0])

        from rabbitvcs.ui.dialog import OneLineTextChange
        dialog = OneLineTextChange(_("Rename"), _("New Name:"), filename)
        (result, new_name) = dialog.run()

        if result == Gtk.ResponseType.CANCEL:
            return

        new_url = base.rstrip("/") + "/" + new_name
        path_to_refresh = self.caller.get_url()
        if self.paths[0] == path_to_refresh:
            path_to_refresh = new_url
            self.__update_browser_url(path_to_refresh)

        self.caller.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.caller.action.append(self.svn.move, self.paths[0], new_url)
        self.caller.action.append(self.svn.list, path_to_refresh, recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.schedule()

    def delete(self, data=None, user_data=None):
        path_to_refresh = self.caller.get_url()
        if self.paths[0] == path_to_refresh:
            # If the deleted path is the same as the current path, go to the parent
            path_to_refresh = path_to_refresh.split("/")[0:-1]
            path_to_refresh = "/".join(path_to_refresh)

            self.__update_browser_url(path_to_refresh)

        self.caller.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.caller.action.append(self.svn.remove, self.paths)
        self.caller.action.append(self.svn.list, path_to_refresh, recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.schedule()

    def create_repository_folder(self, data=None, user_data=None):
        self.caller.create_folder(self.paths[0])

    def browser_copy_to(self, data=None, user_data=None):
        from rabbitvcs.ui.dialog import OneLineTextChange
        dialog = OneLineTextChange(
            _("Where do you want to copy the selection?"),
            _("New Location:"),
            self.caller.get_url()
        )
        result = dialog.run()
        if result is None:
            return

        (response, new_url) = result
        if response == Gtk.ResponseType.CANCEL:
            return

        sources = self.__generate_sources_list()

        self.caller.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.caller.action.append(self.svn.copy_all, sources, new_url, copy_as_child=True)
        self.caller.action.append(self.svn.list, self.caller.get_url(), recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.schedule()

    def browser_copy_url_to_clipboard(self, data=None, user_data=None):
        self.caller.set_url_clipboard(self.paths[0])

    def browser_move_to(self, data=None, user_data=None):
        from rabbitvcs.ui.dialog import OneLineTextChange
        dialog = OneLineTextChange(
            _("Where do you want to move the selection?"),
            _("New Location:"),
            self.caller.get_url()
        )
        result = dialog.run()
        if result is None:
            return

        (response, new_url) = result
        if response == Gtk.ResponseType.CANCEL:
            return

        self.caller.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.caller.action.append(self.svn.move_all, self.paths, new_url, move_as_child=True)
        self.caller.action.append(self.svn.list, self.caller.get_url(), recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.schedule()

class BrowserContextMenu:
    def __init__(self, caller, event, base_dir, vcs, paths=[]):

        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs = vcs
        self.svn = self.vcs.svn()

        self.conditions = BrowserContextMenuConditions(
            self.vcs,
            paths,
            self.caller
        )
        self.callbacks = BrowserContextMenuCallbacks(
            self.caller,
            self.base_dir,
            self.vcs,
            paths
        )

        self.structure = [
            (MenuOpen, None),
            (MenuSeparator, None),
            (MenuShowLog, None),
            (MenuAnnotate, None),
            (MenuExport, None),
            (MenuCheckout, None),
            (MenuSeparator, None),
            (MenuCreateRepositoryFolder, None),
            (MenuSeparator, None),
            (MenuRename, None),
            (MenuDelete, None),
            (MenuBrowserCopyTo, None),
            (MenuBrowserCopyUrlToClipboard, None),
            (MenuBrowserMoveTo, None)
        ]

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNBrowser,
    rabbitvcs.vcs.VCS_DUMMY: SVNBrowser
}

def browser_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, url) = main(
        usage="Usage: rabbitvcs browser [url]"
    )

    window = browser_factory(url[0])
    window.register_gtk_quit()
    Gtk.main()
