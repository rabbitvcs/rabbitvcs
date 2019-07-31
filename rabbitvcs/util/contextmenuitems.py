from __future__ import absolute_import
#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2010 by Jason Heeris <jason.heeris@gmail.com>
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

import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from rabbitvcs.util import helper
from rabbitvcs.util.strings import S

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.ui.contextmenuitems")
_ = gettext.gettext


SEPARATOR = u'\u2015' * 10

class MenuItem(object):
    """
    This is the base class for a definition of a menu item. Consider this
    "abstract" (in the language of Java) - it makes no sense to instantiate it
    directly. If you want to define a new kind of menu item, you need to
    subclass it like so:

    class MenuPerformMagic:
        identifier = "RabbitVCS::Perform_Magic"
        label = _("Perform Magic")
        tooltip = _("Put on your robe and wizard hat")
        icon = "rabbitvcs-wand"

    There is some introspection magic that goes on to associate the items
    themselves with certain methods of a ContextMenuCondition object or a
    ContextMenuCallback object. This is done by looking at the identifier - the
    part of the identifier after "::" is converted to lowercase and the item
    looks for a method of that name (eg. in the example above,
    "perform_magic").

    It is easy to override this, just define condition_name and callback_name
    to be what you need. If the item cannot find anything, it defaults to not
    assigning the callback and having the condition return False.

    There a few ways to organise this (and maybe it would be better to have the
    GtkContextMenu class do it), but this is it for the moment.
    """

    @staticmethod
    def default_condition(*args, **kwargs):
        return False

    @staticmethod
    def make_default_name(identifier):
        return identifier.split(MenuItem.IDENTIFIER_SEPARATOR)[-1].lower()

    IDENTIFIER_SEPARATOR = "::"

    # These are all explicitly defined here to make it obvious what a subclass
    # needs to set up.

    # This is relevant for GTK and Nautilus - they require unique identifiers
    # for all the elements of their menus. Make sure it starts with
    # "RabbitVCS::"
    identifier = None

    # The label that appears on the menu item. It is up to the subclass to
    # designate it as translatable.
    label = None

    # The tooltip for the menu item. It is up to the subclass to designate it as
    # translatable.
    tooltip = ""

    # The icon that will appear on the menu item. This can be, say,
    # "rabbitvcs-something"
    icon = None

    # This is a string that holds the name of the function that is called when
    # the menu item is activated (it is assigned to
    # self.signals["activate"]["callback"])
    #
    # The menu item will look for a callable attribute of this name in the
    # callback object passed in to the constructor. If it is None, it will try
    # to assign a default callback based on the identifier. If nothing is found
    # then no callback will be assigned to the "activate" signal.
    callback_name = None
    callback_args = ()


    # This is a string that holds the name of the function that is called to
    # determine whether to show the item.
    #
    # The menu item will look for a callable attribute of this name in the
    # callback object passed in to the constructor. If it is None, or False, or
    # it cannot find anything, it will set up a function that returns False.
    condition_name = None
    condition_args = ()

    def __init__(self, conditions, callbacks):
        """
        Creates a new menu item for constructing the GTK context menu.
        """

        self.signals = {}

        default_name = MenuItem.make_default_name(self.identifier)

        # These flags are used for sanity checks that developers can run to
        # ensure completeness of conditions and callbacks.
        # See contextmenu.TestMenuItemFunctions()
        self.found_callback = False
        self.found_condition = False

        # If no callback name is set, assign the default
        if self.callback_name is None:
            # log.debug("Using default callback name: %s" % default_name)
            self.callback_name = default_name

        # Try to get the callback function for this item
        self.callback = self._get_function(callbacks, self.callback_name)

#        else:
#            log.debug("Could not find callback for %s" % self.identifier)

        self.condition = {
            "callback": MenuItem.default_condition,
            "args": self.condition_args
            }

        if self.condition_name is None:
            self.condition_name = default_name

        condition = self._get_function(conditions, self.condition_name)

        if condition:
            self.condition["callback"] = condition
            self.found_condition = True
