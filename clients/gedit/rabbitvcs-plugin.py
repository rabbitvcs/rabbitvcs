from __future__ import absolute_import
#
# This is a Gedit plugin to allow for RabbitVCS integration in the Gedit
# text editor.
# 
# Copyright (C) 2008-2011 by Adam Plumb <adamplumb@gmail.com>
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

from gettext import gettext as _

import os

try:
    from gi.repository import Gedit, GObject
    from gi.repository import Gtk as gtk
    os.environ["NAUTILUS_PYTHON_REQUIRE_GTK3"] = "1"
    GTK3 = True
except ImportError:
    import gedit
    import gobject
    import gtk
    GTK3 = False



import rabbitvcs.util.helper
from rabbitvcs.vcs import create_vcs_instance
from rabbitvcs.util.contextmenu import GtkFilesContextMenuConditions, \
    GtkFilesContextMenuCallbacks, MainContextMenu, MainContextMenuCallbacks, \
    MenuBuilder, GtkContextMenuCaller
from rabbitvcs.util.contextmenuitems import *

# Menu item example, insert a new item in the Tools menu
ui_str = """<ui>
  <menubar name="MenuBar">
    <placeholder name="ExtraMenu_1">
    <menu name="RabbitVCSMenu" action="RabbitVCSMenu">
        <menu name="RabbitVCS::RabbitVCS_Svn" action="RabbitVCS::RabbitVCS_Svn">
            <menuitem name="RabbitVCS::Update" action="RabbitVCS::Update" />
            <menuitem name="RabbitVCS::Commit" action="RabbitVCS::Commit" />
            <menuitem name="RabbitVCS::Checkout" action="RabbitVCS::Checkout" />
            <menu name="RabbitVCS::Diff_Menu" action="RabbitVCS::Diff_Menu">
                <menuitem name="RabbitVCS::Diff" action="RabbitVCS::Diff" />
                <menuitem name="RabbitVCS::Diff_Previous_Revision" action="RabbitVCS::Diff_Previous_Revision" />
                <menuitem name="RabbitVCS::Diff_Multiple" action="RabbitVCS::Diff_Multiple" />
                <menuitem name="RabbitVCS::Compare_Tool" action="RabbitVCS::Compare_Tool" />
                <menuitem name="RabbitVCS::Compare_Tool_Previous_Revision" action="RabbitVCS::Compare_Tool_Previous_Revision" />
                <menuitem name="RabbitVCS::Compare_Tool_Multiple" action="RabbitVCS::Compare_Tool_Multiple" />
                <menuitem name="RabbitVCS::Show_Changes" action="RabbitVCS::Show_Changes" />
            </menu>
            <menuitem name="RabbitVCS::Show_Log" action="RabbitVCS::Show_Log" />
            <menuitem name="RabbitVCS::Repo_Browser" action="RabbitVCS::Repo_Browser" />
            <menuitem name="RabbitVCS::Check_For_Modifications" action="RabbitVCS::Check_For_Modifications" />
            <separator />
            <menuitem name="RabbitVCS::Add" action="RabbitVCS::Add" />
            <menu name="RabbitVCS::Add_To_Ignore_List" action="RabbitVCS::Add_To_Ignore_List">
                <menuitem name="RabbitVCS::Ignore_By_Filename" action="RabbitVCS::Ignore_By_Filename" />
                <menuitem name="RabbitVCS::Ignore_By_File_Extension" action="RabbitVCS::Ignore_By_File_Extension" />
            </menu>
            <separator />
            <menuitem name="RabbitVCS::Update_To_Revision" action="RabbitVCS::Update_To_Revision" />
            <menuitem name="RabbitVCS::Rename" action="RabbitVCS::Rename" />
            <menuitem name="RabbitVCS::Delete" action="RabbitVCS::Delete" />
            <menuitem name="RabbitVCS::Revert" action="RabbitVCS::Revert" />
            <menuitem name="RabbitVCS::Edit_Conflicts" action="RabbitVCS::Edit_Conflicts" />
            <menuitem name="RabbitVCS::Mark_Resolved" action="RabbitVCS::Mark_Resolved" />
            <menuitem name="RabbitVCS::Relocate" action="RabbitVCS::Relocate" />
            <menuitem name="RabbitVCS::Get_Lock" action="RabbitVCS::Get_Lock" />
            <menuitem name="RabbitVCS::Unlock" action="RabbitVCS::Unlock" />
            <menuitem name="RabbitVCS::Cleanup" action="RabbitVCS::Cleanup" />
            <menuitem name="RabbitVCS::Annotate" action="RabbitVCS::Annotate" />
            <separator />
            <menuitem name="RabbitVCS::Export" action="RabbitVCS::Export" />
            <menuitem name="RabbitVCS::Create_Repository" action="RabbitVCS::Create_Repository" />
            <menuitem name="RabbitVCS::Import" action="RabbitVCS::Import" />
            <separator />
            <menuitem name="RabbitVCS::Branch_Tag" action="RabbitVCS::Branch_Tag" />
            <menuitem name="RabbitVCS::Switch" action="RabbitVCS::Switch" />
            <menuitem name="RabbitVCS::Merge" action="RabbitVCS::Merge" />
            <separator />
            <menuitem name="RabbitVCS::Apply_Patch" action="RabbitVCS::Apply_Patch" />
            <menuitem name="RabbitVCS::Create_Patch" action="RabbitVCS::Create_Patch" />
            <menuitem name="RabbitVCS::Properties" action="RabbitVCS::Properties" />
            <separator />
        </menu>
        <menu name="RabbitVCS::RabbitVCS_Git" action="RabbitVCS::RabbitVCS_Git">
            <menuitem name="RabbitVCS::Update" action="RabbitVCS::Update" />
            <menuitem name="RabbitVCS::Commit" action="RabbitVCS::Commit" />
            <menuitem name="RabbitVCS::Push" action="RabbitVCS::Push" />
            <separator />
            <menuitem name="RabbitVCS::Clone" action="RabbitVCS::Clone" />
            <menuitem name="RabbitVCS::Initialize_Repository" action="RabbitVCS::Initialize_Repository" />
            <separator />
            <menu name="RabbitVCS::Diff_Menu" action="RabbitVCS::Diff_Menu">
                <menuitem name="RabbitVCS::Diff" action="RabbitVCS::Diff" />
                <menuitem name="RabbitVCS::Diff_Previous_Revision" action="RabbitVCS::Diff_Previous_Revision" />
                <menuitem name="RabbitVCS::Diff_Multiple" action="RabbitVCS::Diff_Multiple" />
                <menuitem name="RabbitVCS::Compare_Tool" action="RabbitVCS::Compare_Tool" />
                <menuitem name="RabbitVCS::Compare_Tool_Previous_Revision" action="RabbitVCS::Compare_Tool_Previous_Revision" />
                <menuitem name="RabbitVCS::Compare_Tool_Multiple" action="RabbitVCS::Compare_Tool_Multiple" />
                <menuitem name="RabbitVCS::Show_Changes" action="RabbitVCS::Show_Changes" />
            </menu>
            <menuitem name="RabbitVCS::Show_Log" action="RabbitVCS::Show_Log" />
            <separator />
            <menuitem name="RabbitVCS::Stage" action="RabbitVCS::Stage" />
            <menuitem name="RabbitVCS::Unstage" action="RabbitVCS::Unstage" />
            <menu name="RabbitVCS::Add_To_Ignore_List" action="RabbitVCS::Add_To_Ignore_List">
                <menuitem name="RabbitVCS::Ignore_By_Filename" action="RabbitVCS::Ignore_By_Filename" />
                <menuitem name="RabbitVCS::Ignore_By_File_Extension" action="RabbitVCS::Ignore_By_File_Extension" />
            </menu>
            <separator />
            <menuitem name="RabbitVCS::Rename" action="RabbitVCS::Rename" />
            <menuitem name="RabbitVCS::Delete" action="RabbitVCS::Delete" />
            <menuitem name="RabbitVCS::Revert" action="RabbitVCS::Revert" />
            <menuitem name="RabbitVCS::Edit_Conflicts" action="RabbitVCS::Edit_Conflicts" />
            <menuitem name="RabbitVCS::Clean" action="RabbitVCS::Clean" />
            <menuitem name="RabbitVCS::Reset" action="RabbitVCS::Reset" />
            <menuitem name="RabbitVCS::Checkout" action="RabbitVCS::Checkout" />
            <separator />
            <menuitem name="RabbitVCS::Branches" action="RabbitVCS::Branches" />
            <menuitem name="RabbitVCS::Tags" action="RabbitVCS::Tags" />
            <menuitem name="RabbitVCS::Remotes" action="RabbitVCS::Remotes" />
            <separator />
            <menuitem name="RabbitVCS::Export" action="RabbitVCS::Export" />
            <menuitem name="RabbitVCS::Merge" action="RabbitVCS::Merge" />
            <separator />
            <menuitem name="RabbitVCS::Annotate" action="RabbitVCS::Annotate" />
            <separator />
            <menuitem name="RabbitVCS::Apply_Patch" action="RabbitVCS::Apply_Patch" />
            <menuitem name="RabbitVCS::Create_Patch" action="RabbitVCS::Create_Patch" />
            <separator />
        </menu>
        <menuitem name="RabbitVCS::Settings" action="RabbitVCS::Settings" />
        <menuitem name="RabbitVCS::About" action="RabbitVCS::About" />
    </menu>
    </placeholder>
  </menubar>
</ui>
"""
class RabbitVCSWindowHelper(GtkContextMenuCaller):

    _menu_paths = [
#        "/MenuBar/RabbitVCSMenu",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Commit",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Update",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Checkout",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Diff",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Previous_Revision",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Multiple",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Previous_Revision",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Multiple",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Diff_Menu/RabbitVCS::Show_Changes",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Show_Log",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Repo_Browser",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Check_For_Modifications",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Add",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Add_To_Ignore_List",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_Filename",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_File_Extension",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Update_To_Revision",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Rename",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Delete",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Revert",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Edit_Conflicts",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Mark_Resolved",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Get_Lock",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Unlock",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Cleanup",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Annotate",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Export",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Create_Repository",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Import",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Branch_Tag",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Switch",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Merge",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Apply_Patch",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Create_Patch",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Svn/RabbitVCS::Properties",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Update",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Commit",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Push",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Clone",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Initialize_Repository",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Diff",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Previous_Revision",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Multiple",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Previous_Revision",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Multiple",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Diff_Menu/RabbitVCS::Show_Changes",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Show_Log",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Stage",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Unstage",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Add_To_Ignore_List",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_Filename",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_File_Extension",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Rename",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Delete",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Revert",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Edit_Conflicts",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Clean",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Reset",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Checkout",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Branches",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Tags",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Remotes",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Export",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Merge",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Annotate",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Apply_Patch",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::RabbitVCS_Git/RabbitVCS::Create_Patch",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::Settings",
        "/MenuBar/ExtraMenu_1/RabbitVCSMenu/RabbitVCS::About"
    ]

    _default_base_dir = os.path.expanduser("~")

    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        self.base_dir = self._default_base_dir
        self._menubar_menu = None
        self._menu_action = None
        
        self.vcs_client = create_vcs_instance()

        # Insert menu items
        self._insert_menu()

    def deactivate(self):
        # Remove any installed menu items
        self._remove_menu()

        self._window = None
        self.base_dir = None
        self._plugin = None
        self._menubar_menu = None
        self._action_group = None

    def _insert_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        self._menubar_menu = GeditMenu(self, self.vcs_client, self.base_dir, [self._get_document_path()])
        self._menu_action = gtk.Action( name="RabbitVCSMenu", label="RabbitVCS", tooltip="Excellent Version Control for Linux", stock_id=None )
        
        self._action_group = gtk.ActionGroup("RabbitVCSActions")
        self._action_group = self._menubar_menu.get_action_group(self._action_group)
        self._action_group.add_action( self._menu_action )

        # Insert the action group
        manager.insert_action_group(self._action_group, 0)

        # Merge the UI
        self._ui_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()

    def update_ui(self):
        self.update_base_dir()
        
        document = self._window.get_active_document()
        self._action_group.set_sensitive(document != None)
        if document != None:
            manager = self._window.get_ui_manager()
            manager.get_widget("/MenuBar/ExtraMenu_1/RabbitVCSMenu").set_sensitive(True)
            self._menubar_menu.set_paths([self._get_document_path()])
            self._determine_menu_sensitivity([self._get_document_path()])

    def connect_view(self, view, id_name):
        handler_id = view.connect("populate-popup", self.on_view_populate_popup)
        view.set_data(id_name, [handler_id])

    def disconnect_view(self, view, id_name):
        view.disconnect(view.get_data(id_name)[0])
        
    def on_view_populate_popup(self, view, menu):
        separator = gtk.SeparatorMenuItem()
        menu.append(separator)
        separator.show()

        context_menu = GeditMainContextMenu(self, self.vcs_client, self.base_dir, [self._get_document_path()]).get_menu()
        for context_menu_item in context_menu:
            menu.append(context_menu_item)

    def _get_document_path(self):
        document = self._window.get_active_document()
        path = self.base_dir
        
        if document:
            tmp_path = document.get_uri_for_display()
            if os.path.exists(tmp_path):
                path = tmp_path

        return path

    def update_base_dir(self):
        document = self._window.get_active_document()
        if document:
            path = document.get_uri_for_display()
            if os.path.exists(path):
                self.base_dir = os.path.dirname(path)
        else:
            self.base_dir = self._default_base_dir

        self._menubar_menu.set_base_dir(self.base_dir)

    def _determine_menu_sensitivity(self, paths):
        self._menubar_menu.update_conditions(paths)
        
        manager = self._window.get_ui_manager()
        for menu_path in self._menu_paths:
            # Gtk3 changes how we access a widget's action.  Get it from the
            # UI Manager instead of the widget directly
            if hasattr(manager, "get_action"):
                action = manager.get_action(menu_path)
            else:
                widget = manager.get_widget(menu_path)
                action = widget.get_action()

            self._menubar_menu.update_action(action)

    # Menu activate handlers
    def reload_settings(self, proc):
        self.update_ui()

    def on_context_menu_command_finished(self):
        self.update_ui()

