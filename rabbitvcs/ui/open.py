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

from os import getcwd
import os.path

from rabbitvcs.util import helper

import gi
gi.require_version("Gtk", "3.0")
sa = helper.SanitizeArgv()
from gi.repository import Gtk, GObject, Gdk
sa.restore()

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction, GitAction

import rabbitvcs.vcs
from rabbitvcs.util.strings import S

from rabbitvcs import gettext
_ = gettext.gettext

import six

class SVNOpen(InterfaceNonView):
    """
    This class provides a handler to open tracked files.

    """

    def __init__(self, path, revision):
        """
        @type   path: string
        @param  path: The path to open

        @type   revision: string
        @param  revision: The revision of the file to open

        """

        InterfaceNonView.__init__(self)

        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        if revision and isinstance(revision, (str, six.text_type)):
            revision_obj = self.svn.revision("number", number=revision)
        else:
            revision_obj = self.svn.revision("HEAD")

        url = path
        if not self.svn.is_path_repository_url(path):
            url = self.svn.get_repo_root_url(path) + '/' + path
        dest = helper.get_tmp_path("rabbitvcs-" + revision + "-" + os.path.basename(path))

        self.svn.export(
            url,
            dest,
            revision=revision_obj,
            force=True
        )

        helper.open_item(dest)

        raise SystemExit()

class GitOpen(InterfaceNonView):
    """
    This class provides a handler to open tracked files.

    """

    def __init__(self, path, revision):
        """
        @type   path: string
        @param  path: The path to open

        @type   revision: string
        @param  revision: The revision of the file to open

        """

        InterfaceNonView.__init__(self)

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        if revision:
            revision_obj = self.git.revision(revision)
        else:
            revision_obj = self.git.revision("HEAD")

        dest_dir = helper.get_tmp_path("rabbitvcs-" + S(revision))

        self.git.export(
            path,
            dest_dir,
            revision=revision_obj
        )

        repo_path = self.git.find_repository_path(path)
        relative_path = path
        if path.startswith(repo_path):
            relative_path = path[len(repo_path)+1:]

        dest_path = "%s/%s" % (dest_dir, relative_path)

        helper.open_item(dest_path)

        raise SystemExit()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNOpen,
    rabbitvcs.vcs.VCS_GIT: GitOpen
}

def open_factory(vcs, path, revision):
    if not vcs:
        guess = rabbitvcs.vcs.guess(path)
        vcs = guess["vcs"]

    return classes_map[vcs](path, revision)


if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT, VCS_OPT
    (options, paths) = main(
        [REVISION_OPT, VCS_OPT],
        usage="Usage: rabbitvcs open path [-r REVISION]"
    )

    window = open_factory(options.vcs, paths[0], options.revision)
    window.register_gtk_quit()
    Gtk.main()
