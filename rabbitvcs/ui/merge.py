from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.util.strings import S
import rabbitvcs.util.settings
import rabbitvcs.ui.widget
import rabbitvcs.vcs
from rabbitvcs.ui.action import SVNAction
from rabbitvcs.ui.log import SVNLogDialog
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



@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/merge.xml")
class SVNMerge(GtkTemplateHelper, Gtk.Assistant):
    __gtype_name__ = "Merge"

    mergetree_to_revision_number = Gtk.Template.Child()
    mergetree_from_revision_number = Gtk.Template.Child()
    mergetype_range_opt = Gtk.Template.Child()
    mergerange_revisions = Gtk.Template.Child()
    mergetype_tree_opt = Gtk.Template.Child()
    mergetype_reintegrate_opt = Gtk.Template.Child()
    mergeoptions_only_record = Gtk.Template.Child()
    mergeoptions_recursive = Gtk.Template.Child()
    mergeoptions_ignore_ancestry = Gtk.Template.Child()
    mergetree_from_revision_number_opt = Gtk.Template.Child()
    mergetree_to_revision_number_opt = Gtk.Template.Child()
    mergerange_from_urls = Gtk.Template.Child()
    mergerange_working_copy = Gtk.Template.Child()
    mergerange_show_log1 = Gtk.Template.Child()
    merge_reintegrate_working_copy = Gtk.Template.Child()
    merge_reintegrate_repos = Gtk.Template.Child()
    revision_container = Gtk.Template.Child()
    mergetree_from_urls = Gtk.Template.Child()
    mergetree_to_urls = Gtk.Template.Child()
    mergetree_working_copy = Gtk.Template.Child()

    mergetree_from_repos = None
    mergerange_repos = None
    _merge_reintegrate_repos = None
    _merge_reintegrate_revision = None

    def __init__(self, path, revision_range=None):
        GtkTemplateHelper.__init__(self, "Merge")
        Gtk.Assistant.__init__(self)

        self.window = self
        # forward signals
        self.connect("prepare", self.on_prepare)

        keycontroller = Gtk.EventControllerKey()
        keycontroller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(keycontroller)

        controller = Gtk.EventControllerFocus()
        controller.connect("enter", self.on_mergetree_to_revision_number_focused)
        self.mergetree_to_revision_number.add_controller(controller)

        controller = Gtk.EventControllerFocus()
        controller.connect("enter", self.on_mergetree_from_revision_number_focused)
        self.mergetree_from_revision_number.add_controller(controller)

        self.revision_range = revision_range

        self.assistant = self.window

        self.path = path

        self.page = self.assistant.get_nth_page(0)
        self.set_current_page(0)
        self.last_page = None

        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        if not self.svn.has_merge2():
            self.mergetype_range_opt.set_sensitive(False)
            self.mergetype_tree_opt.set_active(True)
            self.mergetype_reintegrate_opt.set_active(False)
            self.mergeoptions_only_record.set_active(False)

        if not self.svn.has_merge_reintegrate():
            self.mergetype_reintegrate_opt.set_sensitive(False)

        self.assistant.set_page_complete(self.page, True)
        self.assistant.set_forward_page_func(self.on_forward_clicked)

        self.repo_paths = helper.get_repository_paths()

        # Keeps track of which stages should be marked as complete
        self.type = None

        self.initialize_root_url()

    def initialize_root_url(self):
        action = SVNAction(self.svn, notification=False, run_in_thread=False)

        self.root_url = action.run_single(self.svn.get_repo_url, self.path)

    #
    # Assistant UI Signal Callbacks
    #

    @Gtk.Template.Callback()
    def on_ok_clicked(self, widget):
        self.merge()

    @Gtk.Template.Callback()
    def on_cancel_clicked(self, widget):
        self.destroy()

    @Gtk.Template.Callback()
    def on_test_clicked(self, widget):
        self.merge(test=True)

    def merge(self, test=False):
        if self.type is None:
            return

        if test:
            startcmd = _("Running Merge Test")
            endcmd = _("Completed Merge Test")
        else:
            startcmd = _("Running Merge Command")
            endcmd = _("Completed Merge")
            self.hide()

        recursive = self.mergeoptions_recursive.get_active()
        ignore_ancestry = self.mergeoptions_ignore_ancestry.get_active()

        record_only = False
        if self.svn.has_merge2():
            record_only = self.mergeoptions_only_record.get_active()

        action = SVNAction(self.svn, register_gtk_quit=(not test))
        action.append(action.set_header, _("Merge"))
        action.append(action.set_status, startcmd)

        args = ()
        kwargs = {}

        if self.type == "range":
            url = self.mergerange_repos.get_active_text()
            head_revision = self.svn.get_head(self.path)
            revisions = self.mergerange_revisions.get_text()
            if revisions == "":
                revisions = "head"
            revisions = revisions.lower().replace("head", str(head_revision))

            ranges = []
            for r in revisions.split(","):
                if r.find("-") != -1:
                    (low, high) = [int(i) for i in r.split("-")]
                    if low < high:
                        low -= 1
                elif r.find(":") != -1:
                    (low, high) = [int(i) for i in r.split(":")]
                    if low < high:
                        low -= 1
                else:
                    high = int(r)
                    low = high - 1

                # Before pysvn v1.6.3, there was a bug that required the ranges
                # tuple to have three elements, even though only two were used
                # Fixed in Pysvn Revision 1114
                if self.svn.interface == "pysvn" and self.svn.is_version_less_than(
                    (1, 6, 3, 0)
                ):
                    ranges.append(
                        (
                            self.svn.revision("number", number=low).primitive(),
                            self.svn.revision("number", number=high).primitive(),
                            None,
                        )
                    )
                else:
                    ranges.append(
                        (
                            self.svn.revision("number", number=low).primitive(),
                            self.svn.revision("number", number=high).primitive(),
                        )
                    )

            action.append(helper.save_repository_path, url)

            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.svn.merge_ranges,
                url,
                ranges,
                self.svn.revision("head"),
                self.path,
            )
            kwargs = {"notice_ancestry": (not ignore_ancestry), "dry_run": test}
            if record_only:
                kwargs["record_only"] = record_only

        elif self.type == "reintegrate":
            url = self._merge_reintegrate_repos.get_active_text()
            revision = self._merge_reintegrate_revision.get_revision_object()

            action.append(helper.save_repository_path, url)

            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (self.svn.merge_reintegrate, url, revision, self.path)
            kwargs = {"dry_run": test}

        elif self.type == "tree":
            from_url = self.mergetree_from_repos.get_active_text()
            from_revision = self.svn.revision("head")
            if self.mergetree_from_revision_number_opt.get_active():
                from_revision = self.svn.revision(
                    "number",
                    number=int(
                        self.mergetree_from_revision_number.get_text()
                    ),
                )
            to_url = self.mergetree_to_repos.get_active_text()
            to_revision = self.svn.revision("head")
            if self.mergetree_to_revision_number_opt.get_active():
                to_revision = self.svn.revision(
                    "number",
                    number=int(
                        self.mergetree_to_revision_number.get_text()
                    ),
                )

            action.append(helper.save_repository_path, from_url)
            action.append(helper.save_repository_path, to_url)

            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.svn.merge_trees,
                from_url,
                from_revision,
                to_url,
                to_revision,
                self.path,
            )
            kwargs = {"recurse": recursive, "dry_run": test}

        if len(args) > 0:
            action.append(*args, **kwargs)

        action.append(action.set_status, endcmd)
        action.append(action.finish)
        action.schedule()

    def on_prepare(self, widget, page):
        self.page = page

        current = self.assistant.get_current_page()
        if current == 1:
            self.on_mergerange_prepare()
        elif current == 2:
            self.on_mergetree_prepare()
        elif current == 3:
            self.on_merge_reintegrate_prepare()
        elif current == 4:
            self.on_mergeoptions_prepare()

        self.last_page = current

    def on_forward_clicked(self, widget):
        current = self.assistant.get_current_page()
        if current == 0:
            if self.mergetype_range_opt.get_active():
                next = 1
                self.type = "range"
                if self.revision_range:
                    self.mergerange_revisions.set_text(
                        S(self.revision_range).display()
                    )
            elif self.mergetype_tree_opt.get_active():
                next = 2
                self.type = "tree"
            elif self.mergetype_reintegrate_opt.get_active():
                next = 3
                self.type = "reintegrate"
        else:
            next = 4

        return next

    #
    # Step 2a: Merge a Range of Revisions
    #

    def on_mergerange_prepare(self):
        if not self.mergerange_repos:
            self.mergerange_repos = rabbitvcs.ui.widget.ComboBox(
                self.mergerange_from_urls, self.repo_paths
            )
            self.mergerange_repos.set_child_text(self.root_url)
            self.mergerange_working_copy.set_text(S(self.path).display())

        self.mergerange_check_ready()

    @Gtk.Template.Callback()
    def on_mergerange_show_log1_clicked(self, widget):
        merge_candidate_revisions = self.svn.find_merge_candidate_revisions(
            self.mergerange_repos.get_active_text(), self.path
        )
        log = SVNLogDialog(
            self.mergerange_repos.get_active_text(),
            ok_callback=self.on_mergerange_log1_closed,
            multiple=True,
            merge_candidate_revisions=merge_candidate_revisions,
        )
        log.window.set_visible(True)

    def on_mergerange_log1_closed(self, data):
        if not data is None:
            self.mergerange_revisions.set_text(S(data).display())

    @Gtk.Template.Callback()
    def on_mergerange_from_urls_changed(self, widget):
        self.mergerange_check_ready()

    @Gtk.Template.Callback()
    def on_mergerange_revisions_changed(self, widget):
        self.mergerange_check_ready()

    def mergerange_check_ready(self):
        ready = True
        if self.mergerange_repos.get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

        allow_log = False
        if self.mergerange_repos.get_active_text():
            allow_log = True
        self.mergerange_show_log1.set_sensitive(allow_log)

    #
    # Step 2b: Reintegrate a Branch
    #

    def on_merge_reintegrate_prepare(self):
        if not self._merge_reintegrate_repos:
            self._merge_reintegrate_repos = rabbitvcs.ui.widget.ComboBox(
                self.merge_reintegrate_repos, self.repo_paths
            )
            self._merge_reintegrate_repos.cb.connect(
                "changed", self.on_merge_reintegrate_from_urls_changed
            )
            self.merge_reintegrate_working_copy.set_text(
                S(self.path).display()
            )

        if not self._merge_reintegrate_revision:
            self._merge_reintegrate_revision = rabbitvcs.ui.widget.RevisionSelector(
                self.revision_container,
                self.svn,
                url_combobox=self._merge_reintegrate_repos,
                expand=True,
            )

    @Gtk.Template.Callback()
    def on_merge_reintegrate_browse_clicked(self, widget):
        from rabbitvcs.ui.browser import SVNBrowserDialog

        SVNBrowserDialog(self.path, callback=self.on_repo_chooser_closed)

    def on_repo_chooser_closed(self, new_url):
        self.merge_reintegrate_repos.set_child_text(new_url)
        self.merge_reintegrate_check_ready()

    @Gtk.Template.Callback()
    def on_merge_reintegrate_from_urls_changed(self, widget):
        self.merge_reintegrate_check_ready()

    def merge_reintegrate_check_ready(self):
        ready = True
        if self.merge_reintegrate_repos.get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

    #
    # Step 2c: Merge two different trees
    #

    def on_mergetree_prepare(self):
        if not self.mergetree_from_repos:
            self.mergetree_from_repos = rabbitvcs.ui.widget.ComboBox(
                self.mergetree_from_urls, self.repo_paths
            )
            self.mergetree_to_repos = rabbitvcs.ui.widget.ComboBox(
                self.mergetree_to_urls, self.repo_paths
            )
            self.mergetree_working_copy.set_text(S(self.path).display())

    @Gtk.Template.Callback()
    def on_mergetree_from_show_log_clicked(self, widget):
        log = SVNLogDialog(
            self.path,
            ok_callback=self.on_mergetree_from_show_log_closed,
            multiple=False,
        )
        log.window.set_visible(True)

    def on_mergetree_from_show_log_closed(self, data):
        self.mergetree_from_revision_number.set_text(S(data).display())
        self.mergetree_from_revision_number_opt.set_active(True)

    @Gtk.Template.Callback()
    def on_mergetree_to_show_log_clicked(self, widget):
        log = SVNLogDialog(
            self.path, ok_callback=self.on_mergetree_to_show_log_closed, multiple=False
        )
        log.window.set_visible(True)

    def on_mergetree_to_show_log_closed(self, data):
        self.mergetree_to_revision_number.set_text(S(data).display())
        self.mergetree_to_revision_number_opt.set_active(True)

    def on_mergetree_working_copy_show_log_clicked(self, widget):
        SVNLogDialog(self.path)

    def on_mergetree_from_revision_number_focused(self, widget):
        self.mergetree_from_revision_number_opt.set_active(True)

    def on_mergetree_to_revision_number_focused(self, widget):
        self.mergetree_to_revision_number_opt.set_active(True)

    @Gtk.Template.Callback()
    def on_mergetree_from_urls_changed(self, widget):
        self.mergetree_check_ready()

    @Gtk.Template.Callback()
    def on_mergetree_to_urls_changed(self, widget):
        self.mergetree_check_ready()

    def mergetree_check_ready(self):
        ready = True
        if self.mergetree_from_repos.get_active_text() == "":
            ready = False
        if self.mergetree_to_repos.get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

    #
    # Step 3: Merge Options
    #

    def on_mergeoptions_prepare(self):
        if self.last_page == 3:
            self.mergeoptions_recursive.hide()
            self.mergeoptions_ignore_ancestry.hide()
            self.mergeoptions_only_record.hide()
        else:
            self.mergeoptions_recursive.show()
            self.mergeoptions_ignore_ancestry.show()
            self.mergeoptions_only_record.show()

        self.assistant.set_page_complete(self.page, True)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/branch-merge.xml")
