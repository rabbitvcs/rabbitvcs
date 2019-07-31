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
from rabbitvcs.ui.checkout import SVNCheckout
from rabbitvcs.ui.clone import GitClone
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.ui.action import SVNAction, GitAction
from rabbitvcs.util.strings import S
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class SVNExport(SVNCheckout):
    def __init__(self, path=None, revision=None):
        SVNCheckout.__init__(self, path, url=None, revision=revision)

        self.svn = self.vcs.svn()

        self.get_widget("Checkout").set_title(_("Export - %s") % path)

        # Determine behavior based on the given path
        if self.svn.is_in_a_or_a_working_copy(path):
            # If path is from a working copy, export FROM path and set revision
            # to working copy
            self.repositories.set_child_text(path)
            self.get_widget("destination").set_text("")
            if revision is None:
                self.revision_selector.set_kind_working()
        elif self.svn.is_path_repository_url(path):
            # If path is a repository, export FROM path
            self.repositories.set_child_text(path)
            self.get_widget("destination").set_text("")
        else:
            # Path is not a working copy so the user probably wants to export
            # TO this path
            self.repositories.set_child_text("")
            self.get_widget("destination").set_text(S(path).display())

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()
        path = self._get_path()
        omit_externals = self.get_widget("omit_externals").get_active()
        recursive = self.get_widget("recursive").get_active()

        if not url or not path:
            MessageBox(_("The repository URL and destination path are both required fields."))
            return

        if url.startswith("file://"):
            url = self._parse_path(url)

        # Cannot do:
        # url = os.path.normpath(url)
        # ...in general, since it might be eg. an http URL. Doesn't seem to
        # affect pySvn though.

        path = os.path.normpath(path)
        revision = self.revision_selector.get_revision_object()

        self.hide()
        self.action = SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Export"))
        self.action.append(self.action.set_status, _("Running Export Command..."))
        self.action.append(helper.save_repository_path, url)
        self.action.append(
            self.svn.export,
            url,
            path,
            force=True,
            recurse=recursive,
            revision=revision,
            ignore_externals=omit_externals
        )
        self.action.append(self.action.set_status, _("Completed Export"))
        self.action.append(self.action.finish)
        self.action.schedule()

class GitExport(GitClone):
    def __init__(self, path=None, revision=None):

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = None
        guess = rabbitvcs.vcs.guess(path)
        if guess["vcs"] == rabbitvcs.vcs.VCS_GIT:
            self.git = self.vcs.git(path)
            export_to = ""
            export_from = path
        else:
            export_to = path
            export_from = ""

        GitClone.__init__(self, export_to, export_from)

        self.get_widget("Checkout").set_title(_("Export - %s") % path)

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.git,
            revision=revision,
            url_combobox=self.repositories,
            expand=True
        )

        self.get_widget("revision_selector_box").show()

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()
        path = self._get_path()

        if not url or not path:
            MessageBox(_("The repository URL and destination path are both required fields."))
            return

        if url.startswith("file://"):
            url = self._parse_path(url)

        # Cannot do:
        # url = os.path.normpath(url)
        # ...in general, since it might be eg. an http URL. Doesn't seem to
        # affect pySvn though.

        path = os.path.normpath(path)
        revision = self.revision_selector.get_revision_object()

        self.hide()
        self.action = GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Export"))
        self.action.append(self.action.set_status, _("Running Export Command..."))
        self.action.append(helper.save_repository_path, url)
        self.action.append(
            self.git.export,
            url,
            path,
            revision=revision
        )
        self.action.append(self.action.set_status, _("Completed Export"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_repositories_changed(self, widget, data=None):
        # Do not use quoting for this bit
        url = self.repositories.get_active_text()
        tmp = url.replace("//", "/").split("/")[1:]
        append = ""
        prev = ""
        while len(tmp):
            prev = append
            append = tmp.pop()
            if append not in ("trunk", "branches", "tags"):
                break

            if append in ("http:", "https:", "file:", "svn:", "svn+ssh:"):
                append = ""
                break

        self.get_widget("destination").set_text(
            S(os.path.join(self.destination, append)).display()
        )

        self.check_form()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNExport,
    rabbitvcs.vcs.VCS_GIT: GitExport
}

def export_factory(vcs, path, revision=None):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]

    if vcs == rabbitvcs.vcs.VCS_DUMMY:
        vcs = rabbitvcs.vcs.VCS_SVN

    return classes_map[vcs](path, revision)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, paths) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs export --vcs=[git|svn] [url_or_path]"
    )

    window = export_factory(options.vcs, paths[0], revision=options.revision)
    window.register_gtk_quit()
    Gtk.main()
