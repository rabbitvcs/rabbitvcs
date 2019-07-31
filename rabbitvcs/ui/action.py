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

from __future__ import division
from __future__ import absolute_import
import threading

from os.path import basename

import shutil
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.util
import rabbitvcs.vcs
from rabbitvcs.util import helper
from rabbitvcs.util.strings import S
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.util.decorators import gtk_unsafe

from rabbitvcs import gettext
_ = gettext.gettext

helper.gobject_threads_init()

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.ui.action")

class VCSNotifier(InterfaceView):
    """
    Provides a base class to handle threaded/gtk_unsafe calls to our vcs

    """

    def __init__(self, callback_cancel=None, visible=True):
        InterfaceView.__init__(self)

        if visible:
            self.show()

        self.callback_cancel = callback_cancel
        self.was_canceled_by_user = False
        self.canceled = False

    def set_canceled_by_user(self, was_canceled_by_user):
        self.was_canceled_by_user = was_canceled_by_user

    def toggle_ok_button(self, sensitive):
        pass

    def append(self, entry):
        pass

    def focus_on_ok_button(self):
        pass

class DummyNotifier:
    def __init__(self):
        pass

    def close(self):
        pass

    def set_canceled_by_user(self, was_canceled_by_user):
        pass

    @gtk_unsafe
    def exception_callback(self, e):
        log.exception(e)
        MessageBox(str(e))

class MessageCallbackNotifier(VCSNotifier):
    """
    Provides an interface to handle the Notification UI.

    """

    gtkbuilder_filename = "notification"
    gtkbuilder_id = "Notification"

    def __init__(self, callback_cancel=None, visible=True, client_in_same_thread=True):
        """
        @type   callback_cancel: def
        @param  callback_cancel: A method to call when cancel button is clicked.

        @type   visible: boolean
        @param  visible: Show the notification window.  Defaults to True.

        """

        VCSNotifier.__init__(self, callback_cancel, visible)

        self.client_in_same_thread = client_in_same_thread

        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("table"),
            [GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING],
            [_("Action"), _("Path"), _("Mime Type")]
        )

        self.pbar = rabbitvcs.ui.widget.ProgressBar(
            self.get_widget("pbar")
        )
        self.pbar.start_pulsate()
        self.finished = False

    def on_destroy(self, widget):
        if self.callback_cancel is not None:
            self.callback_cancel()

        self.canceled = True
        self.close()

    def on_cancel_clicked(self, widget):

        if self.canceled or self.finished:
            self.close()

        if self.callback_cancel is not None:
            self.callback_cancel()

        self.canceled = True

    def on_ok_clicked(self, widget):
        self.close()

    @gtk_unsafe
    def toggle_ok_button(self, sensitive):
        self.finished = True
        self.get_widget("ok").set_sensitive(sensitive)
        self.get_widget("saveas").set_sensitive(sensitive)

    @gtk_unsafe
    def append(self, entry):
        self.table.append(entry)
        self.table.scroll_to_bottom()

    def get_title(self):
        return self.get_widget("Notification").get_title()

    @gtk_unsafe
    def set_title(self, title):
        self.get_widget("Notification").set_title(title)

    @gtk_unsafe
    def set_header(self, header):
        self.set_title(header)

        self.get_widget("action").set_markup(
            "<span size=\"xx-large\"><b>%s</b></span>" % header
        )

    @gtk_unsafe
    def focus_on_ok_button(self):
        self.get_widget("ok").grab_focus()

    def exception_callback(self, e):
        self.append(["", str(e), ""])

    def on_saveas_clicked(self, widget):
        self.saveas()

    @gtk_unsafe
    def enable_saveas(self):
        self.get_widget("saveas").set_sensitive(True)

    @gtk_unsafe
    def disable_saveas(self):
        self.get_widget("saveas").set_sensitive(False)

    def saveas(self, path=None):
        if path is None:
            from rabbitvcs.ui.dialog import FileSaveAs
            dialog = FileSaveAs()
            path = dialog.run()

        if path is not None:
            fh = open(path, "w")
            fh.write(self.table.generate_string_from_data())
            fh.close()

class LoadingNotifier(VCSNotifier):

    gtkbuilder_filename = "dialogs/loading"
    gtkbuilder_id = "Loading"

    def __init__(self, callback_cancel=None, visible=True):

        VCSNotifier.__init__(self, callback_cancel, visible)

        self.pbar = rabbitvcs.ui.widget.ProgressBar(
            self.get_widget("pbar")
        )
        self.pbar.start_pulsate()

    def on_destroy(self, widget):
        self.close()

    def on_loading_cancel_clicked(self, widget):
        self.set_canceled_by_user(True)
        if self.callback_cancel is not None:
            self.callback_cancel()

        self.close()

    def get_title(self):
        return self.get_widget("Loading").get_title()

    @gtk_unsafe
    def set_title(self, title):
        self.get_widget("Loading").set_title(title)

    def set_header(self, header):
        self.set_title(header)

    @gtk_unsafe
    def exception_callback(self, e):
        if not self.was_canceled_by_user:
            log.exception(e)
            MessageBox(str(e))

