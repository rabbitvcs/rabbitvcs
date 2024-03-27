from __future__ import absolute_import
from rabbitvcs import gettext
import rabbitvcs.vcs
import rabbitvcs.ui.widget
from rabbitvcs.ui.action import GitAction
from rabbitvcs.ui import GtkTemplateHelper
import time
from datetime import datetime
from gi.repository import Gtk, GObject, Gdk, Pango

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

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


_ = gettext.gettext


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/clean.xml")
class CleanWidget(Gtk.Box):
    __gtype_name__ = "CleanWidget"

    remove_directories = Gtk.Template.Child()
    remove_ignored_too = Gtk.Template.Child()
    remove_only_ignored = Gtk.Template.Child()
    dryrun = Gtk.Template.Child()
    force = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)


class GitClean(GtkTemplateHelper):
    """
    Provides a UI to clean your repository of untracked files

    """

    def __init__(self, path):
        GtkTemplateHelper.__init__(self, "Clean")

        self.widget = CleanWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Clean", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.remove_ignored_too.connect("toggled", self.on_remove_ignored_too_toggled)
        self.widget.remove_only_ignored.connect("toggled", self.on_remove_only_ignored_toggled)
        
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)
        self.path = path

    def on_ok_clicked(self, widget):
        remove_dir = self.widget.remove_directories.get_active()
        remove_ignored_too = self.widget.remove_ignored_too.get_active()
        remove_only_ignored = self.widget.remove_only_ignored.get_active()
        dry_run = self.widget.dryrun.get_active()
        force = self.widget.force.get_active()

        self.window.set_visible(False)
        self.action = rabbitvcs.ui.action.GitAction(
            self.git
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
            force,
        )
        self.action.append(self.action.set_status, _("Completed Clean"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def on_remove_ignored_too_toggled(self, widget):
        if self.widget.remove_ignored_too.get_active():
            self.widget.remove_only_ignored.set_active(False)

    def on_remove_only_ignored_toggled(self, widget):
        if self.widget.remove_only_ignored.get_active():
            self.widget.remove_ignored_too.set_active(False)


def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs clean path")

    widget = GitClean(paths[0])
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
