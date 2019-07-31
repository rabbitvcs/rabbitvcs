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

from rabbitvcs.ui.properties import PropertiesBase
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
from rabbitvcs.util.strings import S
import rabbitvcs.vcs
from rabbitvcs.util.log import Log
from rabbitvcs.ui.action import SVNAction

log = Log("rabbitvcs.ui.revprops")

from rabbitvcs import gettext
_ = gettext.gettext

class SVNRevisionProperties(PropertiesBase):
    def __init__(self, path, revision=None):
        PropertiesBase.__init__(self, path)

        self.svn = self.vcs.svn()

        if not self.svn.is_path_repository_url(path):
            self.path = self.svn.get_repo_url(path)
            self.get_widget("path").set_text(S(self.path).display())

        self.revision = revision
        self.revision_obj = None
        if revision is not None:
            self.revision_obj = self.svn.revision("number", revision)

        self.load()

    def load(self):
        self.table.clear()
        try:
            self.proplist = self.svn.revproplist(
                self.get_widget("path").get_text(),
                self.revision_obj
            )
        except Exception as e:
            log.exception(e)
            rabbitvcs.ui.dialog.MessageBox(_("Unable to retrieve properties list"))
            self.proplist = {}

        if self.proplist:
            for key,val in list(self.proplist.items()):
                self.table.append([False, key,val.rstrip()])

    def save(self):
        delete_recurse = self.get_widget("delete_recurse").get_active()

        self.action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )

        for row in self.delete_stack:
            self.action.append(
                self.svn.revpropdel,
                self.path,
                row[1],
                self.revision_obj,
                force=True
            )

        for row in self.table.get_items():
            self.action.append(
                self.svn.revpropset,
                row[1],
                row[2],
                self.path,
                self.revision_obj,
                force=True
            )

        self.action.schedule()

        self.close()


if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT
    (options, args) = main(
        [VCS_OPT],
        usage="Usage: rabbitvcs revprops [url1@rev1]"
    )

    pathrev = helper.parse_path_revision_string(args.pop(0))
    window = SVNRevisionProperties(pathrev[0], pathrev[1])
    window.register_gtk_quit()
    Gtk.main()
