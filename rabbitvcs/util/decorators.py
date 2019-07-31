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

Simple decorators (usable in Python >= 2.4).

Decorators should be named as verbs (present or paste tense).

See:

  - https://linkchecker.svn.sourceforge.net/svnroot/linkchecker/trunk/linkchecker/linkcheck/decorators.py
  - http://wiki.python.org/moin/PythonDecoratorLibrary

"""
from __future__ import absolute_import

import os

from gi.repository import GLib

import time
import warnings
import threading

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.util.decorators")

def update_func_meta(fake_func, real_func):
    """
    Set meta information (eg. __doc__) of fake function to that of the real
    function.

    @rtype: function
    @return Fake function with metadata of the real function.
    """

    fake_func.__module__ = real_func.__module__
    fake_func.__name__ = real_func.__name__
    fake_func.__doc__ = real_func.__doc__
    fake_func.__dict__.update(real_func.__dict__)

    return fake_func

def deprecated(func):
    """
    A decorator which can be used to mark functions as deprecated.
    It emits a warning when the function is called.

    @type   func: function
    @param  func: The function to be designated as deprecated.
    """

    def newfunc(*args, **kwargs):
        """
        Print deprecated warning and execute original function.
        """
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)

    return update_func_meta(newfunc, func)

def timeit(func):
    """
    This is a decorator which times a function and prints the time it took in
    milliseconds to stdout.

    Based on the timeit function from LinkChecker.

    @type   func: function
    @param  func: The function to be timed.

    """

    def newfunc(*args, **kwargs):
        """Execute function and print execution time."""
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start_time) * 1000.0
        log.info("%s() took %0.4f milliseconds" % (func.__name__, duration))
        return result

    return update_func_meta(newfunc, func)

def disable(func):
    """
    Disable a function.

    @type   func: function
    @param  func: The function to be disabled.

    """

    def newfunc(*args, **kwargs):
        return

    return update_func_meta(newfunc, func)

def gtk_unsafe(func):
    """
    Used to wrap a function that makes calls to GTK from a thread in
    the main thread's idle loop.
    """

    from rabbitvcs.util import helper

    def newfunc(*args, **kwargs):
        return helper.run_in_main_thread(func, *args, **kwargs)

    return update_func_meta(newfunc, func)

def debug_calls(caller_log, show_caller=False):
    """
    Given a log to write messages to, wrap a function and log its invocation
    and return. Use like:

    @debug_calls(my_modules_log)
    def actual_function(...):
        ...

    Warning: do not use with DBUS decorated methods, as this will play havoc
    with introspection.
    """

    # We need a function within a function to be able to use the log argument.
    def real_debug(func):

        def newfunc(*args, **kwargs):
            caller_log.debug("Calling: %s (%s)" %
                                (func.__name__,
                                 threading.currentThread().getName()))

            result = func(*args, **kwargs)
            caller_log.debug("Returned: %s (%s)" %
                                (func.__name__,
                                 threading.currentThread().getName()))
            return result

        return update_func_meta(newfunc, func)

    return real_debug

def structure_map(func):
    """
    Descend recursively into object if it is a list, a tuple, a set or a dict
    and build the equivalent structure with func results.
    Do not apply function to None.
    """
    def newfunc(obj, *args, **kwargs):
        if obj is None:
            return obj
        if isinstance(obj, list):
            return [newfunc(item, *args, **kwargs) for item in obj]
        if isinstance(obj, tuple):
            return tuple(newfunc(item, *args, **kwargs) for item in obj)
        if isinstance(obj, set):
            return {newfunc(item, *args, **kwargs) for item in obj}
        if isinstance(obj, dict):
            return {key: newfunc(obj[key], *args, **kwargs) for key in obj}
        return func(obj, *args, **kwargs)

    return update_func_meta(newfunc, func)