#        else:
#            log.debug("Could not find condition for %s" % self.identifier)

    def show(self):
        return self.condition["callback"](*self.condition["args"])

    def _get_function(self, object, name):

        function = None

        if hasattr(object, name):

            attr = getattr(object, name)
            if callable(attr):
                function = attr

        return function

    def make_magic_id(self, id_magic = None):
        identifier = self.identifier

        if id_magic:
            identifier = identifier + "-" + str(id_magic)

        return identifier

    def make_action(self, id_magic = None):
        """
        Creates the Action for the menu item. To avoid GTK "helpfully"
        preventing us from adding duplicates (eg. separators), you can pass in
        a string that will be appended and separated from the actual identifier.
        """
        identifier = self.make_magic_id(id_magic)

        return Action(identifier, self.make_label(), None, None)

    def make_thunar_action(self, id_magic = None):
        identifier = self.make_magic_id(id_magic)

        action = RabbitVCSAction(
            identifier,
            self.make_label(),
            self.tooltip,
            self.icon
        )

        return action

    def make_gtk_menu_item(self, id_magic = None):
        action = self.make_action(id_magic)

        if self.icon:
            # We use this instead of Gtk.Action.set_icon_name because
            # that method is not available until pyGtk 2.16
            action.set_menu_item_type(Gtk.ImageMenuItem)
            menuitem = action.create_menu_item()
            menuitem.set_image(Gtk.image_new_from_icon_name(self.icon, Gtk.IconSize.MENU))
        else:
            menuitem = action.create_menu_item()

        return menuitem

    def make_gtk3_menu_item(self, id_magic = None):
        action = self.make_action(id_magic)
        menuitem = action.create_menu_item()

        if self.icon:
            menuitem.set_image(Gtk.Image.new_from_icon_name(self.icon, Gtk.IconSize.MENU))

        return menuitem

    def make_thunarx_menu_item(self, id_magic = None):
        # WARNING: this import is here because it will fail if it is not done
        # inside a thunar process and therefore can't be in the module proper.
        # This should only be used for Thunarx-3
        identifier = self.make_magic_id(id_magic)

        from gi.repository import Thunarx
        menuitem = Thunarx.MenuItem(
            name=identifier,
            label=self.make_label(),
            tooltip=self.tooltip,
            icon=self.icon
        )

        return menuitem

    def make_nautilus_menu_item(self, id_magic = None):
        # WARNING: this import is here because it will fail if it is not done
        # inside a nautilus process and therefore can't be in the module proper.
        # I'm happy to let the exception propagate the rest of the time, since
        # this method shouldn't be called outside of nautilus.
        identifier = self.make_magic_id(id_magic)

        try:
            from gi.repository import Nautilus
            menuitem = Nautilus.MenuItem(
                name=identifier,
                label=self.make_label(),
                tip=self.tooltip,
                icon=self.icon
            )
        except ImportError:
            import nautilus
            menuitem = nautilus.MenuItem(
                identifier,
                self.make_label(),
                self.tooltip,
                self.icon
            )

        return menuitem

    def make_label(self):
        label = S(self.label).display().replace('_', '__')
        return label

class MenuSeparator(MenuItem):
    identifier = "RabbitVCS::Separator"
    label = SEPARATOR

    def make_insensitive(self, menuitem):
        menuitem.set_property("sensitive", False)

    def make_thunar_action(self, id_magic = None):
        menuitem = super(MenuSeparator, self).make_thunar_action(id_magic)
        self.make_insensitive(menuitem)
        return menuitem
        # FIXME: I thought that this would work to create separators,
        # but all I get are black "-"s...
        # I thought
        #~ identifier = self.make_magic_id(id_magic)
        #~ # This information is not actually used, but is necessary for
        #~ # the required subclassing of Action.
        #~ action = ThunarSeparator(
            #~ identifier,
            #~ self.label,
            #~ self.tooltip,
            #~ self.icon,
        #~ )
        #~ return action

    # Make separators insensitive
    def make_gtk_menu_item(self, id_magic = None):
        menuitem = Gtk.SeparatorMenuItem()
        menuitem.show()
        return menuitem

    def make_gtk3_menu_item(self, id_magic = None):
        menuitem = Gtk.SeparatorMenuItem()
        menuitem.show()
        return menuitem

    def make_nautilus_menu_item(self, id_magic = None):
        menuitem = super(MenuSeparator, self).make_nautilus_menu_item(id_magic)
        self.make_insensitive(menuitem)
        return menuitem

class MenuDebug(MenuItem):
    identifier = "RabbitVCS::Debug"
    label = _("Debug")
    icon = "rabbitvcs-monkey"

