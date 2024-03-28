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

All sorts of helper functions.

"""
from __future__ import absolute_import

from collections import deque
import locale
import os
import os.path
import sys
import subprocess
import re
import datetime
import time
import shutil
import hashlib
import threading
import codecs

from gi.repository import GLib

import six
from six.moves import filter
from six.moves import range
import six.moves.urllib.parse

from rabbitvcs.util.settings import *
from rabbitvcs.util.decorators import structure_map
from rabbitvcs.util.strings import *

from rabbitvcs.util.log import Log

log = Log("rabbitvcs.util.helper")

from rabbitvcs import gettext

ngettext = gettext.ngettext

try:
    from html import escape as html_escape
except ImportError:
    from cgi import escape as html_escape

import gi
from gi.repository import GObject

from rabbitvcs import gettext

_ = gettext.gettext

LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M"  # for log files

DT_FORMAT_TIME = _("%I:%M%P")
DT_FORMAT_THISWEEK = _("%a %I:%M%p")
DT_FORMAT_THISYEAR = _("%b %d")
DT_FORMAT_ALL = _("%b %d %Y")

LINE_BREAK_CHAR = six.unichr(0x23CE)


def compare_version(version1, version2, length=None):
    if not length:
        length = max(len(version1), len(version2))
    for i in range(length):
        x = int(version1[i]) if i in version1 else 0
        y = int(version2[i]) if i in version2 else 0
        r = x - y
        if r:
            return r
    return 0


def gobject_threads_init():
    """
    Call GObject.threads_init() only if not deprecated.
    """

    if compare_version(GObject.pygobject_version, [3, 10, 2]) < 0:
        GObject.threads_init()


@structure_map
def to_bytes(s, encoding=UTF8_ENCODING):
    """
    Convert string (whatever type it is) to bytes in the given encoding.
    """
    if isinstance(s, six.text_type):
        return S(s).bytes(encoding)
    if isinstance(s, bytearray):
        if encoding.lower() == UTF8_ENCODING:
            return s
        return bytearray(S(s).bytes(encoding))
    if isinstance(s, bytes) and encoding.lower() != UTF8_ENCODING:
        return S(s).bytes(encoding)
    return s


def run_in_main_thread(func, *args, **kwargs):
    """
    Execute function in main thread's idle loop.
    """

    def dofunc(event, func, args, kwargs):
        try:
            event.result = func(*args, **kwargs)
        except Exception as e:
            event.exception = e
        event.set()

    if isinstance(threading.current_thread(), threading._MainThread):
        return func(*args, **kwargs)
    event = threading.Event()
    event.result = None
    event.exception = None
    GLib.idle_add(dofunc, event, func, args, kwargs)
    event.wait()
    if event.exception:
        raise event.exception
    return event.result


def get_tmp_path(filename):
    day = datetime.datetime.now().day
    day_string = S(str(day) + str(os.geteuid())).bytes()
    m = hashlib.md5(day_string).hexdigest()[0:10]

    tmpdir = "/tmp/rabbitvcs-%s" % m
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)

    return "%s/%s" % (tmpdir, filename)


def process_memory(pid):
    # ps -p 5205 -w -w -o rss --no-headers
    psproc = subprocess.Popen(
        [
            "ps",
            "-p",
            str(pid),
            "-w",
            "-w",  # Extra-wide format
            "-o",
            "size",  # "Size" is probably the best all round
            # memory measure.
            "--no-headers",
        ],
        stdout=subprocess.PIPE,
    )

    (output, stdin) = psproc.communicate()

    mem_in_kb = 0

    try:
        mem_in_kb = int(output)
    except ValueError:
        pass

    # log.debug("Memory for %i: %i" % (pid, mem_in_kb))

    return mem_in_kb


def format_long_text(text, cols=None, line1only=False):
    """Nicely formats text containing linebreaks to display in a single line
    by replacing newlines with U+23CE, or keeping only the first non-empty
    line. If the param "cols" is given, the text
    beyond cols is replaced by "...".
    """
    text = S(text.strip()).unicode().replace(six.u("\n"), LINE_BREAK_CHAR)
    if line1only:
        i = text.find(LINE_BREAK_CHAR)
        if i >= 0:
            text = text[:i]
    if cols and len(text) > cols:
        text = six.u("%s...") % text[0:cols]

    return text


def format_datetime(dt, format=None):
    if format:
        return S(dt.strftime(format), None).unicode()

    now = datetime.datetime.now()
    delta = now - dt

    returner = ""
    if dt.year == 1900:
        returner = _("(no date)")
    else:
        if delta.days == 0:
            if delta.seconds < 60:
                returner = _("just now")
            elif delta.seconds >= 60 and delta.seconds < 600:
                returner = _("%d minute(s) ago") % (delta.seconds / 60)
            elif delta.seconds >= 600 and delta.seconds < 43200:
                returner = dt.strftime(DT_FORMAT_TIME)
            else:
                returner = dt.strftime(DT_FORMAT_THISWEEK)
        elif delta.days > 0 and delta.days < 7:
            returner = dt.strftime(DT_FORMAT_THISWEEK)
        elif delta.days >= 7 and delta.days < 365:
            returner = dt.strftime(DT_FORMAT_THISYEAR)
        else:
            returner = dt.strftime(DT_FORMAT_ALL)

    return S(returner).unicode()


def in_rich_compare(item, list):
    """Tests whether the item is in the given list. This is mainly to work
    around the rich-compare bug in pysvn. This is not identical to the "in"
    operator when used for substring testing.
    """

    in_list = False

    if list is not None:
        for thing in list:
            try:
                in_list = item == thing
            except AttributeError as e:
                pass

    return in_list


def get_user_path():
    """
    Returns the location of the user's home directory.
    /home/$USER

    @rtype:     string
    @return:    The location of the user's home directory.

    """

    return os.path.abspath(os.path.expanduser("~"))


def get_repository_paths_path():
    """
    Returns a valid URI for the repository paths file

    @rtype:     string
    @return:    The location of the repository paths file.

    """
    return os.path.join(get_home_folder(), "repos_paths")


def get_repository_paths():
    """
    Gets all previous repository paths stored in the user's home folder

    @rtype:     list
    @return:    A list of previously used repository paths.

    """

    returner = []
    paths_file = get_repository_paths_path()
    if os.path.exists(paths_file):
        returner = [x.strip() for x in open(paths_file, "r").readlines()]

    return returner


def get_previous_messages_path():
    """
    Returns a valid URI for the previous messages file

    @rtype:     string
    @return:    The location of the previous messages file.

    """

    return os.path.join(get_home_folder(), "previous_log_messages")


def get_previous_messages():
    """
    Gets all previous messages stored in the user's home folder

    @rtype:     list
    @return:    A list of previous used messages.

    """

    path = get_previous_messages_path()
    if not os.path.exists(path):
        return

    lines = open(path, "r").readlines()

    cur_entry = ""
    returner = []
    date = None
    msg = ""
    regex = re.compile(r"-- ([\d\-]+ [\d\:]+) --")
    for line in lines:
        m = regex.match(line)
        if m:
            cur_entry = m.groups()[0]
            if date:
                returner.append((date, msg.rstrip()))
                msg = ""
            date = cur_entry
        else:
            msg += line

    if date and msg:
        returner.append((date, msg.rstrip()))

    returner.reverse()

    return returner


def get_exclude_paths_path():
    return os.path.join(get_home_folder(), "exclude_paths")


def get_exclude_paths():
    path = get_exclude_paths_path()
    if not os.path.exists(path):
        return []

    f = open(path, "r")
    paths = []
    for l in f:
        paths.append(l.strip())
    f.close()

    return paths


def encode_revisions(revision_array):
    """
    Takes a list of integer revision numbers and converts to a TortoiseSVN-like
    format. This means we have to determine what numbers are consecutives and
    collapse them into a single element (see doctest below for an example).

    @type revision_array:   list of integers
    @param revision_array:  A list of revision numbers.

    @rtype:                 string
    @return                 A string of revision numbers in TortoiseSVN-like format.

    >>> encode_revisions([4,5,7,9,10,11,12])
    '4-5,7,9-12'

    >>> encode_revisions([])
    ''

    >>> encode_revisions([1])
    '1'
    """

    # Let's get a couple of cases out of the way
    if len(revision_array) == 0:
        return ""

    if len(revision_array) == 1:
        return str(revision_array[0])

    # Instead of repeating a set of statements we'll just define them as an
    # inner function.
    def append(start, last, list):
        if start == last:
            result = "%s" % start
        else:
            result = "%s-%s" % (start, last)

        list.append(result)

    # We need a couple of variables outside of the loop
    start = revision_array[0]
    last = revision_array[0]
    current_position = 0
    returner = []

    while True:
        if current_position + 1 >= len(revision_array):
            append(start, last, returner)
            break

        current = revision_array[current_position]
        next = revision_array[current_position + 1]

        if not current + 1 == next:
            append(start, last, returner)
            start = next
            last = next

        last = next
        current_position += 1

    return ",".join(returner)


def decode_revisions(string, head):
    """
    Takes a TortoiseSVN-like revision string and returns a list of integers.
    EX. 4-5,7,9-12 -> [4,5,7,9,10,11,12]

    TODO: This function is a first draft.  It may not be production-worthy.
    """
    returner = []
    arr = string.split(",")
    for el in arr:
        if el.find("-") != -1:
            subarr = el.split("-")
            if subarr[1] == "HEAD":
                subarr[1] = head
            for subel in range(int(subarr[0]), int(subarr[1]) + 1):
                returner.append(subel)
        else:
            returner.append(int(el))

    return returner


def get_diff_tool():
    """
    Gets the path to the diff_tool, and whether or not to swap lhs/rhs.

    @rtype:     dictionary
    @return:    A dictionary with the diff tool path and swap boolean value.
    """

    sm = SettingsManager()
    diff_tool = sm.get("external", "diff_tool")
    diff_tool_swap = sm.get("external", "diff_tool_swap")

    return {"path": diff_tool, "swap": diff_tool_swap}


def get_merge_tool():
    """
    Gets the path to the merge_tool.

    @rtype:     string
    @return:    A string with the path and arguments to launch the merge tool.
    """

    sm = SettingsManager()
    return sm.get("external", "merge_tool")


def launch_diff_tool(path1, path2=None):
    """
    Launches the diff tool of choice.

      1.  Generate a standard diff between the path and the latest revision.
      2.  Write the diff text to a tmp file
      3.  Copy the given file (path) to the tmp directory
      4.  Do a reverse patch to get a version of the file that is in the repo.
      5.  Now you have two files and you can send them to the diff tool.

    @type   paths: list
    @param  paths: Paths to the given files

    """

    diff = get_diff_tool()

    if diff["path"] == "":
        return

    if not os.path.exists(diff["path"]):
        return

    # If path2 is set, that means we are comparing one file/folder to another
    if path2 is not None:
        (lhs, rhs) = (path1, path2)
    else:
        tmp_path = get_tmp_path(os.path.split(path1)[-1])
        os.popen(
            "svn export --force -r BASE '%s' '%s'" % (path1, os.path.dirname(tmp_path))
        )
        (lhs, rhs) = (tmp_path, path1)

    if diff["swap"]:
        (lhs, rhs) = (rhs, lhs)

    os.spawnl(os.P_NOWAIT, diff["path"], diff["path"], lhs, rhs)


def launch_merge_tool(base="", mine="", theirs="", merged=""):
    merge_tool = get_merge_tool()

    if (
        mine == None
        or mine == ""
        or not os.path.exists(mine)
        or theirs == None
        or theirs == ""
        or not os.path.exists(theirs)
    ):
        return

    if "%base" in merge_tool:
        merge_tool = merge_tool.replace("%base", base)

    if "%mine" in merge_tool:
        merge_tool = merge_tool.replace("%mine", mine)

    if "%theirs" in merge_tool:
        merge_tool = merge_tool.replace("%theirs", theirs)

    if "%merged" in merge_tool:
        merge_tool = merge_tool.replace("%merged", merged)

    log.debug("merge_tool: %s" % merge_tool)
    os.popen(merge_tool)


def get_file_extension(path):
    """
    Wrapper that retrieves a file path's extension.

    @type   path:   string
    @param  path:   A filename or path.

    @rtype:         string
    @return:        A file extension.

    """
    return os.path.splitext(path)[1]


def open_item(path):
    """
    Use GNOME default opener to handle file opening.

    @type   path: string
    @param  path: A file path.

    """

    if path == "" or path is None:
        return

    openers = []

    import platform

    if platform.system() == "Darwin":
        openers.append("open")
        subprocess.Popen(["open", os.path.abspath(path)])
    else:
        openers.append("gio")
        openers.append("gvfs-open")
        openers.append("xdg-open")

    for o in openers:
        for p in set(os.environ["PATH"].split(":")):
            if os.path.exists("%s/%s" % (p, o)):
                command = [o]
                if o == "gio":
                    command.append("open")
                command.append(os.path.abspath(path))

                subprocess.Popen(command)
                return


def browse_to_item(path):
    """
    Browse to the specified path in the file manager

    @type   path: string
    @param  path: A file path.

    """

    import platform

    if platform.system() == "Darwin":
        subprocess.Popen(["open", "--reveal", os.path.dirname(os.path.abspath(path))])
    else:
        subprocess.Popen(
            [
                "nautilus",
                "--no-desktop",
                "--browser",
                os.path.dirname(os.path.abspath(path)),
            ]
        )


def delete_item(path):
    """
    Send an item to the trash.

    @type   path: string
    @param  path: A file path.
    """

    abspath = os.path.abspath(path)
    permanent_delete = False
    try:

        import platform

        if platform.system() == "Darwin":
            retcode = subprocess.call(["mv", abspath, os.getenv("HOME") + "/.Trash"])
            if retcode:
                permanent_delete = True
        else:
            # If the gvfs-trash program is not found, an OSError exception will
            # be thrown, and rm will be used instead
            retcode = subprocess.call(["gio trash", abspath])
            if retcode:
                permanent_delete = True
    except OSError:
        permanent_delete = True

    if permanent_delete:
        if os.path.isdir(abspath):
            shutil.rmtree(abspath, True)
        else:
            os.remove(abspath)


def save_log_message(message):
    """
    Saves a log message to the user's home folder for later usage

    @type   message: string
    @param  message: A log message.

    """

    messages = []
    path = get_previous_messages_path()
    if os.path.exists(path):
        limit = get_log_messages_limit()
        messages = get_previous_messages()

        # If the current message already exists, delete the old one
        # The new one will take it's place at the top
        tmp = []
        for i, m in enumerate(messages):
            if message != m[1]:
                tmp.append(m)

        messages = tmp

        # Don't allow the number of messages to pile up past the limit
        while len(messages) > limit:
            messages.pop()

    t = time.strftime(LOG_DATETIME_FORMAT)
    messages.insert(0, (t, message))

    f = open(get_previous_messages_path(), "w")
    s = ""
    for m in messages:
        s = """\