if GTK3:
    class RabbitVCSGedit3Plugin(GObject.Object, Gedit.WindowActivatable):
        __gtype_name__ = "RabbitVCSGedit3Plugin"
        window = GObject.property(type=Gedit.Window)
        
        def __init__(self):
            GObject.Object.__init__(self)
            self._instances = {}
            self.id_name = "RabbitVCSContextMenuID"

        def do_activate(self):
            self._instances[self.window] = RabbitVCSWindowHelper(self, self.window)

            handler_ids = []
            for signal in ('tab-added', 'tab-removed'):
                method = getattr(self, 'on_window_' + signal.replace('-', '_'))
                handler_ids.append(self.window.connect(signal, method))
            
            self.window.set_data(self.id_name, handler_ids)
            if self.window in self._instances:
                for view in self.window.get_views():
                    self._instances[self.window].connect_view(view, self.id_name)

        def do_deactivate(self):
            widgets = [self.window] + self.window.get_views()
            for widget in widgets:
                handler_ids = widget.get_data(self.id_name)
                if handler_ids is not None:
                    for handler_id in handler_ids:
                        widget.disconnect(handler_id)
                    widget.set_data(self.id_name, None)

            if self.window in self._instances:
                self._instances[self.window].deactivate()
                del self._instances[self.window]

        def do_update_state(self):
            self.update_ui()

        def update_ui(self):
            if self.window in self._instances:
                self._instances[self.window].update_ui()

        def on_window_tab_added(self, window, tab):
            if self.window in self._instances:
                self._instances[self.window].connect_view(tab.get_view(), self.id_name)
        
        def on_window_tab_removed(self, window, tab):
            if window in self._instances:
                self._instances[self.window].disconnect_view(tab.get_view(), self.id_name)