class VCSAction(threading.Thread):
    """
    Provides a central interface to handle vcs actions & callbacks.
    Loads UI elements that require user interaction.

    """

    def __init__(self, client, register_gtk_quit=False, notification=True,
            run_in_thread=True):

        self.run_in_thread = run_in_thread

        if run_in_thread is True:
            threading.Thread.__init__(self)

        self.message = None

        self.queue = rabbitvcs.util.FunctionQueue()

        self.login_tries = 0
        self.cancel = False

        self.has_loader = False
        self.has_notifier = False

        if notification:
            self.notification = MessageCallbackNotifier(
                self.set_cancel,
                notification,
                client_in_same_thread=self.client_in_same_thread
            )
            self.has_notifier = True
        elif run_in_thread:
            visible = run_in_thread
            self.notification = LoadingNotifier(self.set_cancel, visible=visible)
            self.has_loader = True
        else:
            self.notification = DummyNotifier()

        self.pbar_ticks = None
        self.pbar_ticks_current = -1

        # Tells the notification window to do a Gtk.main_quit() when closing
        # Is used when the script is run from a command line
        if register_gtk_quit:
            self.notification.register_gtk_quit()

    def schedule(self):
        if self.run_in_thread:
            self.start()
        else:
            self.run()

    def set_pbar_ticks(self, num):
        """
        Set the total number of ticks to represent in the progress bar.
        Each time the notify method is called, update the pbar fraction.
        If this function isn't called, the progress bar just pulsates.

        @type   num: integer
        @param  num: The number of ticks in the progress bar.
        """

        self.pbar_ticks = num

    def set_progress_fraction(self, fraction):
        """
        An alternative method to access the progress bar directly.

        @type   percentage: int
        @param  percentage: The percentage value to set the progress bar.

        """

        if self.has_notifier:
            self.notification.pbar.update(fraction)

    def set_header(self, header):
        self.notification.set_header(header)

    def cancel(self):
        """
        PySVN calls this callback method frequently to see if the user wants
        to cancel the action.  If self.cancel is True, then it will cancel
        the action.  If self.cancel is False, it will continue.

        """

        return self.cancel

    def set_cancel(self, cancel=True):
        """
        Used as a callback function by the Notification UI.  When the cancel
        button is clicked, it sets self.cancel to True, and the cancel callback
        method returns True.

        """
        self.cancel = cancel
        self.notification.set_canceled_by_user(True)
        self.queue.cancel_queue()

    def finish(self, message=None):
        """
        This is called when the final notifcation message has been received,
        or it is called manually when no final notification message is expected.

        It sets the current "status", and enables the OK button to allow
        the user to leave the window.

        @type   message: string
        @param  message: A message to show the user.

        """

        if self.has_notifier:
            self.notification.append(
                ["", _("Finished"), ""]
            )
            self.notification.focus_on_ok_button()
            title = self.notification.get_title()
            self.notification.set_title(_("%s - Finished") % title)
            self.set_status(message)
            self.notification.pbar.stop_pulsate()
            self.notification.pbar.update(1)
            self.notification.toggle_ok_button(True)

    def get_log_message(self):
        """
        A callback method that retrieves a supplied log message.

        Returns a list where the first element is True/False.  Returning true
        tells the action to continue, false tells it to cancel.  The second
        element is the log message, which is specified by self.message.
        self.message is set by calling the self.set_log_message() method from
        the UI interface class.

        @rtype:  (boolean, string)
        @return: (True=continue/False=cancel, log message)

        """

        should_continue = True
        message = self.message
        if message is None:
            settings = rabbitvcs.util.settings.SettingsManager()
            message = settings.get_multiline("general", "default_commit_message")
            result = helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.TextChange(_("Log Message"), message).run())
            should_continue = (result[0] == Gtk.ResponseType.OK)
            message = result[1]
        if isinstance(message, bytes):
            message = message.decode()
        if not should_continue:
            self.set_cancel()
        return should_continue, message

    def get_login(self, realm, username, may_save):
        """
        A callback method that requests a username/password to login to a
        password-protected repository.  This method runs the Authentication
        dialog, which provides a username, password, and saving widget.  The
        dialog returns a tuple, which is returned directly to the VCS caller.

        If the login fails greater than three times, cancel the action.

        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.

        @type   realm:      string
        @param  realm:      The realm of the repository.

        @type   username:   string
        @param  username:   Username passed by the vcs caller.

        @type   may_save:   boolean
        @param  may_save:   Whether or not the authentication can be saved.

        @rtype:             (boolean, string, string, boolean)
        @return:            (True=continue/False=cancel, username,password, may_save)
        """

        if self.login_tries >= 3:
            return (False, "", "", False)

        result = helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.Authentication(realm, may_save).run())

        if result is not None:
            self.login_tries += 1

        return result

    def get_ssl_trust(self, data):
        """
        A callback method that requires the user to either accept or deny
        a certificate from an ssl secured repository.  It opens a dialog that
        shows the user information about the ssl certificate and then gives
        them the option of denying, accepting, or accepting once.

        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.

        @type   data:   dictionary
        @param  data:   A dictionary with SSL certificate info.

        @rtype:         (boolean, int, boolean)
        @return:        (True=Accept/False=Deny, number of accepted failures, remember)
        """

        result = 0
        if data:
            result = helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.Certificate(
                data["realm"],
                data["hostname"],
                data["issuer_dname"],
                data["valid_from"],
                data["valid_until"],
                data["finger_print"]
            ).run())

        if result == 0:
            #Deny
            return (False, 0, False)
        elif result == 1:
            #Accept Once
            return (True, data["failures"], False)
        elif result == 2:
            #Accept Forever
            return (True, data["failures"], True)

    def get_ssl_password(self, realm, may_save):
        """
        A callback method that is used to get an ssl certificate passphrase.

        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.

        @type   realm:      string
        @param  realm:      The certificate realm.

        @type   may_save:   boolean
        @param  may_save:   Whether or not the passphrase can be saved.

        @rtype:             (boolean, string, boolean)
        @return:            (True=continue/False=cancel, password, may save)
        """

        return helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.CertAuthentication(
                realm,
                may_save
            ).run())

    def get_client_cert(self, realm, may_save):
        """
        A callback method that is used to get an ssl certificate.

        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.

        @type   realm:      string
        @param  realm:      The certificate realm.

        @type   may_save:   boolean
        @param  may_save:   Whether or not the passphrase can be saved.

        @rtype:             (boolean, string, boolean)
        @return:            (True=continue/False=cancel, password, may save)
        """

        return helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.SSLClientCertPrompt(
                realm,
                may_save
            ).run())

    def set_log_message(self, message):
        """
        Set this action's log message from the UI interface.  self.message
        is referred to when the VCS does the get_log_message callback.

        @type   message: string
        @param  message: Set a log message.
        """

        self.message = message

    @gtk_unsafe
    def set_status(self, message):
        """
        Set the current status of the VCS action.  Currently, this method
        is called at the beginning and end of each action, to display what is
        going on.  Currently, it just appends the status message to the
        notification window.  In the future, I may set up a progress bar
        and put the status message there.

        @type   message: string
        @param  message: A status message.
        """

        if message is not None:
            self.notification.get_widget("status").set_text(S(message).display())

    def append(self, func, *args, **kwargs):
        """
        Append a function call to the action queue.

        """

        self.queue.append(func, *args, **kwargs)

    def get_result(self, index):
        """
        Retrieve the result of a single function call by specifying the order
        in which the function was in the queue.

        @type   index: int
        @param  index: The queue index

        """

        return self.queue.get_result(index)

    def __queue_exception_callback(self, e):
        """
        Used internally when an exception is raised within the queue

        @type   e: Exception
        @param  e: The exception object passed by the FunctionQueue

        """
        self.notification.exception_callback(e)

        if self.has_notifier:
            self.finish()
        if self.has_loader:
            self.stop()

    def stop(self):
        if self.notification:
            self.notification.close()

    def run(self):
        """
        The central method that drives this class.  It runs the before and
        after methods, as well as the main vcs method.

        """

        if self.has_loader:
            self.queue.append(self.notification.close, threaded=True)

        self.queue.set_exception_callback(self.__queue_exception_callback)
        self.queue.start()

    def run_single(self, func, *args, **kwargs):
        try:
            try:
                returner = func(*args, **kwargs)
            except Exception as e:
                self.__queue_exception_callback(e)
                returner = None
        finally:
            self.stop()

        return returner

    def stop_loader(self):
        self.stop()

