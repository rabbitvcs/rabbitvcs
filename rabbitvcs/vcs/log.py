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

import rabbitvcs.util.helper
import rabbitvcs.vcs

DATETIME_FORMAT = rabbitvcs.util.helper.LOCAL_DATETIME_FORMAT

class LogChangedPath:
    path = ""
    action = ""
    copy_from_path = ""
    copy_from_revision = ""
    
    def __init__(self, path, action, copy_from_path, copy_from_revision):
        self.path = path
        self.action = action
        self.copy_from_path = copy_from_path
        self.copy_from_revision = copy_from_revision

class Log:
    date = None
    revision = None
    author = None
    message = None
    parents = []
    head = False
    
    # A list of LogChangedFiles elements
    changed_paths = []
    
    def __init__(self, date, revision, author, message, changed_paths, parents=[], head=False):
        self.date = date
        self.revision = revision
        self.author = author
        self.message = message
        self.changed_paths = changed_paths
        self.parents = parents
        self.head = head
        
    def get_date(self):
        return self.date
        
    def set_date(self, date):
        self.date = date
