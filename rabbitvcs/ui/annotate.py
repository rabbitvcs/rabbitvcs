from __future__ import absolute_import
from rabbitvcs.util.log import Log
from rabbitvcs import gettext
import rabbitvcs.vcs
from rabbitvcs.util.settings import SettingsManager
from rabbitvcs.util.highlighter import highlight
from rabbitvcs.util.decorators import gtk_unsafe
from rabbitvcs.util.strings import S
from rabbitvcs.util.contextmenuitems import *
from rabbitvcs.util.contextmenu import GtkContextMenu
from rabbitvcs.ui.dialog import MessageBox, Loading
from rabbitvcs.ui.widget import Clickable, Table, TYPE_MARKUP, TYPE_HIDDEN
from rabbitvcs.ui.action import SVNAction, GitAction
from rabbitvcs.ui.log import log_dialog_factory
from rabbitvcs.ui import InterfaceView
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
from datetime import datetime
import time
from random import random, uniform

from rabbitvcs.util import helper

from gi import require_version

require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
sa.restore()


_ = gettext.gettext

logger = Log("rabbitvcs.ui.annotate")


LUMINANCE = 0.90


class Annotate(InterfaceView):
    """
    Provides a UI interface to annotate items in the repository or
    working copy.

    Pass a single path to the class when initializing

    """

    def __init__(self, path, revision=None):
        if os.path.isdir(path):
            MessageBox(_("Cannot annotate a directory"))
            raise SystemExit()
            return

        InterfaceView.__init__(self, "annotate", "Annotate")

        self.get_widget("Annotate").set_title(_("Annotate - %s") % path)
        self.vcs = rabbitvcs.vcs.VCS()

        sm = SettingsManager()
        self.datetime_format = sm.get("general", "datetime_format")
        self.colorize = sm.get("general", "enable_colorize")

        self.log_by_order = []
        self.log_by_revision = {}
        self.author_background = {}
        self.history = [revision or "HEAD"]
        self.history_index = 0
        self.loading_dialog = None

        self.table = self.build_table()
        self.revision = self.get_widget("revision")
        self.history_first = Clickable(self.get_widget("history_first"))
        self.history_prev = Clickable(self.get_widget("history_prev"))
        self.history_next = Clickable(self.get_widget("history_next"))
        self.history_last = Clickable(self.get_widget("history_last"))
        self.history_first.connect("single-click", self.on_history_first)
        self.history_prev.connect("single-click", self.on_history_prev)
        self.history_prev.connect("long-click", self.history_popup_menu)
        self.history_next.connect("single-click", self.on_history_next)
        self.history_next.connect("long-click", self.history_popup_menu)
        self.history_last.connect("single-click", self.on_history_last)
        self.set_history_sensitive()

    def build_table(self):
        treeview = self.get_widget("table")
        table = Table(
            treeview,
            [
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                TYPE_MARKUP,
                TYPE_HIDDEN,
                TYPE_HIDDEN,
            ],
            [
                _("Revision"),
                _("Author"),
                _("Date"),
                _("Line"),
                _("Text"),
                "revision color",
                "author color",
            ],
            callbacks={"mouse-event": self.on_annotate_table_mouse_event},
        )
        table.allow_multiple()
        table.get_column(3).get_cells()[0].set_property("xalign", 1.0)
        treeview.connect("query-tooltip", self.on_query_tooltip, (0, (0, 1, 2)))
        treeview.set_has_tooltip(True)

        if self.colorize:
            for i, n in [(1, 6), (4, 5)]:
                column = table.get_column(i)
                cell = column.get_cells()[0]
                column.add_attribute(cell, "background", n)

        return table

    def on_close_clicked(self, widget):
        self.close()

    def on_save_clicked(self, widget):
        self.save()

    def on_revision_focus_out_event(self, widget, event, data=None):
        self.show_revision(widget.get_text())

    def on_revision_key_press_event(self, widget, event, data=None):
        if event.state == 0 and Gdk.keyval_name(event.keyval) == "Return":
            self.show_revision(widget.get_text())
        return False

    def on_show_log_clicked(self, widget, data=None):
        log_dialog_factory(self.path, ok_callback=self.on_log_closed)

    def on_log_closed(self, data):
        if data:
            self.show_revision(data)

    def on_annotate_table_mouse_event(self, treeview, event, data=None):
        if event.button == 1:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                revisions = self.table.get_selected_row_items(0)
                if len(revisions) == 1:
                    if revisions[0]:
                        self.show_revision(revisions[0])
        elif event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.show_annotate_table_popup_menu(treeview, event, data)

    def on_query_tooltip(self, treeview, x, y, kbdmode, tooltip, data=None):
        if kbdmode:
            return False

        try:
            position, enabled_columns = data
            enabled_columns[0]
        except (TypeError, ValueError, IndexError):
            return False

        bx, by = treeview.convert_widget_to_bin_window_coords(x, y)
        t = treeview.get_path_at_pos(bx, by)
        if t is None:
            return False

        path, column, cellx, celly = t
        columns = treeview.get_columns()
        try:
            pos = columns.index(column)
        except ValueError:
            return False
        if not pos in enabled_columns:
            return False

        revision = treeview.get_model()[path][position]
        if not revision:
            return False

        revision = str(revision)
        if not revision in self.log_by_revision:
            return False

        log = self.log_by_revision[revision]
        message = helper.format_long_text(log.message, line1only=True)
        if not message:
            return False

        tooltip.set_text(S(message).display())
        treeview.set_tooltip_cell(tooltip, path)
        return True

    def on_history_first(self, clickable, widget, event, *args):
        forceload = self.history[self.history_index] != self.history[0]
        self.history_index = 0
        self.show_revision(forceload=forceload)

    def on_history_prev(self, clickable, widget, event, *args):
        forceload = (
            self.history[self.history_index] != self.history[self.history_index - 1]
        )
        self.history_index -= 1
        self.show_revision(forceload=forceload)

    def on_history_next(self, clickable, widget, event, *args):
        forceload = (
            self.history[self.history_index] != self.history[self.history_index + 1]
        )
        self.history_index += 1
        self.show_revision(forceload=forceload)

    def on_history_last(self, clickable, widget, event, *args):
        forceload = self.history[self.history_index] != self.history[-1]
        self.history_index = len(self.history) - 1
        self.show_revision(forceload=forceload)

    def history_popup_menu(self, clickable, widget, event, *args):
        menu = Gtk.Menu()
        width = 0
        for i, revision in list(enumerate(self.history))[: self.history_index + 6][
            -11:
        ]:
            message = ""
            revision = self.short_revision(revision)
            if revision in self.log_by_revision:
                log = self.log_by_revision[revision]
                message = helper.format_long_text(log.message, cols=32, line1only=True)
            revision = helper.html_escape(revision)
            message = helper.html_escape(message)
            if i == self.history_index:
                revision = "<b>" + revision + "</b>"
                message = "<b>" + message + "</b>"
            row = Gtk.Grid()
            cell1 = Gtk.Label()
            cell1.set_properties(xalign=0, yalign=0.5)
            cell1.set_markup(revision)
            row.attach(cell1, 0, 0, 1, 1)
            cell2 = Gtk.Label()
            cell2.set_properties(xalign=0, yalign=0.5)
            cell2.set_markup(message)
            row.attach(cell2, 1, 0, 1, 1)
            menuitem = Gtk.MenuItem()
            menuitem.add(row)
            menuitem.connect("activate", self.on_history_menu_activate, i)
            menu.add(menuitem)
        menu.show_all()
        menu.popup_at_pointer(event)
        for menuitem in menu.get_children():
            w = menuitem.get_child().get_child_at(0, 0).get_allocation().width
            if width < w:
                width = w
        width += 4
        for menuitem in menu.get_children():
            menuitem.get_child().get_child_at(0, 0).set_size_request(width, -1)

    def on_history_menu_activate(self, menu, index):
        forceload = self.history[self.history_index] != self.history[index]
        self.history_index = index
        self.show_revision(forceload=forceload)

    def set_history_sensitive(self):
        self.history_first.set_sensitive(self.history_index > 0)
        self.history_prev.set_sensitive(self.history_index > 0)
        last = len(self.history) - 1
        self.history_next.set_sensitive(self.history_index < last)
        self.history_last.set_sensitive(self.history_index < last)

    def show_revision(self, revision=None, forceload=False):
        if revision is None:
            revision = self.history[self.history_index]
        revision = S(S(revision).strip())
        self.revision.set_text(revision.display())
        if revision.lower() != self.history[self.history_index].lower():
            forceload = True
            self.history_index += 1
            self.history = self.history[: self.history_index] + [revision]
        self.set_history_sensitive()
        if forceload:
            self.load(revision)

    def enable_saveas(self):
        self.get_widget("save").set_sensitive(True)

    def disable_saveas(self):
        self.get_widget("save").set_sensitive(False)

    def save(self, path=None):
        if path is None:
            from rabbitvcs.ui.dialog import FileSaveAs

            dialog = FileSaveAs()
            path = dialog.run()

        if path is not None:
            fh = open(path, "w")
            fh.write(self.generate_string_from_result())
            fh.close()

    def launch_loading(self):
        self.loading_dialog = Loading()
        GLib.idle_add(self.loading_dialog.run)

    def kill_loading(self):
        GLib.idle_add(self.loading_dialog.destroy)

    def show_annotate_table_popup_menu(self, treeview, event, data):
        revisions = list(set(self.table.get_selected_row_items(0)))
        AnnotateContextMenu(self, event, self.path, revisions).show()

    def set_log(self):
        self.log_by_order = self.action.get_result(1)
        self.log_by_order.reverse()
        self.log_by_revision = {}
        self.author_background = {}
        for n, log in enumerate(self.log_by_order):
            setattr(log, "n", n)
            c = self.randomHSL()
            c = helper.HSLtoRGB(*c)
            setattr(log, "background", helper.html_color(*c))
            self.log_by_revision[self.short_revision(log.revision)] = log
            author = S(log.author.strip())
            if author:
                c = self.randomHSL()
                c = helper.HSLtoRGB(*c)
                self.author_background[author] = helper.html_color(*c)

    def previous_revision(self, revision):
        revision = self.short_revision(revision)
        n = self.log_by_revision[revision].n
        if n:
            return self.short_revision(self.log_by_order[n - 1].revision)
        return None

    def next_revision(self, revision):
        revision = self.short_revision(revision)
        n = self.log_by_revision[revision].n
        if n < len(self.log_by_order) - 1:
            return self.short_revision(self.log_by_order[n + 1].revision)
        return None

    def compare_revision_order(self, rev1, rev2):
        return self.log_by_revision[rev1].n - self.log_by_revision[rev2].n

    def randomHSL(self):
        return (uniform(0.0, 360.0), uniform(0.5, 1.0), LUMINANCE)

    def get_vcs_name(self):
        vcs = rabbitvcs.vcs.VCS_DUMMY
        if hasattr(self, "svn"):
            vcs = rabbitvcs.vcs.VCS_SVN
        elif hasattr(self, "git"):
            vcs = rabbitvcs.vcs.VCS_GIT

        return vcs