-- %s --
%s
%s
""" % (
            m[0],
            m[1],
            s,
        )

    f.write(s)
    f.close()


def save_repository_path(path):
    """
    Saves a repository path to the user's home folder for later usage
    If the given path has already been saved, remove the old one from the list
    and append the new one to the end.

    @type   path: string
    @param  path: A repository path.

    """

    paths = get_repository_paths()
    if path in paths:
        paths.pop(paths.index(path))
    paths.insert(0, path)

    limit = get_repository_paths_limit()
    while len(paths) > limit:
        paths.pop()

    f = open(get_repository_paths_path(), "w")
    f.write(S("\n".join(paths)))
    f.close()


def launch_ui_window(filename, args=[], block=False):
    """
    Launches a UI window in a new process, so that we don't have to worry about
    nautilus and threading.

    @type   filename:   string
    @param  filename:   The filename of the window, without the extension

    @type   args:       list
    @param  args:       A list of arguments to be passed to the window.

    @rtype:             integer
    @return:            The pid of the process (if launched)
    """

    # Hackish.  Get's the helper module's path, then assumes it is in
    # the lib folder.  Removes the /lib part of the path.
    basedir, head = os.path.split(os.path.dirname(os.path.realpath(__file__)))

    if not head == "util":
        log.warning('Helper module (%s) not in "util" dir' % __file__)

    # Puts the whole path together.
    # path = "%s/ui/%s.py" % (basedir, filename)
    path = os.path.join(basedir, "ui", filename + ".py")

    if os.path.exists(path):
        executable = sys.executable
        if "PYTHON" in list(os.environ.keys()):
            executable = os.environ["PYTHON"]
        # Give all subprocesses the name 'RabbitVCS' to give Ubuntu desktop files the possibility
        # to group those windows in the launcher on WM_CLASS.
        proc = subprocess.Popen([executable, path] + ["--name", "RabbitVCS"] + args)

        if block:
            proc.wait()

        return proc
    else:
        return None


def get_log_messages_limit():
    sm = SettingsManager()
    return int(sm.get("cache", "number_messages"))


def get_repository_paths_limit():
    sm = SettingsManager()
    return int(sm.get("cache", "number_repositories"))


def get_common_directory(paths):
    common = os.path.commonprefix(abspaths(paths))

    while not os.path.exists(common) or os.path.isfile(common):
        common = os.path.split(common)[0]

        if common == "":
            break

    return common


def abspaths(paths):
    index = 0
    for path in paths:
        paths[index] = os.path.realpath(os.path.abspath(path))
        index += 1

    return paths


def pretty_timedelta(time1, time2, resolution=None):
    """
    Calculate time delta between two C{datetime} objects.
    (the result is somewhat imprecise, only use for prettyprinting).

    Was originally based on the function pretty_timedelta from:
        http://trac.edgewall.org/browser/trunk/trac/util/datefmt.py
    """

    if time1 > time2:
        time2, time1 = time1, time2
    diff = time2 - time1
    age_s = int(diff.days * 86400 + diff.seconds)
    if resolution and age_s < resolution:
        return ""

    # I do not see a way to make this less repetitive - to make the
    # strings fully translatable (i.e. also for languages that have more
    # or less than two plural forms) we have to state all the strings
    # explicitely within an ngettext call
    if age_s <= 60 * 1.9:
        return ngettext("%i second", "%i seconds", age_s) % age_s
    elif age_s <= 3600 * 1.9:
        r = age_s / 60
        return ngettext("%i minute", "%i minutes", r) % r
    elif age_s <= 3600 * 24 * 1.9:
        r = age_s / 3600
        return ngettext("%i hour", "%i hours", r) % r
    elif age_s <= 3600 * 24 * 7 * 1.9:
        r = age_s / (3600 * 24)
        return ngettext("%i day", "%i days", r) % r
    elif age_s <= 3600 * 24 * 30 * 1.9:
        r = age_s / (3600 * 24 * 7)
        return ngettext("%i week", "%i weeks", r) % r
    elif age_s <= 3600 * 24 * 365 * 1.9:
        r = age_s / (3600 * 24 * 30)
        return ngettext("%i month", "%i months", r) % r
    else:
        r = age_s / (3600 * 24 * 365)
        return ngettext("%i year", "%i years", r) % r


def utc_offset(timestamp=None):
    """
    Compute the UTC offset of current locale for a timestamp in a
    portable way, taking care of daylight saving. Positive is east of
    Greenwich. Result in seconds. If no timestamp is given, the current
    time is used.
    """

    if timestamp is None:
        timestamp = time.time()

    timestamp = int(timestamp)
    utc = datetime.datetime.utcfromtimestamp(timestamp)
    local = datetime.datetime.fromtimestamp(timestamp)
    return int((local - utc).total_seconds())


def _commonpath(l1, l2, common=[]):
    """
    Helper method for the get_relative_path method
    """
    if len(l1) < 1:
        return (common, l1, l2)
    if len(l2) < 1:
        return (common, l1, l2)
    if l1[0] != l2[0]:
        return (common, l1, l2)
    return _commonpath(l1[1:], l2[1:], common + [l1[0]])


def get_relative_path(from_path, to_path):
    """
    Method that returns the relative path between the specified paths
    """

    nice_path1 = from_path.rstrip(os.path.sep).split(os.path.sep)
    nice_path2 = to_path.rstrip(os.path.sep).split(os.path.sep)

    (common, l1, l2) = _commonpath(nice_path1, nice_path2)

    p = []
    if len(l1) > 0:
        p = [".."] * len(l1)
    p = p + l2

    return os.sep.join(p)


def launch_repo_browser(uri):
    sm = SettingsManager()
    repo_browser = sm.get("external", "repo_browser")

    if repo_browser is not None:
        subprocess.Popen([repo_browser, uri])


def launch_url_in_webbrowser(url):
    import webbrowser

    webbrowser.open(url)


def parse_path_revision_string(pathrev):
    index = pathrev.rfind("@")
    if index == -1:
        return (pathrev, None)
    else:
        return (pathrev[0:index], pathrev[index + 1 :])


def create_path_revision_string(path, revision=None):
    if revision:
        return path + "@" + str(revision)
    else:
        return path


def url_join(path, *args):
    return "/".join([path.rstrip("/")] + list(args))


def _quote(text):
    return six.moves.urllib.parse.quote(
        text, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE
    )


def _quote_plus(text):
    return six.moves.urllib.parse.quote_plus(
        text, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE
    )


def _unquote(text):
    return six.moves.urllib.parse.unquote(
        text, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE
    )


def _unquote_plus(text):
    return six.moves.urllib.parse.unquote_plus(
        text, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE
    )


quote = _quote
quote_plus = _quote_plus
unquote = _unquote
unquote_plus = _unquote_plus

try:
    unquote("")
except TypeError:
    quote = six.moves.urllib.parse.quote
    quote_plus = six.moves.urllib.parse.quote_plus
    unquote = six.moves.urllib.parse.unquote
    unquote_plus = six.moves.urllib.parse.unquote_plus


def quote_url(url_text):
    (scheme, netloc, path, params, query, fragment) = six.moves.urllib.parse.urlparse(
        url_text
    )
    # netloc_quoted = quote(netloc)
    path_quoted = quote(path)
    params_quoted = quote(params)
    query_quoted = quote_plus(query)
    fragment_quoted = quote(fragment)

    url_quoted = six.moves.urllib.parse.urlunparse(
        (scheme, netloc, path_quoted, params_quoted, query_quoted, fragment_quoted)
    )

    return url_quoted


def unquote_url(url_text):
    (scheme, netloc, path, params, query, fragment) = six.moves.urllib.parse.urlparse(
        url_text
    )
    # netloc_unquoted = unquote(netloc)
    path_unquoted = unquote(path)
    params_unquoted = unquote(params)
    query_unquoted = unquote_plus(query)
    fragment_unquoted = unquote(fragment)

    url_unquoted = six.moves.urllib.parse.urlunparse(
        (
            scheme,
            netloc,
            path_unquoted,
            params_unquoted,
            query_unquoted,
            fragment_unquoted,
        )
    )

    return url_unquoted


def pretty_filesize(bytes):
    if bytes >= 1073741824:
        return str(int(bytes / 1073741824)) + " GB"
    elif bytes >= 1048576:
        return str(int(bytes / 1048576)) + " MB"
    elif bytes >= 1024:
        return str(int(bytes / 1024)) + " KB"
    elif bytes < 1024:
        return str(bytes) + " bytes"


def get_node_kind(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            return "file"
        else:
            return "dir"

    return "none"


def walk_tree_depth_first(
    tree, show_levels=False, preprocess=None, filter=None, start=None
):
    """
    A non-recursive generator function that walks through a tree (and all
    children) yielding results.

    The tree should be of the form:
      [(NodeOne, None),
       (NodeTwo,
         [(Node2A, None),
          (Node2B, None),
          (Node2C,
            [(Node2C1, None), etc]
         ]
       (NodeThree, None),
        etc...]

    If show_levels is True, the values returned are (level, value) where level
    is zero for the top level items in the tree. Otherwise, just "value" is
    returned.

    If a callable "preprocess" is supplied, it is applied BEFORE the filter,
    as each element is encountered.

    If a callable "filter" is supplied, it is applied to whatever "preprocess"
    returned, and if it returns False for an item, the item and its children
    will be skipped.

    If "start" is given, the walk will be applied only to that node and its
    children. No preprocessing or filtering will be applied to other elements.
    """
    annotated_tree = [(0, element) for element in tree]

    to_process = deque(annotated_tree)

    # If we're not given a starting point, the top is the start
    found_starting_point = not start

    while to_process:
        (level, (node, children)) = to_process.popleft()

        if not found_starting_point and (node == start):
            # If we're given a starting point and we've found it, clear the list
            # and start from here
            found_starting_point = True
            level = 0
            to_process.clear()

        # This should NOT be an else case, since we may have just set this flag
        # to "True" above.
        if found_starting_point:
            if preprocess:
                value = preprocess(node)
            else:
                value = node

            if filter and not filter(value):
                continue

            if show_levels:
                yield (level, value)
            else:
                yield value

        if children:
            annotated_children = [(level + 1, child) for child in children]
            annotated_children.reverse()
            to_process.extendleft(annotated_children)


def urlize(path):
    if path.startswith("/"):
        return "file://%s" % path
    return path


def parse_patch_output(patch_file, base_dir, strip=0):
    """Runs the GNU 'patch' utility, parsing the output. This is actually a
    generator which yields values as each section of the patch is applied.

    @param patch_file: the location of the patch file
    @type patch_file: string

    @param base_dir: the directory in which to apply the patch
    @type base_dir: string

    @return: a generator yielding tuples (filename, success, reject_file).
             "filename" is never None, and should always exist. "success" is
             True iff the patch executed without any error messages.
             "reject_file" may be None, but if it exists is the location of
             rejected "hunks". It's like a bad reality TV dating show.
    """

    PATCHING_RE = re.compile(r"patching file (.*)")
    REJECT_RE = re.compile(r".*saving rejects to file (.*)")

    # PATCH flags...
    # -N: always assume forward diff
    # -t: batch mode:
    #    skip patches whose headers do not contain file
    #    names (the same as -f); skip patches for which
    #    the file has the wrong version for the Prereq:
    #    line in the patch; and assume that patches are
    #    reversed if they look like they are.
    env = os.environ.copy().update({"LC_ALL": "C"})
    p = "-p%s" % strip
    patch_proc = subprocess.Popen(
        ["patch", "-N", "-t", p, "-i", str(patch_file), "--directory", base_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )

    # Intialise things...
    out = codecs.getreader(UTF8_ENCODING)(patch_proc.stdout, SURROGATE_ESCAPE)
    line = out.readline()
    patch_match = PATCHING_RE.match(line)

    current_file = None
    if patch_match:
        current_file = patch_match.group(1)
    elif line:  # and not patch_match
        # There was output, but unexpected. Almost certainly an error of some
        # sort.
        patch_proc.wait()
        output = line + out.read()
        raise rabbitvcs.vcs.ExternalUtilError("patch", output)
        # Note the excluded case: empty line. This falls through, skips the loop
        # and returns.

    any_errors = False
    reject_file = None

    while current_file:

        line = out.readline().rstrip(" \t\r\n")
        while not line and patch_proc.poll() is None:
            line = out.readline().rstrip(" \t\r\n")

        # Does patch tell us we're starting a new file?
        patch_match = PATCHING_RE.match(line)

        # Starting a new file => that's it for the last one, so return the value
        # No line => End of patch output => ditto
        if patch_match or not line:

            yield (current_file, not any_errors, reject_file)

            if not line:
                # That's it from patch, so end the generator
                break

            # Starting a new file...
            current_file = patch_match.group(1)
            any_errors = False
            reject_file = None

        else:
            # Doesn't matter why we're here, anything else means ERROR

            any_errors = True

            reject_match = REJECT_RE.match(line)

            if reject_match:
                # Have current file, getting reject file info
                reject_file = reject_match.group(1)
            # else: we have an unknown error

    patch_proc.wait()  # Don't leave process running...
    return


def HSLtoRGB(h, s, l):
    """
    Convert a color from the HSL space to RGB.

    @type   h: (int, float)
    @param  h: Hue in degrees.

    @type   s: float
    @param  s: Saturation in range 0.0 to 1.0

    @type   l: float
    @param  l: Luminance in range 0.0 to 1.0
    """

    if not 0.0 <= s <= 1.0:
        raise ValueError("Saturation should be >= 0.0 and <= 1.0")
    if not 0.0 <= l <= 1.0:
        raise ValueError("Luminance should be >= 0.0 and <= 1.0")

    if s == 0.0:
        return (0, 0, 0)

    sextant = h % 360.0 / 60.0
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = (1.0 - abs(sextant % 2.0 - 1.0)) * c
    m = l - c / 2.0
    i = int(sextant)
    r = [c, x, 0.0, 0.0, x, c][i]
    g = [x, c, c, x, 0.0, 0.0][i]
    b = [0.0, 0.0, x, c, c, x][i]
    return (int((v + m) * 255.0) for v in (r, g, b))


def html_color(r, g, b, a=None):
    fmt = "%02X"
    alpha = a or 0
    if r < 0x10 and g < 0x10 and b < 0x10 and alpha < 0x10:
        fmt = "%01X"
    color = (fmt * 3) % (r, g, b)
    if not a is None:
        color += fmt % a
    return "#" + color


"""
In Python 3, Gdk.init_check() encodes sys.argv without handling surrogates,
causing an UnicodeEncodeError exception while importing Gdk.
The following class implements a mechanism to avoid that:
- The first Gdk import performed by a program should be preceded by
  a SanitizeArgv object creation.
- After Gdk import, call this object's method restore().
For this reason, the current module MAY NOT import Gdk, directly or
indirectly.
"""


class SanitizeArgv(object):
    def __init__(self):
        self.argmap = None
        if len(sys.argv) and isinstance(sys.argv[0], six.text_type):
            argmap = []
            newargv = []
            for arg in sys.argv:
                newarg = S(arg).display()
                newargv.append(newarg)
                argmap.append((newarg, arg))
                if arg != newarg:
                    self.argmap = argmap
            if self.argmap:
                sys.argv = newargv

    def restore(self):
        if self.argmap:
            newargv = []
            i = 0
            for arg in sys.argv:
                while arg != self.argmap[i][0]:
                    i += 1
                newargv.append(self.argmap[i][1])
                i += 1
            sys.argv = newargv