class MenuBugs(MenuItem):
    identifier = "RabbitVCS::Bugs"
    label = _("Bugs")
    icon = "rabbitvcs-bug"

class MenuDebugShell(MenuItem):
    identifier = "RabbitVCS::Debug_Shell"
    label = _("Open Shell")
    icon = "gnome-terminal"
    condition_name = "debug"

class MenuRefreshStatus(MenuItem):
    identifier = "RabbitVCS::Refresh_Status"
    label = _("Refresh Status")
    icon = "rabbitvcs-refresh"

class MenuDebugRevert(MenuItem):
    identifier = "RabbitVCS::Debug_Revert"
    label = _("Debug Revert")
    tooltip = _("Reverts everything it sees")
    icon = "rabbitvcs-revert"
    condition_name = "debug"

class MenuDebugInvalidate(MenuItem):
    identifier = "RabbitVCS::Debug_Invalidate"
    label = _("Invalidate")
    tooltip = _("Force an invalidate_extension_info() call")
    icon = "rabbitvcs-clear"
    condition_name = "debug"

class MenuDebugAddEmblem(MenuItem):
    identifier = "RabbitVCS::Debug_Add_Emblem"
    label = _("Add Emblem")
    tooltip = _("Add an emblem")
    icon = "rabbitvcs-emblems"
    condition_name = "debug"

class MenuCheckout(MenuItem):
    identifier = "RabbitVCS::Checkout"
    label = _("Checkout...")
    tooltip = _("Check out a working copy")
    icon = "rabbitvcs-checkout"

class MenuUpdate(MenuItem):
    identifier = "RabbitVCS::Update"
    label = _("Update")
    tooltip = _("Update a working copy")
    icon = "rabbitvcs-update"

class MenuCommit(MenuItem):
    identifier = "RabbitVCS::Commit"
    label = _("Commit")
    tooltip = _("Commit modifications to the repository")
    icon = "rabbitvcs-commit"

class MenuRabbitVCS(MenuItem):
    identifier = "RabbitVCS::RabbitVCS"
    label = _("RabbitVCS")
    icon = "rabbitvcs"

class MenuRabbitVCSSvn(MenuItem):
    identifier = "RabbitVCS::RabbitVCS_Svn"
    label = _("RabbitVCS SVN")
    icon = "rabbitvcs"

class MenuRabbitVCSGit(MenuItem):
    identifier = "RabbitVCS::RabbitVCS_Git"
    label = _("RabbitVCS Git")
    icon = "rabbitvcs"

class MenuRabbitVCSMercurial(MenuItem):
    identifier = "RabbitVCS::RabbitVCS_Mercurial"
    label = _("RabbitVCS Hg")
    icon = "rabbitvcs"

class MenuRepoBrowser(MenuItem):
    identifier = "RabbitVCS::Repo_Browser"
    label = _("Repository Browser")
    tooltip = _("Browse a repository tree")
    icon = "edit-find"

class MenuCheckForModifications(MenuItem):
    identifier = "RabbitVCS::Check_For_Modifications"
    label = _("Check for Modifications...")
    tooltip = _("Check for modifications made to the repository")
    icon = "rabbitvcs-checkmods"

class MenuDiffMenu(MenuItem):
    identifier = "RabbitVCS::Diff_Menu"
    label = _("Diff Menu...")
    tooltip = _("List of comparison options")
    icon = "rabbitvcs-diff"

class MenuDiff(MenuItem):
    identifier = "RabbitVCS::Diff"
    label = _("View diff against base")
    tooltip = _("View the modifications made to a file")
    icon = "rabbitvcs-diff"

class MenuDiffMultiple(MenuItem):
    identifier = "RabbitVCS::Diff_Multiple"
    label = _("View diff between files/folders")
    tooltip = _("View the differences between two files")
    icon = "rabbitvcs-diff"

class MenuDiffPrevRev(MenuItem):
    identifier = "RabbitVCS::Diff_Previous_Revision"
    label = _("View diff against previous revision")
    tooltip = _("View the modifications made to a file since its last change")
    icon = "rabbitvcs-diff"

class MenuCompareTool(MenuItem):
    identifier = "RabbitVCS::Compare_Tool"
    label = _("Compare with base")
    tooltip = _("Compare with base using side-by-side comparison tool")
    icon = "rabbitvcs-compare"