else:
    class RabbitVCSGedit2Plugin(gedit.Plugin):
        def __init__(self):
            gedit.Plugin.__init__(self)
            self._instances = {}
            self.id_name = "RabbitVCSContextMenuID"

        def activate(self, window):
            self._instances[window] = RabbitVCSWindowHelper(self, window)

            handler_ids = []
            for signal in ('tab-added', 'tab-removed'):
                method = getattr(self, 'on_window_' + signal.replace('-', '_'))
                handler_ids.append(window.connect(signal, method))
            
            window.set_data(self.id_name, handler_ids)
            if window in self._instances:
                for view in window.get_views():
                    self._instances[window].connect_view(view, self.id_name)

        def deactivate(self, window):
            widgets = [window] + window.get_views()
            for widget in widgets:
                handler_ids = widget.get_data(self.id_name)
                if handler_ids is not None:
                    for handler_id in handler_ids:
                        widget.disconnect(handler_id)
                    widget.set_data(self.id_name, None)

            if window in self._instances:
                self._instances[window].deactivate()
                del self._instances[window]

        def update_ui(self, window):
            if window in self._instances:
                self._instances[window].update_ui()

        def on_window_tab_added(self, window, tab):
            if window in self._instances:
                self._instances[window].connect_view(tab.get_view(), self.id_name)
        
        def on_window_tab_removed(self, window, tab):
            if window in self._instances:
                self._instances[window].disconnect_view(tab.get_view(), self.id_name)

