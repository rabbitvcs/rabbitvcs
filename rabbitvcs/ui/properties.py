from __future__ import absolute_import
from rabbitvcs import gettext
from rabbitvcs.util.log import Log
from rabbitvcs.util.strings import S
import rabbitvcs.vcs
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

import os
from rabbitvcs.util import helper

import gi

gi.require_version("Gtk", "4.0")
sa = helper.SanitizeArgv()
sa.restore()


log = Log("rabbitvcs.ui.properties")

_ = gettext.gettext


@Gtk.Template(filename=f"{os.path.dirname(os.path.abspath(__file__))}/xml/properties.xml")
class PropertiesWidget(Gtk.Grid):
    __gtype_name__ = "PropertiesWidget"

    new = Gtk.Template.Child()
    refresh = Gtk.Template.Child()
    path = Gtk.Template.Child()
    table = Gtk.Template.Child()
    edit = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    delete_recurse = Gtk.Template.Child()

    def __init__(self):
        Gtk.Grid.__init__(self)

class PropertiesBase(GtkTemplateHelper):
    """
    Provides an interface to add/edit/delete properties on versioned
    items in the working copy.

    """

    selected_row = None
    selected_rows = []

    def __init__(self, path):
        GtkTemplateHelper.__init__(self, "Properties")

        self.widget = PropertiesWidget()
        self.window = self.get_window(self.widget)
        # add dialog buttons
        self.ok = self.add_dialog_button("Ok", self.on_ok_clicked, suggested=True)
        self.cancel = self.add_dialog_button("Cancel", self.on_cancel_clicked, hideOnAdwaita=True)
        # forward signals
        self.widget.new.connect("clicked", self.on_new_clicked)
        self.widget.edit.connect("clicked", self.on_edit_clicked)
        self.widget.delete.connect("clicked", self.on_delete_clicked)
        self.widget.refresh.connect("clicked", self.on_refresh_activate)
        self.widget.path.connect("activate", self.on_refresh_activate)
        self.widget.table.connect("cursor-changed", self.on_table_cursor_changed)
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_table_button_released)
        self.widget.table.add_controller(gesture)
        # set window properties
        self.window.set_default_size(600, -1)

        self.path = path
        self.delete_stack = []

        self.window.set_title(_("Properties - %s") % path)

        self.widget.path.set_text(S(path).display())

        self.table = rabbitvcs.ui.widget.Table(
            self.widget.table,
            [GObject.TYPE_BOOLEAN, GObject.TYPE_STRING, GObject.TYPE_STRING],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Name"), _("Value")],
        )
        self.table.allow_multiple()

        self.vcs = rabbitvcs.vcs.VCS()

    #
    # UI Signal Callbacks
    #

    def on_ok_clicked(self, widget):
        self.save()

    def on_new_clicked(self, widget):
        self.property = rabbitvcs.ui.dialog.Property()
        self.exec_dialog(self.window, self.property, self.on_new_response)

    def on_new_response(self, response):
        if response == Gtk.ResponseType.OK:
            name = self.property.property_name.get_active_text()
            if name:
                recurse = self.property.property_recurse.get_active()
                value_buffer = self.property.property_value.get_buffer()
                value = value_buffer.get_text(
                    value_buffer.get_start_iter(), value_buffer.get_end_iter(), True)
                self.table.append([recurse, name, value])

    def on_edit_clicked(self, widget):
        (recurse, name, value) = self.get_selected_name_value()
        self.property = rabbitvcs.ui.dialog.Property(name, value)
        self.exec_dialog(self.window, self.property, self.on_edit_response)

    def on_edit_response(self, response):
        if response == Gtk.ResponseType.OK:
            name = self.property.property_name.get_active_text()
            if name:
                recurse = self.property.property_recurse.get_active()
                value_buffer = self.property.property_value.get_buffer()
                value = value_buffer.get_text(
                    value_buffer.get_start_iter(), value_buffer.get_end_iter(), True)
                self.set_selected_name_value(name, value, recurse)

    def on_delete_clicked(self, widget, data=None):
        if not self.selected_rows:
            return

        for i in self.selected_rows:
            row = self.table.get_row(i)
            self.delete_stack.append([row[0], row[1]])

        self.table.remove_multiple(self.selected_rows)

    def on_table_cursor_changed(self, treeview, data=None):
        self.on_table_event(treeview)

    def on_table_button_released(self, gesture, n_press, x, y):
        self.on_table_event(self.widget.table)

    def on_table_event(self, treeview):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()
        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        length = len(self.selected_rows)
        if length == 0:
            self.widget.edit.set_sensitive(False)
            self.widget.delete.set_sensitive(False)
        elif length == 1:
            self.widget.edit.set_sensitive(True)
            self.widget.delete.set_sensitive(True)
        else:
            self.widget.edit.set_sensitive(False)
            self.widget.delete.set_sensitive(True)

    def on_refresh_activate(self, widget):
        self.load()

    #
    # Helper methods
    #

    def set_selected_name_value(self, name, value, recurse):
        self.table.set_row(self.selected_rows[0], [recurse, name, value])

    def get_selected_name_value(self):
        returner = None
        if self.selected_rows is not None:
            returner = self.table.get_row(self.selected_rows[0])
        return returner


class SVNProperties(PropertiesBase):
    def __init__(self, path):
        PropertiesBase.__init__(self, path)
        self.svn = self.vcs.svn()
        self.load()

    def load(self):
        self.table.clear()
        try:
            self.proplist = self.svn.proplist(self.widget.path.get_text())
        except Exception as e:
            log.exception(e)
            self.exec_dialog(self.window, _("Unable to retrieve properties list"), show_cancel=False)
            self.proplist = []

        if self.proplist:
            for key, val in list(self.proplist.items()):
                self.table.append([False, key, val.rstrip()])

    def save(self):
        delete_recurse = self.widget.delete_recurse.get_active()

        for row in self.delete_stack:
            self.svn.propdel(self.path, row[1], recurse=delete_recurse)

        failure = False
        for row in self.table.get_items():
            if not self.svn.propset(
                self.path, row[1], row[2], overwrite=True, recurse=row[0]
            ):
                failure = True
                break

        if failure:
            self.exec_dialog(
                self.window,
                _("There was a problem saving your properties."),
                show_cancel=False
            )

        self.window.close()


def on_activate(app):
    from rabbitvcs.ui import main

    (options, paths) = main(usage="Usage: rabbitvcs properties [url_or_path]")

    widget = SVNProperties(paths[0])
    app.add_window(widget.window)
    widget.window.set_visible(True)

if __name__ == "__main__":
    GtkTemplateHelper.run_application(on_activate)
