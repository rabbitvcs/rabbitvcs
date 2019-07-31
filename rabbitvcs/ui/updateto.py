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
import rabbitvcs.ui.action
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog

from rabbitvcs import gettext
_ = gettext.gettext

class UpdateToRevision(InterfaceView):
    """
    This class provides an interface to update a working copy to a specific
    revision.  It has a glade .

    """

    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "update", "Update")
        self.path = path
        self.revision = revision
        self.vcs = rabbitvcs.vcs.VCS()



class SVNUpdateToRevision(UpdateToRevision):
    def __init__(self, path, revision):
        UpdateToRevision.__init__(self, path, revision)

        self.svn = self.vcs.svn()
        self.get_widget("options_box").show()

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.svn,
            revision=revision,
            url=self.path,
            expand=True,
            revision_changed_callback=self.on_revision_changed
        )

    def on_ok_clicked(self, widget):

        revision = self.revision_selector.get_revision_object()
        recursive = self.get_widget("recursive").get_active()
        omit_externals = self.get_widget("omit_externals").get_active()
        rollback = self.get_widget("rollback").get_active()

        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        if rollback:
            self.action.append(self.action.set_header, _("Rollback To Revision"))
            self.action.append(self.action.set_status, _("Rolling Back..."))
            self.action.append(
                self.svn.merge_ranges,
                self.svn.get_repo_url(self.path),
                [(self.svn.revision("HEAD").primitive(), revision.primitive())],
                self.svn.revision("head"),
                self.path
            )
            self.action.append(self.action.set_status, _("Completed Rollback"))
        else:
            self.action.append(self.action.set_header, _("Update To Revision"))
            self.action.append(self.action.set_status, _("Updating..."))
            self.action.append(
                self.svn.update,
                self.path,
                revision=revision,
                recurse=recursive,
                ignore_externals=omit_externals
            )
            self.action.append(self.action.set_status, _("Completed Update"))

        self.action.append(self.action.finish)
        self.action.schedule()

    def on_revision_changed(self, revision_selector):
        # Only allow rollback when a revision number is specified
        if (revision_selector.revision_kind_opt.get_active() == 1
                and revision_selector.revision_entry.get_text() != ""):
            self.get_widget("rollback").set_sensitive(True)
        else:
            self.get_widget("rollback").set_sensitive(False)

class GitUpdateToRevision(UpdateToRevision):
    def __init__(self, path, revision):
        UpdateToRevision.__init__(self, path, revision)

        self.get_widget("revision_label").set_text(_("What revision/branch do you want to checkout?"))

        self.git = self.vcs.git(path)

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.git,
            revision=revision,
            url=self.path,
            expand=True,
            revision_changed_callback=self.on_revision_changed
        )

    def on_ok_clicked(self, widget):
        revision = self.revision_selector.get_revision_object()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )

        self.action.append(self.action.set_header, _("Checkout"))
        self.action.append(self.action.set_status, _("Checking out %s..." % revision))
        self.action.append(
            self.git.checkout,
            [self.path],
            revision
        )
        self.action.append(self.action.set_status, _("Completed Checkout"))
        self.action.append(self.action.finish)
        self.action.schedule()

    def on_revision_changed(self, revision_selector):
        pass

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNUpdateToRevision,
    rabbitvcs.vcs.VCS_GIT: GitUpdateToRevision,
}

def updateto_factory(vcs, path, revision=None):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]

    return classes_map[vcs](path, revision)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, args) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs updateto [path]"
    )

    window = updateto_factory(options.vcs, args[0], revision=options.revision)
    window.register_gtk_quit()
    Gtk.main()
