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

import os.path

import pygtk
import gobject
import gtk
import os
import commands

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.vcs
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.applypatch")

from rabbitvcs import gettext
_ = gettext.gettext

class ApplyPatch(InterfaceNonView):
    """
    This class provides a handler to the apply patch functionality.
    
    """

    def __init__(self, paths):
        InterfaceNonView.__init__(self)
        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.common = rabbitvcs.util.helper.get_common_directory(paths)

    def choose_patch_path(self):
        path = None
        
        dialog = gtk.FileChooserDialog(
            _("Apply Patch"),
            None,
            gtk.FILE_CHOOSER_ACTION_OPEN,(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            path = dialog.get_filename()
        
        dialog.destroy()
        
        return path
    
    def choose_patch_dir(self):
        if len(self.paths) == 1 and os.path.isdir(self.paths[0]):
            return self.paths[0]
        
        dir = None
        
        dialog = gtk.FileChooserDialog(
                    _("Apply Patch To Directory..."),
                    None,
                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            dir = dialog.get_filename()
            
        dialog.destroy()
        
        return dir

class SVNApplyPatch(ApplyPatch):
    def __init__(self, paths):
        ApplyPatch.__init__(self, paths)
        
        self.svn = self.vcs.svn()

    def start(self):
    
        path = self.choose_patch_path()
        # If empty path, means we've cancelled
        if not path:
            return
        
        base_dir = self.choose_patch_dir()
        if not base_dir:
            return        
        
        ticks = 2
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Apply Patch"))
        self.action.append(self.action.set_status, _("Applying Patch File..."))
        self.action.append(self.svn.apply_patch, path, base_dir)
        self.action.append(self.action.set_status, _("Patch File Applied"))
        self.action.append(self.action.finish)
        self.action.start()

class GitApplyPatch(ApplyPatch):
    def __init__(self, paths):
        ApplyPatch.__init__(self, paths)
        
        self.git = self.vcs.git(paths[0])

    def start(self):
    
        path = self.choose_patch_path()
        # If empty path, means we've cancelled
        if not path:
            return
        
        base_dir = self.choose_patch_dir()
        if not base_dir:
            return        
        
        ticks = 2
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Apply Patch"))
        self.action.append(self.action.set_status, _("Applying Patch File..."))
        self.action.append(self.git.apply_patch, path, base_dir)
        self.action.append(self.action.set_status, _("Patch File Applied"))
        self.action.append(self.action.finish)
        self.action.start()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNApplyPatch,
    rabbitvcs.vcs.VCS_GIT: GitApplyPatch
}

def applypatch_factory(paths):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs applypatch [path1] [path2] ...")

    window = applypatch_factory(paths)
    window.register_gtk_quit()
    window.start()
    gtk.main()
    
