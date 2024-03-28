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

from __future__ import division, absolute_import
from six.moves import range
from rabbitvcs import gettext
import rabbitvcs.vcs
import rabbitvcs.util.settings
from rabbitvcs.util.strings import S
from rabbitvcs.util.decorators import gtk_unsafe
from rabbitvcs.util.contextmenuitems import *
from rabbitvcs.util.contextmenu import GtkContextMenu
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.ui.action import SVNAction, GitAction, vcs_action_factory
from rabbitvcs.ui import InterfaceView
from gi.repository import Gtk, GObject, Gdk
import six
import threading
from locale import strxfrm

import os
import os.path

from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
sa.restore()


_ = gettext.gettext


REVISION_LABEL = _("Revision")
DATE_LABEL = _("Date")
AUTHOR_LABEL = _("Author")


def revision_grapher(history):
    """
    Expects a list of revision items like so:
    [
        item.commit = "..."
        item.parents = ["...", "..."]
    ]

    Output can be put directly into the CellRendererGraph
    """
    items = []
    revisions = []
    last_lines = []
    color = "#d3b9d3"
    for item in history:
        commit = S(item.revision)
        parents = []
        for parent in item.parents:
            parents.append(S(parent))

        if commit not in revisions:
            revisions.append(commit)

        index = revisions.index(commit)
        next_revisions = revisions[:]

        parents_to_add = []
        for parent in parents:
            if parent not in next_revisions:
                parents_to_add.append(parent)

        next_revisions[index : index + 1] = parents_to_add

        lines = []
        for i, revision in enumerate(revisions):
            if revision in next_revisions:
                lines.append((i, next_revisions.index(revision), color))
            elif revision == commit:
                for parent in parents:
                    lines.append((i, next_revisions.index(parent), color))

        node = (index, "#a9f9d2")

        items.append((item, node, last_lines, lines))
        revisions = next_revisions
        last_lines = lines

    return items


class Log(InterfaceView):
    """
    Provides an interface to the Log UI

    """

    selected_rows = []
    selected_row = []
    paths_selected_rows = []
    display_items = []

    limit = 100

    def __init__(self, path):
        """
        @type   path: string
        @param  path: A path for which to get log items

        """

        InterfaceView.__init__(self, "log", "Log")

        self.get_widget("Log").set_title(_("Log - %s") % path)
        self.vcs = rabbitvcs.vcs.VCS()

        sm = rabbitvcs.util.settings.SettingsManager()
        self.datetime_format = sm.get("general", "datetime_format")

        self.filter_text = None
        self.path = path
        self.cache = LogCache()

        self.rev_first = None
        self.rev_start = None
        self.rev_end = None
        self.rev_max = 1
        self.previous_starts = []
        self.initialize_revision_labels()
        self.revision_number_column = 0
        self.head_row = 0
        self.get_widget("limit").set_text(S(self.limit).display())

        self.message = rabbitvcs.ui.widget.TextView(self.get_widget("message"))

        self.stop_on_copy = False
        self.revision_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        style = self.get_widget("revisions_table").get_style_context()
        textcolor = style.get_color(Gtk.StateFlags.NORMAL)
        self.orgTextColor = textcolor.to_string()

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget, data=None):
        self.destroy()

    def on_close_clicked(self, widget, data=None):
        if self.is_loading:
            self.action.set_cancel(True)
            self.action.stop()
            self.set_loading(False)

        self.close()

    def on_key_pressed(self, widget, event, *args):
        InterfaceView.on_key_pressed(self, widget, event)
        if (
            event.state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(event.keyval).lower() == "c"
        ):
            if len(self.revisions_table.get_selected_rows()) > 0:
                self.copy_revision_text()

    def on_stop_on_copy_toggled(self, widget):
        self.stop_on_copy = self.get_widget("stop_on_copy").get_active()
        if not self.is_loading:
            self.refresh()

    def on_refresh_clicked(self, widget):
        self.limit = int(self.get_widget("limit").get_text())
        self.cache.empty()
        self.load()

    def on_search(self, widget):
        tb = self.get_widget("search_buffer")
        self.filter_text = tb.get_text(
            tb.get_start_iter(), tb.get_end_iter(), 0
        ).lower()

        self.refresh()

    #
    # Revisions table callbacks
    #

    # In this UI, we have an ability to filter and display only certain items.
    def get_displayed_row_items(self, col):
        items = []
        for row in self.selected_rows:
            items.append(self.display_items[row][col])

        return items

    def on_revisions_table_row_activated(self, treeview, event, col):
        paths = self.revisions_table.get_displayed_row_items(1)

        helper.launch_diff_tool(*paths)

    def on_revisions_table_cursor_changed(self, treeview):
        if len(self.revisions_table.get_selected_rows()) == 0:
            return
        self.paths_table.clear()
        self.message.set_text("")
        self.update_revision_message()

    def on_revisions_table_mouse_event(self, treeview, event, *args):
        if len(self.revisions_table.get_selected_rows()) == 0:
            self.message.set_text("")
            self.paths_table.clear()
            return

        if event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.show_revisions_table_popup_menu(treeview, event)

        # Let the rest be handled by the on_revisions_table_cursor changed event

    #
    # Paths table callbacks
    #

    def on_paths_table_row_activated(self, treeview, data=None, col=None):
        try:
            revision1 = S(
                self.display_items[self.revisions_table.get_selected_rows()[0]].revision
            )
            revision2 = S(
                self.display_items[
                    self.revisions_table.get_selected_rows()[0] + 1
                ].revision
            )
            path_item = self.paths_table.get_row(
                self.paths_table.get_selected_rows()[0]
            )[1]
            url = self.root_url + path_item
            self.view_diff_for_path(url, S(revision1), S(revision2), sidebyside=True)
        except IndexError:
            pass

    def on_paths_table_mouse_event(self, treeview, event, *args):
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.show_paths_table_popup_menu(treeview, event)

    def show_paths_table_popup_menu(self, treeview, event):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            line = {
                "revision": self.display_items[row].revision,
                "author": self.display_items[row].author,
                "message": self.display_items[row].message,
            }

            if self.display_items[row].parents:
                line["parents"] = self.display_items[row].parents

            try:
                line["next_revision"] = self.display_items[row + 1].revision
            except IndexError as e:
                pass

            try:
                line["previous_revision"] = self.display_items[row - 1].revision
            except IndexError as e:
                pass

            revisions.append(line)

        revisions.reverse()

        paths = []
        for row in self.paths_table.get_selected_rows():
            paths.append(self.paths_table.get_row(row)[1])

        LogBottomContextMenu(self, event, paths, revisions).show()

    #
    # Helper methods
    #

    def load_or_refresh(self):
        if self.cache.has(self.rev_start):
            self.refresh()
        else:
            self.load()

    def get_selected_revision_numbers(self):
        if len(self.revisions_table.get_selected_rows()) == 0:
            return ""

        revisions = []
        for row in self.revisions_table.get_selected_rows():
            revisions.append(
                int(self.revisions_table.get_row(row)[self.revision_number_column])
            )

        revisions.sort()
        return helper.encode_revisions(revisions)

    def get_selected_revision_number(self):
        if len(self.revisions_table.get_selected_rows()):
            return self.revisions_table.get_row(
                self.revisions_table.get_selected_rows()[0]
            )[self.revision_number_column]
        else:
            return ""

    @gtk_unsafe
    def set_start_revision(self, rev):
        self.get_widget("start").set_text(S(rev).display())

    @gtk_unsafe
    def set_end_revision(self, rev):
        self.get_widget("end").set_text(S(rev).display())

    def initialize_revision_labels(self):
        self.set_start_revision(_("N/A"))
        self.set_end_revision(_("N/A"))

    def set_loading(self, loading):
        self.is_loading = loading

    def show_revisions_table_popup_menu(self, treeview, data):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            line = {
                "revision": self.display_items[row].revision,
                "author": self.display_items[row].author,
                "message": self.display_items[row].message,
            }
            try:
                line["next_revision"] = self.display_items[row + 1].revision
            except IndexError as e:
                pass

            try:
                line["previous_revision"] = self.display_items[row - 1].revision
            except IndexError as e:
                pass

            revisions.append(line)

        LogTopContextMenu(self, data, self.path, revisions).show()

    #
    # Other helper methods
    #

    def view_diff_for_path(self, url, revision1, revision2=None, sidebyside=False):
        if revision2 == None:
            revision2 = revision1

        options = [
            "%s@%s" % (url, revision2),
            "%s@%s" % (url, revision1),
            "--vcs=%s" % self.get_vcs_name(),
        ]

        if sidebyside:
            options += ["-s"]

        helper.launch_ui_window("diff", options)

    def get_vcs_name(self):
        vcs = rabbitvcs.vcs.VCS_DUMMY
        if hasattr(self, "svn"):
            vcs = rabbitvcs.vcs.VCS_SVN
        elif hasattr(self, "git"):
            vcs = rabbitvcs.vcs.VCS_GIT

        return vcs


