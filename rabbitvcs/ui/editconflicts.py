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

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction, GitAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.editconflicts")

from rabbitvcs import gettext
_ = gettext.gettext

class SVNEditConflicts(InterfaceNonView):
    def __init__(self, path):
        InterfaceNonView.__init__(self)

        log.debug("incoming path: %s"%path)
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
        action = dialog.run()
        dialog.destroy()

        if action == -1:
            #Cancel
            pass

        elif action == 0:
            #Accept Mine
            working = self.get_working_path(path)
            shutil.copyfile(working, path)
            self.svn.resolve(path)

        elif action == 1:
            #Accept Theirs
            ancestor, theirs = self.get_revisioned_paths(path)
            shutil.copyfile(theirs, path)
            self.svn.resolve(path)

        elif action == 2:
            #Merge Manually

            working = self.get_working_path(path)
            ancestor, theirs = self.get_revisioned_paths(path)

            log.debug("launching merge tool with base: %s, mine: %s, theirs: %s, merged: %s"%(ancestor, working, theirs, path))
            helper.launch_merge_tool(base=ancestor, mine=working, theirs=theirs, merged=path)

            dialog = rabbitvcs.ui.dialog.MarkResolvedPrompt()
            mark_resolved = dialog.run()
            dialog.destroy()

            if mark_resolved == 1:
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

    def get_revisioned_paths(self, path):
        """ Will return a tuple where the first element is the common ancestor's
            path and the second is the path of the the file being merged in."""
        ancestorPath = ""
        theirsPath = ""
        revisionPaths = []
        baseDir, baseName = os.path.split(path)
        log.debug("baseDir: %s, baseName: %s"%(baseDir, baseName))
        for name in os.listdir(baseDir):
            if baseName in name:
                extension = name.split(".")[-1]
                log.debug("extension: %s"%extension)
                if extension.startswith("r"):
                    revision = extension[1:]
                    log.debug("revision: %s"%revision)
                    revisionPaths.append((revision,name))
        if len(revisionPaths) == 2:
            if revisionPaths[0][0] < revisionPaths[1][0]:
                ancestorPath = os.path.join(baseDir, revisionPaths[0][1])
                theirsPath = os.path.join(baseDir, revisionPaths[1][1])
            else:
                ancestorPath = os.path.join(baseDir, revisionPaths[1][1])
                theirsPath = os.path.join(baseDir, revisionPaths[0][1])
            return (ancestorPath, theirsPath)
        else:
            log.error("Unexpected number (%d) of revision paths found"%len(revisionPaths))
            return ("", "")


class GitEditConflicts(InterfaceNonView):
    def __init__(self, path):
        InterfaceNonView.__init__(self)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        helper.launch_merge_tool(self.path)

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
    Gtk.main()
