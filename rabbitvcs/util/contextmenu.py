from __future__ import absolute_import
from __future__ import print_function

#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2010 by Jason Heeris <jason.heeris@gmail.com>
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
import os.path
from time import sleep
from collections import deque
from six.moves import range

# Yes, * imports are bad. You write it out then.
from .contextmenuitems import *

from rabbitvcs.util import helper

import gi

try:
    gi.require_version("Gtk", "3.0")
except:
    gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GLib

sa.restore()

from rabbitvcs.vcs import (
    create_vcs_instance,
    VCS_SVN,
    VCS_GIT,
    VCS_DUMMY,
    VCS_MERCURIAL,
)
from rabbitvcs.util.log import Log
from rabbitvcs import gettext
from rabbitvcs.util.settings import SettingsManager
import rabbitvcs.vcs

log = Log("rabbitvcs.util.contextmenu")
_ = gettext.gettext

settings = SettingsManager()


class MenuBuilder(object):
    """
    Generalised menu builder class. Subclasses must provide:

    connect_to_signal(self, menuitem, callback, callback_args) - connect the
    menu item to a signal (or do whatever needs to be done) so that the callback
    is called upon activation.

    In actual fact, a standard GTK compatible method for this is provided by
    this class. All a subclass has to do is define the class parameter "signal",
    and it will be automatically done.

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

    def __init__(self, structure, conditions, callbacks):
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
                    (MenuClassOneSubA, None),
                    (MenuClassOneSubB, None)
                ]),
                (MenuClassTwo, None),
                (MenuClassThree, None)
            ]

        """
        # The index is mostly for identifier magic
        index = 0
        last_level = -1
        last_item = last_menuitem = None

        stack = []  # ([items], last_item, last_menuitem)
        flat_structure = helper.walk_tree_depth_first(
            structure,
            show_levels=True,
            preprocess=lambda x: x(conditions, callbacks),
            filter=lambda x: x.show(),
        )

        # Here's how this works: we walk the tree, which is a series of (level,
        # MenuItem instance) tuples. We accumulate items in the list in
        # stack[level][0], and when we go back up a level we put them in a
        # submenu (as defined by the subclasses). We need to keep track of the
        # last item on each level, in case they are separators, so that's on the
        # stack too.
        for (level, item) in flat_structure:
            index += 1

            # Have we dropped back a level? Restore previous context
            if level < last_level:
                # We may have ended up descending several levels (it works, but
                # please no-one write triply nested menus, it's just dumb).
                for num in range(last_level - level):
                    # Remove separators at the end of menus
                    if type(last_item) == MenuSeparator:
                        stack[-1][0].remove(last_menuitem)

                    (items, last_item, last_menuitem) = stack.pop()

                    # Every time we back out of a level, we attach the list of
                    # items as a submenu, however the subclass wants to do it.
                    self.attach_submenu(last_menuitem, items)

            # Have we gone up a level? Save the context and create a submenu
            if level > last_level:
                # Skip separators at the start of a menu
                if type(item) == MenuSeparator:
                    continue

                stack.append(([], last_item, last_menuitem))

                last_item = last_menuitem = None

            # Skip duplicate separators
            if type(last_item) == type(item) == MenuSeparator and level == last_level:
                continue

            menuitem = self.make_menu_item(item, index)

            self.connect_signal(menuitem, item.callback, item.callback_args)

            stack[-1][0].append(menuitem)

            last_item = item
            last_menuitem = menuitem
            last_level = level

        # Hey, we're out of the loop. Go back up any remaining levels (in case
        # there were submenus at the end) and finish the job.
        for (items, last_item2, last_menuitem2) in stack[:0:-1]:

            if type(last_item) == MenuSeparator:
                stack[-1][0].remove(last_menuitem)

            self.attach_submenu(last_menuitem2, items)

            last_item = last_item2
            last_menuitem = last_menuitem2

        if stack:
            self.menu = self.top_level_menu(stack[0][0])
        else:
            log.debug("Empty top level menu!")
            self.menu = self.top_level_menu([])

    def connect_signal(self, menuitem, callback, callback_args):
        if callback:
            if callback_args:
                menuitem.connect(self.signal, callback, callback_args)
            else:
                menuitem.connect(self.signal, callback)