class SVNLog(Log):
    def __init__(self, path, merge_candidate_revisions=None):
        Log.__init__(self, path)

        self.svn = self.vcs.svn()
        self.merge_candidate_revisions = merge_candidate_revisions

        self.revisions_table = rabbitvcs.ui.widget.Table(
            self.get_widget("revisions_table"),
            [
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_HIDDEN,
            ],
            [_("Revision"), _("Author"), _("Date"), _("Message"), _("Color")],
            callbacks={
                "mouse-event": self.on_revisions_table_mouse_event,
                "cursor-changed": self.on_revisions_table_cursor_changed,
            },
        )

        for i in range(4):
            column = self.revisions_table.get_column(i)
            cell = column.get_cells()[0]
            column.add_attribute(cell, "foreground", 4)

        self.paths_table = rabbitvcs.ui.widget.Table(
            self.get_widget("paths_table"),
            [
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
            ],
            [_("Action"), "", _("Path"), _("Copy From Path"), _("Copy From Revision")],
            callbacks={
                "mouse-event": self.on_paths_table_mouse_event,
                "row-activated": self.on_paths_table_row_activated,
            },
            flags={"sortable": True, "sort_on": 2},
        )

        self.initialize_root_url()
        self.load_or_refresh()

    def initialize_root_url(self):
        action = SVNAction(self.svn, notification=False, run_in_thread=False)

        self.root_url = action.run_single(self.svn.get_repo_root_url, self.path)

    #
    # Log-loading callback methods
    #

    def refresh(self):
        """
        Refresh the items in the main log table that shows Revision/Author/etc.

        """

        self.revision_items = []
        self.revisions_table.clear()
        self.message.set_text("")
        self.paths_table.clear()

        if self.rev_start and self.cache.has(self.rev_start):
            self.revision_items = self.cache.get(self.rev_start)
        else:
            # Make sure the int passed is the order the log call was made
            self.revision_items = self.action.get_result(0)

        if not self.revision_items or len(self.revision_items) == 0:
            return

        # Get the starting/ending point from the actual returned revisions
        self.rev_start = int(S(self.revision_items[0].revision))
        self.rev_end = int(S(self.revision_items[-1].revision))

        if not self.rev_first:
            self.rev_first = self.rev_start

        self.cache.set(self.rev_start, self.revision_items)

        # The first time the log items return, the rev_start will be as large
        # as it will ever be.  So set this to our maximum revision.
        if self.rev_start > self.rev_max:
            self.rev_max = self.rev_start

        self.display_items = []

        for item in self.revision_items:
            msg = helper.html_escape(item.message).lower()

            should_add = not self.filter_text
            should_add = should_add or msg.find(self.filter_text) > -1
            should_add = should_add or item.author.lower().find(self.filter_text) > -1
            should_add = (
                should_add or str(item.revision).lower().find(self.filter_text) > -1
            )
            should_add = (
                should_add or str(item.date).lower().find(self.filter_text) > -1
            )

            if should_add:
                self.display_items.append(item)

        self.set_start_revision(self.rev_start)
        self.set_end_revision(self.rev_end)

        self.check_previous_sensitive()
        self.check_next_sensitive()

        for item in self.display_items:
            msg = helper.format_long_text(item.message, cols=80, line1only=True)
            rev = item.revision
            color = self.orgTextColor  # "#000000"
            if (
                self.merge_candidate_revisions != None
                and int(rev.short()) not in self.merge_candidate_revisions
            ):
                color = "#c9c9c9"

            self.populate_table(rev, item.author, item.date, msg, color)

            # Stop on copy after adding the item to the table
            # so the user can look at the item that was copied
            if self.stop_on_copy:
                for path in item.changed_paths:
                    if path.copy_from_path or path.copy_from_revision:
                        self.set_loading(False)
                        return

        self.set_loading(False)

    def populate_table(self, revision, author, date, msg, color):
        self.revisions_table.append(
            [
                S(revision),
                author,
                helper.format_datetime(date, self.datetime_format),
                msg,
                color,
            ]
        )

    def load(self):
        self.set_loading(True)

        self.action = SVNAction(self.svn, notification=False)

        start = self.svn.revision("head")
        if self.rev_start:
            start = self.svn.revision("number", number=self.rev_start)
        if os.environ.get('RABBITVCS_REVISION_START') is not None:
            start = self.svn.revision("number", number=os.environ.get('RABBITVCS_REVISION_START'))

        if os.environ.get('RABBITVCS_REVISION_END') is None:
            self.action.append(
                self.svn.log,
                self.path,
                revision_start=start,
                limit=self.limit,
                discover_changed_paths=True,
            )
        else:
            self.action.append(
                self.svn.log,
                self.path,
                revision_start=start,
                revision_end=self.svn.revision("number", number=os.environ.get('RABBITVCS_REVISION_END')),
                discover_changed_paths=True,
            )
        self.action.append(self.refresh)
        self.action.schedule()

    def edit_revprop(self, prop_name, prop_value, callback=None):

        failure = False
        url = S(self.svn.get_repo_url(self.path))

        self.action = SVNAction(self.svn, notification=False)

        for row in self.revisions_table.get_selected_rows():
            item = self.display_items[row]
            self.action.append(
                self.svn.revpropset, prop_name, prop_value, url, item.revision
            )

            self.action.append(callback, row, prop_value)

        self.action.schedule()

    @gtk_unsafe
    def on_log_message_edited(self, index, val):
        self.display_items[index].message = val
        self.revisions_table.set_row_item(index, 3, val)
        self.message.set_text(S(val).display())

    @gtk_unsafe
    def on_author_edited(self, index, val):
        self.display_items[index].author = val
        self.revisions_table.set_row_item(index, 1, val)

    def copy_revision_text(self):
        text = ""
        for selected_row in self.revisions_table.get_selected_rows():
            item = self.display_items[selected_row]

            text += "%s: %s\n" % (REVISION_LABEL, S(item.revision).display())
            text += "%s: %s\n" % (AUTHOR_LABEL, S(item.author).display())
            text += "%s: %s\n" % (DATE_LABEL, S(item.date).display())
            text += "%s\n\n" % S(item.message).display()
            if item.changed_paths is not None:
                for subitem in item.changed_paths:
                    text += "%s\t%s" % (
                        S(subitem.action).display(),
                        S(subitem.path).display(),
                    )

                    if subitem.copy_from_path or subitem.copy_from_revision:
                        text += " " + _("(Copied from %s r%s)") % (
                            S(subitem.copy_from_path).display(),
                            S(subitem.copy_from_revision).display(),
                        )

                    text += "\n"

            text += "\n\n\n"

        self.revision_clipboard.set_text(text, -1)

    def update_revision_message(self):
        combined_paths = []
        subitems = []

        for selected_row in self.revisions_table.get_selected_rows():
            item = self.display_items[selected_row]
            msg = S(item.message).display()

            if len(self.revisions_table.get_selected_rows()) == 1:
                self.message.set_text(msg)
            else:
                indented_message = msg.replace("\n", "\n\t")
                self.message.append_text(
                    "%s %s:\n\t%s\n"
                    % (REVISION_LABEL, S(item.revision).display(), indented_message)
                )
            if item.changed_paths is not None:
                for subitem in item.changed_paths:
                    if subitem.path not in combined_paths:
                        combined_paths.append(subitem.path)

                        subitems.append(
                            [
                                subitem.action,
                                subitem.path,
                                subitem.copy_from_path,
                                S(subitem.copy_from_revision),
                            ]
                        )

        subitems.sort(key=lambda x: strxfrm(x[1]))
        for subitem in subitems:
            self.paths_table.append(
                [subitem[0], S(subitem[1]), subitem[1], subitem[2], S(subitem[3])]
            )

    def on_previous_clicked(self, widget):
        self.rev_start = self.previous_starts.pop()
        self.load_or_refresh()

    def on_next_clicked(self, widget):
        self.previous_starts.append(self.rev_start)
        self.rev_start = int(self.rev_end) - 1

        if self.rev_start < 1:
            self.rev_start = 1

        self.load_or_refresh()

    def check_previous_sensitive(self):
        sensitive = self.rev_start < self.rev_max
        self.get_widget("previous").set_sensitive(sensitive)

    def check_next_sensitive(self):
        sensitive = True
        if self.rev_end == 1:
            sensitive = False
        if len(self.revision_items) < self.limit:
            sensitive = False

        self.get_widget("next").set_sensitive(sensitive)


