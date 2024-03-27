from __future__ import absolute_import
from rabbitvcs import gettext
import rabbitvcs.vcs.status
from rabbitvcs.util.decorators import gtk_unsafe
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.util
import rabbitvcs.ui.dialog
import rabbitvcs.ui.widget
import rabbitvcs.ui.action
from rabbitvcs.util.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
from rabbitvcs.ui import GtkTemplateHelper
from gi.repository import Gtk, GObject, Gdk, GLib

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
import six.moves._thread
from time import sleep

from rabbitvcs.util import helper

from gi import require_version

require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.commit")

_ = gettext.gettext

helper.gobject_threads_init()

@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/commit.xml")
class CommitWidget(Gtk.Box):
    __gtype_name__ = "CommitWidget"

    files_table = Gtk.Template.Child()
    toggle_show_unversioned = Gtk.Template.Child()
    message = Gtk.Template.Child()
    status = Gtk.Template.Child()
    commit_to_box = Gtk.Template.Child()
    to = Gtk.Template.Child()
    previous_messages = Gtk.Template.Child()
    toggle_show_unversioned = Gtk.Template.Child()
    toggle_show_all = Gtk.Template.Child()
    refresh = Gtk.Template.Child()
    add_message_box = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)



class Commit(GtkTemplateHelper, GtkContextMenuCaller):
    """
    Provides a user interface for the user to commit working copy
    changes to a repository.  Pass it a list of local paths to commit.

    """

    SETTINGS = rabbitvcs.util.settings.SettingsManager()

    TOGGLE_ALL = False
    SHOW_UNVERSIONED = SETTINGS.get("general", "show_unversioned_files")

    # This keeps track of any changes that the user has made to the row
    # selections
    changes = {}

    def __init__(self, paths, base_dir=None, message=None):
        """

        @type  paths:   list of strings
        @param paths:   A list of local paths.

        """
        GtkTemplateHelper.__init__(self, "Commit")

        self.widget = CommitWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Commit", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.previous_messages.connect("clicked", self.on_previous_messages_clicked)
        self.widget.toggle_show_unversioned.connect("toggled", self.on_toggle_show_unversioned_toggled)
        self.widget.toggle_show_all.connect("toggled", self.on_toggle_show_all_toggled)
        self.widget.refresh.connect("clicked", self.on_refresh_clicked)
        # set window properties
        self.window.set_default_size(800, 640)

        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.items = []

        self.files_table = rabbitvcs.ui.widget.Table(
            self.widget.files_table,
            [
                GObject.TYPE_BOOLEAN,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                rabbitvcs.ui.widget.TYPE_PATH,
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_STATUS,
                GObject.TYPE_STRING,
            ],
            [
                rabbitvcs.ui.widget.TOGGLE_BUTTON,
                "",
                _("Path"),
                _("Extension"),
                _("Text Status"),
                _("Property Status"),
            ],
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.path_filter,
                    "user_data": {"base_dir": base_dir, "column": 2},
                }
            ],
            callbacks={
                "row-activated": self.on_files_table_row_activated,
                "mouse-event": self.on_files_table_mouse_event,
                "key-event": self.on_files_table_key_event,
                "row-toggled": self.on_files_table_toggle_event,
            },
            flags={"sortable": True, "sort_on": 2},
        )
        self.files_table.allow_multiple()
        self.widget.toggle_show_unversioned.set_active(self.SHOW_UNVERSIONED)
        if not message:
            message = self.SETTINGS.get_multiline("general", "default_commit_message")
        self.message = rabbitvcs.ui.widget.TextView(self.widget.message, message)

        self.paths = []
        for path in paths:
            if self.vcs.is_in_a_or_a_working_copy(path):
                self.paths.append(S(path))

    #
    # Helper functions
    #

    def load(self):
        """
        - Gets a listing of file items that are valid for the commit window.
        - Determines which items should be "activated" by default
        - Populates the files table with the retrieved items
        - Updates the status area
        """

        self.widget.status.set_text(_("Loading..."))

        self.items = self.vcs.get_items(
            self.paths, self.vcs.statuses_for_commit(self.paths)
        )

        self.populate_files_table()

    # Overrides the GtkContextMenuCaller method
    def on_context_menu_command_finished(self):
        self.initialize_items()

    def should_item_be_activated(self, item):
        """
        Determines if a file should be activated or not
        """

        if (
            S(item.path) in self.paths
            or item.is_versioned()
            and item.simple_content_status() != rabbitvcs.vcs.status.status_missing
        ):
            return True

        return False

    def should_item_be_visible(self, item):
        show_unversioned = self.SHOW_UNVERSIONED

        if not show_unversioned:
            if not item.is_versioned():
                return False

        return True

    def initialize_items(self):
        """
        Initializes the activated cache and loads the file items in a new thread
        """

        GLib.idle_add(self.load)

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    def delete_items(self):
        paths = self.files_table.get_selected_row_items(1)
        if len(paths) > 0:
            proc = helper.launch_ui_window("delete", paths)
            self.rescan_after_process_exit(proc, paths)

    #
    # Event handlers
    #
    def on_refresh_clicked(self, widget):
        self.initialize_items()

    def on_key_pressed(self, controller, keyval, keycode, state):
        if GtkTemplateHelper.on_key_pressed(self, controller, keyval, keycode, state):
            return True

        if (
            state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(keyval) == "Return"
        ):
            self.on_ok_clicked(controller.get_widget())
            return True

    def on_toggle_show_all_toggled(self, widget, data=None):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        self.changes.clear()
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL
            self.changes[row[1]] = self.TOGGLE_ALL

    def on_toggle_show_unversioned_toggled(self, widget):
        self.SHOW_UNVERSIONED = widget.get_active()
        self.populate_files_table()

        # Save this preference for future commits.
        if (
            self.SETTINGS.get("general", "show_unversioned_files")
            != self.SHOW_UNVERSIONED
        ):
            self.SETTINGS.set(
                "general", "show_unversioned_files", self.SHOW_UNVERSIONED
            )
            self.SETTINGS.write()

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        pathrev1 = helper.create_path_revision_string(paths[0], "base")
        pathrev2 = helper.create_path_revision_string(paths[0], "working")
        proc = helper.launch_ui_window("diff", ["-s", pathrev1, pathrev2])
        self.rescan_after_process_exit(proc, paths)

    def on_files_table_key_event(self, controller, keyval, keycode, state, pressed):
        if not pressed and Gdk.keyval_name(keyval) == "Delete":
            self.delete_items()

    def on_files_table_mouse_event(self, gesture, n_press, x, y, pressed):
        if gesture.get_current_button() == 3 and not pressed:
            # self.show_files_table_popup_menu() todo
            pass

    def on_previous_messages_clicked(self, widget):
        dialog = rabbitvcs.ui.dialog.PreviousMessages(self.window)
        dialog.run(self.on_response)

    def on_response(self, message):
        self.message.set_text(S(message).display())

    def populate_files_table(self):
        """
        First clears and then populates the files table based on the items
        retrieved in self.load()

        """

        self.files_table.clear()
        n = 0
        m = 0
        for item in self.items:
            if item.path in self.changes:
                checked = self.changes[item.path]
            else:
                checked = self.should_item_be_activated(item)

            if item.is_versioned():
                n += 1
            else:
                m += 1

            if not self.should_item_be_visible(item):
                continue

            self.files_table.append(
                [
                    checked,
                    S(item.path),
                    item.path,
                    helper.get_file_extension(item.path),
                    item.simple_content_status(),
                    item.simple_metadata_status(),
                ]
            )
        self.widget.status.set_text(
            _("Found %(changed)d changed and %(unversioned)d unversioned item(s)")
            % {"changed": n, "unversioned": m}
        )