class SVNAction(VCSAction):
    def __init__(self, client, register_gtk_quit=False, notification=True,
            run_in_thread=True):

        self.client_in_same_thread = False

        self.client = client
        self.client.set_callback_cancel(self.cancel)
        self.client.set_callback_notify(self.notify)
        self.client.set_callback_get_log_message(self.get_log_message)
        self.client.set_callback_get_login(self.get_login)
        self.client.set_callback_ssl_server_trust_prompt(self.get_ssl_trust)
        self.client.set_callback_ssl_client_cert_password_prompt(self.get_ssl_password)
        self.client.set_callback_ssl_client_cert_prompt(self.get_client_cert)

        VCSAction.__init__(self, client, register_gtk_quit, notification,
            run_in_thread)


    def notify(self, data):
        """
        This method is called every time the VCS function wants to tell us
        something.  It passes us a dictionary of useful information.  When
        this method is called, it appends some useful data to the notifcation
        window.

        TODO: We need to implement this in a more VCS-agnostic way, since the
        supplied data dictionary is pysvn-dependent.  I'm going to implement
        something in lib/vcs/svn.py soon.

        """

        if self.has_notifier:
            self.conflict_filter(data)

            if self.pbar_ticks is not None:
                self.pbar_ticks_current += 1
                frac = self.pbar_ticks_current / self.pbar_ticks
                if frac > 1:
                    frac = 1
                self.notification.pbar.update(frac)

            is_known_action = False
            if data["action"] in self.client.NOTIFY_ACTIONS:
                action = self.client.NOTIFY_ACTIONS[data["action"]]
                is_known_action = True
            else:
                action = data["action"]

            # Determine if this action denotes completedness
            is_complete_action = False
            for item in self.client.NOTIFY_ACTIONS_COMPLETE:
                if str(data["action"]) == str(item):
                    is_complete_action = True
                    break

            if (is_known_action
                    and is_complete_action
                    and "revision" in data
                    and data["revision"]):
                self.notification.append(
                    ["", "Revision %s" % data["revision"].number, ""]
                )
            elif "path" in data:
                self.notification.append([
                    action,
                    data["path"],
                    data["mime_type"]
                ])

    def conflict_filter(self, data):
        if "content_state" in data and str(data["content_state"]) == "conflicted":
            position = self.queue.get_position()
            self.queue.insert(position+1, self.edit_conflict, data)

    def edit_conflict(self, data):
        helper.launch_ui_window("editconflicts", [data["path"]], block=True)