class SVNAnnotate(Annotate):
    def __init__(self, path, revision=None):
        Annotate.__init__(self, path, revision)
        self.svn = self.vcs.svn()
        self.path = path
        self.show_revision(forceload=True)

    #
    # Helper methods
    #

    def load(self, revision):
        revision = revision.lower()
        rev = self.svn.revision("HEAD")
        if revision.isdigit():
            rev = self.svn.revision("number", number=int(revision))

        self.launch_loading()

        self.action = SVNAction(self.svn, notification=False)

        self.action.append(self.svn.annotate, self.path, to_revision=rev)

        if not self.log_by_order:
            self.action.append(self.svn.log, self.path)
            self.action.append(self.set_log)

        self.action.append(self.populate_table)
        self.action.append(self.enable_saveas)
        self.action.schedule()

        self.kill_loading()

    def blame_info(self, item):
        revision = item["revision"].number
        if revision <= 0:
            return ("", "", "")

        revision = str(revision)

        # remove fractional seconds and timezone information from
        # the end of the string provided by pysvn:
        # * timezone should be always "Z" (for UTC), "%Z" is not yet
        #   yet supported by strptime
        # * fractional could be parsed with "%f" since python 2.6
        #   but this precision is not needed anyway
        # * the datetime module does not include strptime until python 2.4
        #   so this workaround is required for now
        datestr = item["date"][0:-8]
        try:
            date = datetime(*time.strptime(datestr, "%Y-%m-%dT%H:%M:%S")[:-2])
            date = helper.format_datetime(date, self.datetime_format)
        except:
            date = ""

        return revision, date, S(item["author"].strip())

    def populate_table(self):
        blamedict = self.action.get_result(0)
        lines = highlight(self.path, [item["line"] for item in blamedict])

        self.table.clear()
        for i, item in enumerate(blamedict):
            revision, date, author = self.blame_info(item)
            author_color = self.author_background.get(author, "#FFFFFF")
            try:
                revision_color = self.log_by_revision[revision].background
            except KeyError:
                revision_color = "#FFFFFF"

            self.table.append(
                [
                    revision,
                    author,
                    date,
                    str(int(item["number"]) + 1),
                    lines[i],
                    revision_color,
                    author_color,
                ]
            )

    def generate_string_from_result(self):
        blamedict = self.action.get_result(0)

        text = ""
        for item in blamedict:
            revision, date, author = self.blame_info(item)

            text += "%s\t%s\t%s\t%s\t%s\n" % (
                str(int(item["number"]) + 1),
                revision,
                author,
                date,
                item["line"],
            )

        return text

    def short_revision(self, revision):
        revision = str(revision).lower()
        return revision if revision != "head" else "HEAD"