class GitLog(Log):
    def __init__(self, path):
        Log.__init__(self, path)

        self.git = self.vcs.git(path)
        self.limit = 500

        self.get_widget("stop_on_copy").hide()

        self.revision_number_column = 1

        self.revisions_table = rabbitvcs.ui.widget.Table(
            self.get_widget("revisions_table"),
            [
                rabbitvcs.ui.widget.TYPE_GRAPH,
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_MARKUP,
                rabbitvcs.ui.widget.TYPE_MARKUP,
                rabbitvcs.ui.widget.TYPE_MARKUP,
            ],
            [_("Graph"), _("Revision"), _("Author"), _("Date"), _("Message")],
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.git_revision_filter,
                    "user_data": {"column": 1},
                }
            ],
            callbacks={
                "mouse-event": self.on_revisions_table_mouse_event,
                "cursor-changed": self.on_revisions_table_cursor_changed,
            },
        )

        self.paths_table = rabbitvcs.ui.widget.Table(
            self.get_widget("paths_table"),
            [
                GObject.TYPE_STRING,
                rabbitvcs.ui.widget.TYPE_HIDDEN_OBJECT,
                GObject.TYPE_STRING,
            ],
            [_("Action"), "", _("Path")],
            callbacks={
                "mouse-event": self.on_paths_table_mouse_event,
                "row-activated": self.on_paths_table_row_activated,
            },
            flags={"sortable": False},
        )
        self.start_point = 0
        self.initialize_root_url()
        self.load_or_refresh()

    #
    # Log-loading callback methods
    #

    def refresh(self):
        """
        Refresh the items in the main log table that shows Revision/Author/etc.

        """

        self.revisions_table.clear()
        helper.run_in_main_thread(self.message.set_text, "")
        self.paths_table.clear()

        # Make sure the int passed is the order the log call was made
        self.revision_items = self.action.get_result(0)

        if not self.revision_items or len(self.revision_items) == 0:
            return

        # Load tags.
        self.tagItems = []
        for tag in self.tagAction.get_result(0) or []:
            name = tag.name

            # Determine the type of tag, so we know which id to use.
            if "Tag" in str([tag.obj]):
                # Tag object, use the dereferenced id.
                id = tag.obj.object[1]
            else:
                # Commit object, use the sha id.
                id = tag.sha

            # Add tags to list so we can match on id and display in the message.
            self.tagItems.append({"id": id, "name": name})

        # Load branches.
        self.branchItems = []
        for branch in self.branchAction.get_result(0):
            if branch.name.startswith("remotes/"):
                branch.name = branch.name[len("remotes/") :]
            self.branchItems.append({"id": branch.revision, "name": branch.name})

        self.set_start_revision(self.revision_items[0].revision.short())
        self.set_end_revision(self.revision_items[-1].revision.short())

        self.display_items = []

        for item in self.revision_items:
            msg = item.message.lower()

            should_add = not self.filter_text
            should_add = should_add or msg.find(self.filter_text) > -1
            should_add = should_add or item.author.lower().find(self.filter_text) > -1
            should_add = (
                should_add or S(item.revision).lower().find(self.filter_text) > -1
            )
            should_add = (
                should_add or str(item.date).lower().find(self.filter_text) > -1
            )

            if should_add:
                self.display_items.append(item)

        grapher = revision_grapher(self.display_items)
        max_columns = 1
        for (item, node, in_lines, out_lines) in grapher:
            if max_columns < len(out_lines):
                max_columns = len(out_lines)

        # Set the graph column width
        if not self.filter_text:
            graph_width = 21 * max_columns
            if graph_width < 55:
                graph_width = 55

            graph_column = self.revisions_table.get_column(0)
            graph_column.set_fixed_width(graph_width)

        index = 0
        for (item, node, in_lines, out_lines) in grapher:
            revision = S(item.revision)
            msg = helper.html_escape(
                helper.format_long_text(item.message, cols=80, line1only=True)
            )
            author = item.author
            date = helper.format_datetime(item.date, self.datetime_format)

            if item.head:
                self.head_row = index
                msg = "<b>%s</b>" % msg
                author = "<b>%s</b>" % author
                date = "<b>%s</b>" % date

            graph_render = {}
            if not self.filter_text:
                graph_render = {
                    "node": node,
                    "in_lines": in_lines,
                    "out_lines": out_lines,
                }

            # Check if a branch is available for this revision, and if so, insert it in the message description.
            for branch in self.branchItems:
                if branch["id"] == revision:
                    msg = "<b>[" + branch["name"] + "]</b> " + msg

            # Check if a tag is available for this revision, and if so, insert it in the message description.
            for tag in self.tagItems:
                if tag["id"] == revision:
                    msg = "<i>[" + tag["name"] + "]</i> " + msg

            self.revisions_table.append([graph_render, revision, author, date, msg])

            index += 1

        self.check_previous_sensitive()
        self.check_next_sensitive()
        self.set_loading(False)

    def load(self):
        self.set_loading(True)

        # Load branches.
        self.branchAction = GitAction(self.git, notification=False, run_in_thread=True)

        self.branchAction.append(self.git.branch_list)
        self.branchAction.schedule()

        # Load tags.
        self.tagAction = GitAction(self.git, notification=False, run_in_thread=True)

        self.tagAction.append(self.git.tag_list)
        self.tagAction.schedule()

        # Load log.
        self.action = GitAction(self.git, notification=False, run_in_thread=True)

        self.action.append(
            self.git.log, path=self.path, skip=self.start_point, limit=self.limit + 1
        )
        self.action.append(self.refresh)
        self.action.schedule()

    def copy_revision_text(self):
        text = ""
        for selected_row in self.revisions_table.get_selected_rows():
            item = self.display_items[selected_row]

            text += "%s: %s\n" % (REVISION_LABEL, S(item.revision.short()).display())
            text += "%s: %s\n" % (AUTHOR_LABEL, S(item.author).display())
            text += "%s: %s\n" % (DATE_LABEL, S(item.date).display())
            text += "%s\n\n" % S(item.message).display()

        self.revision_clipboard.set_text(text, -1)

    def update_revision_message(self):
        combined_paths = []
        subitems = []

        for selected_row in self.revisions_table.get_selected_rows():
            item = self.display_items[selected_row]
            msg = S(item.message).display()

            if len(self.revisions_table.get_selected_rows()) == 1:
                self.message.set_text(msg)
            else:
                indented_message = msg.replace("\n", "\n\t")
                self.message.append_text(
                    "%s %s:\n\t%s\n" % (REVISION_LABEL, item.revision.short(), msg)
                )

            for subitem in item.changed_paths:

                if subitem.path not in combined_paths:
                    combined_paths.append(subitem.path)

                    subitems.append([subitem.action, subitem.path])

        #        subitems.sort(key = lambda x: strxfrm(x[1]))
        for subitem in subitems:
            self.paths_table.append([subitem[0], S(subitem[1]), subitem[1]])

    def on_previous_clicked(self, widget):
        self.start_point -= self.limit
        if self.start_point < 0:
            self.start_point = 0
        self.load_or_refresh()

    def on_next_clicked(self, widget):
        self.start_point += self.limit
        self.load()

    def check_previous_sensitive(self):
        sensitive = self.start_point > 0
        self.get_widget("previous").set_sensitive(sensitive)

    def check_next_sensitive(self):
        sensitive = True
        if len(self.revision_items) < self.limit:
            sensitive = False

        self.get_widget("next").set_sensitive(sensitive)

    def initialize_root_url(self):
        self.root_url = self.git.get_repository() + "/"


