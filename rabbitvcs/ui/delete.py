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

from rabbitvcs.util import helper

from gi import require_version
require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject
sa.restore()

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.vcs
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.delete")

from rabbitvcs import gettext
_ = gettext.gettext

class Delete(InterfaceNonView):
    """
    This class provides a handler to Delete functionality.

    """

    def __init__(self, paths):
        InterfaceNonView.__init__(self)
        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()

    def start(self):

        # From the given paths, determine which are versioned and which are not
        versioned = []
        unversioned = []
        for path in self.paths:
            if self.vcs.is_versioned(path):
                versioned.append(path)
            elif os.path.exists(path):
                unversioned.append(path)

        # If there are unversioned files, confirm that the user wants to
        # delete those.  Default to true.
        result = True
        if unversioned:
            item = None
            if len(unversioned) == 1:
                item = unversioned[0]
            confirm = rabbitvcs.ui.dialog.DeleteConfirmation(item)
            result = confirm.run()

        # If the user wants to continue (or there are no unversioned files)
        # remove or delete the given files
        if result == Gtk.ResponseType.OK or result == True:
            if versioned:
                try:
                    self.vcs_remove(versioned, force=True)
                except Exception as e:
                    log.exception()
                    return

            if unversioned:
                for path in unversioned:
                    helper.delete_item(path)

class SVNDelete(Delete):
    def __init__(self, paths):
        Delete.__init__(self, paths)

    def vcs_remove(self, paths, **kwargs):
        if rabbitvcs.vcs.guess(paths[0])["vcs"] == rabbitvcs.vcs.VCS_SVN:
            self.vcs.svn().remove(paths, **kwargs)

class GitDelete(Delete):
    def __init__(self, paths):
        Delete.__init__(self, paths)

    def vcs_remove(self, paths, **kwargs):
        if rabbitvcs.vcs.guess(paths[0])["vcs"] == rabbitvcs.vcs.VCS_GIT:
            self.vcs.git(paths[0]).remove(paths)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNDelete,
    rabbitvcs.vcs.VCS_GIT: GitDelete
}

def delete_factory(paths):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs delete [path1] [path2] ...")

    window = delete_factory(paths)
    window.register_gtk_quit()
    window.start()
