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
import subprocess

import pygtk
import gobject
import gtk

import rabbitvcs.ui.dialog
from rabbitvcs.ui.action import GitAction

from rabbitvcs import gettext
_ = gettext.gettext

class SVNCreate:
    """
    Provides an interface to create a svn repository
    """
    
    # Also, might want to just launch a terminal window instead of this
    def __init__(self, path):
    
    
        if not os.path.isdir(path):
            os.makedirs(path)
        
        # Let svnadmin return a bad value if a repo already exists there
        ret = subprocess.call(["/usr/bin/svnadmin", "create", path])
        if ret == 0:
            rabbitvcs.ui.dialog.MessageBox(_("Repository successfully created"))
        else:
            rabbitvcs.ui.dialog.MessageBox(_("There was an error creating the repository.  Make sure the given folder is empty."))
        
class GitCreate:
    # Also, might want to just launch a terminal window instead of this
    def __init__(self, path):
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git()
        self.path = path
        
        self.action = GitAction(
            self.git,
            register_gtk_quit=True
        )
        
        self.action.append(self.action.set_header, _("Initialize Repository"))
        self.action.append(self.action.set_status, _("Setting up repository..."))
        self.action.append(self.git.initialize_repository, self.path)
        self.action.append(self.action.set_status, _("Completed repository setup"))
        self.action.append(self.action.finish)
        self.action.start()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNCreate,
    rabbitvcs.vcs.VCS_GIT: GitCreate
}

if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT, VCS_OPT_ERROR
    (options, paths) = main([VCS_OPT], usage="Usage: rabbitvcs create --vcs [svn|git] path")
    if options.vcs:
        window = classes_map[options.vcs](paths[0])
        if options.vcs == rabbitvcs.vcs.VCS_GIT:
            gtk.main()
    else:
        rabbitvcs.ui.dialog.MessageBox(VCS_OPT_ERROR)
