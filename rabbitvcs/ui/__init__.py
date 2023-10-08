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

"""

UI layer.

"""
from __future__ import absolute_import
import rabbitvcs.vcs.status
from rabbitvcs import APP_NAME, LOCALE_DIR, gettext

import os
from six.moves import range

from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

adwaita_available = True
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
except Exception as e:
    adwaita_available = False

sa = helper.SanitizeArgv()
sa.restore()

_ = gettext.gettext


REVISION_OPT = (["-r", "--revision"], {"help": "specify the revision number"})
BASEDIR_OPT = (["-b", "--base-dir"], {})
QUIET_OPT = (
    ["-q", "--quiet"],
    {
        "help": "Run the add command quietly, with no UI.",
        "action": "store_true",
        "default": False,
    },
)
VCS_OPT = (["--vcs"], {"help": "specify the version control system"})

VCS_OPT_ERROR = _(
    "You must specify a version control system using the --vcs [svn|git] option"
)

#: Maps statuses to emblems.
STATUS_EMBLEMS = {
    rabbitvcs.vcs.status.status_normal: "rabbitvcs-normal",
    rabbitvcs.vcs.status.status_modified: "rabbitvcs-modified",
    rabbitvcs.vcs.status.status_added: "rabbitvcs-added",
    rabbitvcs.vcs.status.status_deleted: "rabbitvcs-deleted",
    rabbitvcs.vcs.status.status_ignored: "rabbitvcs-ignored",
    rabbitvcs.vcs.status.status_read_only: "rabbitvcs-locked",
    rabbitvcs.vcs.status.status_locked: "rabbitvcs-locked",
    rabbitvcs.vcs.status.status_unknown: "rabbitvcs-unknown",
    rabbitvcs.vcs.status.status_missing: "rabbitvcs-complicated",
    rabbitvcs.vcs.status.status_replaced: "rabbitvcs-modified",
    rabbitvcs.vcs.status.status_complicated: "rabbitvcs-complicated",
    rabbitvcs.vcs.status.status_calculating: "rabbitvcs-calculating",
    rabbitvcs.vcs.status.status_error: "rabbitvcs-error",
    rabbitvcs.vcs.status.status_unversioned: "rabbitvcs-unversioned",
}


