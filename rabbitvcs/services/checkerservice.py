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

""" The checker service for RabbitVCS background status checks.

This file can be run as a Python script, in which case it starts a background
VCS status checking service that can be called via DBUS. It also contains class
definitions to call these methods from within a separate Python process.

This currently works like so:

    1. Nautilus loads our extension, RabbitVCS
    2. RabbitVCS creates a StatusCheckerStub
    3. StatusCheckerStub calls start(), which is a wrapper for a more general
       service starter convenience method
    4. The service starter method looks for a DBUS object with the given service
       name and object path; if none is found, it creates it by running this
       script

RabbitVCS can then call the stub methods, getting status info via the
CheckStatus method itself, or more likely from a callback upon completion of a
status check.

NOTE: as a general rule, the data piped between processes or sent over DBUS
should be kept to a minimum. Use convenience methods to condense and summarise
data wherever possible (this is the case in the actual status cache and checker
code).
"""
from __future__ import absolute_import

import os, os.path
import sys
import simplejson
import six

try:
    from gi.repository import GObject as gobject
except ImportError:
    import gobject
    
try:
    from gi.repository import GLib as glib
except:
    import glib

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
import dbus.mainloop.glib
import dbus.service

import rabbitvcs.util.decorators
import rabbitvcs.util._locale
import rabbitvcs.util.helper
import rabbitvcs.services.service
from rabbitvcs.services.statuschecker import StatusChecker

import rabbitvcs.vcs.status

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.checkerservice")

from rabbitvcs import version as SERVICE_VERSION

INTERFACE = "org.google.code.rabbitvcs.StatusChecker"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusChecker"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS.Checker"
TIMEOUT = 60*15*100 # seconds

def find_class(module, name):
    """ Given a module name and a class name, return the actual type object.
    """
    # From Python stdlib pickle module source
    __import__(module)
    mod = sys.modules[module]
    klass = getattr(mod, name)
    return klass

def encode_status(status):
    """ Before encoding a status object to JSON, we need to turn it into
    something simpler.
    """
    return status.__getstate__()

def decode_status(json_dict):
    """ Once we get a JSON encoded string out the other side of DBUS, we need to
    reconstitute the original object. This method is based on the pickle module
    in the Python stdlib.
    """    
    cl = find_class(json_dict['__module__'], json_dict['__type__'])
    st = None
    if cl in rabbitvcs.vcs.status.STATUS_TYPES:
        st = cl.__new__(cl)
        st.__setstate__(json_dict)
    elif 'path' in json_dict:
        log.warning("Could not deduce status class: %s" % json_dict['__type__'])
        st = rabbitvcs.vcs.status.Status.status_error(json_dict['path'])
    else:
        raise TypeError("RabbitVCS status object has no path")
    return st