class SVNLogDialog(SVNLog):
    def __init__(
        self, path, ok_callback=None, multiple=False, merge_candidate_revisions=None
    ):
        """
        Override the normal SVNLog class so that we can hide the window as we need.
        Also, provide a callback for when the OK button is clicked so that we
        can get some desired data.
        """
        SVNLog.__init__(self, path, merge_candidate_revisions)
        self.ok_callback = ok_callback
        self.multiple = multiple
        self.change_button("close", _("_Select"), "rabbitvcs-ok")

    def on_destroy(self, widget):
        pass

    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.ok_callback is not None:
            if self.multiple == True:
                self.ok_callback(self.get_selected_revision_numbers())
            else:
                self.ok_callback(self.get_selected_revision_number())


class GitLogDialog(GitLog):
    def __init__(self, path, ok_callback=None, multiple=False):
        """
        Override the normal GitLog class so that we can hide the window as we need.
        Also, provide a callback for when the OK button is clicked so that we
        can get some desired data.
        """
        GitLog.__init__(self, path)
        self.ok_callback = ok_callback
        self.multiple = multiple

    def on_destroy(self, widget):
        pass

    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.ok_callback is not None:
            if self.multiple == True:
                self.ok_callback(self.get_selected_revision_numbers())
            else:
                self.ok_callback(self.get_selected_revision_number())