class GtkContextMenu(MenuBuilder):
    """
    Provides a standard Gtk Context Menu class used for all context menus
    in Gtk dialogs/windows.
    """

    signal = "button-press-event"

    def make_menu_item(self, item, id_magic):
        return item.make_gtk3_menu_item(id_magic)

    def attach_submenu(self, menu_node, submenu_list):
        submenu = Gtk.Menu()
        menu_node.set_submenu(submenu)
        [submenu.add(item) for item in submenu_list]

    def top_level_menu(self, items):
        menu = Gtk.Menu()
        [menu.add(item) for item in items]
        return menu

    def show(self, event):
        if self.menu.get_children():
            self.menu.show_all()
            self.menu.popup_at_pointer(event)

    def get_widget(self):
        return self.menu


class GtkContextMenuCaller(object):
    """
    Provides an abstract interface to be inherited by dialogs/windows that call
    a GtkContextMenu.  Allows us to have a standard common set of methods we can
    call from the callback object.
    """

    def __init__(self):
        pass

    def on_context_menu_command_finished(self):
        pass

    def rescan_after_process_exit(self, proc, paths=None):
        self.execute_after_process_exit(proc, self.on_context_menu_command_finished)

    def execute_after_process_exit(self, proc, callback=None):
        if callback is None:
            callback = self.on_context_menu_command_finished

        def is_process_still_alive():
            log.debug("is_process_still_alive() for pid: %i" % proc.pid)
            # First we need to see if the process is still running

            retval = proc.poll()

            log.debug("%s" % retval)

            still_going = retval is None

            if not still_going and callable(callback):
                callback()

            return still_going

        # Add our callback function on a 1 second timeout
        GLib.timeout_add_seconds(1, is_process_still_alive)


