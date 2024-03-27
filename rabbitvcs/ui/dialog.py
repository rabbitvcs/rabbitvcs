from __future__ import absolute_import
from rabbitvcs.util.strings import S
import rabbitvcs.util.helper
import rabbitvcs.ui.wraplabel
import rabbitvcs.ui.widget
from rabbitvcs.ui import InterfaceView, GtkTemplateHelper, adwaita_available
from gi.repository import Gtk, GObject, Gdk, Pango, Gio

try:
    from gi.repository import Adw
except Exception as e:
    pass

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

from gettext import gettext as _
import os.path
import gi

gi.require_version("Gtk", "4.0")


ERROR_NOTICE = _(
    """\
An error has occurred in the RabbitVCS Nautilus extension. Please contact the \
<a href="%s">RabbitVCS team</a> with the error details listed below:"""
    % (rabbitvcs.WEBSITE)
)

@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/previous_messages.xml")
class PreviousWidget(Gtk.Box):
    __gtype_name__ = "PreviousWidget"

    prevmes_message = Gtk.Template.Child()
    prevmes_table = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)

class PreviousMessages(GtkTemplateHelper):
    def __init__(self, parent):
        GtkTemplateHelper.__init__(self, "Previous Messages")

        self.parent = parent
        self.widget = PreviousWidget()
        self.message = rabbitvcs.ui.widget.TextView(self.widget.prevmes_message)

        self.message_table = rabbitvcs.ui.widget.Table(
            self.widget.prevmes_table,
            [GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Date"), _("Message")],
            filters=[
                {
                    "callback": rabbitvcs.ui.widget.long_text_filter,
                    "user_data": {"column": 1, "cols": 80},
                }
            ],
            callbacks={
                "cursor-changed": self.on_prevmes_table_cursor_changed,
                "row-activated": self.on_prevmes_table_row_activated,
            },
        )
        self.entries = rabbitvcs.util.helper.get_previous_messages()
        if self.entries is None:
            return None

        for entry in self.entries:
            self.message_table.append([entry[0], entry[1]])

        if len(self.entries) > 0:
            self.message.set_text(S(self.entries[0][1]).display())

    def run(self, parent=None, on_response=None):

        if self.entries is None:
            return None

        self.on_response = on_response
        self.exec_dialog(self.parent, self.widget, self.dialog_responded)

    def dialog_responded(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            message = self.message.get_text()
            if (self.on_response):
                self.on_response(message)

    def on_prevmes_table_row_activated(self, treeview, data, col):
        self.update_message_table()
        self.dialog.response(Gtk.ResponseType.OK)

    def on_prevmes_table_cursor_changed(self, treeview):
        self.update_message_table()

    def update_message_table(self):
        selection = self.message_table.get_selected_row_items(1)

        if selection:
            selected_message = selection[-1]
            self.message.set_text(S(selected_message).display())


class FolderChooser(object):
    _callback = None

    def __init__(self, callback, folder=None, parent=None):
        self._callback = callback
        self.open_dialog = Gtk.FileChooserNative.new(
            title=_("Select a Folder"),
            parent=parent, action=Gtk.FileChooserAction.SELECT_FOLDER)

        if folder and len(folder) > 0 and os.path.exists(folder):
            self.open_dialog.set_current_folder(Gio.File.new_for_path(folder))

        self.open_dialog.connect("response", self._file_chooser_callback)

        self.open_dialog.show()

    def _file_chooser_callback(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_file().get_path()
            self._callback(path)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/certificate.xml")
class Certificate(Gtk.Box, GtkTemplateHelper):
    """
    Provides a dialog to accept/accept_once/deny an ssl certificate

    """
    __gtype_name__ = "Certificate"

    cert_realm = Gtk.Template.Child()
    cert_host = Gtk.Template.Child()
    cert_issuer = Gtk.Template.Child()
    cert_valid = Gtk.Template.Child()
    cert_fingerprint = Gtk.Template.Child()

    def __init__(
        self,
        realm="",
        host="",
        issuer="",
        valid_from="",
        valid_until="",
        fingerprint="",
    ):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Certificate")

        # "Check Certificate"

        self.cert_realm.set_label(realm)
        self.cert_host.set_label(host)
        self.cert_issuer.set_label(issuer)
        to_str = _("to")
        self.cert_valid.set_label(
            "%s %s %s" % (valid_from, to_str, valid_until)
        )
        self.cert_fingerprint.set_label(fingerprint)

    def run(self, parent, on_response):
        """
        Returns three possible values:

            - 0   Deny
            - 1   Accept Once
            - 2   Accept Forever

        """
        # TODO add buttons and handle signals
        self.exec_dialog(parent, self)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/authentication.xml")
class Authentication(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "Authentication"

    auth_realm = Gtk.Template.Child()
    auth_save = Gtk.Template.Child()
    auth_login = Gtk.Template.Child()
    auth_password = Gtk.Template.Child()

    def __init__(self, realm="", may_save=True):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Authentication")

        self.auth_realm.set_label(realm)
        self.auth_save.set_sensitive(may_save)

    def get_values(self):
        login = self.auth_login.get_text()
        password = self.auth_password.get_text()
        save = self.auth_save.get_active()

        return (login, password, save)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/cert_authentication.xml")
class CertAuthentication(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "CertAuthentication"

    certauth_realm = Gtk.Template.Child()
    certauth_save = Gtk.Template.Child()
    certauth_password = Gtk.Template.Child()

    def __init__(self, realm="", may_save=True):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "CertAuthentication")

        self.certauth_realm.set_label(realm)
        self.certauth_save.set_sensitive(may_save)

    def get_values(self):
        password = self.certauth_password.get_text()
        save = self.certauth_save.get_active()

        return (password, save)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/ssl_client_cert_prompt.xml")
class SSLClientCertPrompt(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "SSLClientCertPrompt"

    sslclientcert_realm = Gtk.Template.Child()
    sslclientcert_save = Gtk.Template.Child()
    sslclientcert_path = Gtk.Template.Child()

    def __init__(self, realm="", may_save=True):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "SSLClientCertPrompt")

        self.sslclientcert_realm.set_label(realm)
        self.sslclientcert_save.set_sensitive(may_save)

    @Gtk.Template.Callback()
    def on_sslclientcert_browse_clicked(self, widget, data=None):
        filechooser = FileChooser()
        cert = filechooser.run()
        if cert is not None:
            self.sslclientcert_path.set_text(S(cert).display())

    def get_values(self):
        cert = self.sslclientcert_path.get_text()
        save = self.sslclientcert_save.get_active()

        return (cert, save)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/property.xml")
class Property(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "PropertyWidget"

    property_name = Gtk.Template.Child()
    property_value = Gtk.Template.Child()
    property_recurse = Gtk.Template.Child()

    callback = None

    def __init__(self, name="", value="", recurse=True):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Property")

        self.save_name = name
        self.save_value = value

        self.name = rabbitvcs.ui.widget.ComboBox(
            self.property_name,
            [  # default svn properties
                "svn:author",
                "svn:autoversioned",
                "svn:date",
                "svn:eol-style",
                "svn:executable",
                "svn:externals",
                "svn:ignore",
                "svn:keywords",
                "svn:log",
                "svn:mergeinfo",
                "svn:mime-type",
                "svn:needs-lock",
                "svn:special",
            ],
        )
        self.name.set_child_text(name)

        self.value = rabbitvcs.ui.widget.TextView(
            self.property_value, value
        )

        self.recurse = self.property_recurse
        self.recurse.set_active(recurse)

    def run(self, on_response):
        self.callback = on_response
        self.connect("response", self.on_response)
        self.set_visible(True)

    def on_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            self.save()

        if self.callback:
            self.callback (self.save_name, self.save_value, self.recurse.get_active())

    def save(self):
        self.save_name = self.name.get_active_text()
        self.save_value = self.value.get_text()
        self.save_recurse = self.recurse.get_active()


class FileChooser(object):
    _callback = None

    def __init__(self, title=_("Select a File"), folder=None, callback=None, parent=None):
        self._callback = callback
        self.dialog = Gtk.FileChooserNative.new(
            title=title,
            parent=parent, action=Gtk.FileChooserAction.OPEN)

        if folder and len(folder) > 0 and os.path.exists(folder):
            self.dialog.set_current_folder(Gio.File.new_for_path(folder))

        self.dialog.connect("response", self._file_chooser_callback)

        self.dialog.show()

    def _file_chooser_callback(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_file().get_path()
            self._callback(path)


class FileSaveAs(object):
    _callback = None

    def __init__(self, title=_("Save As..."), folder=None, parent=None, callback=None):
        self._callback = callback
        self.save_dialog = Gtk.FileChooserNative.new(
            title=title, parent=parent, action=Gtk.FileChooserAction.SAVE
        )

        if folder and len(folder) > 0 and os.path.exists(folder):
            self.save_dialog.set_current_folder(Gio.File.new_for_path(folder))

        self.save_dialog.connect("response", self._file_chooser_callback)

        self.save_dialog.show()

    def _file_chooser_callback(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_file().get_path()
            self._callback(path)


class Confirmation(GtkTemplateHelper):
    def __init__(self, response, title="Confirmation", message=_("Are you sure you want to continue?"), parent=None):
        GtkTemplateHelper.__init__(self, title)
        self.exec_dialog(parent, S(message).display(), response, yes_no=True)


class MessageBox(GtkTemplateHelper):
    def __init__(self, response, title="MessageBox", message="default message", parent=None):
        GtkTemplateHelper.__init__(self, title)
        self.exec_dialog(parent, S(message).display(), response)


class DeleteConfirmation(GtkTemplateHelper):
    def __init__(self, response, path=None, parent=None):
        GtkTemplateHelper.__init__(self, "Delete Confirmation")

        if path:
            path = '"%s"' % os.path.basename(path)
        else:
            path = _("the selected item(s)")

        self.exec_dialog(parent, f"Are you sure you want to delete {path}?", response, yes_no=True)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/text_change.xml")
class TextChange(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "TextChange"

    textchange_message = Gtk.Template.Child()

    def __init__(self, title=None, message=""):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "TextChange")

        if title:
            self.window.set_title(title)

        self.textview = rabbitvcs.ui.widget.TextView(
            self.textchange_message, message
        )

    def get_values(self):
        return self.textview.get_text()


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/one_line_text_change.xml")
class OneLineTextChange(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "OneLineTextChange"

    new_text = Gtk.Template.Child()
    label = Gtk.Template.Child()

    def __init__(self, title="Text Change", label_value=None, current_text=None):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, title)

        if label_value:
            self.label.set_text(S(label_value).display())

        if current_text:
            self.new_text.set_text(S(current_text).display())

    def get_values(self):
        new_text = self.new_text.get_text()

        return new_text


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/create_folder.xml")
class NewFolder(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "CreateFolder"

    folder_name = Gtk.Template.Child()
    log_message = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Create Folder")

        self.textview = rabbitvcs.ui.widget.TextView(
            self.log_message, _("Added a folder to the repository")
        )

    @Gtk.Template.Callback()
    def on_folder_name_changed(self, widget):
        complete = widget.get_text() != ""
        self.set_ok_sensitive(complete)

    def run(self, parent, on_response):
        GtkTemplateHelper.run(self, parent, on_response)

        self.on_folder_name_changed(self.folder_name)

    def get_values(self):
        fields_text = (self.folder_name.get_text(), self.textview.get_text())

        return fields_text


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/error_notification.xml")
class ErrorNotification(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "ErrorNotification"

    notice_box = Gtk.Template.Child()
    error_text = Gtk.Template.Child()

    def __init__(self, text):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Error")

        notice = rabbitvcs.ui.wraplabel.WrapLabel(ERROR_NOTICE)
        notice.set_use_markup(True)

        notice_box = rabbitvcs.ui.widget.Box(self.notice_box)
        notice_box.pack_start(notice, True, True, 0)

        self.textview = rabbitvcs.ui.widget.TextView(
            self.error_text, text, spellcheck=False
        )

        self.textview.view.set_monospace(True)

    def run(self, parent, on_response):
        self.exec_dialog(parent, self, on_response_callback=on_response, show_cancel=False)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/name_email_prompt.xml")
class NameEmailPrompt(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "NameEmailPrompt"

    name = Gtk.Template.Child()
    email = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Name and Email")

        keycontroller = Gtk.EventControllerKey()
        keycontroller.connect("key-released", self._on_key_release_event)
        self.add_controller(keycontroller)

    def _on_key_release_event(self, controller, keyval, keycode, state):
        # The Gtk.Dialog.response() method emits the "response" signal,
        # which tells Gtk.Dialog.run() asyncronously to stop.  This allows the
        # user to press the "Return" button when done writing in the new text
        if self.message_dialog is not None and keyval == Gdk.keyval_from_name("Escape"):
            self.reject_message_dialog()

    def run(self, parent, on_response):
        self.exec_dialog(parent, self, on_response_callback=on_response)
        self.message_dialog.set_focus(self.name)

    def get_values(self):
        name = self.name.get_text()
        email = self.email.get_text()

        return (name, email)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/mark_resolved_prompt.xml")
class MarkResolvedPrompt(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "MarkResolvedPrompt"

    def __init__(self):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Mark Resolved")

    def run(self, parent, on_response=None):
        self.exec_dialog(parent, self, on_response_callback=on_response, yes_no=True)


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/conflict_decision.xml")
class ConflictDecision(Gtk.Box, GtkTemplateHelper):
    """
    Provides a dialog to make conflict decisions with.  User can accept mine,
    accept theirs, or edit conflicts.

    """
    __gtype_name__ = "ConflictDecision"

    filename = Gtk.Template.Child()

    def __init__(self, filename="(unknown)"):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Edit Conflicts")
        self.filename.set_text(S(filename).display())

    def exec_dialog(self, parent, content, on_response_callback = None):
        if adwaita_available:
            dialog = Adw.MessageDialog(transient_for = parent)
            dialog.set_heading(self.gtktemplate_id)
            dialog.set_extra_child(content)
            dialog.add_response("mine", "Mine")
            dialog.add_response("theirs", "Theirs")
            dialog.add_response("edit", "Edit")
            dialog.add_response("cancel", "Cancel")
            dialog.connect("response", self.on_adw_dialog_response)
        else:
            dialog = Gtk.MessageDialog(transient_for = parent)
            dialog.set_title(self.gtktemplate_id)
            dialog.set_modal(True)
            dialog.add_buttons(
                "_Mine", 0,
                "_Theirs", 1,
                "_Edit", 2,
                "_Cancel", Gtk.ResponseType.CANCEL)
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

    def on_adw_dialog_response(self, dialog, response):
        if self.on_response_callback is not None:
            response_id = Gtk.ResponseType.CANCEL
            if response == "mine":
                response_id = 0
            elif response == "theirs":
                response_id = 1
            elif response == "edit":
                response_id = 2
            elif response == "cancel":
                response_id = Gtk.ResponseType.CANCEL
            if self.on_response_callback:
                self.on_response_callback(response_id)

    def on_gtk_dialog_response(self, dialog, response_id):
        if self.on_response_callback:
            self.on_response_callback(response_id)

        dialog.destroy()


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/dialogs/loading.xml")
class Loading(Gtk.Box, GtkTemplateHelper):
    __gtype_name__ = "Loading"

    pbar = Gtk.Template.Child()

    def __init__(self, parent=None):
        Gtk.Box.__init__(self)
        GtkTemplateHelper.__init__(self, "Loading")

        self._pbar = rabbitvcs.ui.widget.ProgressBar(self.pbar)
        self._pbar.start_pulsate()

    def run(self, parent, response):
        self.exec_dialog(parent, self, response, show_ok=False)

app = None

def dummy_response(response):
    # just quit the application
    app.quit()

def dialog_factory(paths, dialog_type, parent):
    guess = rabbitvcs.vcs.guess(paths[0])
    dialog = None

    if dialog_type.casefold() == "previousmessage":
        dialog = PreviousMessages(None)
    elif dialog_type.casefold() == "certificate":
        dialog = Certificate()
    elif dialog_type.casefold() == "authentication":
        dialog = Authentication()
    elif dialog_type.casefold() == "cert_authentication":
        dialog = CertAuthentication()
    elif dialog_type.casefold() == "sslclientcertprompt":
        dialog = SSLClientCertPrompt()
    # elif dialog_type.casefold() == "property":
    #     dialog = Property()
    elif dialog_type.casefold() == "confirmation":
        dialog = Confirmation(dummy_response, parent=parent)
    elif dialog_type.casefold() == "messagebox":
        dialog = MessageBox(dummy_response, parent=parent)
    elif dialog_type.casefold() == "delete_confirmation":
        dialog = DeleteConfirmation(dummy_response, parent=parent)
    elif dialog_type.casefold() == "text_change":
        dialog = TextChange()
    elif dialog_type.casefold() == "one_line_text_change":
        dialog = OneLineTextChange()
    elif dialog_type.casefold() == "new_folder":
        dialog = NewFolder()
    elif dialog_type.casefold() == "error_notification":
        dialog = ErrorNotification("dummy text")
    elif dialog_type.casefold() == "name_email_prompt":
        dialog = NameEmailPrompt()
    elif dialog_type.casefold() == "mark_resolved":
        dialog = MarkResolvedPrompt()
    elif dialog_type.casefold() == "conflict_decision":
        dialog = ConflictDecision()
    elif dialog_type.casefold() == "loading":
        dialog = Loading()

    return dialog

def on_activate(app):
    from rabbitvcs.ui import main, BASEDIR_OPT

    (options, paths) = main(
        [ (["-d", "--dialog"], {"default": "certificate"}) ],
        usage="Usage: rabbitvcs dialog [dialog_name] [url_or_path]"
    )

    parent = Gtk.Window()
    app.add_window(parent)

    window = dialog_factory(paths, options.dialog, parent)

    do_not_run = [Confirmation, MessageBox, DeleteConfirmation]
    if window and type(window) not in do_not_run:
        window.run(parent, dummy_response)

if __name__ == "__main__":
    app = Adw.Application() if adwaita_available else Gtk.Application()

    app.connect('activate', on_activate)
    app.run()
