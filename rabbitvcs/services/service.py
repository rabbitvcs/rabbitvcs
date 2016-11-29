#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
# Copyright (C) 2009 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2009 by Adam Plumb <adamplumb@gmail.com>#
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

""" Simple utility module for starting DBUS services.

This module contains helper functions for starting DBUS services. Usually they
would be used from within a constructor.
"""
from __future__ import absolute_import

import sys
import subprocess

import dbus

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.service")

def start_service(script_file, dbus_service_name, dbus_object_path):
    """
    This function is used to start a service that exports a DBUS object. If the
    DBUS object can be found already, nothing is done and the function returns
    True. Otherwise we try to start the given script file and wait until we
    receive a newline over stdout. 
    
    The "wait for newline" mechanism ensures any function calling this one will
    not try to access the object via DBUS until it is ready. It is recommended
    to use something like
    
    glib.idle_add(sys.stdout.write, "Started service\n")
    glib.idle_add(sys.stdout.flush)
    mainloop.run()
 
    That way a newline will be sent when the mainloop is started.
    
    @param script_file: the Python script file to run if the DBUS object does
                        not already exist
    @type script_file: a Python script file that will create the DBUS object and
                       send a newline over stdout when it is ready
                       
    @param dbus_service_name: the name of the DBUS service to request
    @type dbus_service_name: string (confirming to the DBUS service format)

    @param dbus_object_path: the DBUS object path to request
    @type dbus_object_path: string (confirming to the DBUS object path format)
        
    @rtype: boolean
    @return: Whether or not the service was successfully started.
    """
    
    object_exists = False
    
    try:
        session_bus = dbus.SessionBus()
        obj = session_bus.get_object(dbus_service_name, dbus_object_path)
        object_exists = True
    except dbus.DBusException:
        proc = subprocess.Popen([sys.executable, script_file],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
        pid = proc.pid
        log.debug("Started process: %i" % pid)
        
        # Wait for subprocess to send a newline, to tell us it's ready
        proc.stdout.readline() # We don't care what the message is
        object_exists = True
        
    return object_exists