class LogCache(object):
    def __init__(self, cache={}):
        self.cache = cache

    def set(self, key, val):
        self.cache[key] = val

    def get(self, key):
        return self.cache[key]

    def has(self, key):
        return key in self.cache

    def empty(self):
        self.cache = {}


class MenuViewDiffWorkingCopy(MenuItem):
    identifier = "RabbitVCS::View_Diff_Working_Copy"
    label = _("View diff against working copy")
    icon = "rabbitvcs-diff"


class MenuViewDiffPreviousRevision(MenuItem):
    identifier = "RabbitVCS::View_Diff_Previous_Revision"
    label = _("View diff against previous revision")
    icon = "rabbitvcs-diff"


class MenuViewDiffRevisions(MenuItem):
    identifier = "RabbitVCS::View_Diff_Revisions"
    label = _("View diff between revisions")
    icon = "rabbitvcs-diff"


class MenuCompareWorkingCopy(MenuItem):
    identifier = "RabbitVCS::Compare_Working_Copy"
    label = _("Compare with working copy")
    icon = "rabbitvcs-compare"


class MenuComparePreviousRevision(MenuItem):
    identifier = "RabbitVCS::Compare_Previous_Revision"
    label = _("Compare with previous revision")
    icon = "rabbitvcs-compare"


