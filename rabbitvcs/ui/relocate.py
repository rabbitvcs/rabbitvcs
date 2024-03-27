from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.util.strings import S
import rabbitvcs.vcs
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.ui.action import SVNAction
from rabbitvcs.ui import GtkTemplateHelper
from gi.repository import Gtk, GObject, Gdk

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


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/relocate.xml")
class RelocateWidget(Gtk.Grid):
    __gtype_name__ = "RelocateWidget"

    from_url = Gtk.Template.Child()
    to_url = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

class Relocate(GtkTemplateHelper):
    """
    Interface to relocate your working copy's repository location.

    """

    def __init__(self, path):
        """
        @type   path: string
        @param  path: A path to a local working copy

        """

        GtkTemplateHelper.__init__(self, "Relocate")

        self.widget = RelocateWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Relocate", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # set window properties
        self.window.set_default_size(640, -1)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        repo = S(self.svn.get_repo_url(self.path)).display()
        self.widget.from_url.set_text(repo)
        self.widget.to_url.get_child().set_text(repo)

        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.widget.to_url, helper.get_repository_paths()
        )

    def on_ok_clicked(self, widget):

        from_url = self.widget.from_url.get_text()
        to_url = self.widget.to_url.get_active_text()

        if not from_url or not to_url:
            self.exec_dialog(self.window, _("The from and to url fields are both required."), show_cancel=False)
            return

        self.window.hide()

        self.action = SVNAction(self.svn, register_gtk_quit=self.gtk_quit_is_set())

        self.action.append(self.action.set_header, _("Relocate"))
        self.action.append(self.action.set_status, _("Running Relocate Command..."))
        self.action.append(self.svn.relocate, from_url, to_url, self.path)
        self.action.append(self.action.set_status, _("Completed Relocate"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()


def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs relocate [path]")

    widget = Relocate(paths[0])
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