class GitAnnotate(Annotate):
    def __init__(self, path, revision=None):
        Annotate.__init__(self, path, revision)
        self.git = self.vcs.git(path)
        self.path = path
        self.show_revision(forceload=True)

    #
    # Helper methods
    #

    def launch_loading(self):
        self.loading_dialog = Loading()
        GLib.idle_add(self.loading_dialog.run)

    def kill_loading(self):
        GLib.idle_add(self.loading_dialog.destroy)

    def load(self, revision):
        self.launch_loading()

        self.action = GitAction(self.git, notification=False)

        self.action.append(self.git.annotate, self.path, self.git.revision(revision))

        if not self.log_by_order:
            self.action.append(self.git.log, self.path)
            self.action.append(self.set_log)

        self.action.append(self.populate_table)
        self.action.append(self.enable_saveas)
        self.action.schedule()
        self.kill_loading()

    def populate_table(self):
        blamedict = self.action.get_result(0)
        lines = highlight(self.path, [item["line"] for item in blamedict])

        self.table.clear()
        for i, item in enumerate(blamedict):
            revision = item["revision"][:7]
            author = S(item["author"].strip())
            author_color = self.author_background.get(author, "#FFFFFF")
            try:
                revision_color = self.log_by_revision[revision].background
            except KeyError:
                revision_color = "#FFFFFF"

            self.table.append(
                [
                    revision,
                    author,
                    helper.format_datetime(item["date"], self.datetime_format),
                    str(item["number"]),
                    lines[i],
                    revision_color,
                    author_color,
                ]
            )

    def generate_string_from_result(self):
        blamedict = self.action.get_result(0)

        text = ""
        for item in blamedict:
            text += "%s\t%s\t%s\t%s\t%s\n" % (
                str(item["number"]),
                item["revision"][:7],
                item["author"],
                helper.format_datetime(item["date"], self.datetime_format),
                item["line"],
            )

        return text

    def short_revision(self, revision):
        revision = str(revision)[:7].lower()
        return revision if revision != "head" else "HEAD"