class MenuCompareRevisions(MenuItem):
    identifier = "RabbitVCS::Compare_Revisions"
    label = _("Compare revisions")
    icon = "rabbitvcs-compare"


class MenuShowChangesPreviousRevision(MenuItem):
    # This is for the revs list
    identifier = "RabbitVCS::Show_Changes_Previous_Revision"
    label = _("Show changes against previous revision")
    icon = "rabbitvcs-changes"


class MenuShowChangesRevisions(MenuItem):
    # This is for the revs list
    identifier = "RabbitVCS::Show_Changes_Revisions"
    label = _("Show changes between revisions")
    icon = "rabbitvcs-changes"


class MenuUpdateToThisRevision(MenuItem):
    identifier = "RabbitVCS::Update_To_This_Revision"
    label = _("Update to this revision")
    tooltip = _("Update the selected path to this revision")
    icon = "rabbitvcs-update"


class MenuRevertChangesFromThisRevision(MenuItem):
    identifier = "RabbitVCS::Revert_Changes_From_This_Revision"
    label = _("Revert changes from this revision")
    tooltip = _("Update the selected path by reverse merging the changes")
    icon = "rabbitvcs-revert"


class MenuCopyClipboard(MenuItem):
    identifier = "RabbitVCS::Copy_Clipboard"
    label = _("Copy to clipboard")
    tooltip = _("Copy to clipboard the full data of these revisions")
    icon = "rabbitvcs-asynchronous"


class MenuEditAuthor(MenuItem):
    identifier = "RabbitVCS::Edit_Author"
    label = _("Edit author...")
    icon = "rabbitvcs-monkey"


class MenuEditLogMessage(MenuItem):
    identifier = "RabbitVCS::Edit_Log_Message"
    label = _("Edit log message...")
    icon = "rabbitvcs-editconflicts"


class MenuEditRevisionProperties(MenuItem):
    identifier = "RabbitVCS::Edit_Revision_Properties"
    label = _("Edit revision properties...")
    icon = "rabbitvcs-editprops"


class MenuSeparatorLast(MenuSeparator):
    identifier = "RabbitVCS::Separator_Last"