class ContextMenuCallbacks(object):
    """
    The base class for context menu callbacks. This is inherited by sub-classes.
    """

    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """
        @param  caller: The calling object
        @type   caller: RabbitVCS extension

        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.vcs.create_vcs_instance()

        @param  paths: The selected paths
        @type   paths: list

        """
        self.caller = caller
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        self.paths = paths

    def python_console(self, widget, data1=None, data2=None):
        """
        Open up an interactive Python console sharing our current context.
        """

        from rabbitvcs.debug.pythonconsole import PythonConsole

        def exit():
            window.destroy()

        window = Gtk.Window()
        window.set_size_request(750, 550)
        window.set_resizable(True)
        window.set_position(Gtk.WindowPosition.CENTER)
        console = PythonConsole(exit, namespace={"extension": self.caller})
        console.eval(
            'print("You can access the extension through ' "'extension'\")", False
        )
        window.add(console)
        window.show_all()

    def refresh_status(self, widget, data1=None, data2=None):
        """
        Refreshes an item status, which is actually just invalidate.
        """

        self.debug_invalidate(widget)

    def debug_revert(self, widget, data1=None, data2=None):
        client = pysvn.Client()
        for path in self.paths:
            client.revert(path, recurse=True)

    def debug_invalidate(self, widget, data1=None, data2=None):
        rabbitvcs_extension = self.caller
        VFSFile_table = rabbitvcs_extension.VFSFile_table
        for path in self.paths:
            log.debug("callback_debug_invalidate() called for %s" % path)
            if path in VFSFile_table:
                VFSFile_table[path].invalidate_extension_info()

    def debug_add_emblem(self, widget, data1=None, data2=None):
        def add_emblem_dialog():
            from subprocess import Popen, PIPE

            command = [
                "zenity",
                "--entry",
                "--title=RabbitVCS",
                "--text=Emblem to add:",
            ]
            emblem = S(Popen(command, stdout=PIPE).communicate()[0]).replace("\n", "")

            rabbitvcs_extension = self.caller
            VFSFile_table = rabbitvcs_extension.VFSFile_table
            for path in self.paths:
                if path in VFSFile_table:
                    VFSFile_table[path].add_emblem(emblem)
            return False

        GLib.idle_add(add_emblem_dialog)

    # End debugging callbacks

    def checkout(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("checkout", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def update(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("update", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def commit(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("commit", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def add(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("add", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def check_for_modifications(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("checkmods", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def delete(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("delete", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def revert(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("revert", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def diff(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("diff", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def diff_multiple(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("diff", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def diff_previous_revision(self, widget, data1=None, data2=None):
        guess = self.vcs_client.guess(self.paths[0])
        if guess["vcs"] == rabbitvcs.vcs.VCS_SVN:
            previous_revision_number = (
                self.vcs_client.svn().get_revision(self.paths[0]) - 1
            )

            pathrev1 = helper.create_path_revision_string(
                self.vcs_client.svn().get_repo_url(self.paths[0]),
                previous_revision_number,
            )
            pathrev2 = helper.create_path_revision_string(self.paths[0], "working")

            proc = helper.launch_ui_window(
                "diff", ["-s", pathrev1, pathrev2, "--vcs=%s" % rabbitvcs.vcs.VCS_SVN]
            )
            self.caller.rescan_after_process_exit(proc, self.paths)

    def compare_tool(self, widget, data1=None, data2=None):
        pathrev1 = helper.create_path_revision_string(self.paths[0], "base")
        pathrev2 = helper.create_path_revision_string(self.paths[0], "working")

        proc = helper.launch_ui_window("diff", ["-s", pathrev1, pathrev2])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def compare_tool_multiple(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("diff", ["-s"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def compare_tool_previous_revision(self, widget, data1=None, data2=None):
        guess = self.vcs_client.guess(self.paths[0])
        if guess["vcs"] == rabbitvcs.vcs.VCS_SVN:
            previous_revision_number = (
                self.vcs_client.svn().get_revision(self.paths[0]) - 1
            )

            pathrev1 = helper.create_path_revision_string(
                self.vcs_client.svn().get_repo_url(self.paths[0]),
                previous_revision_number,
            )
            pathrev2 = helper.create_path_revision_string(self.paths[0], "working")

            proc = helper.launch_ui_window(
                "diff", ["-s", pathrev1, pathrev2, "--vcs=%s" % rabbitvcs.vcs.VCS_SVN]
            )
            self.caller.rescan_after_process_exit(proc, self.paths)

    def show_changes(self, widget, data1=None, data2=None):
        pathrev1 = helper.create_path_revision_string(self.paths[0])
        pathrev2 = pathrev1
        if len(self.paths) == 2:
            pathrev2 = helper.create_path_revision_string(self.paths[1])

        proc = helper.launch_ui_window("changes", [pathrev1, pathrev2])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def show_log(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("log", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def rename(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("rename", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def create_patch(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("createpatch", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def apply_patch(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("applypatch", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def properties(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("property_editor", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def about(self, widget, data1=None, data2=None):
        helper.launch_ui_window("about")

    def settings(self, widget, data1=None, data2=None):
        base_dir = self.base_dir
        if len(self.paths) == 1 and os.path.isdir(self.paths[0]):
            base_dir = self.paths[0]
        proc = helper.launch_ui_window("settings", [base_dir])
        self.caller.reload_settings(proc)

    def ignore_by_filename(self, widget, data1=None, data2=None):
        path = self.paths[0]
        base_dir = os.path.join(self.base_dir, os.path.dirname(path))
        proc = helper.launch_ui_window("ignore", [base_dir, os.path.basename(path)])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def ignore_by_file_extension(self, widget, data1=None, data2=None):
        path = self.paths[0]
        pattern = "*%s" % helper.get_file_extension(path)
        base_dir = os.path.join(self.base_dir, os.path.dirname(path))
        proc = helper.launch_ui_window("ignore", [base_dir, pattern])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def get_lock(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("lock", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def branch_tag(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("branch", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def switch(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("switch", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def merge(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("merge", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def _import(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("import", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def export(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("export", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def svn_export(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("export", ["--vcs=svn", self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def git_export(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("export", ["--vcs=git", self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def update_to_revision(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("updateto", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def mark_resolved(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("markresolved", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def annotate(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("annotate", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def unlock(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("unlock", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def create_repository(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("create", ["--vcs", "svn", self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def relocate(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("relocate", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def cleanup(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("cleanup", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def restore(self, widget, data1=None, data2=None):
        guess = self.vcs_client.guess(self.paths[0])
        if guess["vcs"] == rabbitvcs.vcs.VCS_SVN:
            proc = helper.launch_ui_window("update", self.paths)
        elif guess["vcs"] == rabbitvcs.vcs.VCS_GIT:
            proc = helper.launch_ui_window(
                "checkout", ["-q", "--vcs", "git"] + self.paths
            )

        self.caller.rescan_after_process_exit(proc, self.paths)

    def _open(self, widget, data1=None, data2=None):
        pass

    def browse_to(self, widget, data1=None, data2=None):
        pass

    def repo_browser(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("browser", [self.paths[0]])

    def initialize_repository(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("create", ["--vcs", "git", self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def clone(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("clone", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def push(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("push", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def branches(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("branches", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def tags(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("tags", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def remotes(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("remotes", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def clean(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("clean", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def reset(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("reset", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def stage(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("stage", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def unstage(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("unstage", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, self.paths)

    def edit_conflicts(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("editconflicts", [self.paths[0]])
        self.caller.rescan_after_process_exit(proc, [self.paths[0]])


class ContextMenuConditions(object):
    """
    Provides a standard interface to checking conditions for menu items.

    This class should never be instantied directly, rather the narrowly defined
    FileManagerContextMenuConditions and GtkFilesContextMenuConditions classes
    should be called.

    """

    def __init__(self):
        pass

    def generate_path_dict(self, paths):
        self.path_dict = {"length": len(paths)}

        checks = {
            "is_svn": lambda path: (self.vcs_client.guess(path)["vcs"] == VCS_SVN),
            "is_git": lambda path: (self.vcs_client.guess(path)["vcs"] == VCS_GIT),
            "is_mercurial": lambda path: (
                self.vcs_client.guess(path)["vcs"] == VCS_MERCURIAL
            ),
            "is_dir": os.path.isdir,
            "is_file": os.path.isfile,
            "exists": os.path.exists,
            "is_working_copy": self.vcs_client.is_working_copy,
            "is_in_a_or_a_working_copy": self.vcs_client.is_in_a_or_a_working_copy,
            "is_versioned": self.vcs_client.is_versioned,
            "is_normal": lambda path: self.statuses[path].simple_content_status()
            == "unchanged"
            and self.statuses[path].simple_metadata_status() == "normal",
            "is_added": lambda path: self.statuses[path].simple_content_status()
            == "added",
            "is_modified": lambda path: self.statuses[path].simple_content_status()
            == "modified"
            or self.statuses[path].simple_metadata_status() == "modified",
            "is_deleted": lambda path: self.statuses[path].simple_content_status()
            == "deleted",
            "is_ignored": lambda path: self.statuses[path].simple_content_status()
            == "ignored",
            "is_locked": self.vcs_client.is_locked,
            "is_missing": lambda path: self.statuses[path].simple_content_status()
            == "missing",
            "is_conflicted": lambda path: self.statuses[path].simple_content_status()
            == "complicated",
            "is_obstructed": lambda path: self.statuses[path].simple_content_status()
            == "obstructed",
            "has_unversioned": lambda path: "unversioned" in self.text_statuses,
            "has_added": lambda path: "added" in self.text_statuses,
            "has_modified": lambda path: "modified" in self.text_statuses
            or "modified" in self.prop_statuses,
            "has_deleted": lambda path: "deleted" in self.text_statuses,
            "has_ignored": lambda path: "ignored" in self.text_statuses,
            "has_missing": lambda path: "missing" in self.text_statuses,
            "has_conflicted": lambda path: "complicated" in self.text_statuses,
            "has_obstructed": lambda path: "obstructed" in self.text_statuses,
        }

        for key, func in list(checks.items()):
            self.path_dict[key] = False

        # Each path gets tested for each check
        # If a check has returned True for any path, skip it for remaining paths
        for path in paths:
            for key, func in list(checks.items()):
                try:
                    self.path_dict[key] = func(path)
                except KeyError as e:
                    self.path_dict[key] = False

    def checkout(self, data=None):
        if self.path_dict["length"] == 1:
            if self.path_dict["is_git"]:
                return (
                    self.path_dict["is_in_a_or_a_working_copy"]
                    and self.path_dict["is_versioned"]
                )
            else:
                return (
                    self.path_dict["is_dir"] and not self.path_dict["is_working_copy"]
                )

        return False

    def update(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and not self.path_dict["is_added"]
        )

    def commit(self, data=None):
        if (
            self.path_dict["is_svn"]
            or self.path_dict["is_git"]
            or self.path_dict["is_mercurial"]
        ):
            if self.path_dict["is_in_a_or_a_working_copy"]:
                if (
                    self.path_dict["is_added"]
                    or self.path_dict["is_modified"]
                    or self.path_dict["is_deleted"]
                    or not self.path_dict["is_versioned"]
                ):
                    return True
                elif self.path_dict["is_dir"]:
                    return True
        return False

    def diff_menu(self, data=None):
        return self.path_dict["is_in_a_or_a_working_copy"]

    def diff_multiple(self, data=None):
        if (
            self.path_dict["length"] == 2
            and self.path_dict["is_versioned"]
            and self.path_dict["is_in_a_or_a_working_copy"]
        ):
            return True
        return False

    def compare_tool_multiple(self, data=None):
        if (
            self.path_dict["length"] == 2
            and self.path_dict["is_versioned"]
            and self.path_dict["is_in_a_or_a_working_copy"]
        ):
            return True
        return False

    def diff(self, data=None):
        if (
            self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
            and (
                self.path_dict["is_modified"]
                or self.path_dict["has_modified"]
                or self.path_dict["is_conflicted"]
                or self.path_dict["has_conflicted"]
            )
        ):
            return True
        return False

    def diff_previous_revision(self, data=None):
        if (
            self.path_dict["is_svn"]
            and self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
        ):
            return True
        return False

    def compare_tool(self, data=None):
        if (
            self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
            and (
                self.path_dict["is_modified"]
                or self.path_dict["has_modified"]
                or self.path_dict["is_conflicted"]
                or self.path_dict["has_conflicted"]
            )
        ):
            return True
        return False

    def compare_tool_previous_revision(self, data=None):
        if (
            self.path_dict["is_svn"]
            and self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
        ):
            return True
        return False

    def show_changes(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and self.path_dict["length"] in (1, 2)
        )

    def show_log(self, data=None):
        return (
            self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and not self.path_dict["is_added"]
        )

    def add(self, data=None):
        if not self.path_dict["is_svn"]:
            return False

        if self.path_dict["is_dir"] and self.path_dict["is_in_a_or_a_working_copy"]:
            return True
        elif (
            not self.path_dict["is_dir"]
            and self.path_dict["is_in_a_or_a_working_copy"]
            and not self.path_dict["is_versioned"]
        ):
            return True
        return False

    def check_for_modifications(self, data=None):
        return self.path_dict["is_working_copy"] or self.path_dict["is_versioned"]

    def rename(self, data=None):
        return (
            self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
            and not self.path_dict["is_working_copy"]
            and self.path_dict["is_versioned"]
        )

    def delete(self, data=None):
        return (
            self.path_dict["exists"] or self.path_dict["is_versioned"]
        ) and not self.path_dict["is_deleted"]

    def revert(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (
                self.path_dict["is_added"]
                or self.path_dict["is_modified"]
                or self.path_dict["is_deleted"]
            ):
                return True
            else:
                if self.path_dict["is_dir"] and (
                    self.path_dict["has_added"]
                    or self.path_dict["has_modified"]
                    or self.path_dict["has_deleted"]
                    or self.path_dict["has_missing"]
                ):
                    return True
        return False

    def annotate(self, data=None):
        return (
            self.path_dict["length"] == 1
            and not self.path_dict["is_dir"]
            and self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and not self.path_dict["is_added"]
        )

    def properties(self, data=None):
        return (
            self.path_dict["length"] == 1
            and self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
        )

    def create_patch(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (
                self.path_dict["is_added"]
                or self.path_dict["is_modified"]
                or self.path_dict["is_deleted"]
                or not self.path_dict["is_versioned"]
            ):
                return True
            elif self.path_dict["is_dir"] and (
                self.path_dict["has_added"]
                or self.path_dict["has_modified"]
                or self.path_dict["has_deleted"]
                or self.path_dict["has_unversioned"]
                or self.path_dict["has_missing"]
            ):
                return True
        return False

    def apply_patch(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            return True
        return False

    def add_to_ignore_list(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and not self.path_dict["is_versioned"]
        )

    def ignore_by_filename(self, *args):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and not self.path_dict["is_versioned"]
        )

    def ignore_by_file_extension(self, *args):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and not self.path_dict["is_versioned"]
        )

    def refresh_status(self, data=None):
        return True

    def get_lock(self, data=None):
        return self.path_dict["is_versioned"]

    def branch_tag(self, data=None):
        return self.path_dict["is_versioned"]

    def relocate(self, data=None):
        return self.path_dict["is_versioned"]

    def switch(self, data=None):
        return self.path_dict["is_versioned"]

    def merge(self, data=None):
        return self.path_dict["is_versioned"]

    def _import(self, data=None):
        return (
            self.path_dict["length"] == 1
            and not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def export(self, data=None):
        return self.path_dict["length"] == 1

    def svn_export(self, data=None):
        return self.export(data)

    def git_export(self, data=None):
        return self.export(data)

    def update_to_revision(self, data=None):
        return (
            self.path_dict["length"] == 1
            and self.path_dict["is_versioned"]
            and self.path_dict["is_in_a_or_a_working_copy"]
        )

    def mark_resolved(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and self.path_dict["is_conflicted"]
        )

    def create_repository(self, data=None):
        return (
            self.path_dict["length"] == 1
            and not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def unlock(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and (self.path_dict["is_dir"] or self.path_dict["is_locked"])
        )

    def cleanup(self, data=None):
        return self.path_dict["is_versioned"]

    def browse_to(self, data=None):
        return self.path_dict["exists"]

    def _open(self, data=None):
        return self.path_dict["is_file"]

    def restore(self, data=None):
        return self.path_dict["has_missing"]

    def update(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and not self.path_dict["is_added"]
        )

    def repo_browser(self, data=None):
        return True

    def rabbitvcs(self, data=None):
        return False

    def rabbitvcs_svn(self, data=None):
        return (
            self.path_dict["is_svn"] or not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def rabbitvcs_git(self, data=None):
        return (
            self.path_dict["is_git"] or not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def rabbitvcs_mercurial(self, data=None):
        return (
            self.path_dict["is_mercurial"]
            or not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def debug(self, data=None):
        return settings.get("general", "show_debug")

    def separator(self, data=None):
        return True

    def help(self, data=None):
        return False

    def settings(self, data=None):
        return True

    def about(self, data=None):
        return True

    def bugs(self, data=None):
        return True

    def initialize_repository(self, data=None):
        return (
            self.path_dict["is_dir"] and not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def clone(self, data=None):
        return (
            self.path_dict["is_dir"] and not self.path_dict["is_in_a_or_a_working_copy"]
        )

    def push(self, data=None):
        return self.path_dict["is_git"] or self.path_dict["is_mercurial"]

    def branches(self, data=None):
        return self.path_dict["is_git"]

    def tags(self, data=None):
        return self.path_dict["is_git"]

    def remotes(self, data=None):
        return self.path_dict["is_git"]

    def clean(self, data=None):
        return self.path_dict["is_git"]

    def reset(self, data=None):
        return self.path_dict["is_git"]

    def stage(self, data=None):
        if self.path_dict["is_git"]:
            if self.path_dict["is_dir"] and self.path_dict["is_in_a_or_a_working_copy"]:
                return True
            elif (
                not self.path_dict["is_dir"]
                and self.path_dict["is_in_a_or_a_working_copy"]
                and not self.path_dict["is_versioned"]
            ):
                return True
        return False

    def unstage(self, data=None):
        if self.path_dict["is_git"]:
            if self.path_dict["is_dir"] and self.path_dict["is_in_a_or_a_working_copy"]:
                return True
            elif (
                not self.path_dict["is_dir"]
                and self.path_dict["is_in_a_or_a_working_copy"]
                and self.path_dict["is_added"]
            ):
                return True
        return False

    def edit_conflicts(self, data=None):
        return (
            self.path_dict["is_in_a_or_a_working_copy"]
            and self.path_dict["is_versioned"]
            and self.path_dict["is_conflicted"]
        )


class GtkFilesContextMenuCallbacks(ContextMenuCallbacks):
    """
    A callback class created for GtkFilesContextMenus.  This class inherits from
    the standard ContextMenuCallbacks class and overrides some methods.
    """

    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """
        @param  caller: The calling object
        @type   caller: RabbitVCS extension

        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.vcs.create_vcs_instance()

        @param  paths: The selected paths
        @type   paths: list

        """
        ContextMenuCallbacks.__init__(self, caller, base_dir, vcs_client, paths)

    def _open(self, widget, data1=None, data2=None):
        for path in self.paths:
            helper.open_item(path)

    def add(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("add", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def revert(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("revert", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def mark_resolved(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("markresolved", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def browse_to(self, widget, data1=None, data2=None):
        helper.browse_to_item(self.paths[0])

    def delete(self, widget, data1=None, data2=None):
        if len(self.paths) > 0:
            proc = helper.launch_ui_window("delete", self.paths)
            self.caller.rescan_after_process_exit(proc, self.paths)

    def update(self, data1=None, data2=None):
        proc = helper.launch_ui_window("update", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def unlock(self, data1=None, data2=None):
        proc = helper.launch_ui_window("unlock", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def show_log(self, data1=None, data2=None):
        proc = helper.launch_ui_window("log", self.paths)
        self.caller.rescan_after_process_exit(proc, [self.paths[0]])

    def stage(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("stage", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def unstage(self, widget, data1=None, data2=None):
        proc = helper.launch_ui_window("unstage", ["-q"] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)


class GtkFilesContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions for our dialogs.  Allows us to override
    some generic condition methods with condition logic more suitable
    to the dialogs.

    """

    def __init__(self, vcs_client, paths=[]):
        """
        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.vcs.create_vcs_instance()

        @param  paths: The selected paths
        @type   paths: list

        """
        self.vcs_client = vcs_client
        self.paths = paths
        self.statuses = {}

        self.generate_statuses(self.paths)
        self.generate_path_dict(self.paths)

    def generate_statuses(self, paths):
        self.statuses = {}
        for path in paths:
            if not path:
                continue

            statuses_tmp = self.vcs_client.statuses(path, invalidate=True)
            for status in statuses_tmp:
                self.statuses[status.path] = status

        self.text_statuses = [
            self.statuses[key].simple_content_status()
            for key in list(self.statuses.keys())
        ]
        self.prop_statuses = [
            self.statuses[key].simple_metadata_status()
            for key in list(self.statuses.keys())
        ]


class GtkFilesContextMenu(object):
    """
    Defines context menu items for a table with files

    """

    def __init__(
        self, caller, event, base_dir, paths=[], conditions=None, callbacks=None
    ):
        """
        @param  caller: The calling object
        @type   caller: RabbitVCS extension

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
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = create_vcs_instance()

        self.conditions = conditions
        if self.conditions is None:
            self.conditions = GtkFilesContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = GtkFilesContextMenuCallbacks(
                self.caller, self.base_dir, self.vcs_client, paths
            )

        ignore_items = get_ignore_list_items(paths)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuDiff, None),
            (MenuCompareTool, None),
            (MenuUnlock, None),
            (MenuShowLog, None),
            (MenuOpen, None),
            (MenuBrowseTo, None),
            (MenuDelete, None),
            (MenuRevert, None),
            (MenuRestore, None),
            (MenuEditConflicts, None),
            (MenuMarkResolved, None),
            (MenuCreatePatch, None),
            (MenuAdd, None),
            (MenuStage, None),
            (MenuUnstage, None),
            (MenuAddToIgnoreList, ignore_items),
        ]

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)

    def get_menu(self):
        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        return context_menu.menu


class MainContextMenuCallbacks(ContextMenuCallbacks):
    """
    The callback class used for the main context menu.  This inherits from
    and overrides the ContextMenuCallbacks class.

    """

    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """
        @param  caller: The calling object
        @type   caller: RabbitVCS extension

        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.vcs.create_vcs_instance()

        @param  paths: The selected paths
        @type   paths: list

        """
        ContextMenuCallbacks.__init__(self, caller, base_dir, vcs_client, paths)


class MainContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions used for file manager extensions.
    Allows us to override some generic condition methods with condition logic
    more suitable to the dialogs.

    """

    def __init__(self, vcs_client, paths=[]):
        """
        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.vcs.create_vcs_instance()

        @param  paths: The selected paths
        @type   paths: list

        """

        self.vcs_client = vcs_client
        self.paths = paths
        self.statuses = {}

        self.generate_statuses(paths)
        self.generate_path_dict(paths)

    # FIXME: major bottleneck
    def generate_statuses(self, paths):
        self.statuses = {}
        for path in paths:
            if not path:
                continue

            statuses_tmp = self.vcs_client.statuses(path)
            for status in statuses_tmp:
                self.statuses[status.path] = status

        self.text_statuses = [
            self.statuses[key].simple_content_status()
            for key in list(self.statuses.keys())
        ]
        self.prop_statuses = [
            self.statuses[key].simple_metadata_status()
            for key in list(self.statuses.keys())
        ]


class MainContextMenu(object):
    """
    Defines and composes the main context menu.

    """

    def __init__(self, caller, base_dir, paths=[], conditions=None, callbacks=None):
        """
        @param  caller: The calling object
        @type   caller: RabbitVCS extension

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
        self.vcs_client = create_vcs_instance()

        self.conditions = conditions
        if self.conditions is None:
            self.conditions = MainContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = MainContextMenuCallbacks(
                self.caller, self.base_dir, self.vcs_client, paths
            )

        ignore_items = get_ignore_list_items(paths)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (
                MenuDebug,
                [
                    (MenuBugs, None),
                    (MenuPythonConsole, None),
                    (MenuRefreshStatus, None),
                    (MenuDebugRevert, None),
                    (MenuDebugInvalidate, None),
                    (MenuDebugAddEmblem, None),
                ],
            ),
            (MenuUpdate, None),
            (MenuCommit, None),
            (MenuPush, None),
            None
            if settings.get("HideItem", "svn")
            else (
                MenuRabbitVCSSvn,
                [
                    (MenuCheckout, None),
                    (
                        MenuDiffMenu,
                        [
                            (MenuDiff, None),
                            (MenuDiffPrevRev, None),
                            (MenuDiffMultiple, None),
                            (MenuCompareTool, None),
                            (MenuCompareToolPrevRev, None),
                            (MenuCompareToolMultiple, None),
                            (MenuShowChanges, None),
                        ],
                    ),
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
                    (MenuSVNExport, None),
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
                    (MenuAbout, None),
                ],
            ),
            None
            if settings.get("HideItem", "git")
            else (
                MenuRabbitVCSGit,
                [
                    (MenuClone, None),
                    (MenuInitializeRepository, None),
                    (MenuSeparator, None),
                    (
                        MenuDiffMenu,
                        [
                            (MenuDiff, None),
                            (MenuDiffPrevRev, None),
                            (MenuDiffMultiple, None),
                            (MenuCompareTool, None),
                            (MenuCompareToolPrevRev, None),
                            (MenuCompareToolMultiple, None),
                            (MenuShowChanges, None),
                        ],
                    ),
                    (MenuShowLog, None),
                    (MenuStage, None),
                    (MenuUnstage, None),
                    (MenuAddToIgnoreList, ignore_items),
                    (MenuSeparator, None),
                    (MenuRename, None),
                    (MenuDelete, None),
                    (MenuRevert, None),
                    (MenuClean, None),
                    (MenuReset, None),
                    (MenuCheckout, None),
                    (MenuSeparator, None),
                    (MenuBranches, None),
                    (MenuTags, None),
                    (MenuRemotes, None),
                    (MenuSeparator, None),
                    (MenuGitExport, None),
                    (MenuMerge, None),
                    (MenuSeparator, None),
                    (MenuAnnotate, None),
                    (MenuSeparator, None),
                    (MenuCreatePatch, None),
                    (MenuApplyPatch, None),
                    (MenuSeparator, None),
                    (MenuSettings, None),
                    (MenuAbout, None),
                ],
            ),
            None
            if settings.get("HideItem", "hg")
            else (MenuRabbitVCSMercurial, [(MenuSettings, None), (MenuAbout, None)]),
        ]
        self.structure = [_f for _f in self.structure if _f]

    def get_menu(self):
        pass


def TestMenuItemFunctions():
    """
    This is a test for developers to ensure that they've written all the
    necessary conditions and callbacks (and haven't made any typos).

    What it does:
      - build a list of all the subclasses of MenuItem
      - build lists of the methods in ContextMenuConditions/ContextMenuCallbacks
      - checks to see whether all the MenuItems conditions and callbacks have
        been assigned - if not, a message is printed
    """

    # These are some simple tests:
    import inspect
    import types

    from . import contextmenuitems

    menu_item_subclasses = []

    # Let's create a list of all MenuItem subclasses
    for name in dir(contextmenuitems):
        entity = getattr(contextmenuitems, name)
        if type(entity) == type:
            mro = inspect.getmro(entity)
            if (
                entity is not contextmenuitems.MenuItem
                and contextmenuitems.MenuItem in mro
            ):
                menu_item_subclasses.append(entity)

    condition_functions = []

    # Now let's create a list of all of the functions in our conditions class
    for name in dir(ContextMenuConditions):
        entity = getattr(ContextMenuConditions, name)
        if type(entity) == types.UnboundMethodType and not name.startswith("__"):
            condition_functions.append(entity)

    callback_functions = []

    # ...and in our callbacks class
    for name in dir(ContextMenuCallbacks):
        entity = getattr(ContextMenuCallbacks, name)
        if type(entity) == types.UnboundMethodType and not name.startswith("__"):
            condition_functions.append(entity)

    for cls in menu_item_subclasses:
        item = cls(
            ContextMenuConditions(), ContextMenuCallbacks(None, None, None, None)
        )
        if not item.found_condition:
            print(
                "Did not find condition function in ContextMenuConditions "
                "for %s (type: %s)" % (item.identifier, cls)
            )
        if not item.callback:
            print(
                "Did not find callback function in ContextMenuCallbacks "
                "for %s (type: %s)" % (item.identifier, cls)
            )


if __name__ == "__main__":
    TestMenuItemFunctions()
