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

import pygtk
import gobject
import gtk
import pango

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import GitAction
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
from rabbitvcs.ui.log import log_dialog_factory
import rabbitvcs.util.helper
import rabbitvcs.vcs

from rabbitvcs import gettext
import six
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
            [gobject.TYPE_STRING], 
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

        vbox = gtk.VBox(False, 6)

        # Set up the Tag line
        label = gtk.Label(_("Name:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=.5)
        self.tag_entry = gtk.Entry()
        self.tag_name_container = gtk.HBox(False, 0)
        self.tag_name_container.pack_start(label, False, False, 0)
        self.tag_name_container.pack_start(self.tag_entry, False, False, 0)
        vbox.pack_start(self.tag_name_container, False, False, 0)

        # Set up the Commit-sha line
        label = gtk.Label(_("Revision:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=.5)
        self.start_point_entry = gtk.Entry()
        self.start_point_entry.set_size_request(300, -1)
        self.start_point_container = gtk.HBox(False, 0)
        if self.revision_obj.value:
            self.start_point_entry.set_text(six.text_type(self.revision_obj))
        self.log_dialog_button = gtk.Button()
        self.log_dialog_button.connect("clicked", self.on_log_dialog_button_clicked)
        image = gtk.Image()
        image.set_from_icon_name("rabbitvcs-show_log", 2)
        self.log_dialog_button.set_image(image)
        self.start_point_container.pack_start(label, False, False, 0)
        self.start_point_container.pack_start(self.start_point_entry, False, False, 0)
        self.start_point_container.pack_start(self.log_dialog_button, False, False, 0)
        vbox.pack_start(self.start_point_container, False, False, 0)

        # Set up the Log Message Entry line
        label = gtk.Label(_("Message:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=0)
        self.message_entry = rabbitvcs.ui.widget.TextView()
        self.message_entry.view.set_size_request(300, 75)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.add(self.message_entry.view)
        self.message_entry_container = gtk.HBox(False, 0)
        self.message_entry_container.pack_start(label, False, False, 0)
        self.message_entry_container.pack_start(swin, False, False, 0)
        vbox.pack_start(self.message_entry_container, False, False, 0)

        # Set up Save button
        label = gtk.Label("")
        label.set_size_request(90, -1)
        self.save_button = gtk.Button(label=_("Save"))
        self.save_button.connect("clicked", self.on_save_clicked)
        self.save_container = gtk.HBox(False, 0)
        self.save_container.pack_start(label, False, False, 0)
        self.save_container.pack_start(self.save_button, False, False, 0)
        vbox.pack_start(self.save_container, False, False, 0)

        # Set up the tagger line
        label = gtk.Label(_("Tagger:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=0)
        self.tagger_label = gtk.Label("")
        self.tagger_label.set_properties(xalign=0,yalign=0,selectable=True)
        self.tagger_label.set_line_wrap(True)
        self.tagger_container = gtk.HBox(False, 0)
        self.tagger_container.pack_start(label, False, False, 0)
        self.tagger_container.pack_start(self.tagger_label, False, False, 0)
        vbox.pack_start(self.tagger_container, False, False, 0)

        # Set up the Date line
        label = gtk.Label(_("Date:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=0)
        self.date_label = gtk.Label("")
        self.date_label.set_properties(xalign=0,yalign=0,selectable=True)
        self.date_container = gtk.HBox(False, 0)
        self.date_container.pack_start(label, False, False, 0)
        self.date_container.pack_start(self.date_label, False, False, 0)
        vbox.pack_start(self.date_container, False, False, 0)

        # Set up the Revision line
        label = gtk.Label(_("Revision:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=0)
        self.revision_label = gtk.Label("")
        self.revision_label.set_properties(xalign=0,selectable=True)
        self.revision_label.set_line_wrap(True)
        self.revision_container = gtk.HBox(False, 0)
        self.revision_container.pack_start(label, False, False, 0)
        self.revision_container.pack_start(self.revision_label, False, False, 0)
        vbox.pack_start(self.revision_container, False, False, 0)

        # Set up the Log Message line
        label = gtk.Label(_("Message:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=0)
        self.message_label = gtk.Label("")
        self.message_label.set_properties(xalign=0,yalign=0,selectable=True)
        self.message_label.set_line_wrap(True)
        self.message_label.set_size_request(250, -1)
        self.message_container = gtk.HBox(False, 0)
        self.message_container.pack_start(label, False, False, 0)
        self.message_container.pack_start(self.message_label, False, False, 0)
        vbox.pack_start(self.message_container, False, False, 0)
        
        self.add_containers = [self.tag_name_container, self.message_entry_container,
            self.start_point_container, self.save_container]
            
        self.view_containers = [self.tag_name_container, self.tagger_container,
            self.date_container, self.revision_container, self.message_container]

        self.all_containers = [self.tag_name_container,  self.tagger_container, 
            self.date_container, self.revision_container, self.message_container, 
            self.message_entry_container, self.save_container, self.start_point_container]

        vbox.show()
        self.detail_container.add(vbox)
        
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
        
        if result == gtk.RESPONSE_OK or result == True:
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
        if gtk.gdk.keyval_name(data.keyval) in ("Up", "Down", "Return"):
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

    def show_containers(self, containers):
        for container in self.all_containers:
            container.hide()
        for container in containers:
            container.show_all()

    def show_add(self):
        self.items_treeview.unselect_all()
        self.tag_entry.set_text("")
        self.message_entry.set_text("")
        self.save_button.set_label(_("Add"))
        self.show_containers(self.add_containers)
        self.get_widget("detail_label").set_markup(_("<b>Add Tag</b>"))
    
    def show_detail(self, tag_name):
        self.selected_tag = None
        for item in self.tag_list:
            if item.name == tag_name:
                self.selected_tag = item
                break

        self.save_button.set_label(_("Save"))
        if self.selected_tag:
            self.tag_entry.set_text(self.selected_tag.name)
            self.revision_label.set_text(self.selected_tag.sha)
            self.message_label.set_text(self.selected_tag.message.rstrip("\n"))
            self.tagger_label.set_text(self.selected_tag.tagger)
            self.date_label.set_text(rabbitvcs.util.helper.format_datetime(datetime.fromtimestamp(self.selected_tag.tag_time)))

            self.show_containers(self.view_containers)
            self.get_widget("detail_label").set_markup(_("<b>Tag Detail</b>"))


    def on_log_dialog_button_clicked(self, widget):
        log_dialog_factory(
            self.path,
            ok_callback=self.on_log_dialog_closed
        )
    
    def on_log_dialog_closed(self, data):
        if data:
            self.start_point_entry.set_text(data)

if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, paths) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs tag-manager path"
    )
    
    window = GitTagManager(paths[0], options.revision)
    window.register_gtk_quit()
    gtk.main()
