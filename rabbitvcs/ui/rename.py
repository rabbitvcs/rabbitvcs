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

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction
from rabbitvcs.ui.dialog import MessageBox, OneLineTextChange
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class Rename(InterfaceNonView):
    DO_RENAME = False

    def __init__(self, path):
        InterfaceNonView.__init__(self)
        self.register_gtk_quit()

        self.vcs = rabbitvcs.vcs.VCS()

        self.path = path

        if not os.path.exists(self.path):
            MessageBox(_("The requested file or folder does not exist."))
            self.close()
            return

        dialog = OneLineTextChange(_("Rename"), _("New Name:"), self.path)
        (result, new_path) = dialog.run()

        if result != Gtk.ResponseType.OK:
            self.close()
            return

        if not new_path:
            MessageBox(_("The new name field is required"))

        self.new_path = new_path
        self.DO_RENAME = True

class SVNRename(Rename):
    def __init__(self, path):
        Rename.__init__(self, path)

        if not self.DO_RENAME:
            return

        self.svn = self.vcs.svn()

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        dirname = os.path.dirname(self.new_path)
        if not os.path.exists(dirname):
            os.mkdir(dirname)
            self.svn.add(dirname)

        self.action.append(self.action.set_header, _("Rename"))
        self.action.append(self.action.set_status, _("Running Rename Command..."))
        self.action.append(
            self.svn.move,
            self.path,
            self.new_path
        )
        self.action.append(self.action.set_status, _("Completed Rename"))
        self.action.append(self.action.finish)
        self.action.append(self.close)
        self.action.schedule()

class GitRename(Rename):
    def __init__(self, path):
        Rename.__init__(self, path)

        if not self.DO_RENAME:
            return

        self.git = self.vcs.git(path)

        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        dirname = os.path.dirname(os.path.realpath(self.new_path))
        if not os.path.exists(dirname):
            os.mkdir(dirname)

        self.action.append(self.action.set_header, _("Rename"))
        self.action.append(self.action.set_status, _("Running Rename Command..."))
        self.action.append(
            self.git.move,
            self.path,
            self.new_path
        )
        self.action.append(self.action.set_status, _("Completed Rename"))
        self.action.append(self.action.finish)
        self.action.append(self.close)
        self.action.schedule()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNRename,
    rabbitvcs.vcs.VCS_GIT: GitRename
}

def rename_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs rename [path]")

    window = rename_factory(os.path.abspath(paths[0]))
    Gtk.main()
