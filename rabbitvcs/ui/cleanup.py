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

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class SVNCleanup(InterfaceNonView):
    """
    This class provides a handler to the Cleanup window view.
    The idea is that it displays a large folder icon with a label like
    "Please Wait...".  Then when it finishes cleaning up, the label will
    change to "Finished cleaning up /path/to/folder"

    """

    def __init__(self, path):
        InterfaceNonView.__init__(self)
        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

    def start(self):
        self.action = SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Cleanup"))
        self.action.append(self.action.set_status, _("Cleaning Up..."))
        self.action.append(self.svn.cleanup, self.path)
        self.action.append(self.action.set_status, _("Completed Cleanup"))
        self.action.append(self.action.finish)
        self.action.schedule()


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs cleanup [path]")

    window = SVNCleanup(paths[0])
    window.register_gtk_quit()
    window.start()
    Gtk.main()
