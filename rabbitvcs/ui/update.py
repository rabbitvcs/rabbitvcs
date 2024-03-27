from __future__ import absolute_import
from rabbitvcs import gettext
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
from rabbitvcs.ui.action import SVNAction, GitAction
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


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/git-update.xml")
class GitUpdateWidget(Gtk.Grid):
    __gtype_name__ = "GitUpdateWidget"

    repository_container = Gtk.Template.Child()
    merge = Gtk.Template.Child()
    rebase = Gtk.Template.Child()
    apply_changes = Gtk.Template.Child()
    all = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)


class SVNUpdate(GtkTemplateHelper):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.
    There is no glade .

    """

    def __init__(self, paths):
        GtkTemplateHelper.__init__(self, "Update")

        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

    def start(self):
        self.action = SVNAction(
            self.svn, run_in_thread=False
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))
        self.action.append(self.svn.update, self.paths)
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.schedule()


class GitUpdate(GtkTemplateHelper):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.
    There is no glade .

    """

    def __init__(self, paths):
        GtkTemplateHelper.__init__(self, "Update")

        self.widget = GitUpdateWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Update", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.apply_changes.connect("toggled", self.on_apply_changes_toggled)

        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(paths[0])

        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.widget.repository_container, self.git
        )

    def on_apply_changes_toggled(self, widget, data=None):
        self.widget.merge.set_sensitive(
            self.widget.apply_changes.get_active()
        )
        self.widget.rebase.set_sensitive(
            self.widget.apply_changes.get_active()
        )

    def on_ok_clicked(self, widget, data=None):
        self.window.set_visible(False)

        rebase = self.widget.rebase.get_active()

        git_function_params = []

        apply_changes = self.widget.apply_changes.get_active()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
        fetch_all = self.widget.all.get_active()

        self.action = GitAction(
            self.git
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

        self.window.close()


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNUpdate, rabbitvcs.vcs.VCS_GIT: GitUpdate}


def update_factory(paths):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths)

def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs update [path1] [path2] ...")
    
    widget = update_factory(paths)

    if isinstance(widget, SVNUpdate):
        widget.start()
    else:
        app.add_window(widget.window)
        widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
