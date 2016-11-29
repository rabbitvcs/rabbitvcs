#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
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
TODO
    1. Integrate translations
    2. Add more of the v0.13 menu items
    3.  or figure out a way to use the regular nautilus extension's menu items/logic
    4.  or clean up the current menuitem logic in some other way
"""
from __future__ import absolute_import
import six

__version__ = "0.13.beta1"

import copy
import glob
import gnomevfs
import gobject
import gtk
import nautilus
import os
import pysvn
import sys

# RabbitVCS is actually more than just this module so we need to add the entire
# directory to the path to be able to find our other modules. Because on import
# Python generates compiled (.pyc) versions of Python source code files we have
# to strip the 'c' from the extension to find the actual file.
sys.path.append(os.path.dirname(os.path.realpath(__file__.rstrip("c"))))

# FIXME: this (and other) should be moved into a rabbitvcs module to prevent 
# collisions with other modules on the path.
import rabbitvcs.util.helper

#============================================================================== 

ENABLE_ATTRIBUTES = True
RECURSIVE_STATUS = True
ENABLE_EMBLEMS = True

class RabbitVCS(nautilus.InfoProvider, nautilus.MenuProvider, nautilus.ColumnProvider):
    """ This is the main class that implements all of our awesome features.
    """
    
    #: Maps statuses to emblems.
    #: TODO: should probably be possible to create this dynamically
    EMBLEMS = {
        pysvn.wc_status_kind.added :       "rabbitvcs-added",
        pysvn.wc_status_kind.deleted:      "rabbitvcs-deleted",
        pysvn.wc_status_kind.modified:     "rabbitvcs-modified",
        pysvn.wc_status_kind.conflicted:   "rabbitvcs-conflicted",
        pysvn.wc_status_kind.normal:       "rabbitvcs-normal",
        pysvn.wc_status_kind.ignored:      "rabbitvcs-ignored",
        pysvn.wc_status_kind.obstructed:   "rabbitvcs-obstructed"
    }

    #-------------------------------------------------------------------------- 
    def __init__(self):
        """ Constructor - initialise our required storage
        """

        # This list keeps track of any files we have come across that will
        # need to be re-scanned if there is a commit/revert.
        self.monitoredFiles = []

        # This list keeps a record of all of the files we're planning to scan
        # when we get some idle time
        self.scanStack = []

    #--------------------------------------------------------------------------
    def OnIdle(self):
        """ We use the idle handler to pop items from our scan stack and run a
            status scan on them. We do this so that we don't hog the processor
            each time a folder is opened.
        """
        if len(self.scanStack):
            self.ScanFile(self.scanStack.pop())
            return True
        else:
            return False

    #-------------------------------------------------------------------------- 
    def get_columns(self):
        """ This is the function called by Nautilus to find out what extra
            columns we can supply to it.
        """
        return (nautilus.Column("NautilusPython::revision_column",
                               "revision",
                               "Revision",
                               "The file revision"),
                nautilus.Column("NautilusPython::user_column",
                               "user",
                               "SVN User",
                               "The SVN user")

                )

    #-------------------------------------------------------------------------- 
    def update_file_info (self, file):
        """ Callback from Nautilus to get the file status.
        """

        if file.get_uri_scheme() != 'file':
            return

        path = gnomevfs.get_local_path_from_uri(file.get_uri())

        c = pysvn.Client()
        try:
            entry = c.info(path)
        except:
            return

        if not entry:
            return

        # We'll scan the files during idle time, so add it to our stack
        self.scanStack.append(file)
        if len(self.scanStack) == 1:
            gobject.idle_add(self.OnIdle)

    #--------------------------------------------------------------------------
    def ScanFile(self, file):
        """ This is where the magic happens! This function check the current
            status of *file*, and updates the display with the relevant emblem.

            file - A NautilusFileItem to check
        """

        # Transform the URI to a path
        path = gnomevfs.get_local_path_from_uri(file.get_uri())

        # Get the SVN info about the path
        c = pysvn.Client()
        entry = c.info(path)

        # Update the columns if we're supposed to
        if ENABLE_ATTRIBUTES:
            file.add_string_attribute('revision', str(entry.revision.number))
            author = entry.commit_author
            if not author:
                author = ""
            file.add_string_attribute('user', author)

        # Update the display emblems if we're supposed to
        if ENABLE_EMBLEMS:
            if os.path.isdir(path):
                # We're a folder
                st = c.status(path, recurse=RECURSIVE_STATUS)

                # Check if this folder had been added
                for x in st:
                    if x.path == path and x.text_status == pysvn.wc_status_kind.added:
                        file.add_emblem(self.EMBLEMS[pysvn.wc_status_kind.added])
                        return

                # Check if any of the contents of the folder have been modified
                t = set([    pysvn.wc_status_kind.modified,
                            pysvn.wc_status_kind.added,
                            pysvn.wc_status_kind.deleted])
                statuses = set([s.text_status for s in st])

                if len( t & statuses ):
                    file.add_emblem(self.EMBLEMS[pysvn.wc_status_kind.modified])
                else:
                    file.add_emblem(self.EMBLEMS[pysvn.wc_status_kind.normal])
            else:
                # We're a file

                # Get our status
                st = c.status(path, recurse=False)[0]

                # Display an emblem if we have a match for the status
                if st.text_status in self.EMBLEMS:
                    file.add_emblem(self.EMBLEMS[st.text_status])

                # Keep a note of this file object in case we have commits etc.
                t = [ pysvn.wc_status_kind.modified, 
                      pysvn.wc_status_kind.added, 
                      pysvn.wc_status_kind.deleted]
                if st.text_status in t:
                    if file not in self.monitoredFiles:
                        self.monitoredFiles.append(file)
                else:
                    try:
                        self.monitoredFiles.remove(file)
                    except:
                        pass

    #-------------------------------------------------------------------------- 
    def get_file_items(self, window, files):
        """ Menu activated with files selected
        """

        # At the moment we're only handling single files or folders
        if len(files) < 1:
            return

        file = files[0]
        if file is None:
            return

        path = gnomevfs.get_local_path_from_uri(file.get_uri())

        items = [ ('NautilusPython::svndelete_file_item', 'Delete' , 'Remove files from the repository.', self.OnDelete, "rabbitvcs-delete"),
		          ('NautilusPython::svnrename_file_item', 'Rename' , 'Rename a file in the repository', self.OnRename, "rabbitvcs-rename"),
                  ('NautilusPython::svnrefreshstatus_file_item', 'Refresh Status', 'Refresh the display status of the selected files.', self.OnRefreshStatus, "rabbitvcs-refresh"),
                  ('NautilusPython::svnrepo_file_item', 'Repository Browser' , 'View Repository Sources', self.OnRepoBrowser, gtk.STOCK_FIND)
        ]

        if len( files ) == 1:
            items += [    ('NautilusPython::svnlog_file_item', 'Log' , 'Log of %s' % file.get_name(), self.OnShowLog, "rabbitvcs-show_log"),
                        ('NautilusPython::svnupdate_file_item', 'Update' , 'Get the latest code from the repository.', self.OnUpdate, "rabbitvcs-update")
            ]

        # Check if this is a folder, and if so if it's under source control
        if os.path.isdir(path):
            # Check if this folder is versioned
            if os.path.isdir(os.path.join(path, ".svn")):
                # Check if any of our children are modified.
                c = pysvn.Client()
                st = c.status(path, recurse=RECURSIVE_STATUS)
                statuses = set([x.text_status for x in st])
                t = set([    pysvn.wc_status_kind.modified,
                            pysvn.wc_status_kind.added,
                            pysvn.wc_status_kind.deleted])
                if len( t & statuses ):
                    # If so, add some useful menu items
                    items += [    ('NautilusPython::svnmkdiff_file_item', 'Patch', 'Create a patch of %s from the repository version'%file.get_name(), self.OnMkDiff, "rabbitvcs-diff"), 
                                ('NautilusPython::svnrevert_file_item', 'Revert' , 'Revert %s back to the repository version.'%file.get_name(), self.OnRevert, "rabbitvcs-revert")]

                items += [
                    ('NautilusPython::svncommit_file_item', 'Commit' , 'Commit %s to the repository.' % file.get_name(), self.OnCommit, "rabbitvcs-commit"),
                    ('NautilusPython::svnproperties_file_item', 'Properties', 'File properties for %s.'%file.get_name(), self.OnProperties, "rabbitvcs-properties")
                ]

            else:
                # Check if the parent is under source control
                if os.path.isdir(os.path.join(os.path.split(path)[0], ".svn")):
                    items = [('NautilusPython::svnadd_file_item', 'Add' , 'Add %s to the repository.'%file.get_name(), self.OnAdd, "rabbitvcs-add")]
                else:
		            items = [('NautilusPython::svncheckout_file_item', 'Checkout' , 'Checkout code from an SVN repository', self.OnCheckout, "rabbitvcs-checkout")]

        else:
            # We're a file, so lets check if we're in a versioned folder
            if os.path.isdir(os.path.join(os.path.split(path)[0], ".svn")):
                # OK we're in a versioned folder - are we already in SVN?
                c = pysvn.Client()
                st = c.status(path)[0]
                if not st.is_versioned:
                    # If not, we can only offer to add the file.
                    items = [('NautilusPython::svnadd_file_item', 'Add' , 'Add %s to the repository.'%file.get_name(), self.OnAdd, "rabbitvcs-add")]

                # Add the revert and diff items if we've changed from the repos version
                if st.text_status in [pysvn.wc_status_kind.added, pysvn.wc_status_kind.modified]:
                    items += [    ('NautilusPython::svnrevert_file_item', 'Revert' , 'Revert %s back to the repository version.'%file.get_name(), self.OnRevert, "rabbitvcs-revert"), ]

                    if len(files) == 1:
                        items += [    ('NautilusPython::svncommit_file_item', 'Commit' , 'Commit %s to the repository.' % file.get_name(), self.OnCommit, "rabbitvcs-commit"),
                                    ('NautilusPython::svndiff_file_item', 'Diff' , 'Diff %s against the repository version' % file.get_name(), self.OnShowDiff, "rabbitvcs-diff"),
                                    ('NautilusPython::svnmkdiff_file_item', 'Patch', 'Create a patch of %s from the repository version'%file.get_name(), self.OnMkDiff, "rabbitvcs-createpatch"), 
	            ]

                # Add the conflict resolution menu items
                if st.text_status in [pysvn.wc_status_kind.conflicted]:
                    items += [    ('NautilusPython::svnrevert_file_item', 'Revert' , 'Revert %s back to the repository version.'%file.get_name(), self.OnRevert, "rabbitvcs-revert"), ]

                    if len(files) == 1:
                        items += [  ('NautilusPython::svneditconflict_file_item', 'Edit Conflicts' , 'Edit the conflicts found when updating %s.'%file.get_name(), self.OnEditConflicts, None),
                                    ('NautilusPython::svnresolveconflict_file_item', 'Resolved' , 'Mark %s as resolved.'%file.get_name(), self.OnResolveConflicts, "rabbitvcs-resolve")]

                items += [
                    ('NautilusPython::svnproperties_file_item', 'Properties', 'File properties for %s.'%file.get_name(), self.OnProperties, "rabbitvcs-properties")
                ]

            else:
                items = []

        return self.create_menu(window, items, files)

    #-------------------------------------------------------------------------- 
    def get_background_items(self, window, file):
        """ Menu activated on window background
        """

        if file.get_uri() == "x-nautilus-desktop:///":
            return

        path = gnomevfs.get_local_path_from_uri(file.get_uri())

        window.set_data("base_dir", os.path.realpath(six.text_type(path)))

        if not os.path.isdir(os.path.join(path,".svn")):
            items = [     ('NautilusPython::svncheckout_file_item', 'Checkout' , 'Checkout code from an SVN repository', self.OnCheckout, "rabbitvcs-checkout")
                    ]
        else:
            items = [     ('NautilusPython::svnlog_file_item', 'Log' , 'SVN Log of %s' % file.get_name(), self.OnShowLog, "rabbitvcs-show_log"),
                        ('NautilusPython::svncommit_file_item', 'Commit' , 'Commit %s back to the repository.' % file.get_name(), self.OnCommit, "rabbitvcs-commit"),
                        ('NautilusPython::svnrepo_file_item', 'Repository Browser' , 'View Repository Sources', self.OnRepoBrowser, gtk.STOCK_FIND),
                        ('NautilusPython::svnupdate_file_item', 'Update' , 'Get the latest code from the repository.', self.OnUpdate, "rabbitvcs-update"),
                        ('NautilusPython::svnrefreshstatus_file_item', 'Refresh', 'Refresh the display status of %s.'%file.get_name(), self.OnRefreshStatus, "rabbitvcs-refresh"),
                        ('NautilusPython::svnmkdiffdir_file_item', 'Patch', 'Create a patch of %s from the repository version'%file.get_name(), self.OnMkDiffDir, "rabbitvcs-diff"),
                ('NautilusPython::svnproperties_file_item', 'Properties', 'File properties for %s.'%file.get_name(), self.OnProperties, "rabbitvcs-properties")
            ]

        return self.create_menu(window, items, [file])

    def create_menu(self, window, items, paths):
        """
        While I can add submenu items in nautilus-python 0.5.0, I can't get
        the submenu item activate signal to connect to a callback method
        
        menuitem = nautilus.MenuItem('NautilusPython::Svn', 'RabbitVCS', '', "rabbitvcs")
        if hasattr(menuitem, "set_submenu"):
            submenu = nautilus.Menu()
            menuitem.set_submenu(submenu)
            for item in items:
                i = nautilus.MenuItem( item[0], item[1], item[2], item[4] )
                i.connect('activate', item[3], window, paths)
                submenu.append_item( i )

            return menuitem,
		"""
		
        menuitems = []
        for item in items:
            i = nautilus.MenuItem( item[0], item[1], item[2], item[4] )
            i.connect('activate', item[3], window, paths)
            menuitems.append(i)

        return menuitems
            
    #--------------------------------------------------------------------------
    def RescanFilesAfterProcess(self, pid):
        """ Rescans all of the files on our *monitoredFiles* list after the
            process specified by *pid* completes.
        """
        # We need a function that can check the file status once the process has completed.
        def ThreadProc():
            # First we need to see if the commit process is still running
            if os.path.exists("/proc/" + str(pid)):
                # If so, check its status by reading the status file from /proc
                f = open("/proc/%d/status"%pid).readlines()
                # if it's a zombie process, then we can waitpid() on it to end the process
                if "zombie" in f[1]:
                    os.waitpid(pid, 0)

                # Return true to get another callback after the next timeout
                return True
            else:
                # The process has completed, so we now want to rescan the 
                # files we're monitoring to see if their status has changed. We
                # need to make a copy of monitoredFiles as the rescanning process
                # will affect it.
                checkList = copy.copy(self.monitoredFiles)
                while len(checkList):
                    checkList.pop().invalidate_extension_info()
                return False

        # Add our callback function on a 1 second timeout
        gobject.timeout_add(1000, ThreadProc)



    #--------------------------------------------------------------------------
    def OnEditConflicts(self, menuitem, window, files):
        """ Edit Conflicts menu handler.
        """
        file = files[0]    

        path = gnomevfs.get_local_path_from_uri(file.get_uri())
        rabbitvcs.util.helper.launch_diff_tool(path + ".mine", path)

    #-------------------------------------------------------------------------- 
    def OnResolveConflicts(self, menuitem, window, files):
        """ Resolve Conflicts menu handler.
        """
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("resolve", paths)
        self.RescanFilesAfterProcess(pid)

    #--------------------------------------------------------------------------
    def OnRevert(self, menuitem, window, files):
        """ Revert menu handler.
        """

        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("revert", paths)
        self.RescanFilesAfterProcess(pid)

    #--------------------------------------------------------------------------
    def OnCheckout(self, menuitem, window, files):
        """ Checkout menu handler.
        """
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("checkout", paths)

    #--------------------------------------------------------------------------
    def OnShowDiff(self, menuitem, window, files):
        """ Diff menu handler.
        """

        paths = self.get_paths_from_files(files)
        rabbitvcs.util.helper.launch_diff_tool(*paths)

    #--------------------------------------------------------------------------
    def OnShowLog(self, menuitem, window, files):
        """ Show Log menu handler.
        """
        
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("log", paths)
        self.RescanFilesAfterProcess(pid)

    #-------------------------------------------------------------------------- 
    def OnCommit(self, menuitem, window, files):
        """ Commit menu handler.
        """
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("commit", ["--base-dir=" + window.get_data("base_dir")] + paths)
        self.RescanFilesAfterProcess(pid)

    #--------------------------------------------------------------------------
    def OnUpdate(self, menuitem, window, files):
        """ Update menu handler.
        """
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("update", paths)
        self.RescanFilesAfterProcess(pid)

    #--------------------------------------------------------------------------
    def OnAdd(self, menuitem, window, files):
        """ Add menu handler.
        """
        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("add", paths)
        self.RescanFilesAfterProcess(pid)

    #-------------------------------------------------------------------------- 
    def OnDelete(self, menuitem, window, files):
        """ Delete menu handler.
        """

        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("delete", paths)
        self.RescanFilesAfterProcess(pid)

    #-------------------------------------------------------------------------- 
    def OnRename(self, menuitem, window, files):
        """ Delete menu handler.
        """

        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("rename", paths)
        self.RescanFilesAfterProcess(pid)

    #-------------------------------------------------------------------------- 
    def OnRepoBrowser(self, menuitem, window, files):
        """ Repository Browser menu handler.
        """

        paths = self.get_paths_from_files(files)
        pid = rabbitvcs.util.helper.launch_ui_window("browser", [paths[0]])
        self.RescanFilesAfterProcess(pid)
        
    #--------------------------------------------------------------------------
    def OnRefreshStatus(self, menuitem, window, files):
        """ Refresh status menu handler. Invalidates the status of all of the selected files.
        """
        for file in files:
            file.invalidate_extension_info()

    #--------------------------------------------------------------------------
    def OnProperties(self, menuitem, window, files):
        """ Properties menu handler.
        """
        file = files[0]
        path = gnomevfs.get_local_path_from_uri(file.get_uri())
        pid = rabbitvcs.util.helper.launch_ui_window("property_editor", [path])
        self.RescanFilesAfterProcess(pid)

    #--------------------------------------------------------------------------
    def OnMkDiff(self, menuitem, window, files):
        """ MkDiff menu handler.
        """

        paths = self.get_paths_from_files(files)	    
        proc = launch_ui_window("createpatch", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    #--------------------------------------------------------------------------
    def OnMkDiffDir(self, menuitem, window, files):
        """ MkDiffDir menu handler.
        """

        paths = self.get_paths_from_files(files)
        proc = launch_ui_window("createpatch", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def get_paths_from_files(self, files):
        paths = []
        for file in files:
            paths.append(gnomevfs.get_local_path_from_uri(file.get_uri()))
        
        return paths

#============================================================================== 