class StatusCheckerService(dbus.service.Object):
    """ StatusCheckerService objects wrap a StatusCheckerPlus instance,
    exporting methods that can be called via DBUS.

    There should only be a single such object running in a separate process from
    the GUI (ie. do not create this in the Nautilus extension code, you should
    use a StatusCheckerStub there instead).
    """

    def __init__(self, connection, mainloop):
        """ Creates a new status checker wrapper service, with the given DBUS
        connection.

        The mainloop argument is needed for process management (eg. calling
        Quit() for graceful exiting).

        @param connection: the DBUS connection (eg. session bus, system bus)
        @type connection: a DBUS connection object

        @param mainloop: the main loop that DBUS is using
        @type mainloop: any main loop with a quit() method
        """
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        
        self.encoder = simplejson.JSONEncoder(default=encode_status,
                                              separators=(',', ':'))
        
        self.mainloop = mainloop

        # Start the status checking daemon so we can do requests in the
        # background
        self.status_checker = StatusChecker()

    @dbus.service.method(INTERFACE)
    def ExtraInformation(self):
        return self.status_checker.extra_info()

    @dbus.service.method(INTERFACE)
    def MemoryUsage(self):
        own_mem = rabbitvcs.util.helper.process_memory(os.getpid())
        checker_mem = self.status_checker.get_memory_usage()

        return own_mem + checker_mem

    @dbus.service.method(INTERFACE)
    def PID(self):
        return os.getpid()

    @dbus.service.method(INTERFACE)
    def CheckerType(self):
        return self.status_checker.CHECKER_NAME

    @dbus.service.method(INTERFACE, in_signature='sbbb', out_signature='s')
    def CheckStatus(self, path, recurse=False, invalidate=False,
                      summary=False):
        """ Requests a status check from the underlying status checker.
        """
        status = self.status_checker.check_status(six.text_type(path),
                                                  recurse=recurse,
                                                  summary=summary,
                                                  invalidate=invalidate)
        
        return self.encoder.encode(status)

    @dbus.service.method(INTERFACE, in_signature='as', out_signature='s')
    def GenerateMenuConditions(self, paths):
        upaths = []
        for path in paths:
            upaths.append(six.text_type(path))
    
        path_dict = self.status_checker.generate_menu_conditions(upaths)
        return simplejson.dumps(path_dict)

    @dbus.service.method(INTERFACE)
    def CheckVersionOrDie(self, version):
        """
        If the version passed does not match the version of RabbitVCS available
        when this service started, the service will exit. The return value is
        None if the versions match, else it's the PID of the service (useful for
        waiting for the process to exit).
        """
        if not self.CheckVersion(version):
            log.warning("Version mismatch, quitting checker service " \
                        "(service: %s, extension: %s)" \
                        % (SERVICE_VERSION, version))
            return self.Quit()

        return None

    @dbus.service.method(INTERFACE)
    def CheckVersion(self, version):
        """
        Return True iff the version of RabbitVCS imported by this service is the
        same as that passed in (ie. used by extension code).
        """
        return version == SERVICE_VERSION

    @dbus.service.method(INTERFACE)
    def Quit(self):
        """ Quits the service, performing any necessary cleanup operations.

        You can call this from the command line with:

        dbus-send --print-reply \
        --dest=org.google.code.rabbitvcs.RabbitVCS.Checker \
        /org/google/code/rabbitvcs/StatusChecker \
        org.google.code.rabbitvcs.StatusChecker.Quit

        If calling this programmatically, then you can do "os.waitpid(pid, 0)"
        on the returned PID to prevent a zombie process.
        """
        self.status_checker.quit()
        log.debug("Quitting main loop...")
        self.mainloop.quit()
        return self.PID()


