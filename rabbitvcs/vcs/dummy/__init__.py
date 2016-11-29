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

"""
Concrete VCS dummy implementation.
"""
from __future__ import absolute_import

import rabbitvcs.vcs
import rabbitvcs.vcs.status

class Dummy:
    def __init__(self):
        pass
    
    def status(self, path, summarize=True, invalidate=False):
        return rabbitvcs.vcs.status.Status.status_unknown(path)
    
    def is_working_copy(self, path):
        return False
    
    def is_in_a_or_a_working_copy(self, path):
        return False

    def is_versioned(self, path):
        return False
    
    def get_items(self, paths, statuses=[]):
        return []
    
    def is_locked(self, path):
        return False
    
    def statuses(self, path, recurse=True, invalidate=False):
        return []
        
    def revision(self, kind, number=None):
        return None