class MenuCompareToolMultiple(MenuItem):
    identifier = "RabbitVCS::Compare_Tool_Multiple"
    label = _("Compare files/folders")
    tooltip = _("Compare the differences between two items")
    icon = "rabbitvcs-compare"

class MenuCompareToolPrevRev(MenuItem):
    identifier = "RabbitVCS::Compare_Tool_Previous_Revision"
    label = _("Compare with previous revision")
    tooltip = _("Compare with previous revision using side-by-side comparison tool")
    icon = "rabbitvcs-compare"

class MenuShowChanges(MenuItem):
    identifier = "RabbitVCS::Show_Changes"
    label = _("Show Changes...")
    tooltip = _("Show changes between paths and revisions")
    icon = "rabbitvcs-changes"

class MenuShowLog(MenuItem):
    identifier = "RabbitVCS::Show_Log"
    label = _("Show Log")
    tooltip = _("Show a file's log information")
    icon = "rabbitvcs-show_log"

class MenuAdd(MenuItem):
    identifier = "RabbitVCS::Add"
    label = _("Add")
    tooltip = _("Schedule items to be added to the repository")
    icon = "rabbitvcs-add"

class MenuAddToIgnoreList(MenuItem):
    identifier = "RabbitVCS::Add_To_Ignore_List"
    label = _("Add to ignore list")
    icon = None

class MenuUpdateToRevision(MenuItem):
    identifier = "RabbitVCS::Update_To_Revision"
    label = _("Update to revision...")
    tooltip = _("Update a file to a specific revision")
    icon = "rabbitvcs-update"

class MenuRename(MenuItem):
    identifier = "RabbitVCS::Rename"
    label = _("Rename...")
    tooltip = _("Schedule an item to be renamed on the repository")
    icon = "rabbitvcs-rename"

class MenuDelete(MenuItem):
    identifier = "RabbitVCS::Delete"
    label = _("Delete")
    tooltip = _("Schedule an item to be deleted from the repository")
    icon = "rabbitvcs-delete"

class MenuRevert(MenuItem):
    identifier = "RabbitVCS::Revert"
    label = _("Revert")
    tooltip = _("Revert an item to its unmodified state")
    icon = "rabbitvcs-revert"

class MenuMarkResolved(MenuItem):
    identifier = "RabbitVCS::Mark_Resolved"
    label = _("Mark as Resolved")
    tooltip = _("Mark a conflicted item as resolved")
    icon = "rabbitvcs-resolve"

class MenuRestore(MenuItem):
    identifier = "RabbitVCS::Restore"
    label = _("Restore")
    tooltip = _("Restore a missing item")

class MenuRelocate(MenuItem):
    identifier = "RabbitVCS::Relocate"
    label = _("Relocate...")
    tooltip = _("Relocate your working copy")
    icon = "rabbitvcs-relocate"

class MenuGetLock(MenuItem):
    identifier = "RabbitVCS::Get_Lock"
    label = _("Get Lock...")
    tooltip = _("Locally lock items")
    icon = "rabbitvcs-lock"

class MenuUnlock(MenuItem):
    identifier = "RabbitVCS::Unlock"
    label = _("Release Lock...")
    tooltip = _("Release lock on an item")
    icon = "rabbitvcs-unlock"

class MenuCleanup(MenuItem):
    identifier = "RabbitVCS::Cleanup"
    label = _("Cleanup")
    tooltip = _("Clean up working copy")
    icon = "rabbitvcs-cleanup"

class MenuExport(MenuItem):
    identifier = "RabbitVCS::Export"
    label = _("Export...")
    tooltip = _("Export a working copy or repository with no versioning information")
    icon = "rabbitvcs-export"

class MenuSVNExport(MenuExport):
    identifier = "RabbitVCS::SVN_Export"
    pass

class MenuGitExport(MenuExport):
    identifier = "RabbitVCS::Git_Export"
    pass

class MenuCreateRepository(MenuItem):
    identifier = "RabbitVCS::Create_Repository"
    label = _("Create Repository here")
    tooltip = _("Create a repository in a folder")
    icon = "rabbitvcs-run"

class MenuImport(MenuItem):
    identifier = "RabbitVCS::Import"
    label = _("Import")
    tooltip = _("Import an item into a repository")
    icon = "rabbitvcs-import"
    # "import" is reserved
    condition_name = "_import"
    callback_name = "_import"