class SVNCommit(Commit):
    def __init__(self, paths, base_dir=None, message=None):
        Commit.__init__(self, paths, base_dir, message)

        self.widget.commit_to_box.set_visible(True)

        self.widget.to.set_text(
            S(self.vcs.svn().get_repo_url(self.base_dir)).display()
        )

        self.items = None
        if len(self.paths):
            self.initialize_items()

    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.window.set_visible(False)

        if len(items) == 0:
            self.window.close()
            return

        added = 0
        recurse = False
        for item in items:
            status = self.vcs.status(item, summarize=False).simple_content_status()
            try:
                if status == rabbitvcs.vcs.status.status_unversioned:
                    self.vcs.svn().add(item)
                    added += 1
                elif status == rabbitvcs.vcs.status.status_deleted:
                    recurse = True
                elif status == rabbitvcs.vcs.status.status_missing:
                    self.vcs.svn().update(item)
                    self.vcs.svn().remove(item)
            except Exception as e:
                log.exception(e)

        ticks = added + len(items) * 2

        self.action = rabbitvcs.ui.action.SVNAction(
            self.vcs.svn()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Commit"))
        self.action.append(self.action.set_status, _("Running Commit Command..."))
        self.action.append(helper.save_log_message, self.message.get_text()),
        self.action.append(self.do_commit, items, recurse)
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def do_commit(self, items, recurse):
        # pysvn.Revision
        revision = self.vcs.svn().commit(
            items, self.message.get_text(), recurse=recurse
        )

        self.action.set_status(
            _("Completed Commit") + " at Revision: " + str(revision.number)
        )

    def on_files_table_toggle_event(self, row, col):
        # Adds path: True/False to the dict
        self.changes[row[1]] = row[col]


class GitCommit(Commit):
    def __init__(self, paths, base_dir=None, message=None):
        Commit.__init__(self, paths, base_dir, message)

        self.git = self.vcs.git(paths[0])

        self.widget.commit_to_box.set_visible(True)

        active_branch = self.git.get_active_branch()
        if active_branch:
            self.widget.to.set_text(S(active_branch.name).display())
        else:
            self.widget.to.set_text("No active branch")

        self.items = None
        if len(self.paths):
            self.initialize_items()

    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.window.set_visible(False)

        if len(items) == 0:
            self.window.close()
            return

        staged = 0
        for item in items:
            try:
                status = self.vcs.status(item, summarize=False).simple_content_status()
                if status == rabbitvcs.vcs.status.status_missing:
                    self.git.checkout([item])
                    self.git.remove(item)
                else:
                    self.git.stage(item)
                    staged += 1
            except Exception as e:
                log.exception(e)

        ticks = staged + len(items) * 2

        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )

        # notifier window is registered, we can close now
        self.window.close()

        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Commit"))
        self.action.append(self.action.set_status, _("Running Commit Command..."))
        self.action.append(helper.save_log_message, self.message.get_text())
        self.action.append(self.git.commit, self.message.get_text())
        self.action.append(self.action.set_status, _("Completed Commit"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_files_table_toggle_event(self, row, col):
        # Adds path: True/False to the dict
        self.changes[row[1]] = row[col]


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNCommit, rabbitvcs.vcs.VCS_GIT: GitCommit}


def commit_factory(paths, base_dir=None, message=None):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir, message)

def on_activate(app):
    from rabbitvcs.ui import main, BASEDIR_OPT

    (options, paths) = main(
        [BASEDIR_OPT, (["-m", "--message"], {"help": "add a commit log message"})],
        usage="Usage: rabbitvcs commit [path1] [path2] ...",
    )

    widget = commit_factory(paths, options.base_dir, message=options.message)
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
