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

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.vcs
from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.ui.properties")

from rabbitvcs import gettext
_ = gettext.gettext

class PropertiesBase(InterfaceView):
    """
    Provides an interface to add/edit/delete properties on versioned
    items in the working copy.

    """

    selected_row = None
    selected_rows = []

    def __init__(self, path):
        InterfaceView.__init__(self, "properties", "Properties")

        self.path = path
        self.delete_stack = []

        self.get_widget("Properties").set_title(
            _("Properties - %s") % path
        )

        self.get_widget("path").set_text(S(path).display())

        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("table"),
            [GObject.TYPE_BOOLEAN, GObject.TYPE_STRING, GObject.TYPE_STRING],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Name"), _("Value")]
        )
        self.table.allow_multiple()

        self.vcs = rabbitvcs.vcs.VCS()

    #
    # UI Signal Callbacks
    #


    def on_ok_clicked(self, widget):
        self.save()

    def on_new_clicked(self, widget):
        dialog = rabbitvcs.ui.dialog.Property()
        name,value,recurse = dialog.run()
        if name:
            self.table.append([recurse,name,value])

    def on_edit_clicked(self, widget):
        (recurse,name,value) = self.get_selected_name_value()
        dialog = rabbitvcs.ui.dialog.Property(name, value)
        name,value,recurse = dialog.run()
        if name:
            self.set_selected_name_value(name, value, recurse)

    def on_delete_clicked(self, widget, data=None):
        if not self.selected_rows:
            return

        for i in self.selected_rows:
            row = self.table.get_row(i)
            self.delete_stack.append([row[0],row[1]])

        self.table.remove_multiple(self.selected_rows)

    def on_table_cursor_changed(self, treeview, data=None):
        self.on_table_event(treeview)

    def on_table_button_released(self, treeview, data=None):
        self.on_table_event(treeview)

    def on_table_event(self, treeview):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()
        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        length = len(self.selected_rows)
        if length == 0:
            self.get_widget("edit").set_sensitive(False)
            self.get_widget("delete").set_sensitive(False)
        elif length == 1:
            self.get_widget("edit").set_sensitive(True)
            self.get_widget("delete").set_sensitive(True)
        else:
            self.get_widget("edit").set_sensitive(False)
            self.get_widget("delete").set_sensitive(True)

    def on_refresh_activate(self, widget):
        self.load()

    #
    # Helper methods
    #

    def set_selected_name_value(self, name, value, recurse):
        self.table.set_row(self.selected_rows[0], [recurse,name,value])

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
            self.proplist = self.svn.proplist(self.get_widget("path").get_text())
        except Exception as e:
            log.exception(e)
            rabbitvcs.ui.dialog.MessageBox(_("Unable to retrieve properties list"))
            self.proplist = []

        if self.proplist:
            for key,val in list(self.proplist.items()):
                self.table.append([False, key,val.rstrip()])

    def save(self):
        delete_recurse = self.get_widget("delete_recurse").get_active()

        for row in self.delete_stack:
            self.svn.propdel(self.path, row[1], recurse=delete_recurse)

        failure = False
        for row in self.table.get_items():
            if (not self.svn.propset(self.path, row[1], row[2],
                             overwrite=True, recurse=row[0])):
                failure = True
                break

        if failure:
            rabbitvcs.ui.dialog.MessageBox(_("There was a problem saving your properties."))

        self.close()


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs properties [url_or_path]")

    window = SVNProperties(paths[0])
    window.register_gtk_quit()
    Gtk.main()
