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
import os.path
import six.moves._thread
import shutil

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction, GitAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.util.helper
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.editconflicts")

from rabbitvcs import gettext
_ = gettext.gettext

class SVNEditConflicts(InterfaceNonView):
    def __init__(self, path):
        InterfaceNonView.__init__(self)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
        
        status = self.svn.status(self.path)
        if status.simple_content_status() != rabbitvcs.vcs.status.status_complicated:
            log.debug("The specified file is not conflicted.  There is nothing to do.")
            self.close()
            return
        
        filename = os.path.basename(path)
        
        dialog = rabbitvcs.ui.dialog.ConflictDecision(filename)
        (action, mark_resolved) = dialog.run()
        dialog.destroy()
        
        if action == -1:
            #Cancel
            pass
            
        elif action == 0:
            #Accept Mine
            working = self.get_working_path(path)
            shutil.copyfile(working, path)

            if mark_resolved:
                self.svn.resolve(path)
                
        elif action == 1:
            #Accept Theirs
            head = self.get_head_path(path)
            shutil.copyfile(head, path)

            if mark_resolved:
                self.svn.resolve(path)
                
        elif action == 2:
            #Merge Manually
            
            head = self.get_head_path(path)
            working = self.get_working_path(path)
            shutil.copyfile(working, path)
            
            rabbitvcs.util.helper.launch_merge_tool(path, head)

            if mark_resolved:
                self.svn.resolve(path)

        self.close()

    def get_working_path(self, path):
        paths = [
            "%s.mine" % path,
            "%s.working" % path
        ]
        
        for working in paths:
            if os.path.exists(working):
                return working

        return path

    def get_head_path(self, path):
        # There might be a merge-right file if merging from a different branch
        paths = os.listdir(os.path.dirname(path))
        for head in paths:
            if head.find(os.path.basename(path)) != -1 and head.find("merge-right") != -1:
                return os.path.join(os.path.dirname(path), head)

        # If no merge-right file exists, merging is coming from head
        # so export the file from head
        tmppath = rabbitvcs.util.helper.get_tmp_path("%s.head" % os.path.basename(path))
        self.svn.export(path, tmppath)

        return tmppath

class GitEditConflicts(InterfaceNonView):
    def __init__(self, path):
        InterfaceNonView.__init__(self)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        rabbitvcs.util.helper.launch_merge_tool(self.path)
        
        self.close()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNEditConflicts,
    rabbitvcs.vcs.VCS_GIT: GitEditConflicts
}

def editconflicts_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)
        
if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs edit-conflicts [path1] [path2] ..."
    )

    window = editconflicts_factory(paths[0])
    window.register_gtk_quit()
    gtk.main()