class BranchMergeWidget(Gtk.Grid):
    __gtype_name__ = "BranchMergeWidget"

    from_branch_container = Gtk.Template.Child()
    to_branch = Gtk.Template.Child()
    from_branch_info = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

class GitMerge(GtkTemplateHelper):
    def __init__(self, path, branch=None):
        GtkTemplateHelper.__init__(self, "Merge")

        self.widget = BranchMergeWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Merge", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)

        self.path = path
        self.branch = branch
        self.vcs = rabbitvcs.vcs.VCS()

        sm = rabbitvcs.util.settings.SettingsManager()
        self.datetime_format = sm.get("general", "datetime_format")
        self.git = self.vcs.git(path)

        self.init_branch_widgets()

        self.from_branches = rabbitvcs.ui.widget.RevisionSelector(
            self.widget.from_branch_container,
            self.git,
            revision=self.branch,
            url=path,
            expand=True,
            revision_changed_callback=self.__revision_changed,
        )

        self.update_branch_info()

        self.active_branch = self.git.get_active_branch()
        if self.active_branch:
            self.widget.to_branch.set_text(
                S(
                    self.active_branch.name
                    + " ("
                    + self.active_branch.revision[0:7]
                    + ")"
                ).display()
            )
        else:
            self.widget.to_branch.set_text(_("No active branch"))

    def init_branch_widgets(self):

        self.info = {"from": {}, "to": {}}

        # FROM BRANCH INFO #
        from_container = rabbitvcs.ui.widget.Box(
            self.widget.from_branch_info, vertical=True
        )

        # Set up the Author line
        author = Gtk.Label(label=_("Author:"))
        author.set_size_request(90, -1)
        author.set_properties(xalign=0, yalign=0)
        self.info["from"]["author"] = Gtk.Label(label="")
        self.info["from"]["author"].set_properties(xalign=0, yalign=0, selectable=True)
        self.info["from"]["author"].set_wrap(True)
        author_container = rabbitvcs.ui.widget.Box()
        author_container.pack_start(author, False, False, 0)
        author_container.pack_start(self.info["from"]["author"], False, False, 0)
        from_container.pack_start(author_container, False, False, 0)

        # Set up the Date line
        date = Gtk.Label(label=_("Date:"))
        date.set_size_request(90, -1)
        date.set_properties(xalign=0, yalign=0)
        self.info["from"]["date"] = Gtk.Label(label="")
        self.info["from"]["date"].set_properties(xalign=0, yalign=0, selectable=True)
        date_container = rabbitvcs.ui.widget.Box()
        date_container.pack_start(date, False, False, 0)
        date_container.pack_start(self.info["from"]["date"], False, False, 0)
        from_container.pack_start(date_container, False, False, 0)

        # Set up the Revision line
        revision = Gtk.Label(label=_("Revision:"))
        revision.set_size_request(90, -1)
        revision.set_properties(xalign=0, yalign=0)
        self.info["from"]["revision"] = Gtk.Label(label="")
        self.info["from"]["revision"].set_properties(xalign=0, selectable=True)
        self.info["from"]["revision"].set_wrap(True)
        revision_container = rabbitvcs.ui.widget.Box()
        revision_container.pack_start(revision, False, False, 0)
        revision_container.pack_start(self.info["from"]["revision"], False, False, 0)
        from_container.pack_start(revision_container, False, False, 0)

        # Set up the Log Message line
        message = Gtk.Label(label=_("Message:"))
        message.set_size_request(90, -1)
        message.set_properties(xalign=0, yalign=0)
        self.info["from"]["message"] = Gtk.Label(label="")
        self.info["from"]["message"].set_properties(xalign=0, yalign=0, selectable=True)
        self.info["from"]["message"].set_wrap(True)
        self.info["from"]["message"].set_size_request(250, -1)
        message_container = rabbitvcs.ui.widget.Box()
        message_container.pack_start(message, False, False, 0)
        message_container.pack_start(self.info["from"]["message"], False, False, 0)
        from_container.pack_start(message_container, False, False, 0)

    def update_branch_info(self):
        from_branch = self.from_branches.get_revision_object()

        if from_branch.value:
            log = self.git.log(
                self.path, limit=1, revision=from_branch, showtype="branch"
            )
            if log:
                from_info = log[0]
                self.info["from"]["author"].set_text(S(from_info.author).display())
                self.info["from"]["date"].set_text(
                    helper.format_datetime(from_info.date, self.datetime_format)
                )
                self.info["from"]["revision"].set_text(
                    S(from_info.revision).display()[0:7]
                )
                self.info["from"]["message"].set_text(
                    S(
                        helper.html_escape(
                            helper.format_long_text(from_info.message, 500)
                        )
                    ).display()
                )

    def on_from_branches_changed(self, widget):
        self.update_branch_info()

    def on_ok_clicked(self, widget, data=None):
        self.window.hide()

        from_branch = self.from_branches.get_revision_object()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git
        )

        self.action.append(self.action.set_header, _("Merge"))
        self.action.append(self.action.set_status, _("Running Merge Command..."))
        self.action.append(self.git.merge, from_branch)

        self.action.append(self.action.set_status, _("Completed Merge"))
        self.action.append(self.action.finish)
        self.action.schedule()

        self.window.close()

    def __revision_changed(self, widget):
        self.update_branch_info()


def on_activate(app):
    from rabbitvcs.ui import main, VCS_OPT

    (options, args) = main(
        [VCS_OPT], usage="Usage: rabbitvcs merge path [revision/revision_range]"
    )

    path = args[0]

    vcs_name = options.vcs
    if not vcs_name:
        vcs_name = rabbitvcs.vcs.guess(path)["vcs"]

    widget = None
    revision_text = None
    if len(args) >= 2:
        revision_text = args[1]

    if vcs_name == rabbitvcs.vcs.VCS_SVN:
        widget = SVNMerge(path, revision_text)
    elif vcs_name == rabbitvcs.vcs.VCS_GIT:
        widget = GitMerge(path, revision_text)

    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