class MenuShowRevision(MenuItem):
    identifier = "RabbitVCS::Show_Revision"
    label = _("Show this revision")
    tooltip = _("Annotate this file's revision")
    icon = "rabbitvcs-annotate"


class MenuViewRevision(MenuItem):
    identifier = "RabbitVCS::View_Revision"
    label = _("Annotate this revision in another window")
    tooltip = _("Annotate this file's revision in another window")
    icon = "rabbitvcs-annotate"


class MenuShowNextRevision(MenuItem):
    identifier = "RabbitVCS::Show_Next_Revision"
    label = _("Show next revision")
    tooltip = _("Annotate the revision following this one")
    icon = "rabbitvcs-annotate"


class MenuDiffWorkingCopy(MenuItem):
    identifier = "RabbitVCS::Diff_Working_Copy"
    label = _("View diff against working copy")
    tooltip = _("View this revision's diff against working copy")
    icon = "rabbitvcs-diff"


class MenuCompareWorkingCopy(MenuItem):
    identifier = "RabbitVCS::Compare_Working_Copy"
    label = _("Compare against working copy")
    tooltip = _("Compare this revision against working copy")
    icon = "rabbitvcs-compare"


class MenuDiffPreviousRevision(MenuItem):
    identifier = "RabbitVCS::Diff_Previous_Revision"
    label = _("View diff against previous revision")
    tooltip = _("View this revision's diff against previous revision")
    icon = "rabbitvcs-diff"


