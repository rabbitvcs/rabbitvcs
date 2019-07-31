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
from rabbitvcs.util.strings import S
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class GitReset(InterfaceView):
    """
    Provides a UI to reset your repository to some specified state

    """

    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "reset", "Reset")
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)
        self.path = path
        self.revision_obj = None
        if revision:
            self.revision_obj = self.git.revision(revision)

        self.get_widget("path").set_text(S(path).display())

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.git,
            revision=self.revision_obj,
            url=self.path,
            expand=True
        )

        self.get_widget("none_opt").set_active(True)
        self.check_path()

    def on_ok_clicked(self, widget):
        path = self.get_widget("path").get_text()

        mixed = self.get_widget("mixed_opt").get_active()
        soft = self.get_widget("soft_opt").get_active()
        hard = self.get_widget("hard_opt").get_active()
        merge = self.get_widget("merge_opt").get_active()
        none = self.get_widget("none_opt").get_active()

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

        self.hide()
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Reset"))
        self.action.append(self.action.set_status, _("Running Reset Command..."))
        self.action.append(
            self.git.reset,
            path,
            revision,
            type
        )
        self.action.append(self.action.set_status, _("Completed Reset"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_browse_clicked(self, widget, data=None):
        chooser = rabbitvcs.ui.dialog.FolderChooser()
        path = chooser.run()
        if path is not None:
            self.get_widget("path").set_text(S(path).display())

    def on_path_changed(self, widget, data=None):
        self.check_path()

    def check_path(self):
        path = self.get_widget("path").get_text()
        root = self.git.find_repository_path(path)
        if root != path:
            self.get_widget("none_opt").set_active(True)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, paths) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs reset [-r REVISION] path"
    )

    window = GitReset(paths[0], options.revision)
    window.register_gtk_quit()
    Gtk.main()
