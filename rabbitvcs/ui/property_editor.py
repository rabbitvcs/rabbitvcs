#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2009 by Jason Heeris <jason.heeris@gmail.com>
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

"""
A note to anyone intending to work on this in the future... This dialog is
designed to be as stateless as possible. That is, all the information about
properties being changed, deleted, added, etc. should be kept in the SVN admin
system, not in this dialog. SVN should be keeping track of this info, not us!

To this effect, changes are applied immediately... no saving lists of changes to
apply later, no trying to keep track of what was done recursively and what
wasn't; just do the work and make sure the UI is sensible.
"""
from __future__ import absolute_import
from __future__ import print_function

import os.path

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.util.contextmenu import GtkContextMenu, GtkContextMenuCaller
import rabbitvcs.ui.wraplabel
import rabbitvcs.util.contextmenuitems
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.vcs
from rabbitvcs.util.helper import format_long_text
from rabbitvcs.vcs.svn import Revision
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.property_editor")

from rabbitvcs import gettext
_ = gettext.gettext


PROP_EDITOR_NOTE = _("""\
<b>Note:</b> changes to properties are applied instantly. You may review and \
undo changes using the context menu for each item.
""")

RECURSIVE_DELETE_MSG = _("""\
Do you want to delete the selected properties from all files and subdirectories
beneath this directory?""") 

PROP_MENU_STRUCTURE = [
    (rabbitvcs.util.contextmenuitems.PropMenuEdit, None),
    (rabbitvcs.util.contextmenuitems.PropMenuRevert, None),
    (rabbitvcs.util.contextmenuitems.PropMenuRevertRecursive, None),
    (rabbitvcs.util.contextmenuitems.PropMenuDelete, None),
    (rabbitvcs.util.contextmenuitems.PropMenuDeleteRecursive, None)]