class MenuIgnoreByFilename(MenuItem):
    identifier = "RabbitVCS::Ignore_By_Filename"
    label = _("Ignore by File Name")
    tooltip = _("Ignore item by filename")

class MenuIgnoreByFileExtension(MenuItem):
    identifier = "RabbitVCS::Ignore_By_File_Extension"
    label = _("Ignore by File Extension")
    tooltip = _("Ignore item by extension")

class GeditMenuBuilder(object):
    """
    Generalised menu builder class. Subclasses must provide:
    
    make_menu_item(self, item, id_magic) - create the menu item for whatever
    toolkit (usually this should be just call a  convenience method on the
    MenuItem instance).
    
    attach_submenu(self, menu_node, submenu_list) - given a list of whatever
    make_menu_item(...) returns, create a submenu and attach it to the given
    node.
    
    top_level_menu(self, items) - in some circumstances we need to treat the top
    level menu differently (eg. Nautilus, because Xenu said so). This processes
    a list of menu items returned by make_menu_item(...) to create the overall
    menu.  
    """
    
    def __init__(self, structure, conditions, callbacks, action_group):
        """
        @param  structure: Menu structure
        @type   structure: list
                
        Note on "structure". The menu structure is defined in a list of tuples 
        of two elements each.  The first element is a class - the MenuItem
        subclass that defines the menu interface (see below).
        
        The second element is either None (if there is no submenu) or a list of
        tuples if there is a submenu.  The submenus are generated recursively. 
        FYI, this is a list of tuples so that we retain the desired menu item
        order (dicts do not retain order)
        
            Example:
            [
                (MenuClassOne, [
                    (MenuClassOneSubA,
                    (MenuClassOneSubB
                ]),
                (MenuClassTwo,
                (MenuClassThree
            ]
            
        """

        self.action_group = action_group

        for item_class in structure:
            
            item = item_class(conditions, callbacks)

            default_name = MenuItem.make_default_name(item.identifier)            
            action = RabbitVCSAction(item.identifier, item.label, item.tooltip, item.icon)

            if item.icon and hasattr(action, "set_icon_name"):
                action.set_icon_name(item.icon)
           
            if item.callback:
                if item.callback_args:
                    action.connect("activate", item.callback, item.callback_args)
                else:
                    action.connect("activate", item.callback)
            
            action.set_property("visible", item.show())
            
            action.set_data("item", item)
             
            self.action_group.add_action(action)

    def _get_function(self, object, name):
        
        function = None
        
        if hasattr(object, name):
            
            attr = getattr(object, name)
            if callable(attr):
                function = attr
        
        return function
        