class GitAction(VCSAction):
    def __init__(self, client, register_gtk_quit=False, notification=True,
            run_in_thread=True):

        self.client_in_same_thread = True

        self.client = client

        VCSAction.__init__(self, client, register_gtk_quit, notification,
            run_in_thread)

        self.client.set_callback_notify(self.notify)
        self.client.set_callback_progress_update(self.set_progress_fraction)
        self.client.set_callback_get_user(self.get_user)
        self.client.set_callback_get_cancel(self.cancel)

    def notify(self, data):
        if self.has_notifier:
            if data:
                self.conflict_filter(data)
                if isinstance(data, dict):
                    self.notification.append([
                        data["action"],
                        data["path"],
                        data["mime_type"]
                    ])
                else:
                    self.notification.append(["", data, ""])

    def get_user(self):
        return helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.NameEmailPrompt().run())

    def conflict_filter(self, data):
        if str(data).startswith("ERROR:"):
            path = data[27:]
            helper.launch_ui_window("editconflicts", [path], block=True)

class MercurialAction(VCSAction):
    def __init__(self, client, register_gtk_quit=False, notification=True,
            run_in_thread=True):

        self.client_in_same_thread = True

        self.client = client
        self.client.set_callback_notify(self.notify)
        self.client.set_callback_get_user(self.get_user)
        self.client.set_callback_get_cancel(self.cancel)

        VCSAction.__init__(self, client, register_gtk_quit, notification,
            run_in_thread)

    def notify(self, data):
        if self.has_notifier:
            if data:
                self.conflict_filter(data)
                if isinstance(data, dict):
                    self.notification.append([
                        data["action"],
                        data["path"],
                        data["mime_type"]
                    ])
                else:
                    self.notification.append(["", data, ""])

    def get_user(self):
        return helper.run_in_main_thread(lambda: rabbitvcs.ui.dialog.NameEmailPrompt().run())

    def conflict_filter(self, data):
        if str(data).startswith("ERROR:"):
            path = data[27:]
            helper.launch_ui_window("editconflicts", [path], block=True)

def vcs_action_factory(client, register_gtk_quit=False, notification=True,
        run_in_thread=True):

    if client.vcs == rabbitvcs.vcs.VCS_GIT:
        return GitAction(client, register_gtk_quit, notification,
            run_in_thread)
    else:
        return SVNAction(client, register_gtk_quit, notification,
            run_in_thread)
