#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
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
Very simple status checking class. Useful when you can't get any of the others
to work, or you need to prototype things. 
"""
from __future__ import absolute_import

import rabbitvcs.vcs
import rabbitvcs.vcs.status

import simplejson

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.statuschecker")

class StatusChecker:
    """ A class for performing status checks. """
    
    # All subclasses should override this! This is to be displayed in the
    # settings dialog
    CHECKER_NAME = _("Simple status checker")
    
    def __init__(self):
        """ Initialises status checker. Obviously. """
        self.vcs_client = rabbitvcs.vcs.create_vcs_instance()
        self.conditions_dict_cache = {}

    def check_status(self, path, recurse, summary, invalidate):
        """ Performs a status check, blocking until the check is done.
        """
        path_status = self.vcs_client.status(path, summary, invalidate)
        return path_status
    
    def generate_menu_conditions(self, paths, invalidate=False):
        from rabbitvcs.util.contextmenu import MainContextMenuConditions
        
        conditions = MainContextMenuConditions(self.vcs_client, paths)
        return conditions.path_dict
    
    def extra_info(self):
        return None
    
    def get_memory_usage(self):
        """ Returns any additional memory of any subprocesses used by this
        checker. In other words, DO NOT return the memory usage of THIS process! 
        """
        return 0
    
    def quit(self):
        # We will exit when the main process does
        pass
