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
from rabbitvcs.ui.log import log_dialog_factory
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
import rabbitvcs.util.helper
import rabbitvcs.vcs

from xml.sax import saxutils

from rabbitvcs import gettext
import six
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
            self.show_edit(revision_branches[0].name)
        else:
            self.show_add()
        
    def initialize_detail(self):
        self.detail_container = self.get_widget("detail_container")

        vbox = gtk.VBox(False, 6)

        # Set up the Branch line
        label = gtk.Label(_("Name:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=.5)
        self.branch_entry = gtk.Entry()
        self.branch_name_container = gtk.HBox(False, 0)
        self.branch_name_container.pack_start(label, False, False, 0)
        self.branch_name_container.pack_start(self.branch_entry, False, False, 0)
        vbox.pack_start(self.branch_name_container, False, False, 0)

        # Set up the Commit-sha line
        label = gtk.Label(_("Start Point:"))
        label.set_size_request(90, -1)
        label.set_properties(xalign=0,yalign=.5)
        self.start_point_entry = gtk.Entry()
        self.start_point_entry.set_size_request(300, -1)
        self.start_point_container = gtk.HBox(False, 0)
        self.log_dialog_button = gtk.Button()
        self.log_dialog_button.connect("clicked", self.on_log_dialog_button_clicked)
        image = gtk.Image()
        image.set_from_icon_name("rabbitvcs-show_log", 2)
        self.log_dialog_button.set_image(image)
        self.start_point_container.pack_start(label, False, False, 0)
        self.start_point_container.pack_start(self.start_point_entry, False, False, 0)
        self.start_point_container.pack_start(self.log_dialog_button, False, False, 0)
        vbox.pack_start(self.start_point_container, False, False, 0)

        # Set up the Track line
        label = gtk.Label("")
        label.set_size_request(90, -1)
        self.track_checkbox = gtk.CheckButton(_("Keep old branch's history"))
        self.track_container = gtk.HBox(False, 0)
        self.track_container.pack_start(label, False, False, 0)
        self.track_container.pack_start(self.track_checkbox, False, False, 0)
        vbox.pack_start(self.track_container, False, False, 0)

        # Set up the checkout line
        label = gtk.Label("")
        label.set_size_request(90, -1)
        self.checkout_checkbox = gtk.CheckButton(_("Set as active branch"))
        self.checkout_container = gtk.HBox(False, 0)
        self.checkout_container.pack_start(label, False, False, 0)
        self.checkout_container.pack_start(self.checkout_checkbox, False, False, 0)
        vbox.pack_start(self.checkout_container, False, False, 0)
        
        # Set up Save button
        label = gtk.Label("")
        label.set_size_request(90, -1)
        self.save_button = gtk.Button(label=_("Save"))
        self.save_button.connect("clicked", self.on_save_clicked)
        self.save_container = gtk.HBox(False, 0)
        self.save_container.pack_start(label, False, False, 0)
        self.save_container.pack_start(self.save_button, False, False, 0)
        vbox.pack_start(self.save_container, False, False, 0)

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
        
        self.add_containers = [self.branch_name_container, self.track_container, 
            self.save_container, self.start_point_container,
            self.checkout_container]
            
        self.view_containers = [self.branch_name_container, self.revision_container, 
            self.message_container, self.save_container,  self.checkout_container]

        self.all_containers = [self.branch_name_container, self.track_container,
            self.revision_container, self.message_container, self.save_container, 
            self.start_point_container, self.checkout_container]

        vbox.show()
        self.detail_container.add(vbox)
        
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
       
        if result == gtk.RESPONSE_OK or result == True:
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
        if gtk.gdk.keyval_name(data.keyval) in ("Up", "Down", "Return"):
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

    def show_containers(self, containers):
        for container in self.all_containers:
            container.hide()
        for container in containers:
            container.show_all()

    def show_add(self):
        self.state = STATE_ADD
        
        revision = "HEAD"
        if self.revision:
            revision = six.text_type(self.git.get_active_branch().name)

        self.items_treeview.unselect_all()
        self.branch_entry.set_text("")
        self.save_button.set_label(_("Add"))
        self.start_point_entry.set_text(revision)
        self.track_checkbox.set_active(True)
        self.checkout_checkbox.set_sensitive(True)
        self.checkout_checkbox.set_active(False)
        self.show_containers(self.add_containers)
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
            self.branch_entry.set_text(self.selected_branch.name)
            self.revision_label.set_text(six.text_type(self.selected_branch.revision))
            self.message_label.set_text(self.selected_branch.message.rstrip("\n"))
            if self.selected_branch.tracking:
                self.checkout_checkbox.set_active(True)
                self.checkout_checkbox.set_sensitive(False)
            else:
                self.checkout_checkbox.set_active(False)
                self.checkout_checkbox.set_sensitive(True)

        self.show_containers(self.view_containers)
        self.get_widget("detail_label").set_markup(_("<b>Branch Detail</b>"))

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
        usage="Usage: rabbitvcs branch-manager path [-r revision]"
    )
    
    window = GitBranchManager(paths[0], revision=options.revision)
    window.register_gtk_quit()
    gtk.main()
