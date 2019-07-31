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

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
from rabbitvcs.util.strings import S

from rabbitvcs import gettext
_ = gettext.gettext

class SVNImport(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "import", "Import")

        self.get_widget("Import").set_title(_("Import - %s") % path)

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        if self.svn.is_in_a_or_a_working_copy(path):
            self.get_widget("repository").set_text(S(self.svn.get_repo_url(path)).display())

        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("repositories"),
            helper.get_repository_paths()
        )

        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
        )

    def on_ok_clicked(self, widget):

        url = self.get_widget("repository").get_text()
        if not url:
            rabbitvcs.ui.dialog.MessageBox(_("The repository URL field is required."))
            return

        ignore = not self.get_widget("include_ignored").get_active()

        self.hide()

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Import"))
        self.action.append(self.action.set_status, _("Running Import Command..."))
        self.action.append(
            self.svn.import_,
            self.path,
            url,
            self.message.get_text(),
            ignore=ignore
        )
        self.action.append(self.action.set_status, _("Completed Import"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(S(message).display())



classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNImport
}

def import_factory(path):
    vcs = rabbitvcs.vcs.VCS_SVN
    return classes_map[vcs](path)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs import [path]")

    window = import_factory(paths[0])
    window.register_gtk_quit()
    Gtk.main()