class LogTopContextMenuConditions(object):
    def __init__(self, caller, vcs, path, revisions):
        self.caller = caller
        self.vcs = vcs
        self.path = path
        self.revisions = revisions

        self.vcs_name = caller.get_vcs_name()

    def view_diff_working_copy(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 1
        )

    def copy_clipboard(self, data=None):
        return len(self.revisions) > 0

    def view_diff_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def view_diff_revisions(self, data=None):
        return len(self.revisions) > 1

    def compare_working_copy(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 1
        )

    def compare_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def compare_revisions(self, data=None):
        return len(self.revisions) > 1

    def show_changes_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def show_changes_revisions(self, data=None):
        return len(self.revisions) > 1

    def update_to_this_revision(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN and len(self.revisions) == 1

    # TODO Evaluate multiple revisions later
    # TODO Git?
    def revert_changes_from_this_revision(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN and len(self.revisions) == 1

    def checkout(self, data=None):
        return len(self.revisions) == 1

    def branches(self, data=None):
        return len(self.revisions) == 1 and self.vcs_name == rabbitvcs.vcs.VCS_GIT

    def tags(self, data=None):
        return len(self.revisions) == 1 and self.vcs_name == rabbitvcs.vcs.VCS_GIT

    def branch_tag(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN and len(self.revisions) == 1

    def export(self, data=None):
        return len(self.revisions) == 1

    def edit_author(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN

    def edit_log_message(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN

    def edit_revision_properties(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN and len(self.revisions) == 1

    def separator(self, data=None):
        return True

    def separator_last(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_SVN

    def merge(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_GIT

    def reset(self, data=None):
        return self.vcs_name == rabbitvcs.vcs.VCS_GIT


class LogTopContextMenuCallbacks(object):
    def __init__(self, caller, vcs, path, revisions):
        self.caller = caller
        self.vcs = vcs
        self.path = path
        self.revisions = revisions

        self.vcs_name = self.caller.get_vcs_name()

    def find_parent(self, revision):
        if ("parents" in revision) and len(revision["parents"]) > 0:
            parent = S(revision["parents"][0])
        elif "next_revision" in revision:
            parent = S(revision["next_revision"])
        else:
            parent = S(int(S(revision["revision"])) - 1)

        return parent

    def view_diff_working_copy(self, widget, data=None):
        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (self.path, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def copy_clipboard(self, widget, data=None):
        self.caller.copy_revision_text()

    def view_diff_previous_revision(self, widget, data=None):
        parent = self.find_parent(self.revisions[0])

        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (self.path, parent),
                "%s@%s" % (self.path, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def view_diff_revisions(self, widget, data=None):
        path_older = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (path_older, self.revisions[1]["revision"].value),
                "%s@%s" % (self.path, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def compare_working_copy(self, widget, data=None):
        path_older = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "diff",
            [
                "-s",
                "%s@%s" % (path_older, S(self.revisions[0]["revision"])),
                "%s" % (self.path),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def compare_previous_revision(self, widget, data=None):
        parent = self.find_parent(self.revisions[0])

        helper.launch_ui_window(
            "diff",
            [
                "-s",
                "%s@%s" % (self.path, parent),
                "%s@%s" % (self.path, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def compare_revisions(self, widget, data=None):
        path_older = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "diff",
            [
                "-s",
                "%s@%s" % (path_older, self.revisions[1]["revision"].value),
                "%s@%s" % (self.path, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def show_changes_previous_revision(self, widget, data=None):
        rev_first = S(self.revisions[0]["revision"])
        parent = self.find_parent(self.revisions[0])

        path = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "changes",
            [
                "%s@%s" % (path, parent),
                "%s@%s" % (path, S(rev_first)),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def show_changes_revisions(self, widget, data=None):
        rev_first = S(self.revisions[0]["revision"])
        rev_last = S(self.revisions[-1]["revision"])

        path = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "changes",
            [
                "%s@%s" % (path, S(rev_first)),
                "%s@%s" % (path, S(rev_last)),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def update_to_this_revision(self, widget, data=None):
        helper.launch_ui_window(
            "updateto",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def revert_changes_from_this_revision(self, widget, data=None):
        helper.launch_ui_window(
            "merge",
            [
                self.path,
                S(self.revisions[0]["revision"])
                + "-"
                + str(int(S(self.revisions[0]["revision"])) - 1),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def checkout(self, widget, data=None):
        url = ""
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            url = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "checkout",
            [
                self.path,
                url,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def branch_tag(self, widget, data=None):
        helper.launch_ui_window(
            "branch",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def branches(self, widget, data=None):
        helper.launch_ui_window(
            "branches",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def tags(self, widget, data=None):
        helper.launch_ui_window(
            "tags",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def export(self, widget, data=None):
        helper.launch_ui_window(
            "export",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def merge(self, widget, data=None):
        extra = []
        if self.vcs_name == rabbitvcs.vcs.VCS_GIT:
            extra.append(S(self.revisions[0]["revision"]))
            try:
                fromrev = S(self.revisions[1]["revision"])
                extra.append(fromrev)
            except IndexError as e:
                pass

        extra += ["--vcs=%s" % self.caller.get_vcs_name()]

        helper.launch_ui_window("merge", [self.path] + extra)

    def reset(self, widget, data=None):
        helper.launch_ui_window(
            "reset",
            [
                self.path,
                "-r",
                S(self.revisions[0]["revision"]),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def edit_author(self, widget, data=None):
        author = ""
        if len(self.revisions) == 1:
            author = self.revisions[0]["author"]
            if author == _("(no author)"):
                author = ""

        from rabbitvcs.ui.dialog import TextChange

        dialog = TextChange(_("Edit author"), author)
        (result, new_author) = dialog.run()

        if result == Gtk.ResponseType.OK:
            self.caller.edit_revprop(
                "svn:author", new_author, self.caller.on_author_edited
            )

    def edit_log_message(self, widget, data=None):
        message = ""
        if len(self.revisions) == 1:
            message = self.revisions[0]["message"]

        from rabbitvcs.ui.dialog import TextChange

        dialog = TextChange(_("Edit log message"), message)
        (result, new_message) = dialog.run()

        if result == Gtk.ResponseType.OK:
            self.caller.edit_revprop(
                "svn:log", new_message, self.caller.on_log_message_edited
            )

    def edit_revision_properties(self, widget, data=None):
        url = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "revprops",
            [
                "%s@%s" % (url, S(self.revisions[0]["revision"])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )


class LogTopContextMenu(object):
    """
    Defines context menu items for a table with files

    """

    def __init__(self, caller, event, path, revisions=[]):
        """
        @param  caller: The calling object
        @type   caller: object

        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  path: The loaded path
        @type   path: string

        @param  revisions: The selected revisions
        @type   revisions: list of rabbitvcs.vcs.Revision object

        """
        self.caller = caller
        self.event = event
        self.path = path
        self.revisions = revisions
        self.vcs = rabbitvcs.vcs.VCS()

        self.conditions = LogTopContextMenuConditions(
            self.caller, self.vcs, self.path, self.revisions
        )

        self.callbacks = LogTopContextMenuCallbacks(
            self.caller, self.vcs, self.path, self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuViewDiffWorkingCopy, None),
            (MenuViewDiffPreviousRevision, None),
            (MenuViewDiffRevisions, None),
            (MenuCompareWorkingCopy, None),
            (MenuComparePreviousRevision, None),
            (MenuCompareRevisions, None),
            (MenuShowChangesPreviousRevision, None),
            (MenuShowChangesRevisions, None),
            (MenuSeparator, None),
            (MenuCopyClipboard, None),
            (MenuSeparator, None),
            (MenuUpdateToThisRevision, None),
            (MenuRevertChangesFromThisRevision, None),
            (MenuCheckout, None),
            (MenuBranches, None),
            (MenuTags, None),
            (MenuBranchTag, None),
            (MenuExport, None),
            (MenuMerge, None),
            (MenuReset, None),
            (MenuSeparatorLast, None),
            (MenuEditAuthor, None),
            (MenuEditLogMessage, None),
            (MenuEditRevisionProperties, None),
        ]

    def show(self):
        if len(self.revisions) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


class LogBottomContextMenuConditions(object):
    def __init__(self, caller, vcs, paths, revisions):
        self.caller = caller
        self.vcs = vcs
        self.paths = paths
        self.revisions = revisions

    def view_diff_working_copy(self, data=None):
        return False

    def view_diff_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def view_diff_revisions(self, data=None):
        return len(self.paths) == 1 and len(self.revisions) > 1

    def compare_working_copy(self, data=None):
        return False

    def compare_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def compare_revisions(self, data=None):
        return len(self.paths) == 1 and len(self.revisions) > 1

    def show_changes_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return "previous_revision" in self.revisions[0] and len(self.revisions) == 1

    def show_changes_revisions(self, data=None):
        return len(self.paths) == 1 and len(self.revisions) > 1

    def _open(self, data=None):
        return True

    def annotate(self, data=None):
        return len(self.paths) == 1

    def separator(self, data=None):
        return True


class LogBottomContextMenuCallbacks(object):
    def __init__(self, caller, vcs, paths, revisions):
        self.caller = caller
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.vcs_name = self.caller.get_vcs_name()

        self.paths = paths
        self.revisions = revisions

    def find_parent(self, revision):
        if ("parents" in revision) and len(revision["parents"]) > 0:
            parent = S(revision["parents"][0])
        elif "next_revision" in revision:
            parent = S(revision["next_revision"])
        else:
            parent = S(int(S(revision["revision"])) - 1)

        return parent

    def view_diff_previous_revision(self, widget, data=None):
        rev = S(self.revisions[0]["revision"])

        parent = self.find_parent(self.revisions[0])

        path_item = S(self.paths[0]).unicode()
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url, rev, parent)

    def view_diff_revisions(self, widget, data=None):
        rev_first = S(self.revisions[0]["revision"])
        rev_last = S(self.revisions[-1]["revision"])
        path_item = S(self.paths[0]).unicode()
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(
            url, latest_revision_number=rev_last, earliest_revision_number=rev_first
        )

    def compare_previous_revision(self, widget, data=None):
        rev = S(self.revisions[0]["revision"])

        parent = self.find_parent(self.revisions[0])

        path_item = S(self.paths[0]).unicode()
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url, rev, parent, sidebyside=True)

    def compare_revisions(self, widget, data=None):
        earliest_rev = S(self.revisions[0]["revision"])
        latest_rev = S(self.revisions[-1]["revision"])
        path_item = S(self.paths[0]).unicode()
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(
            url, latest_rev, sidebyside=True, earliest_revision_number=earliest_rev
        )

    def show_changes_previous_revision(self, widget, data=None):
        rev_first = S(self.revisions[0]["revision"])
        rev_last = S(self.revisions[-1]["revision"])

        parent = self.find_parent(self.revisions[0])

        url = self.caller.root_url + S(self.paths[0]).unicode()

        helper.launch_ui_window(
            "changes",
            [
                six.u("%s@%s") % (url, parent),
                six.u("%s@%s") % (url, rev_last),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def show_changes_revisions(self, widget, data=None):
        rev_first = S(self.revisions[0]["revision"])
        rev_last = S(self.revisions[-1]["revision"])

        url = self.caller.root_url + S(self.paths[0]).unicode()

        helper.launch_ui_window(
            "changes",
            [
                six.u("%s@%s") % (url, rev_first),
                six.u("%s@%s") % (url, rev_last),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def _open(self, widget, data=None):
        for path in self.paths:
            path = self.caller.root_url + S(path).unicode()
            helper.launch_ui_window(
                "open",
                [
                    path,
                    "--vcs=%s" % self.vcs_name,
                    "-r",
                    S(self.revisions[0]["revision"]),
                ],
            )

    def annotate(self, widget, data=None):
        url = self.caller.root_url + S(self.paths[0]).unicode()
        helper.launch_ui_window(
            "annotate",
            [url, "--vcs=%s" % self.vcs_name, "-r", S(self.revisions[0]["revision"])],
        )


class LogBottomContextMenu(object):
    """
    Defines context menu items for a table with files

    """

    def __init__(self, caller, event, paths, revisions):
        """
        @param  caller: The calling object
        @type   caller: object

        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  paths: The selected paths
        @type   paths: list

        @param  revision: The selected revision
        @type   revision: rabbitvcs.vcs.Revision object

        """
        self.caller = caller
        self.event = event
        self.paths = paths
        self.revisions = revisions
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.conditions = LogBottomContextMenuConditions(
            self.caller, self.vcs, self.paths, self.revisions
        )

        self.callbacks = LogBottomContextMenuCallbacks(
            self.caller, self.vcs, self.paths, self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuViewDiffRevisions, None),
            (MenuViewDiffPreviousRevision, None),
            (MenuComparePreviousRevision, None),
            (MenuCompareRevisions, None),
            (MenuShowChangesPreviousRevision, None),
            (MenuShowChangesRevisions, None),
            (MenuSeparator, None),
            (MenuOpen, None),
            (MenuAnnotate, None),
        ]

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNLog, rabbitvcs.vcs.VCS_GIT: GitLog}

dialogs_map = {rabbitvcs.vcs.VCS_SVN: SVNLogDialog, rabbitvcs.vcs.VCS_GIT: GitLogDialog}


def log_factory(path, vcs):
    # vcs option is allowed for URL only
    if os.path.exists(path):
        vcs = None

    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]
        if not vcs in classes_map:
            from rabbitvcs.ui import VCS_OPT_ERROR

            raise SystemExit(VCS_OPT_ERROR)

    return classes_map[vcs](path)


def log_dialog_factory(path, ok_callback=None, multiple=False, vcs=None):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]

    return dialogs_map[vcs](path, ok_callback, multiple)


if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT

    (options, paths) = main(
        [VCS_OPT], usage="Usage: rabbitvcs log [--vcs=svn|git] [url_or_path]"
    )

    window = log_factory(paths[0], vcs=options.vcs)
    window.register_gtk_quit()
    Gtk.main()
