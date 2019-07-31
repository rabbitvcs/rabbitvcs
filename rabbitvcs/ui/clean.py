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

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk, Pango
sa.restore()

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import GitAction
import rabbitvcs.ui.widget
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class GitClean(InterfaceView):
    """
    Provides a UI to clean your repository of untracked files

    """

    def __init__(self, path):
        InterfaceView.__init__(self, "clean", "Clean")
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)
        self.path = path

    def on_ok_clicked(self, widget):
        remove_dir = self.get_widget("remove_directories").get_active()
        remove_ignored_too = self.get_widget("remove_ignored_too").get_active()
        remove_only_ignored = self.get_widget("remove_only_ignored").get_active()
        dry_run = self.get_widget("dryrun").get_active()
        force = self.get_widget("force").get_active()

        self.hide()
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Clean"))
        self.action.append(self.action.set_status, _("Running Clean Command..."))
        self.action.append(
            self.git.clean,
            self.path,
            remove_dir,
            remove_ignored_too,
            remove_only_ignored,
            dry_run,
            force
        )
        self.action.append(self.action.set_status, _("Completed Clean"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_remove_ignored_too_toggled(self, widget):
        remove_ignored_too = self.get_widget("remove_ignored_too")
        remove_only_ignored = self.get_widget("remove_only_ignored")

        if remove_ignored_too.get_active():
            remove_only_ignored.set_active(False)

    def on_remove_only_ignored_toggled(self, widget):
        remove_ignored_too = self.get_widget("remove_ignored_too")
        remove_only_ignored = self.get_widget("remove_only_ignored")

        if remove_only_ignored.get_active():
            remove_ignored_too.set_active(False)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs clean path")

    window = GitClean(paths[0])
    window.register_gtk_quit()
    Gtk.main()