class PropEditor(InterfaceView, GtkContextMenuCaller):
    '''
    User interface for the property editor.
    
    The UI is basically an "instant update" editor, that is as soon as you add a
    property in the dialog, it is actually added in the WC. Each row has a
    context menu available to perform other actions.
    '''


    def __init__(self, path):
        '''
        Initialises the UI.
        '''
        InterfaceView.__init__(self, "property_editor", "PropertyEditor")
        
        note = rabbitvcs.ui.wraplabel.WrapLabel(PROP_EDITOR_NOTE)
        note.set_use_markup(True)
        
        self.get_widget("note_box").pack_start(note)        
        self.get_widget("note_box").show_all()
                
        self.path = path
        
        self.get_widget("wc_text").set_text(self.get_local_path(os.path.realpath(path)))
                
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
                
        if not self.svn.is_versioned(self.path):
            rabbitvcs.ui.dialog.MessageBox(_("File is not under version control."))
            self.close()
            return
        
        self.get_widget("remote_uri_text").set_text(self.svn.get_repo_url(path))
               
        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, rabbitvcs.ui.widget.TYPE_ELLIPSIZED,
             gobject.TYPE_STRING, rabbitvcs.ui.widget.TYPE_STATUS], 
            [_("Name"), _("Value"), _("Reserved"), _("Status")],
            
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.long_text_filter,
                    "user_data": {
                        "cols": 0,
                        "column": 1
                    }
                },
                
                {
                    "callback": rabbitvcs.ui.widget.translate_filter,
                    "user_data": {
                        "column": 3
                    }
                }],
                
            callbacks={
                "row-activated":  self.on_table_row_activated,
                "mouse-event":   self.on_table_mouse_event,
                "key-event":     self.on_table_key_event
            }
        )
        self.table.allow_multiple()
        
        self.refresh()

    def get_local_path(self, path):
        return path.replace("file://", "")

    def on_note_box_add(self, *args, **kwargs):
        print("Added!")
    
    def refresh(self):
        self.table.clear()
        
        propdets = {}
                
        try:
            propdets = self.svn.propdetails(self.path)
                       
        except Exception as e:
            log.exception(e)
            rabbitvcs.ui.dialog.MessageBox(_("Unable to retrieve properties list"))
        
        for propname, details in list(propdets.items()):
            
            self.table.append(
                [propname, details["value"], "N/A", details["status"]]
                              )

    def on_refresh_clicked(self, widget):
        self.refresh()

    def on_new_clicked(self, widget):
        self.edit_property()

    def edit_property(self, name=""):
        
        value = self.svn.propget(self.path, name)
        
        dialog = rabbitvcs.ui.dialog.Property(name, value)
        
        name,value,recurse = dialog.run()
        if name:
            success = self.svn.propset(self.path, name, value, overwrite=True, recurse=False)
            if not success:
                rabbitvcs.ui.dialog.MessageBox(_("Unable to set new value for property."))
            
        self.refresh()

    def delete_properties(self, names):
        
        recursive = False

        if(os.path.isdir(self.path)):
            dialog = rabbitvcs.ui.dialog.Confirmation(RECURSIVE_DELETE_MSG)
            recursive = dialog.run()
        
        for name in names:
            self.svn.propdel(self.path, name, recurse=recursive)

        self.refresh()

    def on_table_row_activated(self, treeview, event, col):
        for name in self.table.get_selected_row_items(0):
            self.edit_property(name)

    def on_table_key_event(self, treeview, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            names = self.table.get_selected_row_items(0)
            self.delete_properties(names)

    def on_table_mouse_event(self, treeview, data=None):
        if data and data.button == 3:
            self.show_menu(data)
    
    def show_menu(self, data):
        # self.show_files_table_popup_menu(treeview, data)
        selected_propnames = self.table.get_selected_row_items(0)
        propdetails = self.svn.propdetails(self.path)
        
        filtered_details = {}
        for propname, detail in list(propdetails.items()):
            if propname in selected_propnames:
                filtered_details[propname] = detail
        
        conditions = PropMenuConditions(self.path, filtered_details)
        callbacks = PropMenuCallbacks(self, self.path, filtered_details,
                                      self.vcs)
        
        GtkContextMenu(PROP_MENU_STRUCTURE, conditions, callbacks).show(data)

class PropMenuCallbacks:

    def __init__(self, caller, path, propdetails, vcs):
        self.path = path
        self.caller = caller
        self.propdetails = propdetails
        self.vcs = vcs
        self.svn = self.vcs.svn()

    def property_edit(self, widget, *args):
        if list(self.propdetails.keys()):
            propname  = list(self.propdetails.keys())[0]
            self.caller.edit_property(propname)
            
    def property_delete(self, widget, *args):
        for propname in list(self.propdetails.keys()):
            self.svn.propdel(self.path, propname, recurse=False)
        self.caller.refresh()
    
    def property_delete_recursive(self, widget, *args):
        for propname in list(self.propdetails.keys()):
            self.svn.propdel(self.path, propname, recurse=True)
        self.caller.refresh()
    
    def property_revert(self, widget, *args):
        pass

    def property_revert_recursive(self, widget, *args):
        pass

        
class PropMenuConditions:
    
    def __init__(self, path, propdetails):
        self.path = path
        self.propdetails = propdetails
    
    def all_modified(self):
        return all([detail["status"] != "unchanged"
                       for (propname, detail) in list(self.propdetails.items())])
    
    def all_not_deleted(self):
        return all([detail["status"] != "deleted"
                       for (propname, detail) in list(self.propdetails.items())])
    
    def property_revert(self):
        return False
        # return self.all_modified()
    
    def property_delete(self):
        return self.all_not_deleted()
    
    def property_edit(self):
        return len(list(self.propdetails.keys())) == 1

if __name__ == "__main__":
    # These are some dumb tests before I add any functionality.
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs propedit [url_or_path]")
    
    window = PropEditor(paths[0])
    window.register_gtk_quit()
    gtk.main()