class StatusCheckerStub:
    """ StatusCheckerStub objects contain methods that call an actual status
    checker running in another process.

    These objects should be created by the GUI as needed (eg. the nautilus
    extension code).

    The inter-process communication is via DBUS.
    """

    def __init__(self):
        """ Creates an object that can call the VCS status checker via DBUS.

        If there is not already a DBUS object with the path "OBJECT_PATH", we
        create one by starting a new Python process that runs this file.
        """
        # We need this to for the client to be able to do asynchronous calls
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus()
        self.decoder = simplejson.JSONDecoder(object_hook=decode_status)
        self.status_checker = None
        start()
        self._connect_to_checker()

    def _connect_to_checker(self):

        # Start the status checker, if it's not running this should start it up.
        # Otherwise it leaves it alone.
        # start()

        # Try to get a new checker
        try:
            self.status_checker = self.session_bus.get_object(SERVICE,
                                                              OBJECT_PATH)
        except dbus.DBusException as ex:
            # There is not much we should do about this...
            log.exception(ex)

    def assert_version(self, version):
        """
        This will use the CheckVersionOrDie method to ensure that either the
        checker service currently running has the correct version, or that it
        is quit and restarted.
        
        Note that if the version of the newly started checker still doesn't
        match, nothing is done. 
        """
        try:
            pid = self.status_checker.CheckVersionOrDie(version)
        except dbus.DBusException as ex:
            log.exception(ex)
            self._connect_to_checker()
        else:
            if pid is not None:
                try:
                    os.waitpid(pid, 0)
                except OSError:
                    # Process already gone...
                    pass
                start()
                self._connect_to_checker()
                
                try:
                    if not self.status_checker.CheckVersion(version):
                        log.warning("Version mismatch even after restart!")
                except dbus.DBusException as ex:
                    log.exception(ex)
                    self._connect_to_checker()
                    

    def check_status_now(self, path, recurse=False, invalidate=False,
                       summary=False):
        
        status = None
                
        try:
            json_status = self.status_checker.CheckStatus(path,
                                                          recurse, invalidate,
                                                          summary,
                                                          dbus_interface=INTERFACE,
                                                          timeout=TIMEOUT)
            status = self.decoder.decode(json_status)
            # Test client error problems :)
            # raise dbus.DBusException("Test")
        except dbus.DBusException as ex:
            log.exception(ex)

            status = rabbitvcs.vcs.status.Status.status_error(path)

            # Try to reconnect
            self._connect_to_checker()

        return status
        
    def check_status_later(self, path, callback, recurse=False,
                           invalidate=False, summary=False):
        
        def real_reply_handler(json_status):
            # Note that this a closure referring to the outer functions callback
            # parameter
            status = self.decoder.decode(json_status)
            assert status.path == path, "Status check returned the wrong path "\
                                        "(asked about %s, got back %s)" % \
                                        (path, status.path)
            callback(status)
        
        def reply_handler(*args, **kwargs):
            # The callback should be performed as a low priority task, so we
            # keep Nautilus as responsive as possible.
            gobject.idle_add(real_reply_handler, *args, **kwargs)
        
        def error_handler(dbus_ex):
            log.exception(dbus_ex)
            self._connect_to_checker()
            callback(rabbitvcs.vcs.status.Status.status_error(path))
        
        try:
            self.status_checker.CheckStatus(path,
                                            recurse, invalidate,
                                            summary,
                                            dbus_interface=INTERFACE,
                                            timeout=TIMEOUT,
                                            reply_handler=reply_handler,
                                            error_handler=error_handler)
        except dbus.DBusException as ex:
            log.exception(ex)
            callback(rabbitvcs.vcs.status.Status.status_error(path))
            # Try to reconnect
            self._connect_to_checker()

    # @rabbitvcs.util.decorators.deprecated
    # Can't decide whether this should be deprecated or not... -JH
    def check_status(self, path, recurse=False, invalidate=False,
                       summary=False, callback=None):
        """ Check the VCS status of the given path.

        This is a pass-through method to the check_status method of the DBUS
        service (which is, in turn, a wrapper around the real status checker).
        """
        if callback:
            gobject.idle_add(self.check_status_later,
                     path, callback, recurse, invalidate, summary)
            return rabbitvcs.vcs.status.Status.status_calc(path)
        else:
            return self.check_status_now(path, recurse, invalidate, summary)

    def generate_menu_conditions(self, provider, base_dir, paths, callback):
    
        def real_reply_handler(json):
            # Note that this a closure referring to the outer functions callback
            # parameter
            path_dict = simplejson.loads(json)
            callback(provider, base_dir, paths, path_dict)
        
        def reply_handler(*args, **kwargs):
            # The callback should be performed as a low priority task, so we
            # keep Nautilus as responsive as possible.
            gobject.idle_add(real_reply_handler, *args, **kwargs)
        
        def error_handler(dbus_ex):
            log.exception(dbus_ex)
            self._connect_to_checker()
            callback(provider, base_dir, paths, {})
        
        try:
            self.status_checker.GenerateMenuConditions(paths,
                                            dbus_interface=INTERFACE,
                                            timeout=TIMEOUT,
                                            reply_handler=reply_handler,
                                            error_handler=error_handler)
        except dbus.DBusException as ex:
            log.exception(ex)
            callback(provider, base_dir, paths, {})
            # Try to reconnect
            self._connect_to_checker()

    def generate_menu_conditions_async(self, provider, base_dir, paths, callback):
        gobject.idle_add(self.generate_menu_conditions, provider, base_dir, paths, callback)
        return {}

def start():
    """ Starts the checker service, via the utility method in "service.py". """
    rabbitvcs.services.service.start_service(os.path.abspath(__file__), SERVICE,
                                             OBJECT_PATH)

def Main():
    """ The main point of entry for the checker service.

    This will set up the DBUS and glib extensions, the gobject/glib main loop,
    and start the service.
    """
    global log
    log = Log("rabbitvcs.services.checkerservice:main")
    log.debug("Checker: starting service: %s (%s)" % (OBJECT_PATH, os.getpid()))

    # We need this to for the client to be able to do asynchronous calls
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # The following calls are required to make DBus thread-aware and therefore
    # support the ability run threads.
    gobject.threads_init()
    dbus.glib.threads_init()

    # This registers our service name with the bus
    session_bus = dbus.SessionBus()
    service_name = dbus.service.BusName(SERVICE, session_bus)

    mainloop = gobject.MainLoop()

    checker_service = StatusCheckerService(session_bus, mainloop)

    gobject.idle_add(sys.stdout.write, "Started status checker service\n")
    gobject.idle_add(sys.stdout.flush)

    mainloop.run()

    log.debug("Checker: ended service: %s (%s)" % (OBJECT_PATH, os.getpid()))

if __name__ == "__main__":
    rabbitvcs.util._locale.initialize_locale()

    # import cProfile
    # import rabbitvcs.util.helper
    # profile_data_file = os.path.join(
    #                        rabbitvcs.util.helper.get_home_folder(),
    #                        "checkerservice.stats")
    # cProfile.run("Main()", profile_data_file)

    Main()