class MenuComparePreviousRevision(MenuItem):
    identifier = "RabbitVCS::Compare_Previous_Revision"
    label = _("Compare against previous revision")
    tooltip = _("Compare this revision against previous revision")
    icon = "rabbitvcs-compare"


class MenuDiffRevisions(MenuItem):
    identifier = "RabbitVCS::Diff_Revisions"
    label = _("View diff between revisions")
    tooltip = _("View diff between selected revisions")
    icon = "rabbitvcs-diff"


class MenuCompareRevisions(MenuItem):
    identifier = "RabbitVCS::Compare_Revisions"
    label = _("Compare revisions")
    tooltip = _("Compare selected revisions")
    icon = "rabbitvcs-compare"


class AnnotateContextMenuConditions(object):
    def __init__(self, caller, vcs, path, revisions):
        self.caller = caller
        self.vcs = vcs
        self.path = path
        self.revisions = revisions
        self.vcs_name = caller.get_vcs_name()

    def show_revision(self, data=None):
        return len(self.revisions) == 1

    def view_revision(self, data=None):
        return len(self.revisions) == 1

    def show_next_revision(self, data=None):
        return (
            len(self.revisions) == 1
            and not self.caller.next_revision(self.revisions[0]) is None
        )

    def diff_working_copy(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 1
        )

    def compare_working_copy(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 1
        )

    def diff_previous_revision(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path)
            and len(self.revisions) == 1
            and not self.caller.previous_revision(self.revisions[0]) is None
        )

    def compare_previous_revision(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path)
            and len(self.revisions) == 1
            and not self.caller.previous_revision(self.revisions[0]) is None
        )

    def diff_revisions(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 2
        )

    def compare_revisions(self, data=None):
        return (
            self.vcs.is_in_a_or_a_working_copy(self.path) and len(self.revisions) == 2
        )