class MenuBranchTag(MenuItem):
    identifier = "RabbitVCS::Branch_Tag"
    label = _("Branch/tag...")
    tooltip = _("Copy an item to another location in the repository")
    icon = "rabbitvcs-branch"

class MenuSwitch(MenuItem):
    identifier = "RabbitVCS::Switch"
    label = _("Switch...")
    tooltip = _("Change the repository location of a working copy")
    icon = "rabbitvcs-switch"

class MenuMerge(MenuItem):
    identifier = "RabbitVCS::Merge"
    label = _("Merge...")
    tooltip = _("A wizard with steps for merging")
    icon = "rabbitvcs-merge"

class MenuAnnotate(MenuItem):
    identifier = "RabbitVCS::Annotate"
    label = _("Annotate...")
    tooltip = _("Annotate a file")
    icon = "rabbitvcs-annotate"

class MenuCreatePatch(MenuItem):
    identifier = "RabbitVCS::Create_Patch"
    label = _("Create Patch...")
    tooltip = _("Creates a unified diff file with all changes you made")
    icon = "rabbitvcs-createpatch"

class MenuApplyPatch(MenuItem):
    identifier = "RabbitVCS::Apply_Patch"
    label = _("Apply Patch...")
    tooltip = _("Applies a unified diff file to the working copy")
    icon = "rabbitvcs-applypatch"

class MenuProperties(MenuItem):
    identifier = "RabbitVCS::Properties"
    label = _("Properties")
    tooltip = _("View the properties of an item")
    icon = "rabbitvcs-properties"

class MenuHelp(MenuItem):
    identifier = "RabbitVCS::Help"
    label = _("Help")
    tooltip = _("View help")
    icon = "rabbitvcs-help"

class MenuSettings(MenuItem):
    identifier = "RabbitVCS::Settings"
    label = _("Settings")
    tooltip = _("View or change RabbitVCS settings")
    icon = "rabbitvcs-settings"

class MenuAbout(MenuItem):
    identifier = "RabbitVCS::About"
    label = _("About")
    tooltip = _("About RabbitVCS")
    icon = "rabbitvcs-about"

class MenuOpen(MenuItem):
    identifier = "RabbitVCS::Open"
    label = _("Open")
    tooltip = _("Open a file")
    icon = "document-open"
    # Not sure why, but it was like this before...
    condition_name = "_open"
    callback_name = "_open"

class MenuBrowseTo(MenuItem):
    identifier = "RabbitVCS::Browse_To"
    label = _("Browse to")
    tooltip = _("Browse to a file or folder")
    icon = "drive-harddisk"

class PropMenuRevert(MenuItem):
    identifier = "RabbitVCS::Property_Revert"
    label = _("Revert property")
    icon =  "rabbitvcs-revert"
    tooltip = _("Revert this property to its original state")

class PropMenuRevertRecursive(MenuItem):
    identifier = "RabbitVCS::Property_Revert_Recursive"
    label = _("Revert property (recursive)")
    icon =  "rabbitvcs-revert"
    tooltip = _("Revert this property to its original state (recursive)")
    condition_name = "property_revert"

class PropMenuDelete(MenuItem):
    identifier = "RabbitVCS::Property_Delete"
    label = _("Delete property")
    icon =  "rabbitvcs-delete"
    tooltip = _("Delete this property")

class PropMenuDeleteRecursive(MenuItem):
    identifier = "RabbitVCS::Property_Delete_Recursive"
    label = _("Delete property (recursive)")
    icon =  "rabbitvcs-delete"
    tooltip = _("Delete this property (recursive)")
    condition_name = "property_delete"

class PropMenuEdit(MenuItem):
    identifier = "RabbitVCS::Property_Edit"
    label = _("Edit details")
    icon = "rabbitvcs-editprops"
    tooltip = _("Show and edit property details")

class MenuInitializeRepository(MenuItem):
    identifier = "RabbitVCS::Initialize_Repository"
    label = _("Initialize Repository")
    icon = "rabbitvcs-run"

class MenuClone(MenuItem):
    identifier = "RabbitVCS::Clone"
    label = _("Clone")
    icon = "rabbitvcs-checkout"

class MenuFetchPull(MenuItem):
    identifier = "RabbitVCS::Fetch_Pull"
    label = _("Fetch/Pull")
    icon = "rabbitvcs-update"

class MenuPush(MenuItem):
    identifier = "RabbitVCS::Push"
    label = _("Push")
    icon = "rabbitvcs-push"

