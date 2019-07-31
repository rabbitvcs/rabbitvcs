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
import six.moves._thread
from datetime import datetime

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.vcs

from rabbitvcs import gettext
import six
_ = gettext.gettext

DATETIME_FORMAT = helper.DT_FORMAT_THISWEEK

helper.gobject_threads_init()

class Push(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "push", "Push")

        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()

    #
    # Event handlers
    #

    def on_ok_clicked(self, widget, data=None):
        pass


class GitPush(Push):
    def __init__(self, path):
        Push.__init__(self, path)

        self.git = self.vcs.git(path)

        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.get_widget("repository_container"),
            self.git,
            self.on_branch_changed
        )

        self.log_table = rabbitvcs.ui.widget.Table(
            self.get_widget("log"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Date"), _("Message")],
            flags={
                "sortable": True,
                "sort_on": 0
            }
        )

        # Set default for checkboxes.
        self.get_widget("tags").set_active(True)
        self.get_widget("force_with_lease").set_active(False)

        self.initialize_logs()

    def on_ok_clicked(self, widget, data=None):
        self.hide()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
        tags = self.get_widget("tags").get_active()
        force_with_lease = self.get_widget("force_with_lease").get_active()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Push"))
        self.action.append(self.action.set_status, _("Running Push Command..."))
        self.action.append(self.git.push, repository, branch, tags, force_with_lease)
        self.action.append(self.action.set_status, _("Completed Push"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def initialize_logs(self):
        """
        Initializes the git logs
        """

        try:
            six.moves._thread.start_new_thread(self.load_logs, ())
        except Exception as e:
            log.exception(e)

    def load_logs_exit(self):
        self.get_widget("status").set_text("")
        self.update_widgets()

    def load_logs(self):
        helper.run_in_main_thread(self.get_widget("status").set_text, _("Loading..."))

        self.load_push_log()
        helper.run_in_main_thread(self.load_logs_exit)

    def load_push_log(self):
        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        refspec = "refs/remotes/%s/%s" % (repository, branch)
        self.push_log = self.git.log(revision=self.git.revision(refspec), showtype="push")

    def on_branch_changed(self, repository, branch):
        self.load_push_log()
        self.update_widgets()

    def update_widgets(self):
        self.log_table.clear()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        if not repository or not branch:
            self.get_widget("ok").set_sensitive(False)
            return

        has_commits = False
        for item in self.push_log:
            self.log_table.append([
                helper.format_datetime(item.date),
                helper.format_long_text(item.message.rstrip("\n"))
            ])
            has_commits = True

        self.get_widget("ok").set_sensitive(True)
        if not has_commits:
            self.get_widget("status").set_text(_("No commits found"))

classes_map = {
    rabbitvcs.vcs.VCS_GIT: GitPush
}

def push_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(
        usage="Usage: rabbitvcs push [path]"
    )

    window = push_factory(paths[0])
    window.register_gtk_quit()
    Gtk.main()
