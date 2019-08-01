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

import six.moves._thread

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.add import Add
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log

import rabbitvcs.vcs

log = Log("rabbitvcs.ui.unstage")

from rabbitvcs import gettext
_ = gettext.gettext

class GitUnstage(Add):
    def setup(self, window, columns):
        window.set_title(_("Unstage"))
        self.git = self.vcs.git(self.paths[0])
        self.statuses = self.git.STATUSES_FOR_UNSTAGE

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append([
                True,
                S(item.path),
                item.path,
                helper.get_file_extension(item.path)
            ])

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return
        self.hide()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Unstage"))
        self.action.append(self.action.set_status, _("Running Unstage Command..."))
        for item in items:
            self.action.append(self.git.unstage, item)
        self.action.append(self.action.set_status, _("Completed Unstage"))
        self.action.append(self.action.finish)
        self.action.schedule()

class GitUnstageQuiet:
    def __init__(self, paths, base_dir=None):
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(paths[0])
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            run_in_thread=False
        )

        for path in paths:
            self.action.append(self.git.unstage, path)
        self.action.schedule()

classes_map = {
    rabbitvcs.vcs.VCS_GIT: GitUnstage
}

quiet_classes_map = {
    rabbitvcs.vcs.VCS_GIT: GitUnstageQuiet
}

def unstage_factory(classes_map, paths, base_dir=None):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)


if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT, QUIET_OPT
    (options, paths) = main(
        [BASEDIR_OPT, QUIET_OPT],
        usage="Usage: rabbitvcs unstage [path1] [path2] ..."
    )

    if options.quiet:
        unstage_factory(quiet_classes_map, paths)
    else:
        window = unstage_factory(classes_map, paths, options.base_dir)
        window.register_gtk_quit()
        Gtk.main()
