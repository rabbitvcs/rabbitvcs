from __future__ import absolute_import
from __future__ import print_function
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

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk, Pango
sa.restore()

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import GitAction
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

STATE_ADD = 0
STATE_EDIT = 1

class GitRemotes(InterfaceView):
    """
    Provides a UI interface to manage items

    """

    state = STATE_ADD

    def __init__(self, path):
        InterfaceView.__init__(self, "manager", "Manager")
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        self.get_widget("right_side").hide()
        self.get_widget("Manager").set_title(_("Remote Repository Manager"))
        self.get_widget("items_label").set_markup(_("<b>Remote Repositories</b>"))

        self.selected_branch = None
        self.items_treeview = rabbitvcs.ui.widget.Table(
            self.get_widget("items_treeview"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Name"), _("Host")],
            callbacks={
                "mouse-event":   self.on_treeview_mouse_event,
                "key-event":     self.on_treeview_key_event,
                "cell-edited":   self.on_treeview_cell_edited_event
            },
            flags={
                "sortable": False,
                "sort_on": 0,
                "editable": [0,1]
            }
        )

        self.load()

    def load(self):
        self.items_treeview.clear()

        self.remote_list = self.git.remote_list()
        for remote in self.remote_list:
            self.items_treeview.append([remote["name"], remote["host"]])

    def save(self, row, column, data):
        row = int(row)

        if row in self.remote_list:
            remote = self.remote_list[row]

            name = remote["name"]
            if column == 0:
                name = data

            host = remote["host"]
            if column == 1:
                host = data

            if name != remote["name"]:
                self.git.remote_rename(remote["name"], name)

            if host != remote["host"]:
                self.git.remote_set_url(remote["name"], host)

            self.load()
        else:
            (name, host) = self.items_treeview.get_row(row)
            if name and host:
                self.git.remote_add(name, host)
                self.load()

    def on_add_clicked(self, widget):
        self.show_add()

    def on_delete_clicked(self, widget):
        selected = self.items_treeview.get_selected_row_items(0)

        confirm = rabbitvcs.ui.dialog.Confirmation(_("Are you sure you want to delete %s?" % ", ".join(selected)))
        result = confirm.run()

        if result == Gtk.ResponseType.OK or result == True:
            for remote in selected:
                self.git.remote_delete(remote)

            self.load()

    def on_treeview_key_event(self, treeview, data=None):
        if Gdk.keyval_name(data.keyval) in ("Up", "Down", "Return"):
            self.on_treeview_event(treeview, data)

    def on_treeview_mouse_event(self, treeview, data=None):
        self.on_treeview_event(treeview, data)

    def on_treeview_cell_edited_event(self, cell, row, data, column):
        self.items_treeview.set_row_item(row, column, data)
        self.save(row, column, data)

    def on_treeview_event(self, treeview, data):
        selected = self.items_treeview.get_selected_row_items(0)
        if len(selected) > 0:
            if len(selected) == 1:
                self.show_edit(selected[0])
            self.get_widget("delete").set_sensitive(True)

    def show_add(self):
        self.state = STATE_ADD
        self.items_treeview.unselect_all()

        self.items_treeview.append(["", ""])
        self.items_treeview.focus(len(self.remote_list), 0)

    def show_edit(self, remote_name):
        self.state = STATE_EDIT


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs branch-manager path")

    window = GitRemotes(paths[0])
    window.register_gtk_quit()
    Gtk.main()