class GtkTemplateHelper(object):
    gtktemplate_id = ""
    header = None
    toast_overlay = None
    button_box = None
    suggested_button = None
    message_dialog = None

    def __init__(self, gtktemplate_id = None):
        if gtktemplate_id:
            self.gtktemplate_id = gtktemplate_id

    def get_window(self, widget):
        if adwaita_available:
            window = Adw.ApplicationWindow()
            self.header = Adw.HeaderBar()
            self.toast_overlay = Adw.ToastOverlay()
            self.toast_overlay.set_child(widget)
            box = Gtk.Box()
            box.set_orientation(Gtk.Orientation.VERTICAL)
            box.append(self.header)
            box.append(self.toast_overlay)
            window.set_content(box)
        else:
            window = Gtk.ApplicationWindow()
            box = Gtk.Box()
            box.set_orientation(Gtk.Orientation.VERTICAL)
            box.append(widget)
            window.set_child(box)

        keycontroller = Gtk.EventControllerKey()
        keycontroller.connect("key-pressed", self.on_key_pressed)
        window.add_controller(keycontroller)

        window.set_title(self.gtktemplate_id)
        window.set_icon_name("rabbitvcs-small")

        return window

    def update_dialog_title(self, title):
        old_title = self.suggested_button.get_label()
        if not adwaita_available or old_title != title:
            self.window.set_title(title)

    def add_dialog_button(self, text, callback, suggested = False, hideOnAdwaita = False):
        button = Gtk.Button()
        button.set_label(text)
        button.connect("clicked", callback)
        if suggested:
            self.suggested_button = button
            button.add_css_class("suggested-action")

        if adwaita_available:
            self.header.pack_start(button)
            # hide title if suggested button has the same text
            if suggested and text == self.window.get_title():
                self.window.set_title("")
            if hideOnAdwaita:
                button.set_visible(False)
        else:
            if self.button_box == None:
                self.button_box = Gtk.Box()
                self.button_box.set_margin_start(6)
                self.button_box.set_margin_top(6)
                self.button_box.set_margin_end(6)
                self.button_box.set_margin_bottom(6)
                self.button_box.set_spacing(6)
                self.button_box.set_hexpand(True)
                self.button_box.set_halign(Gtk.Align.END)
                box = self.window.get_child()
                box.append(self.button_box)

            self.button_box.append(button)

        return button
    
    def exec_notification(self, notification):
        if adwaita_available:
            toast = Adw.Toast()
            toast.set_title(notification)
            self.toast_overlay.add_toast(toast)
        else:
            self.exec_dialog(self.window, notification, None, False)

    def exec_dialog(self, parent, content, on_response_callback = None, show_cancel = True, yes_no = False, show_ok=True):
        if adwaita_available:
            dialog = Adw.MessageDialog(transient_for = parent)
            dialog.set_heading(self.gtktemplate_id)
            if type(content) == str:
                dialog.set_body(content)
            else:
                dialog.set_extra_child(content)

            if show_ok:
                dialog.add_response("ok", "Yes" if yes_no else "Ok")
            if show_cancel:
                dialog.add_response("cancel", "No" if yes_no else "Cancel")
            dialog.connect("response", self.on_adw_dialog_response)
        else:
            dialog = Gtk.MessageDialog(transient_for = parent)
            dialog.set_title(self.gtktemplate_id)
            dialog.set_modal(True)

            if show_ok:
                dialog.add_buttons(
                    "_Yes" if yes_no else "_Ok",
                    Gtk.ResponseType.OK)
            if show_cancel:
                dialog.add_buttons(
                    "_No" if yes_no else "_Cancel",
                    Gtk.ResponseType.CANCEL)
            dialog.connect("response", self.on_gtk_dialog_response)
            area = dialog.get_content_area()
            area.set_margin_top(12)
            area.set_margin_end(12)
            area.set_margin_bottom(12)
            area.set_margin_start(12)
            area.append(content)

        self.on_response_callback = on_response_callback

        dialog.set_size_request(550, 0)
        dialog.show()

        self.message_dialog = dialog

    def accept_message_dialog(self):
        if self.message_dialog is not None:
            if adwaita_available:
                self.message_dialog.response("ok")
            else:
                self.message_dialog.response(Gtk.ResponseType.OK)

    def reject_message_dialog(self):
        if self.message_dialog is not None:
            if adwaita_available:
                self.message_dialog.response("cancel")
            else:
                self.message_dialog.response(Gtk.ResponseType.CANCEL)

    def set_ok_sensitive(self, sensitive):
        if self.message_dialog is not None:
            if adwaita_available:
                self.message_dialog.set_response_enabled("ok", sensitive)
            else:
                self.message_dialog.set_response_sensitive(Gtk.ResponseType.OK, sensitive)
        
    def on_adw_dialog_response(self, dialog, response):
        if self.on_response_callback != None:
            response_id = Gtk.ResponseType.CANCEL
            if response == "ok":
                response_id = Gtk.ResponseType.OK
            if self.on_response_callback:
                self.on_response_callback(response_id)
    
    def on_gtk_dialog_response(self, dialog, response_id):
        if self.on_response_callback:
            self.on_response_callback(response_id)

        dialog.destroy()

    def run(self, parent, response):
        self.exec_dialog(parent, self, response)

    def register_window(self):
        if adwaita_available:
            appl = Adw.Application.get_default()
        else:
            appl = Gtk.Application.get_default()
        
        appl.add_window(self.window)

    @staticmethod
    def run_application(on_activate):
        if adwaita_available:
            app = Adw.Application()
        else:
            app = Gtk.Application()

        app.connect('activate', on_activate)
        app.run()

    def on_cancel_clicked(self, widget):
        if self.window:
            self.window.close()

    def on_close_clicked(self, widget):
        if self.window:
            self.window.close()

    def on_key_pressed(self, controller, keyval, keycode, state):
        widget = controller.get_widget()

        if keyval == Gdk.keyval_from_name("Escape"):
            self.on_cancel_clicked(widget)
            return True

        if (
            state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(keyval).lower() == "w"
        ):
            self.on_cancel_clicked(widget)
            return True

        if (
            state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(keyval).lower() == "q"
        ):
            self.on_cancel_clicked(widget)
            return True

        if (
            state & Gdk.ModifierType.CONTROL_MASK
            and Gdk.keyval_name(keyval).lower() == "r"
        ):
            self.on_refresh_clicked(widget)
            return True


class GtkBuilderWidgetWrapper(object):
    pass # todo remove


class InterfaceView(GtkBuilderWidgetWrapper):
    # todo remove
    def change_button(self, id, label=None, icon=None):
        """
        Replace label and/or icon of the named button.
        """

        button = self.get_widget(id)
        if label:
            button.set_label(label)
        if icon:
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            button.set_image(image)


class InterfaceNonView(object):
    pass # todo remove


class VCSNotSupportedError(Exception):
    """Indicates the desired VCS is not valid for a given action"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def main(allowed_options=None, description=None, usage=None):
    from os import getcwd
    from sys import argv
    from optparse import OptionParser
    from rabbitvcs.util.helper import get_common_directory

    parser = OptionParser(usage=usage, description=description)

    if allowed_options:
        for (option_args, option_kwargs) in allowed_options:
            parser.add_option(*option_args, **option_kwargs)

    (options, args) = parser.parse_args(argv)

    # Convert "." to current working directory
    paths = args[1:]
    for i in range(0, len(paths)):
        if paths[i] == ".":
            paths[i] = getcwd()

    if not paths:
        paths = [getcwd()]

    if parser.has_option("--base-dir") and not options.base_dir:
        options.base_dir = get_common_directory(paths)

    return (options, paths)
