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

from gettext import gettext as _
import os.path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk, Pango

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.wraplabel
import rabbitvcs.util.helper
from rabbitvcs.util.strings import S

ERROR_NOTICE = _("""\
An error has occurred in the RabbitVCS Nautilus extension. Please contact the \
<a href="%s">RabbitVCS team</a> with the error details listed below:"""
    % (rabbitvcs.WEBSITE))

class PreviousMessages(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, "dialogs/previous_messages", "PreviousMessages")

        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("prevmes_message")
        )

        self.message_table = rabbitvcs.ui.widget.Table(
            self.get_widget("prevmes_table"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Date"), _("Message")],
            filters=[{
                "callback": rabbitvcs.ui.widget.long_text_filter,
                "user_data": {
                    "column": 1,
                    "cols": 80
                }
            }],
            callbacks={
                "cursor-changed": self.on_prevmes_table_cursor_changed,
                "row-activated":  self.on_prevmes_table_row_activated
            }
        )
        self.entries = rabbitvcs.util.helper.get_previous_messages()
        if self.entries is None:
            return None

        for entry in self.entries:
            self.message_table.append([entry[0],entry[1]])

        if len(self.entries) > 0:
            self.message.set_text(S(self.entries[0][1]).display())

    def run(self):

        if self.entries is None:
            return None

        returner = None
        self.dialog = self.get_widget("PreviousMessages")
        result = self.dialog.run()
        if result == Gtk.ResponseType.OK:
            returner = self.message.get_text()

        self.dialog.destroy()

        return returner

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

class FolderChooser:
    def __init__(self):
        self.dialog = Gtk.FileChooserDialog(
            title = _("Select a Folder"),
            parent = None,
            action = Gtk.FileChooserAction.SELECT_FOLDER)
        self.dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.dialog.add_button(_("_Select"), Gtk.ResponseType.OK)
        self.dialog.set_default_response(Gtk.ResponseType.OK)

    def run(self):
        returner = None
        result = self.dialog.run()
        if result == Gtk.ResponseType.OK:
            # returner = self.dialog.get_uri()
            returner = self.dialog.get_file().get_path()
        self.dialog.destroy()
        return returner

class Certificate(InterfaceView):
    """
    Provides a dialog to accept/accept_once/deny an ssl certificate

    """

    def __init__(self, realm="", host="",
            issuer="", valid_from="", valid_until="", fingerprint=""):

        InterfaceView.__init__(self, "dialogs/certificate", "Certificate")

        self.get_widget("cert_realm").set_label(realm)
        self.get_widget("cert_host").set_label(host)
        self.get_widget("cert_issuer").set_label(issuer)
        to_str = _("to")
        self.get_widget("cert_valid").set_label(
            "%s %s %s" % (valid_from, to_str, valid_until)
        )
        self.get_widget("cert_fingerprint").set_label(fingerprint)

    def run(self):
        """
        Returns three possible values:

            - 0   Deny
            - 1   Accept Once
            - 2   Accept Forever

        """

        self.dialog = self.get_widget("Certificate")
        result = self.dialog.run()
        self.dialog.destroy()
        return result

class Authentication(InterfaceView):
    def __init__(self, realm="", may_save=True):
        InterfaceView.__init__(self, "dialogs/authentication", "Authentication")

        self.get_widget("auth_realm").set_label(realm)
        self.get_widget("auth_save").set_sensitive(may_save)

    def run(self):
        returner = None
        self.dialog = self.get_widget("Authentication")
        result = self.dialog.run()

        login = self.get_widget("auth_login").get_text()
        password = self.get_widget("auth_password").get_text()
        save = self.get_widget("auth_save").get_active()
        self.dialog.destroy()

        if result == Gtk.ResponseType.OK:
            return (True, login, password, save)
        else:
            return (False, "", "", False)

class CertAuthentication(InterfaceView):
    def __init__(self, realm="", may_save=True):
        InterfaceView.__init__(self, "dialogs/cert_authentication", "CertAuthentication")

        self.get_widget("certauth_realm").set_label(realm)
        self.get_widget("certauth_save").set_sensitive(may_save)

    def run(self):
        self.dialog = self.get_widget("CertAuthentication")
        result = self.dialog.run()

        password = self.get_widget("certauth_password").get_text()
        save = self.get_widget("certauth_save").get_active()
        self.dialog.destroy()

        if result == Gtk.ResponseType.OK:
            return (True, password, save)
        else:
            return (False, "", False)

class SSLClientCertPrompt(InterfaceView):
    def __init__(self, realm="", may_save=True):
        InterfaceView.__init__(self, "dialogs/ssl_client_cert_prompt", "SSLClientCertPrompt")

        self.get_widget("sslclientcert_realm").set_label(realm)
        self.get_widget("sslclientcert_save").set_sensitive(may_save)

    def on_sslclientcert_browse_clicked(self, widget, data=None):
        filechooser = FileChooser()
        cert = filechooser.run()
        if cert is not None:
            self.get_widget("sslclientcert_path").set_text(S(cert).display())

    def run(self):
        self.dialog = self.get_widget("SSLClientCertPrompt")
        result = self.dialog.run()

        cert = self.get_widget("sslclientcert_path").get_text()
        save = self.get_widget("sslclientcert_save").get_active()
        self.dialog.destroy()

        if result == Gtk.ResponseType.OK:
            return (True, cert, save)
        else:
            return (False, "", False)

class Property(InterfaceView):
    def __init__(self, name="", value="", recurse=True):
        InterfaceView.__init__(self, "dialogs/property", "Property")

        self.save_name = name
        self.save_value = value

        self.name = rabbitvcs.ui.widget.ComboBox(
                self.get_widget("property_name"),
                [   # default svn properties
                    'svn:author',
                    'svn:autoversioned',
                    'svn:date',
                    'svn:eol-style',
                    'svn:executable',
                    'svn:externals',
                    'svn:ignore',
                    'svn:keywords',
                    'svn:log',
                    'svn:mergeinfo',
                    'svn:mime-type',
                    'svn:needs-lock',
                    'svn:special',
                    ]
                )
        self.name.set_child_text(name)

        self.value = rabbitvcs.ui.widget.TextView(
            self.get_widget("property_value"),
            value
        )

        self.recurse = self.get_widget("property_recurse")
        self.recurse.set_active(recurse)

    def run(self):
        self.dialog = self.get_widget("Property")
        result = self.dialog.run()

        if result == Gtk.ResponseType.OK:
            self.save()

        self.dialog.destroy()
        return (self.save_name, self.save_value, self.recurse.get_active())

    def save(self):
        self.save_name = self.name.get_active_text()
        self.save_value = self.value.get_text()
        self.save_recurse = self.recurse.get_active()

class FileChooser:
    def __init__(self, title=_("Select a File"), folder=None):
        self.dialog = Gtk.FileChooserDialog(
            title = title,
            parent = None,
            action = Gtk.FileChooserAction.OPEN)
        self.dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.dialog.add_button(_("_Open"),   Gtk.ResponseType.OK)
        if folder is not None:
            self.dialog.set_current_folder(folder)
        self.dialog.set_default_response(Gtk.ResponseType.OK)

    def run(self):
        returner = None
        result = self.dialog.run()
        if result == Gtk.ResponseType.OK:
            returner = self.dialog.get_file().get_path()
        self.dialog.destroy()
        return returner

class FileSaveAs:
    def __init__(self, title=_("Save As..."), folder=None):
        self.dialog = Gtk.FileChooserDialog(
            title = title,
            parent = None,
            action = Gtk.FileChooserAction.SAVE)
        self.dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.dialog.add_button(_("_Save"),   Gtk.ResponseType.OK)
        if folder is not None:
            self.dialog.set_current_folder(folder)
        self.dialog.set_default_response(Gtk.ResponseType.OK)

    def run(self):
        returner = None
        result = self.dialog.run()
        if result == Gtk.ResponseType.OK:
            returner = self.dialog.get_filename()
        self.dialog.destroy()
        return returner

class Confirmation(InterfaceView):
    def __init__(self, message=_("Are you sure you want to continue?")):
        InterfaceView.__init__(self, "dialogs/confirmation", "Confirmation")
        self.get_widget("confirm_message").set_text(S(message).display())

    def run(self):
        dialog = self.get_widget("Confirmation")
        result = dialog.run()

        dialog.destroy()

        return result

class MessageBox(InterfaceView):
    def __init__(self, message):
        InterfaceView.__init__(self, "dialogs/message_box", "MessageBox")
        self.get_widget("messagebox_message").set_text(S(message).display())

        dialog = self.get_widget("MessageBox")
        dialog.run()
        dialog.destroy()

class DeleteConfirmation(InterfaceView):
    def __init__(self, path=None):
        InterfaceView.__init__(self, "dialogs/delete_confirmation", "DeleteConfirmation")

        if path:
            path = "\"%s\"" % os.path.basename(path)
        else:
            path = _("the selected item(s)")

        msg = self.get_widget("message").get_label().replace("%item%", path)
        self.get_widget("message").set_label(msg)

    def run(self):
        dialog = self.get_widget("DeleteConfirmation")
        result = dialog.run()

        dialog.destroy()

        return result

class TextChange(InterfaceView):
    def __init__(self, title=None, message=""):
        InterfaceView.__init__(self, "dialogs/text_change", "TextChange")
        if title:
            self.get_widget("TextChange").set_title(title)

        self.textview = rabbitvcs.ui.widget.TextView(
            self.get_widget("textchange_message"),
            message
        )

    def run(self):
        dialog = self.get_widget("TextChange")
        result = dialog.run()

        dialog.destroy()

        return (result, self.textview.get_text())

class OneLineTextChange(InterfaceView):
    def __init__(self, title=None, label=None, current_text=None):
        InterfaceView.__init__(self, "dialogs/one_line_text_change", "OneLineTextChange")
        if title:
            self.get_widget("OneLineTextChange").set_title(title)

        self.new_text = self.get_widget("new_text")
        self.label = self.get_widget("label")

        if label:
            self.label.set_text(S(label).display())

        if current_text:
            self.new_text.set_text(S(current_text).display())

        self.dialog = self.get_widget("OneLineTextChange")

    def on_key_release_event(self, widget, data):
        # The Gtk.Dialog.response() method emits the "response" signal,
        # which tells Gtk.Dialog.run() asyncronously to stop.  This allows the
        # user to press the "Return" button when done writing in the new text
        if Gdk.keyval_name(data.keyval) == "Return":
            self.dialog.response(Gtk.ResponseType.OK)

    def run(self):
        result = self.dialog.run()
        new_text = self.new_text.get_text()

        self.dialog.destroy()

        return (result, new_text)

class NewFolder(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, "dialogs/create_folder", "CreateFolder")

        self.folder_name = self.get_widget("folder_name")
        self.textview = rabbitvcs.ui.widget.TextView(
            self.get_widget("log_message"),
            _("Added a folder to the repository")
        )
        self.on_folder_name_changed(self.folder_name)

    def on_folder_name_changed(self, widget):
        complete = (widget.get_text() != "")
        self.get_widget("ok").set_sensitive(complete)

    def run(self):
        dialog = self.get_widget("CreateFolder")
        dialog.set_default_response(Gtk.ResponseType.OK)
        result = dialog.run()

        fields_text = (self.folder_name.get_text(), self.textview.get_text())

        dialog.destroy()

        if result == Gtk.ResponseType.OK:
            return fields_text
        else:
            return None

class ErrorNotification(InterfaceView):

    def __init__(self, text):
        InterfaceView.__init__(self, "dialogs/error_notification", "ErrorNotification")

        notice = rabbitvcs.ui.wraplabel.WrapLabel(ERROR_NOTICE)
        notice.set_use_markup(True)

        notice_box = rabbitvcs.ui.widget.Box(self.get_widget("notice_box"))
        notice_box.pack_start(notice, True, True, 0)
        notice_box.show_all()

        self.textview = rabbitvcs.ui.widget.TextView(
            self.get_widget("error_text"),
            text,
            spellcheck=False
        )

        self.textview.view.modify_font(Pango.FontDescription("monospace"))

        dialog = self.get_widget("ErrorNotification")
        dialog.run()
        dialog.destroy()

class NameEmailPrompt(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, "dialogs/name_email_prompt", "NameEmailPrompt")

        self.dialog = self.get_widget("NameEmailPrompt")

    def on_key_release_event(self, widget, data):
        # The Gtk.Dialog.response() method emits the "response" signal,
        # which tells Gtk.Dialog.run() asyncronously to stop.  This allows the
        # user to press the "Return" button when done writing in the new text
        if Gdk.keyval_name(data.keyval) == "Return":
            self.dialog.response(Gtk.ResponseType.OK)

    def run(self):
        result = self.dialog.run()
        name = self.get_widget("name").get_text()
        email = self.get_widget("email").get_text()
        self.dialog.destroy()

        if result == Gtk.ResponseType.OK:
            return (name, email)
        else:
            return (None, None)

class MarkResolvedPrompt(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, "dialogs/mark_resolved_prompt", "MarkResolvedPrompt")

    def run(self):
        self.dialog = self.get_widget("MarkResolvedPrompt")
        result = self.dialog.run()
        self.dialog.destroy()
        return result

class ConflictDecision(InterfaceView):
    """
    Provides a dialog to make conflict decisions with.  User can accept mine,
    accept theirs, or edit conflicts.

    """

    def __init__(self, filename=""):

        InterfaceView.__init__(self, "dialogs/conflict_decision", "ConflictDecision")
        self.get_widget("filename").set_text(S(filename).display())

    def run(self):
        """

        The first has three possible values about how to resolve the conflict.

            - -1  Cancel
            - 0   Accept Mine
            - 1   Accept Theirs
            - 2   Merge Manually


        """

        self.dialog = self.get_widget("ConflictDecision")
        result = self.dialog.run()
        self.dialog.destroy()
        return result

class Loading(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, "dialogs/loading", "Loading")

        self.get_widget("loading_cancel").set_sensitive(False)

        self.pbar = rabbitvcs.ui.widget.ProgressBar(
            self.get_widget("pbar")
        )
        self.pbar.start_pulsate()

    def on_destroy(self, widget):
        self.close()

    def on_loading_cancel_clicked(self, widget):
        self.close()

    def run(self):
        self.dialog = self.get_widget("Loading")
        self.dialog.run()

    def destroy(self):
        self.dialog.destroy()
