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
from rabbitvcs.util.strings import *

from rabbitvcs import gettext
_ = gettext.gettext

class SVNSwitch(InterfaceView):
    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "switch", "Switch")

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.get_widget("path").set_text(S(self.path).display())
        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("repositories"),
            helper.get_repository_paths()
        )

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.svn,
            revision=revision,
            url_combobox=self.repositories,
            expand=True
        )

        self.repositories.set_child_text(helper.unquote_url(self.svn.get_repo_url(self.path)))

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()

        if not url or not self.path:
            rabbitvcs.ui.dialog.MessageBox(_("The repository location is a required field."))
            return

        revision = self.revision_selector.get_revision_object()
        self.hide()
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Switch"))
        self.action.append(self.action.set_status, _("Running Switch Command..."))
        self.action.append(helper.save_repository_path, url)
        self.action.append(
            self.svn.switch,
            self.path,
            helper.quote_url(url),
            revision=revision
        )
        self.action.append(self.action.set_status, _("Completed Switch"))
        self.action.append(self.action.finish)
        self.action.schedule()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNSwitch
}

def switch_factory(path, revision=None):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path, revision)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT
    (options, args) = main(
        [REVISION_OPT],
        usage="Usage: rabbitvcs switch [url]"
    )

    window = switch_factory(args[0], revision=options.revision)
    window.register_gtk_quit()
    Gtk.main()