class GeditMenu:
    def __init__(self, caller, vcs_client, base_dir, paths):
        """    
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  vcs_client: The vcs client
        @type   vcs_client: rabbitvcs.vcs
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list
        
        @param  conditions: The conditions class that determines menu item visibility
        @kind   conditions: ContextMenuConditions
        
        @param  callbacks: The callbacks class that determines what actions are taken
        @kind   callbacks: ContextMenuCallbacks
        
        """        
        self.caller = caller
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        
        self.conditions = GtkFilesContextMenuConditions(self.vcs_client, self.paths)

        self.callbacks = GtkFilesContextMenuCallbacks(
            self.caller, 
            self.base_dir,
            self.vcs_client, 
            self.paths
        )

        self.structure = [
            MenuRabbitVCSSvn,
            MenuRabbitVCSGit,
            MenuCheckout,
            MenuUpdate,
            MenuCommit,
            MenuPush,
            MenuInitializeRepository,
            MenuClone,
            MenuRabbitVCS,
            MenuDiffMenu, 
            MenuDiff,
            MenuDiffPrevRev,
            MenuDiffMultiple,
            MenuCompareTool,
            MenuCompareToolPrevRev,
            MenuCompareToolMultiple,
            MenuShowChanges,
            MenuShowLog,
            MenuRepoBrowser,
            MenuCheckForModifications,
            MenuAdd,
            MenuStage,
            MenuUnstage,
            MenuAddToIgnoreList, 
            MenuUpdateToRevision,
            MenuRename,
            MenuDelete,
            MenuRevert,
            MenuEditConflicts,
            MenuMarkResolved,
            MenuRelocate,
            MenuGetLock,
            MenuUnlock,
            MenuClean,
            MenuReset,
            MenuCleanup,
            MenuExport,
            MenuCreateRepository,
            MenuImport,
            MenuBranches,
            MenuTags,
            MenuRemotes,
            MenuBranchTag,
            MenuSwitch,
            MenuMerge,
            MenuAnnotate,
            MenuCreatePatch,
            MenuApplyPatch,
            MenuProperties,
            MenuHelp,
            MenuSettings,
            MenuAbout,
            MenuIgnoreByFilename,
            MenuIgnoreByFileExtension
        ]

    def set_paths(self, paths):
        self.paths = paths
        self.conditions.paths = paths
        self.callbacks.paths = paths

    def set_base_dir(self, base_dir):
        self.base_dir = base_dir
        self.callbacks.base_dir = base_dir
        self.conditions.base_dir = base_dir

    def get_action_group(self, action_group):
        return GeditMenuBuilder(self.structure, self.conditions, self.callbacks, action_group).action_group
    
    def update_conditions(self, paths):
        self.conditions.generate_statuses(paths)
        self.conditions.generate_path_dict(paths)
    
    def update_action(self, action):
        action.set_property("visible", action.get_data("item").show())

