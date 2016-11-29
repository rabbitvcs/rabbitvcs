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

import os.path
import string
import re

import pygtk
import gobject
import gtk

import rabbitvcs
from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import pysvn
import configobj

from rabbitvcs import gettext
from six.moves import map
_ = gettext.gettext

class About:
    """
    This class provides an interface to the About window.
    
    """

    def __init__(self):
    
        def url_hook(dialog, url):
            rabbitvcs.util.helper.launch_url_in_webbrowser(url)
    
        gtk.about_dialog_set_url_hook(url_hook)
        self.about = gtk.AboutDialog()
        self.about.set_name(rabbitvcs.APP_NAME)

		# The set_program_name method was not added until PyGTK 2.12
        if hasattr(self.about, "set_program_name"):
	        self.about.set_program_name(rabbitvcs.APP_NAME)

        self.about.set_version(rabbitvcs.version)
        self.about.set_website("http://www.rabbitvcs.org")
        self.about.set_website_label("http://www.rabbitvcs.org")
        
        doc_path_root = "/usr/share/doc"
        doc_path_regex = re.compile("rabbitvcs")
        for dir in os.listdir(doc_path_root):
            if doc_path_regex.search(dir):
                # Find all the doc directories containing "rabbitvcs"
                authors_path = os.path.join(doc_path_root, dir, "AUTHORS")
                if os.path.exists(authors_path):
                    # At this point we have found a likely-looking AUTHORS
                    break
        else:
            # Assumes the user is running RabbitVCS through an svn checkout
            # and the doc files are two directories up (from rabbitvcs/ui).
            doc_path = os.path.dirname(os.path.realpath(__file__)).split('/')
            doc_path = '/'.join(doc_path[:-2])
            authors_path = os.path.join(doc_path, "AUTHORS")

        authors = open(authors_path, "r").read()

        self.about.set_authors(authors.split("\n"))
        
        versions = []
        versions.append("Subversion - %s" % string.join(list(map(str,pysvn.svn_version)), "."))
        versions.append("Pysvn - %s" % string.join(list(map(str,pysvn.version)), "."))
        versions.append("ConfigObj - %s" % str(configobj.__version__))
        
        self.about.set_comments("\n".join(versions))
    
    def run(self):
        self.about.show_all()
        self.about.run()
        self.about.destroy()
    
if __name__ == "__main__":
    window = About()
    window.run()
