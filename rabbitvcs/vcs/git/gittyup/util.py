from __future__ import absolute_import
#
# util.py
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

def get_transport_and_path(uri):
    from dulwich.client import TCPGitClient, SSHGitClient, SubprocessGitClient
    for handler, transport in (("git://", TCPGitClient), ("git+ssh://", SSHGitClient)):
        if uri.startswith(handler):
            host, path = uri[len(handler):].split("/", 1)
            return transport(host), "/"+path
    # if its not git or git+ssh, try a local url..
    return SubprocessGitClient(), uri
