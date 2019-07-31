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

from rabbitvcs.ui import InterfaceNonView, InterfaceView
from rabbitvcs.ui.action import SVNAction, GitAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog

from rabbitvcs import gettext
_ = gettext.gettext

class SVNUpdate(InterfaceNonView):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.
    There is no glade .

    """

    def __init__(self, paths):
        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

    def start(self):
        self.action = SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set(),
            run_in_thread=False
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))
        self.action.append(self.svn.update, self.paths)
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.schedule()

class GitUpdate(InterfaceView):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.
    There is no glade .

    """

    def __init__(self, paths):
        InterfaceView.__init__(self, "git-update", "Update")

        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(paths[0])

        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.get_widget("repository_container"),
            self.git
        )

    def on_apply_changes_toggled(self, widget, data=None):
        self.get_widget("merge").set_sensitive(self.get_widget("apply_changes").get_active())
        self.get_widget("rebase").set_sensitive(self.get_widget("apply_changes").get_active())

    def on_ok_clicked(self, widget, data=None):
        self.hide()

        rebase = self.get_widget("rebase").get_active()

        git_function_params = []

        apply_changes = self.get_widget("apply_changes").get_active()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
        fetch_all = self.get_widget("all").get_active()

        self.action = GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set(),
            run_in_thread=False
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))

        if apply_changes:
            if rebase:
                git_function_params.append("rebase")

            if fetch_all:
                git_function_params.append("all")
                repository = ""
                branch = ""

            self.action.append(self.git.pull, repository, branch, git_function_params)
        else:
            if fetch_all:
                self.action.append(self.git.fetch_all)
            else:
                self.action.append(self.git.fetch, repository, branch)

        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.schedule()


classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNUpdate,
    rabbitvcs.vcs.VCS_GIT: GitUpdate
}

def update_factory(paths):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs update [path1] [path2] ...")

    window = update_factory(paths)
    window.register_gtk_quit()
    if isinstance(window, SVNUpdate):
        window.start()
    Gtk.main()
