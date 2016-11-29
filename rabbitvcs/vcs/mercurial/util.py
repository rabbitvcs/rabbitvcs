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

import os

def splitall(path):
    """Split a path into all of its parts.

    From: Python Cookbook, Credit: Trent Mick
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def relativepath(fromdir, tofile):
    """Find relative path from 'fromdir' to 'tofile'.

    An absolute path is returned if 'fromdir' and 'tofile'
    are on different drives. Martin Bless, 2004-03-22.
    """
    f1name = os.path.abspath(tofile)
    if os.path.splitdrive(f1name)[0]:
        hasdrive = True
    else:
        hasdrive = False
    f1basename = os.path.basename(tofile)
    f1dirname = os.path.dirname(f1name)
    f2dirname = os.path.abspath(fromdir)
    f1parts = splitall(f1dirname)
    f2parts = splitall(f2dirname)
    if hasdrive and (f1parts[0].lower() != f2parts[0].lower()):
        "Return absolute path since we are on different drives."
        return f1name
    while f1parts and f2parts:
        if hasdrive:
            if f1parts[0].lower() != f2parts[0].lower():
                break
        else:
            if f1parts[0] != f2parts[0]:
                break
        del f1parts[0]
        del f2parts[0]
    result = ['..' for part in f2parts]
    result.extend(f1parts)
    result.append(f1basename)
    return os.sep.join(result)
