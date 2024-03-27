from __future__ import absolute_import
from rabbitvcs import gettext
import rabbitvcs.vcs
from rabbitvcs.util.strings import S
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


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/reset.xml")
class ResetWidget(Gtk.Box):
    __gtype_name__ = "ResetWidget"

    path = Gtk.Template.Child()
    browse = Gtk.Template.Child()
    revision_container = Gtk.Template.Child()
    none_opt = Gtk.Template.Child()
    mixed_opt = Gtk.Template.Child()
    soft_opt = Gtk.Template.Child()
    hard_opt = Gtk.Template.Child()
    merge_opt = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)

class GitReset(GtkTemplateHelper):
    """
    Provides a UI to reset your repository to some specified state

    """

    def __init__(self, path, revision=None):
        GtkTemplateHelper.__init__(self, "Reset")

        self.widget = ResetWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Reset", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.path.connect("changed", self.on_path_changed)
        self.widget.browse.connect("clicked", self.on_browse_clicked)

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)
        self.path = path
        self.revision_obj = None
        if revision:
            self.revision_obj = self.git.revision(revision)

        self.widget.path.set_text(S(path).display())

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.widget.revision_container,
            self.git,
            revision=self.revision_obj,
            url=self.path,
            expand=True,
        )

        self.widget.none_opt.set_active(True)
        self.check_path()

    def on_ok_clicked(self, widget):
        path = self.widget.path.get_text()

        mixed = self.widget.mixed_opt.get_active()
        soft = self.widget.soft_opt.get_active()
        hard = self.widget.hard_opt.get_active()
        merge = self.widget.merge_opt.get_active()
        none = self.widget.none_opt.get_active()

        type = None
        if mixed:
            type = "mixed"
        if soft:
            type = "soft"
        if hard:
            type = "hard"
        if merge:
            type = "merge"

        revision = self.revision_selector.get_revision_object()

        self.window.hide()
        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )
        self.action.append(self.action.set_header, _("Reset"))
        self.action.append(self.action.set_status, _("Running Reset Command..."))
        self.action.append(self.git.reset, path, revision, type)
        self.action.append(self.action.set_status, _("Completed Reset"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def on_browse_clicked(self, widget, data=None):
        chooser = rabbitvcs.ui.dialog.FolderChooser(parent=self.window, callback=self.on_browse_callback)

    def on_browse_callback(self, path):
        if path is not None:
            self.widget.path.set_text(S(path).display())

    def on_path_changed(self, widget, data=None):
        self.check_path()

    def check_path(self):
        path = self.widget.path.get_text()
        root = self.git.find_repository_path(path)
        if root != path:
            self.widget.none_opt.set_active(True)


def on_activate(app):
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT

    (options, paths) = main(
        [REVISION_OPT, VCS_OPT], usage="Usage: rabbitvcs reset [-r REVISION] path"
    )

    widget = GitReset(paths[0], options.revision)
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