class AnnotateContextMenuCallbacks(object):
    def __init__(self, caller, vcs, path, revisions):
        self.caller = caller
        self.vcs = vcs
        self.path = path
        self.revisions = revisions
        self.vcs_name = self.caller.get_vcs_name()

    def show_revision(self, widget, data=None):
        self.caller.show_revision(self.revisions[0])

    def view_revision(self, widget, data=None):
        helper.launch_ui_window(
            "annotate",
            [
                self.path,
                "--vcs=%s" % self.caller.get_vcs_name(),
                "-r",
                self.revisions[0],
            ],
        )

    def show_next_revision(self, widget, data=None):
        self.caller.show_revision(self.caller.next_revision(self.revisions[0]))

    def diff_working_copy(self, widget, data=None):
        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (self.path, S(self.revisions[0])),
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
                "%s@%s" % (path_older, S(self.revisions[0])),
                self.path,
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def diff_previous_revision(self, widget, data=None):
        prev = self.caller.previous_revision(self.revisions[0])
        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (self.path, S(prev)),
                "%s@%s" % (self.path, S(self.revisions[0])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def compare_previous_revision(self, widget, data=None):
        prev = self.caller.previous_revision(self.revisions[0])
        path_older = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn().get_repo_url(self.path)

        helper.launch_ui_window(
            "diff",
            [
                "-s",
                "%s@%s" % (path_older, S(prev)),
                "%s@%s" % (self.path, S(self.revisions[0])),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def diff_revisions(self, widget, data=None):
        rev1 = self.revisions[0]
        rev2 = self.revisions[-1]
        if self.caller.compare_revision_order(rev1, rev2) > 0:
            rev1, rev2 = rev2, rev1
        helper.launch_ui_window(
            "diff",
            [
                "%s@%s" % (self.path, S(rev1)),
                "%s@%s" % (self.path, S(rev2)),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )

    def compare_revisions(self, widget, data=None):
        rev1 = self.revisions[0]
        rev2 = self.revisions[-1]
        if self.caller.compare_revision_order(rev1, rev2) > 0:
            rev1, rev2 = rev2, rev1
        path_older = self.path
        if self.vcs_name == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn().get_repo_url(self.path)
        helper.launch_ui_window(
            "diff",
            [
                "-s",
                "%s@%s" % (path_older, S(rev1)),
                "%s@%s" % (self.path, S(rev2)),
                "--vcs=%s" % self.caller.get_vcs_name(),
            ],
        )


class AnnotateContextMenu(object):
    """
    Defines context menu items for a table's rows

    """

    def __init__(self, caller, event, path, revisions=[]):
        """
        @param  caller: The calling object
        @type   caller: object

        @param  path: The loaded path
        @type   path: string

        @param  event: The triggering Gtk.Event
        @type   event: Gtk.Event

        @param  revisions: The selected revisions
        @type   revisions: list of rabbitvcs.vcs.Revision object
        """

        self.caller = caller
        self.event = event
        self.path = path
        self.revisions = revisions
        self.vcs = rabbitvcs.vcs.VCS()

        self.conditions = AnnotateContextMenuConditions(
            self.caller, self.vcs, self.path, self.revisions
        )

        self.callbacks = AnnotateContextMenuCallbacks(
            self.caller, self.vcs, self.path, self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuShowRevision, None),
            (MenuViewRevision, None),
            (MenuShowNextRevision, None),
            (MenuDiffWorkingCopy, None),
            (MenuCompareWorkingCopy, None),
            (MenuDiffPreviousRevision, None),
            (MenuComparePreviousRevision, None),
            (MenuDiffRevisions, None),
            (MenuCompareRevisions, None),
        ]

    def show(self):
        if len(self.revisions) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


classes_map = {rabbitvcs.vcs.VCS_SVN: SVNAnnotate, rabbitvcs.vcs.VCS_GIT: GitAnnotate}


def annotate_factory(vcs, path, revision=None):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]

    return classes_map[vcs](path, revision)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT

    (options, paths) = main(
        [REVISION_OPT, VCS_OPT], usage="Usage: rabbitvcs annotate url [-r REVISION]"
    )

    window = annotate_factory(options.vcs, paths[0], options.revision)
    window.register_gtk_quit()
    Gtk.main()
