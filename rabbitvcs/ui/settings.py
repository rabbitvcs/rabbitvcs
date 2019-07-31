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

import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk, Pango
import dbus

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.util.settings
import rabbitvcs.util.helper
from rabbitvcs.util.strings import S

import rabbitvcs.services.checkerservice
from rabbitvcs.services.checkerservice import StatusCheckerStub

from rabbitvcs import gettext, _gettext, APP_NAME, LOCALE_DIR
_ = gettext.gettext

CHECKER_UNKNOWN_INFO = _("Unknown")
CHECKER_SERVICE_ERROR = _(
"There was an error communicating with the status checker service.")

from locale import getdefaultlocale, getlocale, LC_MESSAGES

class Settings(InterfaceView):
    def __init__(self, base_dir=None):
        """
        Provides an interface to the settings library.
        """

        InterfaceView.__init__(self, "settings", "Settings")

        self.checker_service = None
        self.settings = rabbitvcs.util.settings.SettingsManager()

        self.get_widget("enable_attributes").set_active(
            int(self.settings.get("general", "enable_attributes"))
        )
        self.get_widget("enable_emblems").set_active(
            int(self.settings.get("general", "enable_emblems"))
        )
        self.get_widget("enable_recursive").set_active(
            int(self.settings.get("general", "enable_recursive"))
        )
        self.get_widget("show_debug").set_active(
            int(self.settings.get("general","show_debug"))
        )
        self.get_widget("enable_subversion").set_active(
            int(self.settings.get("HideItem", "svn")) == 0
        )
        self.get_widget("enable_git").set_active(
            int(self.settings.get("HideItem", "git")) == 0
        )
        self.default_commit_message = rabbitvcs.ui.widget.TextView(self.get_widget("default_commit_message"))
        self.default_commit_message.set_text(
            S(self.settings.get_multiline("general", "default_commit_message")).display()
        )
        self.get_widget("diff_tool").set_text(
            S(self.settings.get("external", "diff_tool")).display()
        )
        self.get_widget("diff_tool_swap").set_active(
            int(self.settings.get("external", "diff_tool_swap"))
        )
        self.get_widget("merge_tool").set_text(
            S(self.settings.get("external", "merge_tool")).display()
        )
        self.get_widget("cache_number_repositories").set_text(
            S(self.settings.get("cache", "number_repositories")).display()
        )
        self.get_widget("cache_number_messages").set_text(
            S(self.settings.get("cache", "number_messages")).display()
        )

        self.logging_type = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("logging_type"),
            ["None", "Console", "File", "Both"]
        )
        val = self.settings.get("logging", "type")
        if not val:
            val = "Console"
        self.logging_type.set_active_from_value(val)

        self.logging_level = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("logging_level"),
            ["Debug", "Info", "Warning", "Error", "Critical"]
        )
        val = self.settings.get("logging", "level")
        if not val:
            val = "Debug"
        self.logging_level.set_active_from_value(val)

        # Git Configuration Editor
        show_git = False
        self.file_editor = None
        if base_dir:
            vcs = rabbitvcs.vcs.VCS()
            git_config_files = []
            if vcs.is_in_a_or_a_working_copy(base_dir) and vcs.guess(base_dir)["vcs"] == rabbitvcs.vcs.VCS_GIT:
                git = vcs.git(base_dir)
                git_config_files = git.get_config_files(base_dir)

                self.file_editor = rabbitvcs.ui.widget.MultiFileTextEditor(
                    self.get_widget("git_config_container"),
                    _("Config file:"),
                    git_config_files,
                    git_config_files,
                    show_add_line=False
                )
                show_git = True

        if show_git:
            self.get_widget("pages").get_nth_page(5).show()
        else:
            self.get_widget("pages").get_nth_page(5).hide()

        self._populate_checker_tab()

    def _get_checker_service(self, report_failure=True):
        if not self.checker_service:
            try:
                session_bus = dbus.SessionBus()
                self.checker_service = session_bus.get_object(
                                    rabbitvcs.services.checkerservice.SERVICE,
                                    rabbitvcs.services.checkerservice.OBJECT_PATH)
                # Initialize service locale in case it just started.
                self.checker_service.SetLocale(*getlocale(LC_MESSAGES))
            except dbus.DBusException as ex:
                if report_failure:
                    rabbitvcs.ui.dialog.MessageBox(CHECKER_SERVICE_ERROR)

        return self.checker_service

    def _populate_checker_tab(self, report_failure = True, connect = True):
        # This is a limitation of GLADE, and can be removed when we migrate to
        # GTK2 Builder

        checker_service = self.checker_service
        if not checker_service and connect:
            checker_service = self._get_checker_service(report_failure)

        self.get_widget("stop_checker").set_sensitive(bool(checker_service))

        if(checker_service):
            self.get_widget("checker_type").set_text(S(checker_service.CheckerType()).display())
            self.get_widget("pid").set_text(S(checker_service.PID()).display())

            memory = checker_service.MemoryUsage()

            if memory:
                self.get_widget("memory_usage").set_text("%s KB" % memory)
            else:
                self.get_widget("memory_usage").set_text(CHECKER_UNKNOWN_INFO)

            self.get_widget("locale").set_text(S(".".join(checker_service.SetLocale())).display())

            self._populate_info_table(checker_service.ExtraInformation())

        else:
            self.get_widget("checker_type").set_text(CHECKER_UNKNOWN_INFO)
            self.get_widget("pid").set_text(CHECKER_UNKNOWN_INFO)
            self.get_widget("memory_usage").set_text(CHECKER_UNKNOWN_INFO)
            self.get_widget("locale").set_text(CHECKER_UNKNOWN_INFO)
            self._clear_info_table()

    def _clear_info_table(self):
        for info_table in self.get_widget("info_table_area").get_children():
            info_table.destroy()

    def _populate_info_table(self, info):
        self._clear_info_table()

        table_place = self.get_widget("info_table_area")

        table = rabbitvcs.ui.widget.KeyValueTable(info)
        table_place.add(table)
        table.show()


    def on_refresh_info_clicked(self, widget):
        self._populate_checker_tab()

    def _stop_checker(self):
        pid = None
        if self.checker_service:
            try:
                pid = self.checker_service.Quit()
            except dbus.exceptions.DBusException:
                # Ignore it, it will necessarily happen when we kill the service
                pass
        self.checker_service = None
        if pid:
            try:
                os.waitpid(pid, 0)
            except OSError:
                # This occurs if the process is already gone.
                pass

    def on_restart_checker_clicked(self, widget):
        self._stop_checker()
        rabbitvcs.services.checkerservice.start()
        self._populate_checker_tab()

    def on_stop_checker_clicked(self, widget):
        self._stop_checker()
        self._populate_checker_tab(report_failure = False, connect = False)

    def on_destroy(self, widget):
        Gtk.main_quit()

    def on_cancel_clicked(self, widget):
        Gtk.main_quit()

    def on_ok_clicked(self, widget):
        self.save()
        Gtk.main_quit()

    def on_apply_clicked(self, widget):
        self.save()

    def save(self):
        self.settings.set(
            "general", "enable_attributes",
            self.get_widget("enable_attributes").get_active()
        )
        self.settings.set(
            "general", "enable_emblems",
            self.get_widget("enable_emblems").get_active()
        )
        self.settings.set(
            "general", "enable_recursive",
            self.get_widget("enable_recursive").get_active()
        )
        self.settings.set(
            "general", "show_debug",
            self.get_widget("show_debug").get_active()
        )
        self.settings.set(
            "HideItem", "svn",
            not self.get_widget("enable_subversion").get_active()
        )
        self.settings.set(
            "HideItem", "git",
            not self.get_widget("enable_git").get_active()
        )
        self.settings.set_multiline(
            "general", "default_commit_message",
            self.default_commit_message.get_text()
        )
        self.settings.set(
            "external", "diff_tool",
            self.get_widget("diff_tool").get_text()
        )
        self.settings.set(
            "external", "diff_tool_swap",
            self.get_widget("diff_tool_swap").get_active()
        )
        self.settings.set(
            "external", "merge_tool",
            self.get_widget("merge_tool").get_text()
        )
        self.settings.set(
            "cache", "number_repositories",
            self.get_widget("cache_number_repositories").get_text()
        )
        self.settings.set(
            "cache", "number_messages",
            self.get_widget("cache_number_messages").get_text()
        )
        self.settings.set(
            "logging", "type",
            self.logging_type.get_active_text()
        )
        self.settings.set(
            "logging", "level",
            self.logging_level.get_active_text()
        )
        self.settings.write()

        if self.file_editor:
            self.file_editor.save()

    def on_external_diff_tool_browse_clicked(self, widget):
        chooser = rabbitvcs.ui.dialog.FileChooser(
            _("Select a program"), "/usr/bin"
        )
        path = chooser.run()
        if not path is None:
            path = path.replace("file://", "")
            self.get_widget("diff_tool").set_text(S(path).display())

    def on_cache_clear_repositories_clicked(self, widget):
        confirmation = rabbitvcs.ui.dialog.Confirmation(
            _("Are you sure you want to clear your repository paths?")
        )
        if confirmation.run() == Gtk.ResponseType.OK:
            path = rabbitvcs.util.helper.get_repository_paths_path()
            fh = open(path, "w")
            fh.write("")
            fh.close()
            rabbitvcs.ui.dialog.MessageBox(_("Repository paths cleared"))

    def on_cache_clear_messages_clicked(self, widget):
        confirmation = rabbitvcs.ui.dialog.Confirmation(
            _("Are you sure you want to clear your previous messages?")
        )
        if confirmation.run() == Gtk.ResponseType.OK:
            path = rabbitvcs.util.helper.get_previous_messages_path()
            fh = open(path, "w")
            fh.write("")
            fh.close()
            rabbitvcs.ui.dialog.MessageBox(_("Previous messages cleared"))

    def on_cache_clear_authentication_clicked(self, widget):
        confirmation = rabbitvcs.ui.dialog.Confirmation(
            _("Are you sure you want to clear your authentication information?")
        )
        if confirmation.run() == Gtk.ResponseType.OK:
            home_dir = rabbitvcs.util.helper.get_user_path()
            subpaths = [
                '/.subversion/auth/svn.simple',
                '/.subversion/auth/svn.ssl.server',
                '/.subversion/auth/svn.username'
            ]
            for subpath in subpaths:
                path = "%s%s" % (home_dir, subpath)
                if os.path.exists(path):
                    files = os.listdir(path)
                    for filename in files:
                        filepath = "%s/%s" % (path, filename)
                        os.remove(filepath)

            rabbitvcs.ui.dialog.MessageBox(_("Authentication information cleared"))


if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs settings"
    )

    window = Settings(options.base_dir)
    window.register_gtk_quit()
    Gtk.main()
