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

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.checkout import Checkout
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
from rabbitvcs.util.strings import S
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class GitClone(Checkout):
    def __init__(self, path=None, url=None):
        Checkout.__init__(self, path, url)

        self.git = self.vcs.git()

        self.get_widget("Checkout").set_title(_("Clone"))
        self.get_widget("repo_chooser").hide()
        self.get_widget("options_box").hide()
        self.get_widget("revision_selector_box").hide()

        self.default_text()
        self.check_form()

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text().strip()
        path = self._get_path().strip()

        if not url or not path:
            rabbitvcs.ui.dialog.MessageBox(_("The repository URL and destination path are both required fields."))
            return

        self.hide()
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Clone"))
        self.action.append(self.action.set_status, _("Running Clone Command..."))
        self.action.append(helper.save_repository_path, url)
        self.action.append(
            self.git.clone,
            url,
            path
        )
        self.action.append(self.action.set_status, _("Completed Clone"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_repositories_changed(self, widget, data=None):
        url = self.repositories.get_active_text()
        tmp = [x.strip() for x in url.split("/") if x.strip()]
        if tmp and tmp[0].lower() in ("http:", "https:", "file:", "git:"):
            del tmp[0]
        append = tmp[-1] if tmp else ""
        if append.endswith(".git"):
            append = append[:-4]

        helper.run_in_main_thread(self.get_widget("destination").set_text,
                                  S(os.path.join(self.destination, append)).display())
        self.check_form()

    def default_text(self):
        # Use a repo url from the clipboard by default.
        clipboard = Gtk.Clipboard.get(Gdk.Atom.intern("CLIPBOARD", False))
        text = clipboard.wait_for_text()
        if text and text.endswith(('.git', '.git/')):
            self.repositories.set_child_text(text)

    def check_form(self):
        self.complete = True
        if self.repositories.get_active_text() == "":
            self.complete = False
        if self.get_widget("destination").get_text() == "":
            self.complete = False

        self.get_widget("ok").set_sensitive(self.complete)

classes_map = {
    rabbitvcs.vcs.VCS_GIT: GitClone
}

def clone_factory(classes_map, vcs, path=None, url=None):
    return classes_map[vcs](path, url)


if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT
    (options, args) = main(
        [VCS_OPT],
        usage="Usage: rabbitvcs clone --vcs=git [url] [path]"
    )

    # Default to using git
    vcs = rabbitvcs.vcs.VCS_GIT
    if options.vcs:
        vcs = options.vcs

    # If two arguments are passed:
    #   The first argument is expected to be a url
    #   The second argument is expected to be a path
    # If one argument is passed:
    #   If the argument exists, it is a path
    #   Otherwise, it is a url
    path = url = None
    if len(args) == 2:
        path = args[0]
        url = args[1]
    elif len(args) == 1:
        if os.path.exists(args[0]):
            path = args[0]
        else:
            url = args[0]

    window = clone_factory(classes_map, vcs, path=path, url=url)
    window.register_gtk_quit()
    Gtk.main()
