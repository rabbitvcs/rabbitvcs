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
from rabbitvcs.ui.log import log_dialog_factory
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
from rabbitvcs.util.strings import S
import rabbitvcs.vcs

from xml.sax import saxutils

from rabbitvcs import gettext
_ = gettext.gettext

STATE_ADD = 0
STATE_EDIT = 1

class GitBranchManager(InterfaceView):
    """
    Provides a UI interface to manage items

    """

    state = STATE_ADD

    def __init__(self, path, revision=""):
        InterfaceView.__init__(self, "manager", "Manager")

        self.path = path

        self.get_widget("right_side").show()
        self.get_widget("Manager").set_size_request(695, -1)
        self.get_widget("Manager").set_title(_("Branch Manager"))
        self.get_widget("items_label").set_markup(_("<b>Branches</b>"))

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)
        self.revision = self.git.revision(revision)

        self.selected_branch = None
        self.items_treeview = rabbitvcs.ui.widget.Table(
            self.get_widget("items_treeview"),
            [rabbitvcs.ui.widget.TYPE_MARKUP],
            [_("Branch")],
            callbacks={
                "mouse-event":   self.on_treeview_mouse_event,
                "key-event":     self.on_treeview_key_event
            }
        )
        self.initialize_detail()
        self.load()

        if self.revision:
            revision_branches = self.git.branch_list(self.revision)
            if revision_branches:
                self.show_edit(revision_branches[0].name)
            else:
                self.show_add()
        else:
            self.show_add()

    def initialize_detail(self):
        self.detail_container = self.get_widget("detail_container")

        self.detail_grid = Gtk.Grid()
        self.detail_grid.set_row_spacing(4)
        self.detail_grid.set_column_spacing(6)
        self.detail_grid.set_hexpand(True)
        row = 0

        # Set up the Branch line
        label = Gtk.Label(label = _("Name:"))
        label.set_properties(xalign=0, yalign=.5)
        self.branch_entry = Gtk.Entry()
        self.branch_entry.set_hexpand(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.branch_entry, 1, row, 2, 1)
        branch_name_row = row
        row = row + 1

        # Set up the Commit-sha line
        label = Gtk.Label(label = _("Start Point:"))
        label.set_properties(xalign=0, yalign=.5)
        self.start_point_entry = Gtk.Entry()
        self.start_point_entry.set_size_request(300, -1)
        self.start_point_entry.set_hexpand(True)
        self.log_dialog_button = Gtk.Button()
        self.log_dialog_button.connect("clicked", self.on_log_dialog_button_clicked)
        image = Gtk.Image()
        image.set_from_icon_name("rabbitvcs-show_log", Gtk.IconSize.SMALL_TOOLBAR)
        self.log_dialog_button.set_image(image)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.start_point_entry, 1, row, 1, 1)
        self.detail_grid.attach(self.log_dialog_button, 2, row, 1, 1)
        start_point_row = row
        row = row + 1

        # Set up the Track line
        self.track_checkbox = Gtk.CheckButton(label = _("Keep old branch's history"))
        self.detail_grid.attach(self.track_checkbox, 1, row, 2, 1)
        track_row = row
        row = row + 1

        # Set up the checkout line
        self.checkout_checkbox = Gtk.CheckButton(label = _("Set as active branch"))
        self.detail_grid.attach(self.checkout_checkbox, 1, row, 2, 1)
        checkout_row = row
        row = row + 1

        # Set up Save button
        self.save_button = Gtk.Button(label=_("Save"))
        self.save_button.set_halign(Gtk.Align.START)
        self.save_button.connect("clicked", self.on_save_clicked)
        self.detail_grid.attach(self.save_button, 1, row, 1, 1)
        save_row = row
        row = row + 1

        # Set up the Revision line
        label = Gtk.Label(label = _("Revision:"))
        label.set_properties(xalign=0,yalign=0)
        self.revision_label = Gtk.Label(label = "")
        self.revision_label.set_properties(xalign=0, selectable=True)
        self.revision_label.set_line_wrap(True)
        self.revision_label.set_hexpand(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.revision_label, 1, row, 2, 1)
        revision_row = row
        row = row + 1

        # Set up the Log Message line
        label = Gtk.Label(label = _("Message:"))
        label.set_properties(xalign=0, yalign=0)
        self.message_label = Gtk.Label(label = "")
        self.message_label.set_properties(xalign=0, yalign=0, selectable=True)
        self.message_label.set_line_wrap(True)
        self.message_label.set_hexpand(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.message_label, 1, row, 2, 1)
        message_row = row
        row = row + 1

        self.add_rows = [branch_name_row, track_row, save_row, start_point_row,
            checkout_row]

        self.view_rows = [branch_name_row, revision_row, message_row, save_row,
             checkout_row]

        self.detail_grid.show()
        self.detail_container.add(self.detail_grid)

    def load(self):
        self.items_treeview.clear()

        self.branch_list = self.git.branch_list()
        for item in self.branch_list:
            name = saxutils.escape(item.name)
            if item.tracking:
                name = "<b>%s</b>" % name
            self.items_treeview.append([name])

    def on_add_clicked(self, widget):
        self.show_add()

    def on_delete_clicked(self, widget):
        items = self.items_treeview.get_selected_row_items(0)

        selected = []
        for branch in items:
            selected.append(saxutils.unescape(branch).replace("<b>", "").replace("</b>", ""))

        confirm = rabbitvcs.ui.dialog.Confirmation(_("Are you sure you want to delete %s?" % ", ".join(selected)))
        result = confirm.run()

        if result == Gtk.ResponseType.OK or result == True:
            for branch in selected:
                self.git.branch_delete(branch)

            self.load()
            self.show_add()

    def on_save_clicked(self, widget):
        if self.state == STATE_ADD:
            branch_name = self.branch_entry.get_text()
            branch_track = self.track_checkbox.get_active()
            start_point = self.git.revision(self.start_point_entry.get_text())

            self.git.branch(branch_name, revision=start_point)
        elif self.state == STATE_EDIT:
            branch_name = self.branch_entry.get_text()
            branch_track = self.track_checkbox.get_active()

            if self.selected_branch.name != branch_name:
                self.git.branch_rename(self.selected_branch.name, branch_name)

        if self.checkout_checkbox.get_active():
            self.git.checkout([], self.git.revision(branch_name))

        self.load()
        self.show_edit(branch_name)

    def on_treeview_key_event(self, treeview, data=None):
        if Gdk.keyval_name(data.keyval) in ("Up", "Down", "Return"):
            self.on_treeview_event(treeview, data)

    def on_treeview_mouse_event(self, treeview, data=None):
        self.on_treeview_event(treeview, data)

    def on_treeview_event(self, treeview, data):
        selected = self.items_treeview.get_selected_row_items(0)
        if len(selected) > 0:
            if len(selected) == 1:
                branch_name = selected[0]
                if branch_name.startswith("<b>"):
                    branch_name = branch_name[3:-4]

                self.show_edit(branch_name)
            self.get_widget("delete").set_sensitive(True)
        else:
            self.show_add()

    def show_rows(self, rows):
        self.detail_grid.hide()
        for w in self.detail_grid.get_children():
            if self.detail_grid.child_get_property(w, "top-attach") in rows:
                w.show_all()
            else:
                w.hide()
        self.detail_grid.show()

    def show_add(self):
        self.state = STATE_ADD

        revision = "HEAD"
        if self.revision:
            active_branch = self.git.get_active_branch()
            if active_branch:
                revision = S(active_branch.name)

        self.items_treeview.unselect_all()
        self.branch_entry.set_text("")
        self.save_button.set_label(_("Add"))
        self.start_point_entry.set_text(S(revision).display())
        self.track_checkbox.set_active(True)
        self.checkout_checkbox.set_sensitive(True)
        self.checkout_checkbox.set_active(False)
        self.show_rows(self.add_rows)
        self.get_widget("detail_label").set_markup(_("<b>Add Branch</b>"))

    def show_edit(self, branch_name):
        self.state = STATE_EDIT
        branch_name = saxutils.unescape(branch_name)
        self.selected_branch = None
        for item in self.branch_list:
            if item.name == branch_name:
                self.selected_branch = item
                break

        self.save_button.set_label(_("Save"))

        if self.selected_branch:
            self.branch_entry.set_text(S(self.selected_branch.name).display())
            self.revision_label.set_text(S(self.selected_branch.revision).display())
            self.message_label.set_text(S(self.selected_branch.message.rstrip("\n")).display())
            if self.selected_branch.tracking:
                self.checkout_checkbox.set_active(True)
                self.checkout_checkbox.set_sensitive(False)
            else:
                self.checkout_checkbox.set_active(False)
                self.checkout_checkbox.set_sensitive(True)

        self.show_rows(self.view_rows)
        self.get_widget("detail_label").set_markup(_("<b>Branch Detail</b>"))

    def on_log_dialog_button_clicked(self, widget):
        log_dialog_factory(
            self.path,
            ok_callback=self.on_log_dialog_closed
        )

    def on_log_dialog_closed(self, data):
        if data:
            self.start_point_entry.set_text(S(data).display())


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, paths) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs branch-manager path [-r revision]"
    )

    window = GitBranchManager(paths[0], revision=options.revision)
    window.register_gtk_quit()
    Gtk.main()