class GeditContextMenu(MenuBuilder):
    """
    Provides a standard gtk context menu (ie. a list of
    "gtk.MenuItem"s).
    """

    signal = "activate"
        
    def make_menu_item(self, item, id_magic):
        if GTK3:
            return item.make_gtk3_menu_item(id_magic)
        else:
            return item.make_gtk_menu_item(id_magic)
    
    def attach_submenu(self, menu_node, submenu_list):
        submenu = gtk.Menu()
        menu_node.set_submenu(submenu)
        [submenu.append(item) for item in submenu_list]
    
    def top_level_menu(self, items):
        return items

class GeditMainContextMenu(MainContextMenu):
    def __init__(self, caller, vcs_client, base_dir, paths=[], 
            conditions=None, callbacks=None):
        """    
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  vcs_client: The vcs client
        @type   vcs_client: rabbitvcs.vcs
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list
        
        @param  conditions: The conditions class that determines menu item visibility
        @kind   conditions: ContextMenuConditions
        
        @param  callbacks: The callbacks class that determines what actions are taken
        @kind   callbacks: ContextMenuCallbacks
        
        """        
        self.caller = caller
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = vcs_client

        self.conditions = conditions
        if self.conditions is None:
            self.conditions = GtkFilesContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = MainContextMenuCallbacks(
                self.caller, 
                self.base_dir,
                self.vcs_client, 
                paths
            )
            
        ignore_items = get_ignore_list_items(paths)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.        
        self.structure = [
            (MenuUpdate, None),
            (MenuCommit, None),
            (MenuPush, None),
            (MenuRabbitVCSSvn, [
                (MenuCheckout, None),
                (MenuDiffMenu, [
                    (MenuDiff, None),
                    (MenuDiffPrevRev, None),
                    (MenuDiffMultiple, None),
                    (MenuCompareTool, None),
                    (MenuCompareToolPrevRev, None),
                    (MenuCompareToolMultiple, None),
                    (MenuShowChanges, None),
                ]),
                (MenuShowLog, None),
                (MenuRepoBrowser, None),
                (MenuCheckForModifications, None),
                (MenuSeparator, None),
                (MenuAdd, None),
                (MenuAddToIgnoreList, ignore_items),
                (MenuSeparator, None),
                (MenuUpdateToRevision, None),
                (MenuRename, None),
                (MenuDelete, None),
                (MenuRevert, None),
                (MenuEditConflicts, None),
                (MenuMarkResolved, None),
                (MenuRelocate, None),
                (MenuGetLock, None),
                (MenuUnlock, None),
                (MenuCleanup, None),
                (MenuSeparator, None),
                (MenuExport, None),
                (MenuCreateRepository, None),
                (MenuImport, None),
                (MenuSeparator, None),
                (MenuBranchTag, None),
                (MenuSwitch, None),
                (MenuMerge, None),
                (MenuSeparator, None),
                (MenuAnnotate, None),
                (MenuSeparator, None),
                (MenuCreatePatch, None),
                (MenuApplyPatch, None),
                (MenuProperties, None),
                (MenuSeparator, None),
                (MenuSettings, None),
                (MenuAbout, None)
            ]),
            (MenuRabbitVCSGit, [
                (MenuClone, None),
                (MenuInitializeRepository, None),
                (MenuSeparator, None),
                (MenuDiffMenu, [
                    (MenuDiff, None),
                    (MenuDiffPrevRev, None),
                    (MenuDiffMultiple, None),
                    (MenuCompareTool, None),
                    (MenuCompareToolPrevRev, None),
                    (MenuCompareToolMultiple, None),
                    (MenuShowChanges, None),
                ]),
                (MenuShowLog, None),
                (MenuStage, None),
                (MenuUnstage, None),
                (MenuAddToIgnoreList, ignore_items),
                (MenuSeparator, None),
                (MenuRename, None),
                (MenuDelete, None),
                (MenuRevert, None),
                (MenuEditConflicts, None),
                (MenuClean, None),
                (MenuReset, None),
                (MenuCheckout, None),
                (MenuSeparator, None),
                (MenuBranches, None),
                (MenuTags, None),
                (MenuRemotes, None),
                (MenuSeparator, None),
                (MenuExport, None),
                (MenuMerge, None),
                (MenuSeparator, None),
                (MenuAnnotate, None),
                (MenuSeparator, None),
                (MenuCreatePatch, None),
                (MenuApplyPatch, None),
                (MenuSeparator, None),
                (MenuSettings, None),
                (MenuAbout, None)
            ])
        ]
        
    def get_menu(self):
        return GeditContextMenu(self.structure, self.conditions, self.callbacks).menu
