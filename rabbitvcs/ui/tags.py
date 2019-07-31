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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk, Pango

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import GitAction
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
from rabbitvcs.ui.log import log_dialog_factory
from rabbitvcs.util import helper
from rabbitvcs.util.strings import S
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

STATE_ADD = 0
STATE_EDIT = 1

class GitTagManager(InterfaceView):
    """
    Provides a UI interface to manage items

    """

    state = STATE_ADD

    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "manager", "Manager")

        self.path = path

        self.get_widget("right_side").show()
        self.get_widget("Manager").set_size_request(695, -1)
        self.get_widget("Manager").set_title(_("Tag Manager"))
        self.get_widget("items_label").set_markup(_("<b>Tags</b>"))

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        self.revision_obj = self.git.revision(revision)

        self.selected_tag = None
        self.items_treeview = rabbitvcs.ui.widget.Table(
            self.get_widget("items_treeview"),
            [GObject.TYPE_STRING],
            [_("Tag")],
            callbacks={
                "mouse-event":   self.on_treeview_mouse_event,
                "key-event":     self.on_treeview_key_event
            },
            flags={
                "sortable": True,
                "sort_on": 0
            }
        )
        self.initialize_detail()
        self.load(self.show_add)


    def initialize_detail(self):
        self.detail_container = self.get_widget("detail_container")

        self.detail_grid = Gtk.Grid()
        self.detail_grid.set_row_spacing(4)
        self.detail_grid.set_column_spacing(6)
        self.detail_grid.set_hexpand(True)
        row = 0

        # Set up the Tag line
        label = Gtk.Label(label = _("Name:"))
        label.set_properties(xalign=0, yalign=.5)
        self.tag_entry = Gtk.Entry()
        self.tag_entry.set_hexpand(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.tag_entry, 1, row, 2, 1)
        tag_name_row = row
        row = row + 1

        # Set up the Commit-sha line
        label = Gtk.Label(label = _("Revision:"))
        label.set_properties(xalign=0, yalign=.5)
        self.start_point_entry = Gtk.Entry()
        self.start_point_entry.set_size_request(300, -1)
        self.start_point_entry.set_hexpand(True)
        if self.revision_obj.value:
            self.start_point_entry.set_text(S(self.revision_obj).display())
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

        # Set up the Log Message Entry line
        label = Gtk.Label(label = _("Message:"))
        label.set_properties(xalign=0, yalign=0)
        self.message_entry = rabbitvcs.ui.widget.TextView()
        self.message_entry.view.set_size_request(300, 75)
        self.message_entry.view.set_hexpand(True)
        self.message_entry.view.set_vexpand(True)
        swin = Gtk.ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        swin.set_hexpand(True)
        swin.set_vexpand(True)
        swin.add(self.message_entry.view)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(swin, 1, row, 2, 1)
        message_entry_row = row
        row = row + 1

        # Set up Save button
        self.save_button = Gtk.Button(label=_("Save"))
        self.save_button.set_halign(Gtk.Align.START)
        self.save_button.connect("clicked", self.on_save_clicked)
        self.detail_grid.attach(self.save_button, 1, row, 1, 1)
        save_row = row
        row = row + 1

        # Set up the tagger line
        label = Gtk.Label(label = _("Tagger:"))
        label.set_properties(xalign=0, yalign=0)
        self.tagger_label = Gtk.Label(label = "")
        self.tagger_label.set_properties(xalign=0, yalign=0, selectable=True)
        self.tagger_label.set_hexpand(True)
        self.tagger_label.set_line_wrap(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.tagger_label, 1, row, 2, 1)
        tagger_row = row
        row = row + 1

        # Set up the Date line
        label = Gtk.Label(label = _("Date:"))
        label.set_properties(xalign=0, yalign=0)
        self.date_label = Gtk.Label(label = "")
        self.date_label.set_properties(xalign=0, yalign=0, selectable=True)
        self.date_label.set_hexpand(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.date_label, 1, row, 2, 1)
        date_row = row
        row = row + 1

        # Set up the Revision line
        label = Gtk.Label(label = _("Revision:"))
        label.set_properties(xalign=0, yalign=0)
        self.revision_label = Gtk.Label(label = "")
        self.revision_label.set_properties(xalign=0, selectable=True)
        self.revision_label.set_hexpand(True)
        self.revision_label.set_line_wrap(True)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(self.revision_label, 1, row, 2, 1)
        revision_row = row
        row = row + 1

        # Set up the Log Message line
        label = Gtk.Label(label = _("Message:"))
        label.set_properties(xalign=0, yalign=0)
        self.message_label = Gtk.Label(label = "")
        self.message_label.set_properties(xalign=0, yalign=0, selectable=True)
        self.message_label.set_hexpand(True)
        self.message_label.set_vexpand(True)
        self.message_label.set_line_wrap(True)
        vport = Gtk.Viewport()
        vport.set_shadow_type(Gtk.ShadowType.NONE)
        vport.set_hexpand(True)
        vport.set_vexpand(True)
        vport.add(self.message_label)
        swin = Gtk.ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.NONE)
        swin.set_size_request(250, -1)
        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.set_hexpand(True)
        swin.set_vexpand(True)
        swin.add(vport)
        self.detail_grid.attach(label, 0, row, 1, 1)
        self.detail_grid.attach(swin, 1, row, 2, 1)
        message_row = row
        row = row + 1

        self.add_rows = [tag_name_row, message_entry_row,
            start_point_row, save_row]

        self.view_rows = [tag_name_row, tagger_row,
            date_row, revision_row, message_row]

        self.detail_grid.show()
        self.detail_container.add(self.detail_grid)

    def load(self, callback, *args, **kwargs):
        self.items_treeview.clear()

        self.tag_list = self.git.tag_list()

        for item in self.tag_list:
            self.items_treeview.append([item.name])

        if callback:
            callback(*args, **kwargs)

    def on_add_clicked(self, widget):
        self.show_add()

    def on_delete_clicked(self, widget):
        selected = self.items_treeview.get_selected_row_items(0)

        confirm = rabbitvcs.ui.dialog.Confirmation(_("Are you sure you want to delete %s?" % ", ".join(selected)))
        result = confirm.run()

        if result == Gtk.ResponseType.OK or result == True:
            for tag in selected:
                self.git.tag_delete(tag)

            self.load(self.show_add)

    def on_save_clicked(self, widget):
        tag_name = self.tag_entry.get_text()
        tag_message = self.message_entry.get_text()
        tag_revision = self.git.revision(self.start_point_entry.get_text())

        self.git.tag(tag_name, tag_message, tag_revision)
        self.load(self.show_detail, tag_name)

    def on_treeview_key_event(self, treeview, data=None):
        if Gdk.keyval_name(data.keyval) in ("Up", "Down", "Return"):
            self.on_treeview_event(treeview, data)

    def on_treeview_mouse_event(self, treeview, data=None):
        self.on_treeview_event(treeview, data)

    def on_treeview_event(self, treeview, data):
        selected = self.items_treeview.get_selected_row_items(0)
        if len(selected) > 0:
            if len(selected) == 1:
                self.show_detail(selected[0])
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
        self.items_treeview.unselect_all()
        self.tag_entry.set_text("")
        self.message_entry.set_text("")
        self.save_button.set_label(_("Add"))
        self.show_rows(self.add_rows)
        self.get_widget("detail_label").set_markup(_("<b>Add Tag</b>"))

    def show_detail(self, tag_name):
        self.selected_tag = None
        for item in self.tag_list:
            if S(item.name) == tag_name:
                self.selected_tag = item
                break

        self.save_button.set_label(_("Save"))
        if self.selected_tag:
            self.tag_entry.set_text(S(self.selected_tag.name).display())
            self.revision_label.set_text(S(self.selected_tag.sha).display())
            self.message_label.set_text(S(self.selected_tag.message).display().rstrip("\n"))
            self.tagger_label.set_text(S(self.selected_tag.tagger).display())
            self.date_label.set_text(helper.format_datetime(datetime.fromtimestamp(self.selected_tag.tag_time)))

            self.show_rows(self.view_rows)
            self.get_widget("detail_label").set_markup(_("<b>Tag Detail</b>"))


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
        usage="Usage: rabbitvcs tag-manager path"
    )

    window = GitTagManager(paths[0], options.revision)
    window.register_gtk_quit()
    Gtk.main()