class MenuBranches(MenuItem):
    identifier = "RabbitVCS::Branches"
    label = _("Branches")
    icon = "rabbitvcs-branch"

class MenuTags(MenuItem):
    identifier = "RabbitVCS::Tags"
    label = _("Tags")
    icon = "rabbitvcs-branch"

class MenuRemotes(MenuItem):
    identifier = "RabbitVCS::Remotes"
    label = _("Remotes")
    icon = "rabbitvcs-checkmods"

class MenuClean(MenuCleanup):
    identifier = "RabbitVCS::Clean"
    label = _("Clean")

class MenuReset(MenuItem):
    identifier = "RabbitVCS::Reset"
    label = _("Reset")
    icon = "rabbitvcs-reset"

class MenuStage(MenuItem):
    identifier = "RabbitVCS::Stage"
    label = _("Stage")
    icon = "rabbitvcs-add"

class MenuUnstage(MenuItem):
    identifier = "RabbitVCS::Unstage"
    label = _("Unstage")
    icon = "rabbitvcs-unstage"

class MenuEditConflicts(MenuItem):
    identifier = "RabbitVCS::Edit_Conflicts"
    label = _("Edit conflicts")
    icon = "rabbitvcs-editconflicts"

def get_ignore_list_items(paths):
    """
    Build up a list of items to ignore based on the selected paths

    @param  paths: The selected paths
    @type   paths: list

    """
    ignore_items = []

    # Used to weed out duplicate menu items
    added_ignore_labels = []

    # These are ignore-by-filename items
    ignorebyfilename_index = 0
    for path in paths:
        basename = os.path.basename(path)
        if basename not in added_ignore_labels:
            key = "IgnoreByFileName%s" % str(ignorebyfilename_index)

            class MenuIgnoreFilenameClass(MenuItem):
                identifier = "RabbitVCS::%s" % key
                label = basename
                tooltip = _("Ignore item by filename")
                callback_name = "ignore_by_filename"
                callback_args = (path)
                condition_name = "ignore_by_filename"
                condition_args = (path)

            ignore_items.append((MenuIgnoreFilenameClass, None))

    # These are ignore-by-extension items
    ignorebyfileext_index = 0
    for path in paths:
        extension = helper.get_file_extension(path)

        ext_str = "*%s"%extension
        if ext_str not in added_ignore_labels:

            class MenuIgnoreFileExtClass(MenuItem):
                identifier = "RabbitVCS::%s" % key
                label = ext_str
                tooltip = _("Ignore item by file extension")
                callback_name = "ignore_by_file_extension"
                callback_args = (path, extension)
                condition_name = "ignore_by_file_extension"
                condition_args = (path, extension)

            ignore_items.append((MenuIgnoreFileExtClass, None))

    return ignore_items

class Action(object):
    def __init__(self, name, label, tooltip, icon_name):
        self.name = name
        self.label = label
        self.tooltip = tooltip
        self.icon_name = icon_name

    def __repr__(self):
        return self.get_name()

    def create_menu_item(self):
        item = Gtk.ImageMenuItem()
        if self.label:
            item.set_label(self.label)
        if self.tooltip:
            item.set_tooltip_text(self.tooltip)
        if self.icon_name:
            item.set_image(Gtk.image_new_from_icon_name(self.icon_name, Gtk.IconSize.MENU))
        return item

class RabbitVCSAction(Action):
    """
    Sub-classes Action so that we can have submenus.
    This is needed for context menus that use Gtk actions
    """

    __gtype_name__ = "RabbitVCSAction"

    def __init__(self, name, label, tooltip, icon_name):
        Action.__init__(self, name, label, tooltip, icon_name)
        self.sub_actions = None

    def set_sub_actions(self, sub_actions):
        self.sub_actions = sub_actions

    def create_menu_item(self):
        menu_item = super(RabbitVCSAction, self).create_menu_item()
        if self.sub_actions is not None:
            menu = Gtk.Menu()
            menu_item.set_submenu(menu)

            for sub_action in self.sub_actions:
                subitem = sub_action.create_menu_item()
                menu.append(subitem)
                subitem.show()

        return menu_item

# FIXME: apparently it's possible to get real GtkSeparators in a Thunar
# menu, but this doesn't seem to work.
class ThunarSeparator(RabbitVCSAction):

    def create_menu_item(self):
        return Gtk.SeparatorMenuItem()
