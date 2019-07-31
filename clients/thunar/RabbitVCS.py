#
# This is an extension to the Thunar file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
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

Our module for everything related to the Thunar extension.

"""

from __future__ import with_statement
from __future__ import absolute_import
import copy
import os.path
from os.path import isdir, isfile, realpath, basename
import datetime
import time
import threading

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import GObject, Gtk, Thunarx
sa.restore()

from rabbitvcs.vcs.svn import SVN

import os
os.environ["REQUIRE_GTK3"] = "1"

import rabbitvcs.ui
import rabbitvcs.ui.property_page
from rabbitvcs.util.helper import launch_ui_window, launch_diff_tool
from rabbitvcs.util.helper import get_file_extension, get_common_directory
from rabbitvcs.util.helper import pretty_timedelta
from rabbitvcs.util.helper import unquote
from rabbitvcs.util.strings import S
from rabbitvcs.util.decorators import timeit, disable
from rabbitvcs.util.contextmenu import MenuBuilder, MainContextMenu, SEPARATOR

from rabbitvcs.util.log import Log, reload_log_settings
log = Log("rabbitvcs.util.extensions.thunarx.RabbitVCS")

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.settings import SettingsManager
settings = SettingsManager()

import rabbitvcs.services.service
from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker

class RabbitVCS(GObject.GObject, Thunarx.MenuProvider, Thunarx.PropertyPageProvider):
    """
    This is the main class that implements all of our awesome features.

    """

    #: Maps statuses to emblems.
    #: TODO: should probably be possible to create this dynamically
    EMBLEMS = rabbitvcs.ui.STATUS_EMBLEMS

    #: A list of statuses which count as modified (for a directory) in
    #: TortoiseSVN emblem speak.
    MODIFIED_STATUSES = [
        SVN.STATUS["added"],
        SVN.STATUS["deleted"],
        SVN.STATUS["replaced"],
        SVN.STATUS["modified"],
        SVN.STATUS["missing"]
    ]

    MODIFIED_TEXT_STATUSES = [
        "added",
        "deleted",
        "replaced",
        "modified",
        "missing"
    ]

    #: This is our lookup table for C{NautilusVFSFile}s which we need for attaching
    #: emblems. This is mostly a workaround for not being able to turn a path/uri
    #: into a C{NautilusVFSFile}. It looks like:::
    #:
    #:     nautilusVFSFile_table = {
    #:        "/foo/bar/baz": <NautilusVFSFile>
    #:
    #:     }
    #:
    #: Keeping track of C{NautilusVFSFile}s is a little bit complicated because
    #: when an item is moved (renamed) C{update_file_info} doesn't get called. So
    #: we also add C{NautilusVFSFile}s to this table from C{get_file_items} etc.
    nautilusVFSFile_table = {}

    #: Without an actual status monitor it's not possible to just keep
    #: track of stuff that happens (e.g. a commit happens, files are added,
    #: such things). So at the moment we just add all interesting items
    #: to this list.
    monitored_files = []

    #: This is in case we want to permanently enable invalidation of the status
    #: checker info. We put a path here before we invalidate the item, so that
    #: we don't enter an endless loop when updating the status.
    #: The callback should acquire this lock when pushing the path to this.
    always_invalidate = True

    #: When we get the statuses from the callback, but them here for further
    #: use. There is a possible memory problem here if we put a lot of data in
    #: this - even when it's removed, Python may not release the memory. I do
    #: not know this for sure.
    #: This is of the form: [("path/to", {...status dict...}), ...]
    paths_from_callback = []

    paths_last_lookup = {}
    paths_lookup_timeout = 30

    #: It appears that the "update_file_info" call that is triggered by the
    #: "invalidate_extension_info" in the callback function happens
    #: synchronously (ie. in the same thread). However, given the nature of the
    #: python/nautilus extensions module, I'm not sure how reliable this is.
    #: It's certainly supported by debugging statements, but maybe it will
    #: change in the future? Who knows. This should work for both the current
    #: situation, and the possibility that they are asynchronous.
    callback_paths_lock = threading.RLock()

    #: A list of statuses that we want to keep track of for when a process
    #: might have done something.
    STATUSES_TO_MONITOR = copy.copy(MODIFIED_TEXT_STATUSES)
    STATUSES_TO_MONITOR.extend([
        "unversioned",
        # When doing a checkout Nautilus will notice a directory being
        # added and call update_file_info, but at that stage the
        # checkout likely hasn't completed yet and the status will be:
        "incomplete"
    ])

    def __init__(self):
        threading.currentThread().setName("RabbitVCS extension thread")

        self.status_checker = StatusChecker()

    def get_local_path(self, item):
        return unquote(item.get_uri().replace("file://", ""))

    #~ @disable
    # @timeit
    def get_file_menu_items(self, window, items):
        """
        Menu activated with items selected. Nautilus also calls this function
        when rendering submenus, even though this is not needed since the entire
        menu has already been returned.

        Note that calling C{nautilusVFSFile.invalidate_extension_info()} will
        also cause get_file_items to be called.

        @type   window: NautilusNavigationWindow
        @param  window:

        @type   items:  list of NautilusVFSFile
        @param  items:

        @rtype:         list of MenuItems
        @return:        The context menu entries to add to the menu.

        """

        paths = []
        for item in items:
            if self.valid_uri(item.get_uri()):
                path = realpath(S(self.get_local_path(item)))
                paths.append(path)
                self.nautilusVFSFile_table[path] = item

        if len(paths) == 0: return []

        return ThunarxMainContextMenu(self, window.base_dir, paths).get_menu()

    #~ @disable
    @timeit
    def get_folder_menu_items(self, window, item):
        """
        Menu activated on entering a directory. Builds context menu for File
        menu and for window background.

        @type   window: NautilusNavigationWindow
        @param  window:

        @type   item:   NautilusVFSFile
        @param  item:

        @rtype:         list of MenuItems
        @return:        The context menu entries to add to the menu.

        """

        if not self.valid_uri(item.get_uri()): return
        path = realpath(S(self.get_local_path(item)))
        self.nautilusVFSFile_table[path] = item

        # log.debug("get_background_items() called")

        window.base_dir = path

        return ThunarxMainContextMenu(self, path, [path]).get_menu()

    #
    # Helper functions
    #

    def valid_uri(self, uri):
        """
        Check whether or not it's a good idea to have RabbitVCS do
        its magic for this URI. Some examples of URI schemes:

        x-nautilus-desktop:/// # e.g. mounted devices on the desktop

        """

        if not uri.startswith("file://"): return False

        return True

    #
    # Some methods to help with keeping emblems up-to-date
    #

    def rescan_after_process_exit(self, proc, paths):
        """
        Rescans all of the items on our C{monitored_files} list after the
        process specified by C{proc} completes. Also checks the paths
        that were passed.

        TODO: the monitored_files list could grow quite large if somebody
        browses a lot of working copies. It probably won't affect anything
        (most importantly performance) all that negatively.

        """

        def do_check():
            # We'll check the paths first (these were the paths that
            # were originally passed along to the context menu).
            #
            # This is needed among other things for:
            #
            #   - When a directory is normal and you add files inside it
            #
            for path in paths:
                # We're not interested in the result now, just the callback
                self.status_checker.check_status(path,
                                                 recurse=True,
                                                 invalidate=True,
                                                 summary=True)

        self.execute_after_process_exit(proc, do_check)

    def execute_after_process_exit(self, proc, func=None):

        def is_process_still_alive():
            log.debug("is_process_still_alive() for pid: %i" % proc.pid)
            # First we need to see if the commit process is still running

            retval = proc.poll()

            log.debug("%s" % retval)

            still_going = (retval is None)

            if not still_going and callable(func):
                func()

            return still_going

        # Add our callback function on a 1 second timeout
        GObject.timeout_add_seconds(1, is_process_still_alive)

    #
    # Some other methods
    #

    def reload_settings(self, proc):
        """
        Used to re-load settings after the settings dialog has been closed.

        FIXME: This probably doesn't belong here, ideally the settings manager
        does this itself and make sure everything is reloaded properly
        after the settings dialogs saves.
        """

        def do_reload_settings():
            globals()["settings"] = SettingsManager()
            globals()["log"] = reload_log_settings()("rabbitvcs.util.extensions.thunar")
            log.debug("Re-scanning settings")

        self.execute_after_process_exit(proc, do_reload_settings)

    def get_property_pages(self, items):

        paths = []
        for item in items:
            if self.valid_uri(item.get_uri()):
                path = realpath(S(self.get_local_path(item)))
                paths.append(path)
                self.nautilusVFSFile_table[path] = item

        if len(paths) == 0: return []

        label = rabbitvcs.ui.property_page.PropertyPageLabel().get_widget()
        page = rabbitvcs.ui.property_page.PropertyPage(paths).get_widget()

        ppage = Thunarx.PropertyPage.new("")
        ppage.set_label_widget(label)
        ppage.add(page)

        return [ppage]

from rabbitvcs.util.contextmenuitems import *

class ThunarxContextMenu(MenuBuilder):
    """
    Provides a standard Thunar context menu (ie. a list of
    "Thunarx.MenuItem"s).
    """

    signal = "activate"

    def make_menu_item(self, item, id_magic):
        return item.make_thunarx_menu_item(id_magic)

    def attach_submenu(self, menu_node, submenu_list):
        submenu = Thunarx.Menu()
        menu_node.set_menu(submenu)
        [submenu.append_item(item) for item in submenu_list]

    def top_level_menu(self, items):
        return items

class ThunarxMainContextMenu(MainContextMenu):
    def get_menu(self):
        return ThunarxContextMenu(self.structure, self.conditions, self.callbacks).menu
