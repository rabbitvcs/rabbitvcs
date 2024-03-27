from __future__ import absolute_import
import six
from rabbitvcs import gettext
import rabbitvcs.vcs
import rabbitvcs.util.settings
import rabbitvcs.ui.action
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
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

import os.path
import six.moves._thread
from datetime import datetime

from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


_ = gettext.gettext

helper.gobject_threads_init()


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/push.xml")
class PushWidget(Gtk.Grid):
    __gtype_name__ = "PushWidget"

    repository_container = Gtk.Template.Child()
    log = Gtk.Template.Child()
    tags = Gtk.Template.Child()
    force_with_lease = Gtk.Template.Child()
    status = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

    def set_status_text(self, text):
        self.status.set_text(text)
        self.status.set_visible(text != "")


class GitPush(GtkTemplateHelper):
    def __init__(self, path):
        GtkTemplateHelper.__init__(self, "Push")

        self.widget = PushWidget()
        self.window = self.get_window(self.widget)
        self.window.set_default_size(640, 520)
        # add dialog buttons
        self.ok = self.add_dialog_button("Push", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)

        self.path = path

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        sm = rabbitvcs.util.settings.SettingsManager()
        self.datetime_format = sm.get("general", "datetime_format")

        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.widget.repository_container, self.git, self.on_branch_changed
        )

        self.log_table = rabbitvcs.ui.widget.Table(
            self.widget.log,
            [GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Date"), _("Message")],
            flags={"sortable": True, "sort_on": 0},
        )

        # Set default for checkboxes.
        self.widget.tags.set_active(True)
        self.widget.force_with_lease.set_active(False)

        self.initialize_logs()

    def on_ok_clicked(self, widget, data=None):
        self.window.set_visible(False)

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
        tags = self.widget.tags.get_active()
        force_with_lease = self.widget.force_with_lease.get_active()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )
        self.action.append(self.action.set_header, _("Push"))
        self.action.append(self.action.set_status, _("Running Push Command..."))
        self.action.append(self.git.push, repository, branch, tags, force_with_lease)
        self.action.append(self.action.set_status, _("Completed Push"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def initialize_logs(self):
        """
        Initializes the git logs
        """

        try:
            six.moves._thread.start_new_thread(self.load_logs, ())
        except Exception as e:
            log.exception(e)

    def load_logs_exit(self):
        self.widget.set_status_text("")
        self.update_widgets()

    def load_logs(self):
        helper.run_in_main_thread(self.widget.set_status_text, _("Loading..."))

        self.load_push_log()
        helper.run_in_main_thread(self.load_logs_exit)

    def load_push_log(self):
        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        refspec = "refs/remotes/%s/%s" % (repository, branch)
        self.push_log = self.git.log(
            revision=self.git.revision(refspec), showtype="push"
        )

    def on_branch_changed(self, repository, branch):
        self.load_push_log()
        self.update_widgets()

    def update_widgets(self):
        self.log_table.clear()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        if not repository or not branch:
            self.ok.set_sensitive(False)
            return

        has_commits = False
        for item in self.push_log:
            self.log_table.append(
                [
                    helper.format_datetime(item.date, self.datetime_format),
                    helper.format_long_text(item.message.rstrip("\n")),
                ]
            )
            has_commits = True

        self.ok.set_sensitive(True)
        if not has_commits:
            self.widget.set_status_text(_("No commits found"))


classes_map = {rabbitvcs.vcs.VCS_GIT: GitPush}


def push_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)


def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs push [path]")

    widget = push_factory(paths[0])
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
