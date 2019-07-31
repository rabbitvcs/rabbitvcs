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

from rabbitvcs.ui import InterfaceNonView, InterfaceView
from rabbitvcs.ui.action import SVNAction, GitAction

import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class SVNIgnore(InterfaceNonView):
    """
    This class provides a handler to Ignore functionality.

    """

    def __init__(self, path, pattern, glob=False):
        """
        @type   path: string
        @param  path: The path to apply the ignore keyword to

        @type   pattern: string
        @param  pattern: Ignore items with the given pattern

        @type   glob: boolean
        @param  glob: True if the path to ignore is a wildcard "glob"

        """

        InterfaceNonView.__init__(self)
        self.path = path
        self.pattern = pattern
        self.glob = glob
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        prop = self.svn.PROPERTIES["ignore"]

        self.svn.propset(self.path, prop, self.pattern, recurse=self.glob)

        raise SystemExit()

class GitIgnore(InterfaceView):
    def __init__(self, path, pattern=""):
        InterfaceView.__init__(self, "ignore", "Ignore")

        self.path = path
        self.pattern = pattern

        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        ignore_files = self.git.get_ignore_files(path)
        ignore_file_labels = []

        path_dir = os.path.abspath(self.path)
        if os.path.isfile(path_dir):
            path_dir = os.path.dirname(path_dir)

        for ignore_file in ignore_files:
            label = path
            if ignore_file.startswith(path_dir):
               label = ignore_file[len(path_dir)+1:]

            ignore_file_labels.append(label)

        text = ""
        if pattern != path:
            text = pattern

        self.file_editor = rabbitvcs.ui.widget.MultiFileTextEditor(
            self.get_widget("fileeditor_container"),
            _("Ignore file:"),
            ignore_file_labels,
            ignore_files,
            show_add_line=True,
            line_content=text
        )

    def on_ok_clicked(self, widget, data=None):
        self.file_editor.save()
        self.close()



classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNIgnore,
    rabbitvcs.vcs.VCS_GIT: GitIgnore
}

def ignore_factory(path, pattern):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path, pattern)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main(usage="Usage: rabbitvcs ignore <folder> <pattern>")

    path = getcwd()
    pattern = ""
    if args:
        if len(args) == 1:
            pattern = args[0]
        else:
            if args[0] != ".":
                path = args[0]
            pattern = args[1]

    window = ignore_factory(path, pattern)
    window.register_gtk_quit()
    Gtk.main()
