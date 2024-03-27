from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.util.strings import S
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
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

from rabbitvcs.util import helper

import os
import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


_ = gettext.gettext


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/import.xml")
class ImportWidget(Gtk.Grid):
    __gtype_name__ = "ImportWidget"

    repositories = Gtk.Template.Child()
    include_ignored = Gtk.Template.Child()
    message = Gtk.Template.Child()
    previous_messages = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

class SVNImport(GtkTemplateHelper):
    def __init__(self, path):
        GtkTemplateHelper.__init__(self, "Import")

        self.widget = ImportWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.cancel = self.add_dialog_button("Import", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Close", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.previous_messages.connect("clicked", self.on_previous_messages_clicked)
        # set window properties
        self.window.set_default_size(550, -1)

        self.window.set_title(_("Import - %s") % path)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.widget.repositories, helper.get_repository_paths()
        )

        if self.svn.is_in_a_or_a_working_copy(path):
            self.repositories.set_child_text(
                S(self.svn.get_repo_url(path)).display()
            )

        self.message = rabbitvcs.ui.widget.TextView(self.widget.message)

    def on_ok_clicked(self, widget):

        url = self.widget.repositories.get_active_text()
        if not url:
            self.exec_dialog(self.window, _("The repository URL field is required."), show_cancel=False)
            return

        ignore = not self.widget.include_ignored.get_active()

        self.window.set_visible(False)

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn, register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Import"))
        self.action.append(self.action.set_status, _("Running Import Command..."))
        self.action.append(
            self.svn.import_, self.path, url, self.message.get_text(), ignore=ignore
        )
        self.action.append(self.action.set_status, _("Completed Import"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages(self.window)
        dialog.run(self.on_response)

    def on_response(self, message):
        if message is not None:
            self.message.set_text(S(message).display())


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNImport}


def import_factory(path):
    vcs = rabbitvcs.vcs.VCS_SVN
    return classes_map[vcs](path)


def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs import [path]")

    widget = import_factory(paths[0])
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
