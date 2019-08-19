#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
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
Concrete VCS implementation for Subversion functionality.
"""
from __future__ import absolute_import
import subprocess
import os
import shutil
import os.path
from os.path import isdir, isfile, dirname, islink, realpath
from datetime import datetime

import pysvn

import rabbitvcs.vcs
import rabbitvcs.vcs.status
import rabbitvcs.vcs.log
from rabbitvcs.util import helper
from rabbitvcs.util.log import Log
from rabbitvcs.util.decorators import structure_map
from rabbitvcs.util.strings import *
import six
from six.moves import map
from six.moves import range

log = Log("rabbitvcs.vcs.svn")

from rabbitvcs import gettext
_ = gettext.gettext

# Extra "action" for "commit completed"
commit_completed = "commit_completed"

@structure_map
def pure_unicode(obj):
    """
    Map object string subclass components to real unicode type.

    Pysvn (using PyCXX) does not like string subclasses as arguments and
    requires unsubclassed string/unicode objects. In addition, it fails on
    Python2 non-ascii byte strings when converting them to utf-8.
    This function is called each time there is a risk of passing string or
    unicode objects to the pysvn API.
    """
    if isinstance(obj, (six.string_types, six.text_type)):
        obj = S(obj).unicode()
    return obj


class Revision:
    """
    Implements a simple revision object as a wrapper around the pysvn revision
    object.  This allows us to provide a standard interface to the object data.
    """

    KINDS = {
        "unspecified":      pysvn.opt_revision_kind.unspecified,
        "number":           pysvn.opt_revision_kind.number,
        "date":             pysvn.opt_revision_kind.date,
        "committed":        pysvn.opt_revision_kind.committed,
        "previous":         pysvn.opt_revision_kind.previous,
        "working":          pysvn.opt_revision_kind.working,
        "head":             pysvn.opt_revision_kind.head,
        "base":             pysvn.opt_revision_kind.base
    }

    def __init__(self, kind, value=None):
        self.kind = S(kind).lower()
        self.value = value
        self.is_revision_object = True

        # TODO Shift to options factory?
        if self.value and str(self.value).lower().strip() == 'head':
            self.kind = "head"

        if self.value is None and self.kind in ("number", "date"):
            self.kind = "head"

        if self.kind == "head":
            self.value = None

        self.__revision_kind = self.KINDS[self.kind]
        self.__revision = None

        try:
            if self.value is not None:
                self.__revision = pysvn.Revision(self.__revision_kind, self.value)
            else:
                self.__revision = pysvn.Revision(self.__revision_kind)
        except Exception as e:
            log.exception(e)

    def __str__(self):
        if self.value:
            return S(self.value)
        return S(self.kind)

    def __unicode__(self):
        return self.__str__().unicode()

    def short(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def primitive(self):
        return self.__revision

class SVN:
    """

    """

    STATUS = {
        "none"          : pysvn.wc_status_kind.none,
        "unversioned"   : pysvn.wc_status_kind.unversioned,
        "normal"        : pysvn.wc_status_kind.normal,
        "added"         : pysvn.wc_status_kind.added,
        "missing"       : pysvn.wc_status_kind.missing,
        "deleted"       : pysvn.wc_status_kind.deleted,
        "replaced"      : pysvn.wc_status_kind.replaced,
        "modified"      : pysvn.wc_status_kind.modified,
        "merged"        : pysvn.wc_status_kind.merged,
        "conflicted"    : pysvn.wc_status_kind.conflicted,
        "ignored"       : pysvn.wc_status_kind.ignored,
        "obstructed"    : pysvn.wc_status_kind.obstructed,
        "external"      : pysvn.wc_status_kind.external,
        "incomplete"    : pysvn.wc_status_kind.incomplete
    }

    STATUSES_FOR_COMMIT = list(map(str,
        [
            pysvn.wc_status_kind.unversioned,
            pysvn.wc_status_kind.added,
            pysvn.wc_status_kind.deleted,
            pysvn.wc_status_kind.replaced,
            pysvn.wc_status_kind.modified,
            pysvn.wc_status_kind.missing,
            pysvn.wc_status_kind.obstructed
        ]))

    STATUSES_FOR_REVERT = list(map(str,
        [
            pysvn.wc_status_kind.missing,
            pysvn.wc_status_kind.added,
            pysvn.wc_status_kind.modified,
            pysvn.wc_status_kind.deleted
        ]))

    STATUSES_FOR_ADD = list(map(str,
        [
            pysvn.wc_status_kind.unversioned,
            pysvn.wc_status_kind.obstructed
        ]))

    STATUSES_FOR_RESOLVE = list(map(str,
        [
            pysvn.wc_status_kind.conflicted
        ]))

    STATUSES_FOR_CHECK = list(map(str,
        [
            pysvn.wc_status_kind.added,
            pysvn.wc_status_kind.deleted,
            pysvn.wc_status_kind.replaced,
            pysvn.wc_status_kind.modified,
            pysvn.wc_status_kind.missing,
            pysvn.wc_status_kind.conflicted,
        ]))

    PROPERTIES = {
        "executable":   "svn:executable",
        "mime-type":    "svn:mime-type",
        "ignore":       "svn:ignore",
        "keywords":     "svn:keywords",
        "eol-style":    "svn:eol-style",
        "externals":    "svn:externals",
        "special":      "svn:special"
    }

    NOTIFY_ACTIONS = {
        pysvn.wc_notify_action.add:                     _("Added"),
        pysvn.wc_notify_action.copy:                    _("Copied"),
        pysvn.wc_notify_action.delete:                  _("Deleted"),
        pysvn.wc_notify_action.restore:                 _("Restored"),
        pysvn.wc_notify_action.revert:                  _("Reverted"),
        pysvn.wc_notify_action.failed_revert:           _("Failed Revert"),
        pysvn.wc_notify_action.resolved:                _("Resolved"),
        pysvn.wc_notify_action.skip:                    _("Skipped"),
        pysvn.wc_notify_action.update_delete:           _("Deleted"),
        pysvn.wc_notify_action.update_add:              _("Added"),
        pysvn.wc_notify_action.update_started:          _("Updating"),
        pysvn.wc_notify_action.update_update:           _("Updated"),
        pysvn.wc_notify_action.update_completed:        _("Completed"),
        pysvn.wc_notify_action.update_external:         _("External"),
        pysvn.wc_notify_action.status_completed:        _("Completed"),
        pysvn.wc_notify_action.status_external:         _("External"),
        pysvn.wc_notify_action.commit_modified:         _("Modified"),
        pysvn.wc_notify_action.commit_added:            _("Added"),
        pysvn.wc_notify_action.commit_deleted:          _("Deleted"),
        pysvn.wc_notify_action.commit_replaced:         _("Replaced"),
        pysvn.wc_notify_action.commit_postfix_txdelta:  _("Changed"),
        pysvn.wc_notify_action.annotate_revision:       _("Annotated"),
        pysvn.wc_notify_action.locked:                  _("Locked"),
        pysvn.wc_notify_action.unlocked:                _("Unlocked"),
        pysvn.wc_notify_action.failed_lock:             _("Failed Lock"),
        pysvn.wc_notify_action.failed_unlock:           _("Failed Unlock")
    }

    NOTIFY_ACTIONS_COMPLETE = [
        pysvn.wc_notify_action.status_completed,
        pysvn.wc_notify_action.update_completed,
        commit_completed
    ]

    NOTIFY_STATES = {
        pysvn.wc_notify_state.inapplicable:             _("Inapplicable"),
        pysvn.wc_notify_state.unknown:                  _("Unknown"),
        pysvn.wc_notify_state.unchanged:                _("Unchanged"),
        pysvn.wc_notify_state.missing:                  _("Missing"),
        pysvn.wc_notify_state.obstructed:               _("Obstructed"),
        pysvn.wc_notify_state.changed:                  _("Changed"),
        pysvn.wc_notify_state.merged:                   _("Merged"),
        pysvn.wc_notify_state.conflicted:               _("Conflicted")
    }

    NODE_KINDS_REVERSE = {
        pysvn.node_kind.none: "none",
        pysvn.node_kind.file: "file",
        pysvn.node_kind.dir:  "dir",
        pysvn.node_kind.unknown: "unknown"
    }

    def __init__(self):
        self.client = pysvn.Client()
        self.interface = "pysvn"
        self.vcs = rabbitvcs.vcs.VCS_SVN
        self.cache = rabbitvcs.vcs.status.StatusCache()

    def statuses(self, path, recurse=True, update=False, invalidate=False):
        """

        Look up the status for path.

        """

        spath = S(path)
        if spath in self.cache:
            if invalidate:
                del self.cache[spath]
            else:
                return self.cache.find_path_statuses(spath)

        on_error = rabbitvcs.vcs.status.Status.status_unknown(path)

        if not self.is_in_a_or_a_working_copy(path):
            return [on_error]

        try:
            pysvn_statuses = self.client_status(path,
                                                depth=pysvn.depth.infinity,
                                                update=update)
            if not len(pysvn_statuses):
                # This is NOT in the PySVN documentation, but sometimes it
                # returns an empty list if the file goes missing...
                return [on_error]
            else:
                statuslist = []
                for st in pysvn_statuses:
                    # If not recursing, only return the item in question (if a file)
                    # or items directly under the path (if a directory)
                    st_path = S(st.path)
                    cmp_path = os.path.join(path, os.path.basename(st_path))
                    if not recurse and cmp_path != st_path and st_path != path:
                        continue

                    rabbitvcs_status = rabbitvcs.vcs.status.SVNStatus(st)
                    self.cache[st_path] = rabbitvcs_status
                    statuslist.append(rabbitvcs_status)

                return statuslist
        except pysvn.ClientError as ex:
            # TODO: uncommenting these might not be a good idea
            #~ traceback.print_exc()
            log.debug("Exception occurred in SVN.status() for %s" % path)
            log.exception(ex)
            return [on_error]

    def client_info(self, path):
        if islink(path):
            path = realpath(path)
        return self.client.info(pure_unicode(path))

    def client_status(self, *args, **kwargs):
        return self.client.status(*pure_unicode(args), **pure_unicode(kwargs))

    def find_repository_path(self, path):
        path_to_check = path
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".svn")):
                return path_to_check

            path_to_check = os.path.split(path_to_check)[0]

        return None

    def status(self, path, summarize=True, invalidate=False):
        spath = S(path)
        if spath in self.cache:
            if invalidate:
                del self.cache[spath]
            else:
                st = self.cache[spath]
                if summarize:
                    st.summary = st.single
                return st

        all_statuses = self.statuses(path, recurse=summarize)

        if summarize:
            path_status = None
            for st in all_statuses:
                if S(st.path) == spath:
                    path_status = st
                    break

            path_status.make_summary(all_statuses)
        else:
            path_status = all_statuses[0]

        return path_status

    def is_working_copy(self, path):
        try:
            # when a versioned directory is removed and replaced with a
            # non-versioned directory (one that doesn't have a working copy
            # administration area, or .svn directory) you can't do a status
            # call on that item itself (results in an exception).
            #
            # Note that this is not a conflict, it's more of a corruption.
            # And it's associated with the status "obstructed". The only
            # way to make sure that we're dealing with a working copy
            # is by verifying the SVN administration area exists.
            if (isdir(path) and
                    self.client_info(path) and
                    isdir(os.path.join(path, ".svn"))):
                return True
            return False
        except Exception as e:
            # FIXME: ClientError client in use on another thread
            #~ log.debug("EXCEPTION in is_working_copy(): %s" % str(e))
            return False

    def is_in_a_or_a_working_copy(self, path):
        if self.is_working_copy(path):
            return True
        if self.find_repository_path(os.path.split(path)[0]):
            return True
        return False

    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True
        else:
            try:
                # info will return nothing for an unversioned file inside a working copy
                if (self.is_in_a_or_a_working_copy(path) and
                        self.client_info(path)):
                    return True
            except Exception as e:
                log.exception("is_versioned exception for %s" % path)

            return False

    def is_status(self, path, status_kind):
        try:
            status = self.status(path, summarize=False)
        except Exception as e:
            log.exception("is_status exception for %s" % path)
            return False

        # If looking for "NORMAL", then both statuses must be normal (or propstatus=none)
        # Otherwise, it is an either or situation
        if status_kind == pysvn.wc_status_kind.normal:
            return (status.data["text_status"] == status_kind
                and (status.data["prop_status"] == status_kind
                    or status.data["prop_status"] == pysvn.wc_status_kind.none))
        else:
            return (status.data["text_status"] == status_kind
                or status.data["prop_status"] == status_kind)

        return False

    def is_locked(self, path):
        is_locked = False
        path = pure_unicode(path)
        try:
            is_locked = self.client.info2(path, recurse=False)[0][1].lock is not None
        except pysvn.ClientError as e:
            return False
            #log.exception("is_locked exception for %s" % path)

        return is_locked

    def get_items(self, paths, statuses=[]):
        """
        Retrieves a list of files that have one of a set of statuses

        @type   paths:      list
        @param  paths:      A list of paths or files.

        @type   statuses:   list
        @param  statuses:   A list of pysvn.wc_status_kind statuses.

        @rtype:             list
        @return:            A list of statuses

        """

        items = []

        for path in paths:

            sts = self.statuses(path, invalidate=True)
            for st in sts:
                if (not statuses) or (st.content in statuses or st.metadata in statuses):
                    items.append(st)

        return items

    def get_remote_updates(self, paths):
        if paths is None:
            return []

        items = []
        for path in paths:
            try:
                sts = self.statuses(path, update=True, invalidate=True)
            except Exception as e:
                log.exception(e)
                continue

            for st in sts:

                if st.remote_content is None and st.remote_metadata is None:
                    continue

                if st.remote_content == "none" and st.remote_metadata == "none":
                    continue

                items.append(st)

        return items

    def get_repo_url(self, path):
        """
        Retrieve the repository URL for the given working copy path

        @type   path:   string
        @param  path:   A working copy path.

        @rtype:         string
        @return:        A repository URL.

        """

        # If the given path is a URL, the user is passing a repository url
        # In that case we already have the url
        if self.is_path_repository_url(path):
            return path

        # If the given path is not part of a working copy, keep trying the
        # parent path to see if it is part of a working copy
        path = self.get_versioned_path(os.path.abspath(path))
        if not path:
            return ""

        returner = ""

        try:
            info = self.client_info(path)
            returner = S(info["url"], IDENTITY_ENCODING).bytes()
        except Exception as e:
            log.exception(e)

        return returner

    def get_repo_root_url(self, path):
        """
        Retrieve the repository URL for the given working copy path
        FYI this method was not added until svn 1.6.x

        @type   path:   string
        @param  path:   A working copy path.

        @rtype:         string
        @return:        A repository URL.

        """

        returner = ""

        try:
            info = self.client.info2(pure_unicode(path), recurse=False)
            returner = info[0][1]["repos_root_URL"]
        except Exception as e:
            log.exception(e)

        return returner

    def is_path_repository_url(self, path):
        for proto in ("http://", "https://", "svn://", "svn+ssh://", "file://"):
            if path.startswith(proto):
                return True

        return False

    def get_revision(self, path):
        """
        Retrieve the current revision number for a path

        @type   path:   string
        @param  path:   A working copy path.

        @rtype:         integer
        @return:        A repository revision.

        """

        info = self.client_info(path)

        returner = None
        try:
            returner = info["commit_revision"].number
        except KeyError as e:
            log.exception("KeyError exception in svn.py get_revision() for %s" % path)
        except AttributeError as e:
            log.exception("AttributeError exception in svn.py get_revision() for %s" % path)

        return returner

    def get_head(self, path):
        """
        Retrieve the HEAD revision for a repository.

        @type   path:   string
        @param  path:   A working copy path.

        @rtype:         integer
        @return:        A repository revision.

        """

        info = self.client_info(path)

        returner = None
        try:
            returner = info["revision"].number
        except KeyError as e:
            log.exception("KeyError exception in svn.py get_head() for %s" % path)
        except AttributeError as e:
            log.exception("AttributeError exception in svn.py get_head() for %s" % path)

        return returner

    def find_merge_candidate_revisions(self, from_url, to_path):
        """
        Return the list of revisions from from_url that are not already merged into to_path.

        @type  from_url:  string
        @param from_url:  A repository URL to merge from.

        @type  to_path:   string
        @param to_path:   A working copy path to merge into.

        @rtype:           list
        @return:          A list of revisions not already merged.
        """

        from_url_root = self.get_repo_root_url(from_url)
        from_branch = from_url.replace(from_url_root, '')
        from_branch = from_branch.rstrip('/')

        merge_info = self.propget(to_path, "svn:mergeinfo")

        merged_revisions = []
        for branch in merge_info.split('\n'):
            if not branch.startswith(from_branch + ':'):
                continue
            revisions = branch.split(':')[1]  # branch:rev,rev-rev,...
            for rev in revisions.split(','):
                if rev.find('-') != -1:
                    (rev_s, rev_e) = rev.split('-')
                    merged_revisions += list(range(int(rev_s), int(rev_e) + 1))
                else:
                    merged_revisions.append(int(rev))

        from_log = self.log(from_url, strict_node_history=False)
        from_revisions = [ int(l.revision.short()) for l in from_log ]

        to_log = self.log(to_path, strict_node_history=False)
        to_revisions = [ int(l.revision.short()) for l in to_log ]

        candidate_revisions = list(set(from_revisions) - set(to_revisions) - set(merged_revisions))

        return candidate_revisions


    #
    # properties
    #

    def get_versioned_path(self, path):
        """
        Generates a safe path to use with the prop* functions.
        If the given path is unversioned, go to the next path up.

        @type   path:   string
        @param  path:   A file or directory path.

        @rtype:         string
        @return:        A prop* function-safe path.

        """

        path_to_check = path
        path_to_use = None
        while path_to_check != "/" and path_to_check != "":
            if self.is_versioned(path_to_check):
                path_to_use = path_to_check
                return path_to_use

            path_to_check = os.path.split(path_to_check)[0]

        return path_to_use

    def propset(self, path, prop_name, prop_value, overwrite=False, recurse=False):
        """
        Adds an svn property to a path.  If the item is unversioned,
        add a recursive property to the parent path

        @type   path: string
        @param  path: A file or directory path.

        @type   prop_name: string
        @param  prop_name: An svn property name.

        @type   prop_value: string
        @param  prop_value: An svn property value/pattern.

        @type   recurse: boolean
        @param  recurse: If True, the property will be applied to all
                subdirectories as well.

        """

        path = self.get_versioned_path(path)
        if overwrite:
            props = prop_value
        else:
            props = self.propget(path, prop_name)
            props = "%s%s" % (props, prop_value)

        try:
            self.client.propset(
                pure_unicode(prop_name),
                pure_unicode(props),
                pure_unicode(path),
                recurse=recurse
            )
            return True
        except pysvn.ClientError as e:
            log.exception("pysvn.ClientError exception in svn.py propset() for %s" % S(path).display())
        except TypeError as e:
            log.exception("TypeError exception in svn.py propset() %s" % S(path).display())

        return False

    def proplist(self, path, rev=None):
        """
        Retrieves a dictionary of properties for a path.

        @type   path:   string
        @param  path:   A file or directory path.

        @rtype:         dictionary
        @return:        A dictionary of properties.

        """
        path = pure_unicode(path)
        if rev:
            returner = self.client.proplist(path, revision=rev)
        else:
            returner = self.client.proplist(path)
        if returner:
            returner = returner[0][1]
        else:
            returner = {}

        return returner

    def propget(self, path, prop_name, rev=None):
        """
        Retrieves a dictionary of the prop_value of the given
        path and prop_name

        @type   path:       string
        @param  path:       A file or directory path.

        @type   prop_name:  string or self.PROPERTIES
        @param  prop_name:  An svn property name.

        @rtype:             dictionary
        @return:            A dictionary where the key is the path, the value
                            is the prop_value.

        """

        path = self.get_versioned_path(pure_unicode(path))
        prop_name = pure_unicode(prop_name)
        try:
            if rev:
                returner = self.client.propget(
                    prop_name,
                    path,
                    recurse=True,
                    revision=rev
                )
            else:
                returner = self.client.propget(
                    prop_name,
                    path,
                    recurse=True
                )
        except pysvn.ClientError as e:
            log.exception("pysvn.ClientError exception in svn.py propget() for %s" % path)
            return ""

        try:
            returner = returner[path]
        except KeyError as e:
            returner = ""

        return returner

    def propdel(self, path, prop_name, recurse=True):
        """
        Removes a property from a given path

        @type   path: string
        @param  path: A file or directory path.

        @type   prop_name: string or self.PROPERTIES
        @param  prop_name: An svn property name.

        @type   recurse: boolean
        @param  recurse: If True, the property will be deleted from any
                subdirectories also having the property set.

        """

        path = self.get_versioned_path(path)

        returner = False
        try:
            self.client.propdel(
                pure_unicode(prop_name),
                pure_unicode(path),
                recurse=recurse
            )
            returner = True
        except pysvn.ClientError as e:
            log.exception("pysvn.ClientError exception in svn.py propdel() for %s" % S(path).display())
        except TypeError as e:
            log.exception("TypeError exception in svn.py propdel() %s" % S(path).display())

        return returner

    def propdetails(self, path):
        """
        Each property on a path may be modified in the WC, deleted or added.
        This method compares the properties on the local path to the base and
        identifies which.

        @param path: the path (file or dir) in the WC to check
        @type path: a path for something in a WC

        @return a dict of the form:
                {prop_name:
                    {"value": value (WC value, unless deleted then base value),
                     "status": status of property}
                }

        """
        local_props = self.proplist(path)
        base_props = self.proplist(path,
                                   rev=Revision("base").primitive())

        prop_details = {}

        local_propnames = set(local_props.keys())
        base_propnames = set(base_props.keys())

        for propname in (local_propnames | base_propnames):

            if propname in (local_propnames & base_propnames):
                # These are the property names that are common to the WC and
                # base. If their values have changed, list them as changed
                if local_props[propname] == base_props[propname]:
                    prop_details[propname] = {"status": rabbitvcs.vcs.status.status_normal,
                                              "value": local_props[propname]}

                else:
                    prop_details[propname] = {"status": rabbitvcs.vcs.status.status_modified,
                                              "value": local_props[propname]}

            elif propname in local_propnames:
                prop_details[propname] = {"status": rabbitvcs.vcs.status.status_added,
                                          "value": local_props[propname]}

            elif propname in base_propnames:
                prop_details[propname] = {"status": rabbitvcs.vcs.status.status_deleted,
                                          "value": base_props[propname]}

        return prop_details

    def revpropset(self, prop_name, prop_value, url, rev=None, force=False):
        """
        Adds an svn property to a path.  If the item is unversioned,
        add a recursive property to the parent path

        @type   url: string
        @param  url: A url to attach the prop to

        @type   prop_name: string
        @param  prop_name: An svn property name.

        @type   prop_value: string
        @param  prop_value: An svn property value/pattern.

        @type   rev: pysvn.Revision object
        @param  rev: The revision to attach the prop to

        @type   force: boolean
        @param  force: If True, the property will be forced

        """

        if rev is None:
            rev = self.revision("head")

        self.client.revpropset(pure_unicode(prop_name),
                               pure_unicode(prop_value),
                               pure_unicode(url),
                               revision=rev.primitive())

    def revproplist(self, url, rev=None):
        """
        Retrieves a dictionary of properties for a url.

        @type   url:   string
        @param  url:   A repository url

        @type   rev: pysvn.Revision object
        @param  rev: The revision to attach the prop to

        @rtype:         tuple(revision object, propsdict)
        @return:        A tuple with revision information and property dictionary

        """

        if rev is None:
            rev = self.revision("head")

        return self.client.revproplist(pure_unicode(url), rev.primitive())[1]

    def revpropget(self, url, prop_name, rev=None):
        """
        Retrieves the revprop value for a specific url/propname/revision

        @type   url:       string
        @param  url:       A repository url

        @type   prop_name:  string or self.PROPERTIES
        @param  prop_name:  An svn property name.

        @type   rev: pysvn.Revision object
        @param  rev: The revision to attach the prop to

        @rtype:         tuple(revision object, propsdict)
        @return:        A tuple with revision information and property dictionary

        """

        if rev is None:
            rev = self.revision("head")

        return self.client.revpropget(
            pure_unicode(prop_name),
            pure_unicode(url),
            revision=rev.primitive()
        )

    def revpropdel(self, url, prop_name, rev=None, force=False):
        """
        Removes a property from a given path

        @type   url: string
        @param  url: A repository url

        @type   prop_name: string or self.PROPERTIES
        @param  prop_name: An svn property name.

        @type   rev: pysvn.Revision object
        @param  rev: The revision to attach the prop to

        @type   force: boolean
        @param  force: If True, the property deletion will be forced

        """

        if rev is None:
            rev = self.revision("head")

        return self.client.revpropdel(
            pure_unicode(prop_name),
            pure_unicode(url),
            revision=rev.primitive(),
            force=force
        )

    #
    # callbacks
    #

    def set_callback_cancel(self, func):
        self.client.callback_cancel = func

    def callback_cancel(self):
        if hasattr(self.client, "callback_cancel"):
            self.client.callback_cancel()

    def set_callback_notify(self, func):
        self.client.callback_notify = func

    def set_callback_get_log_message(self, func):
        self.client.callback_get_log_message = func

    def set_callback_get_login(self, func):
        self.client.callback_get_login = func

    def set_callback_ssl_server_trust_prompt(self, func):
        self.client.callback_ssl_server_trust_prompt = func

    def set_callback_ssl_client_cert_password_prompt(self, func):
        self.client.callback_ssl_client_cert_password_prompt = func

    def set_callback_ssl_client_cert_prompt(self, func):
        self.client.callback_ssl_client_cert_prompt = func

    #
    # revision
    #

    def revision(self, kind, date=None, number=None):
        """
        Create a revision object usable by pysvn

        @type   kind:   string
        @param  kind:   An svn.REVISIONS keyword.

        @type   date:   integer
        @param  date:   Used for kind=date, in the form of UNIX TIMESTAMP (secs).

        @type   number: integer
        @param  number: Used for kind=number, specifies the revision number.

        @rtype:         pysvn.Revision object
        @return:        A pysvn.Revision object.

        """

        # TODO: Don't use kwargs for date/number, just accept a "value" as a
        #       regular arg

        value = None
        if date:
            value = date
        elif number:
            value = number

        return Revision(kind, value)

    #
    # actions
    #

    def add(self, paths, recurse=True):
        """
        Add files or directories to the repository

        @type   paths: list
        @param  paths: A list of files/directories.

        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children

        """

        return self.client.add(pure_unicode(paths), recurse)

    def add_backwards(self, path):
        """
        This will add the given path to version control, and any parent
        directories that themselves require adding. It is essential that "path"
        contains a WC somewhere in its hierarchy.

        @param path: the path to add to version control
        @type path: string
        """
        head, tail = pure_unicode(path),""
        tails = list()

        # We need to add backwards-recursively, since patch could create
        # files any level deep in the tree
        while not (self.is_working_copy(head) or self.is_versioned(head)):
            head, tail = os.path.split(head)
            tails.insert(0, tail)
            # If we get all the way to the FS root, something really dumb
            # has happened.
            assert head, "No longer in a working copy!"

        # Walk back up the tree...
        for tail in tails:
            head = os.path.join(head, tail)
            self.client.add(head, depth=pysvn.depth.empty)

    def copy(self, src, dest, revision=Revision("head")):
        """
        Copy files/directories from src to dest.  src or dest may both be either
        a local path or a repository URL.  revision is a pysvn.Revision object.

        @type   src: string
        @param  src: Source URL or path.

        @type   dest: string
        @param  dest: Destination URL or path.

        @type   revision: pysvn.Revision object
        @param  revision: A pysvn.Revision object.

        """
        src = helper.urlize(pure_unicode(src))
        dest = helper.urlize(pure_unicode(dest))
        return self.client.copy(src, dest, revision.primitive())

    def copy_all(self, sources, dest_url_or_path, copy_as_child=False,
            make_parents=False, ignore_externals=False):
        """
        Copy sources to the dest_url_or_path.

        @type   sources: list of tuples
        @param  sources: A list of tuples (url_or_path,revision)

        @type   dest_url_or_path: string
        @param  dest_url_or_path: Destination URL or path.

        @type   copy_as_child: boolean
        @param  copy_as_child: If there are multiple sources, copy as child
                    to dest_url_or_path (assumed to be a folder)

        @type   make_parents: boolean
        @param  make_parents: TBD

        @type   ignore_externals: boolean
        @param  ignore_externals: Omit externals

        """

        return self.client.copy2(pure_unicode(sources),
            pure_unicode(dest_url_or_path), copy_as_child,
            make_parents, None, ignore_externals)

    def checkout(self, url, path, recurse=True, revision=Revision("head"),
            ignore_externals=False):

        """
        Checkout a working copy from a vcs repository

        @type   url: string
        @param  url: A repository url.

        @type   path: string
        @param  path: A local destination for the working copy.

        @type   recurse: boolean
        @param  recurse: Whether or not to run a recursive checkout.

        @type   revision: pysvn.Revision
        @param  revision: Revision to checkout, defaults to HEAD.

        @type   ignore_externals: boolean
        @param  ignore_externals: Whether or not to ignore externals.

        """

        url = helper.urlize(pure_unicode(url))

        return self.client.checkout(url, pure_unicode(path),
            recurse=recurse, revision=revision.primitive(),
            ignore_externals=ignore_externals)

    def cleanup(self, path):
        """
        Clean up a working copy.

        @type   path: string
        @param  path: A local working copy path.

        """

        return self.client.cleanup(pure_unicode(path))

    def revert(self, paths):
        """
        Revert files or directories so they are unversioned

        @type   paths: list
        @param  paths: A list of files/directories.

        """

        return self.client.revert(pure_unicode(paths))

    def commit(self, paths, log_message="", recurse=False, keep_locks=False):
        """
        Commit a list of files to the repository.

        @type   paths: list
        @param  paths: A list of files/directories.

        @type   log_message: string
        @param  log_message: A commit log message.

        @type   recurse: boolean
        @param  recurse: Whether or not to recurse into sub-directories.

        @type   keep_locks: boolean
        @param  keep_locks: Whether or not to keep locks on commit.

        """

        kwargs = {"keep_locks": keep_locks}
        try:
            # Simply setting recurse=False will not stop child files from getting
            # committed.  The pysvn.depth kwarg must be set to empty.
            # Unfortunately, older pysvn/svn installations do not have the depth
            # enum so for those, recurse must be used.
            kwargs["depth"] = (recurse and pysvn.depth.infinity or pysvn.depth.empty)
        except AttributeError:
            kwargs["recurse"] = recurse

        retval = self.client.checkin(pure_unicode(paths),
                                     pure_unicode(log_message), **kwargs)
        dummy_commit_dict = {
            "revision": retval,
            "action": rabbitvcs.vcs.svn.commit_completed
            }
        self.client.callback_notify(dummy_commit_dict)

        return retval

    def log(self, url_or_path, revision_start=Revision("head"),
            revision_end=Revision("number", 0), limit=0,
            discover_changed_paths=True, strict_node_history=False):
        """
        Retrieve log items for a given path in the repository

        @type   url_or_path: string
        @param  url_or_path: Path for which to get log items for

        @type   revision_start: pysvn.Revision
        @param  revision_start: Most recent revision.  Defaults to HEAD

        @type   revision_end: pysvn.Revision
        @param  revision_end: Oldest revision.  Defaults to rev 0.

        @type   limit: int
        @param  limit: The maximum number of items to return.  Defaults to 0.

        """

        log = self.client.log(pure_unicode(url_or_path),
            revision_start.primitive(), revision_end.primitive(),
            discover_changed_paths, strict_node_history, limit)

        returner = []
        for item in log:
            revision = Revision(pysvn.opt_revision_kind.number, item.revision.number)
            date = datetime.fromtimestamp(item.date) if hasattr(item, "date") else datetime(1900, 1, 1)

            author = _("(no author)")
            if hasattr(item, "author"):
                author = item["author"]

            message = ""
            if hasattr(item, "message"):
                message = item["message"]

            changed_paths = []
            for changed_path in item.changed_paths:
                copy_from_rev = ""
                if hasattr(changed_path.copyfrom_revision, "number"):
                    copy_from_rev = self.revision("number", changed_path.copyfrom_revision.number)

                copy_from_path = ""
                if hasattr(changed_path, "copy_from_path"):
                    copy_from_path = changed_path.copy_from_path

                changed_paths.append(rabbitvcs.vcs.log.LogChangedPath(
                    changed_path.path,
                    changed_path.action,
                    copy_from_path,
                    copy_from_rev
                ))

            returner.append(rabbitvcs.vcs.log.Log(
                date,
                revision,
                author,
                message,
                changed_paths,
                None
            ))

        return returner

    def export(self, src_url_or_path, dest_path, revision=Revision("head"),
            recurse=True, ignore_externals=False, force=False, native_eol=None):

        """
        Export files from either a working copy or repository into a local
        path without versioning information.

        @type   src_url_or_path: string
        @param  src_url_or_path: A repository url.

        @type   dest_path: string
        @param  dest_path: A local destination for the working copy.

        @type   revision: pysvn.Revision
        @param  revision: The revision to retrieve from the repository.

        @type   ignore_externals: boolean
        @param  ignore_externals: Whether or not to ignore externals.

        @type   recurse: boolean
        @param  recurse: Whether or not to run a recursive checkout.

        """

        self.client.export(pure_unicode(src_url_or_path),
            pure_unicode(dest_path), force,
            revision.primitive(), native_eol, ignore_externals, recurse)

    def import_(self, path, url, log_message, ignore=False):

        """
        Import an unversioned file or directory structure into a repository.

        @type   path: string
        @param  path: An unversioned file or directory structure

        @type   url: string
        @param  url: A repository location to put the imported files

        @type   log_message: string
        @param  log_message: Log message to use for commit

        @type   ignore: boolean
        @param  ignore: Disregard svn:ignore props

        """

        url = helper.urlize(url)
        return self.client.import_(pure_unicode(path),
                                   pure_unicode(url),
                                   pure_unicode(log_message), ignore)

    def lock(self, url_or_path, lock_comment, force=False):

        """
        Lock a url or path.

        @type   url_or_path: string
        @param  url_or_path: A url or path to lock

        @type   lock_comment: string
        @param  lock_comment: A log message to go along with the lock.

        @type   force: boolean
        @param  force: Steal the locks of others if they exist.

        """

        return self.client.lock(pure_unicode(url_or_path),
                                pure_unicode(lock_comment), force)

    def relocate(self, from_url, to_url, path, recurse=True):

        """
        Relocate the working copy from from_url to to_url for path

        @type   from_url: string
        @param  from_url: A url to relocate from

        @type   to_url: string
        @param  to_url: A url to relocate to

        @type   path: string
        @param  path: The path of the local working copy

        """

        from_url = helper.urlize(pure_unicode(from_url))
        to_url = helper.urlize(pure_unicode(to_url))
        return self.client.relocate(from_url, to_url, path, recurse)

    def move(self, src_url_or_path, dest_url_or_path):

        """
        Schedule a file to be moved around the repository

        @type   src_url_or_path: string
        @param  src_url_or_path: A url/path to move from

        @type   dest_url_or_path: string
        @param  dest_url_or_path: A url/path to move to

        """

        src_url_or_path = pure_unicode(src_url_or_path)
        dest_url_or_path = pure_unicode(dest_url_or_path)
        if hasattr(self.client, "move2"):
            return self.client.move2([src_url_or_path], dest_url_or_path)
        else:
            return self.client.move(src_url_or_path, dest_url_or_path,
                force=True)

    def move_all(self, sources, dest_url_or_path, move_as_child=False,
            make_parents=False):
        """
        Move sources to the dest_url_or_path.

        @type   sources: list of tuples
        @param  sources: A list of tuples (url_or_path,revision)

        @type   dest_url_or_path: string
        @param  dest_url_or_path: Destination URL or path.

        @type   move_as_child: boolean
        @param  move_as_child: If there are multiple sources, move as child
                    to dest_url_or_path (assumed to be a folder)

        @type   make_parents: boolean
        @param  make_parents: TBD

        """

        return self.client.move2(pure_unicode(sources),
            pure_unicode(dest_url_or_path),
            move_as_child=move_as_child, make_parents=make_parents)

    def remove(self, url_or_path, force=False, keep_local=False):

        """
        Schedule a file to be removed from the repository

        @type   url_or_path: string
        @param  url_or_path: A url/path to remove

        @type   force: boolean
        @param  force: Force renaming, despite conflicts. Defaults to false.

        @type   keep_local: boolean
        @param  keep_local: Keep the local copy (don't just delete it)

        """

        return self.client.remove(pure_unicode(url_or_path),
                                  force, keep_local)

    def revert(self, paths, recurse=False):
        """
        Revert files or directories from the repository

        @type   paths: list
        @param  paths: A list of files/directories.

        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children

        """

        return self.client.revert(pure_unicode(paths), recurse)

    def resolve(self, path, recurse=True):
        """
        Mark conflicted files as resolved

        @type   path: string
        @param  path: A local path to resolve

        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children

        """

        return self.client.resolved(pure_unicode(path), recurse)

    def switch(self, path, url, revision=Revision("head")):
        """
        Switch the working copy to another repository source.

        @type   path: string
        @param  path: A local path to a working copy

        @type   url: string
        @param  url: The repository location to switch to

        @type   revision: pysvn.Revision
        @param  revision: The revision of the repository to switch to (Def:HEAD)

        """

        url = helper.urlize(pure_unicode(url))
        return self.client.switch(pure_unicode(path), url, revision.primitive())

    def unlock(self, path, force=False):
        """
        Unlock locked files.

        @type   path: string
        @param  path: A local path to resolve

        @type   force: boolean
        @param  force: If locked by another user, unlock it anyway.

        """

        return self.client.unlock(pure_unicode(path), force)

    def update(self, path, recurse=True, revision=Revision("head"),
            ignore_externals=False):
        """
        Update a working copy.

        @type   path: string
        @param  path: A local path to update

        @type   recurse: boolean
        @param  recurse: Update child folders recursively

        @type   revision: pysvn.Revision
        @param  revision: Revision to update to (Def: HEAD)

        @type   ignore_externals: boolean
        @param  ignore_externals: Ignore external items

        """

        return self.client.update(pure_unicode(path),
                                  recurse, revision.primitive(),
                                  ignore_externals)

    def annotate(self, url_or_path, from_revision=Revision("number", 1),
            to_revision=Revision("head")):
        """
        Get the annotate results for the given file and revision range.

        @type   url_or_path: string
        @param  url_or_path: A url or local path

        @type   from_revision: pysvn.Revision
        @param  from_revision: Revision from (def: 1)

        @type   to_revision: pysvn.Revision
        @param  to_revision: Revision to (def: HEAD)

        """

        return self.client.annotate(pure_unicode(url_or_path),
                                    from_revision.primitive(),
                                    to_revision.primitive())

    def merge_ranges(self, source, ranges_to_merge, peg_revision,
            target_wcpath, notice_ancestry=False, force=False, dry_run=False,
            record_only=False):
        """
        Merge a range of revisions.

        @type   source: string
        @param  source: A repository location

        @type   ranges_to_merge: list of tuples
        @param  ranges_to_merge: A list of revision ranges to merge

        @type   peg_revision: pysvn.Revision
        @param  peg_revision: Indicates which revision in sources is valid.

        @type   target_wcpath: string
        @param  target_wcpath: Target working copy path

        @type   notice_ancestry: boolean
        @param  notice_ancestry: unsure

        @type   force: boolean
        @param  force: unsure

        @type   dry_run: boolean
        @param  dry_run: Do a test/dry run or not

        @type   record_only: boolean
        @param  record_only: unsure

        TODO: Will firm up the parameter documentation later

        """
        return self.client.merge_peg2(pure_unicode(source),
                                      ranges_to_merge,
                                      peg_revision.primitive(),
                                      pure_unicode(target_wcpath),
                                      notice_ancestry=notice_ancestry,
                                      force=force,
                                      dry_run=dry_run,
                                      record_only=record_only)

    def has_merge2(self):
        """
        Tests whether the user has a later version of pysvn/svn installed
        with more merge features
        """
        return hasattr(self.client, "merge_peg2")

    def merge_trees(self, url_or_path1, revision1, url_or_path2, revision2,
            local_path, force=False, recurse=True, dry_run=False, record_only=False):
        """
        Merge two trees into one.

        @type   url_or_path1: string
        @param  url_or_path1: From WC/URL location

        @type   revision1: pysvn.Revision
        @param  revision1: Indicates the revision of the URL/Path

        @type   url_or_path2: string
        @param  url_or_path2: To WC/URL location

        @type   revision2: pysvn.Revision
        @param  revision2: Indicates the revision of the URL/Path

        @type   local_path: string
        @param  local_path: Target working copy path

        @type   force: boolean
        @param  force: unsure

        @type   recurse: boolean
        @param  recurse: Merge children recursively

        @type   dry_run: boolean
        @param  dry_run: Do a test/dry run or not

        @type   record_only: boolean
        @param  record_only: unsure

        TODO: Will firm up the parameter documentation later

        """

        url_or_path1 = helper.urlize(pure_unicode(url_or_path1))
        url_or_path2 = helper.urlize(pure_unicode(url_or_path2))
        return self.client.merge(url_or_path1,
                                 revision1.primitive(),
                                 url_or_path2,
                                 revision2.primitive(),
                                 pure_unicode(local_path),
                                 force = force,
                                 recurse = recurse,
                                 dry_run = dry_run,
                                 record_only = record_only)

    def has_merge_reintegrate(self):
        """
        Tests whether the user has a later version of pysvn/svn installed
        with more merge features
        """
        return hasattr(self.client, "merge_reintegrate")

    def merge_reintegrate(self, url_or_path, revision, local_path, dry_run=False):
        """
        Merge a branch into trunk

        @type   url_or_path: string
        @param  url_or_path: From WC/URL location

        @type   revision: Revision()
        @param  revision: Indicates the revision of the URL/Path

        @type   local_path: string
        @param  local_path: Target working copy path

        @type   dry_run: boolean
        @param  dry_run: Do a test/dry run or not

        """

        return self.client.merge_reintegrate(pure_unicode(url_or_path),
                                             revision.primitive(),
                                             pure_unicode(local_path),
                                             dry_run = dry_run)


    def diff(self, tmp_path, url_or_path, revision1, url_or_path2, revision2,
            recurse=True, ignore_ancestry=False, diff_deleted=True,
            ignore_content_type=False):
        """
        Returns the diff text between the base code and the working copy.

        @type   tmp_path: string
        @param  tmp_path: Temporal path to store the diff

        @type   url_or_path: string
        @param  url_or_path: From WC/URL location

        @type   revision1: pysvn.Revision
        @param  revision1: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.base ))

        @type   url_or_path2: string
        @param  url_or_path2: From WC/URL location

        @type   revision2: pysvn.Revision
        @param  revision2: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.working ))

        @type   recurse: boolean
        @param  recurse: Whether or not to recurse into sub-directories. (def: True)

        @type   ignore_ancestry: boolean
        @param  ignore_ancestry: Whether or not to recurse into sub-directories. (def: False)

        @type   diff_deleted: boolean
        @param  diff_deleted: Whether or not to recurse into sub-directories. (def: True)

        @type   ignore_content_type: boolean
        @param  ignore_content_type: Whether or not to recurse into sub-directories. (def: False)

        """

        return self.client.diff(pure_unicode(tmp_path),
                                pure_unicode(url_or_path),
                                revision1.primitive(),
                                pure_unicode(url_or_path2),
                                revision2.primitive(), recurse, ignore_ancestry,
                                diff_deleted, ignore_content_type)

    def diff_summarize(self, url_or_path1, revision1, url_or_path2, revision2,
            recurse=True, ignore_ancestry=False):
        """
        Returns a summary of changed items between two paths/revisions

        @type   url_or_path1: string
        @param  url_or_path1: First WC/URL location

        @type   revision1: pysvn.Revision
        @param  revision1: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.base ))

        @type   url_or_path2: string
        @param  url_or_path2: Second WC/URL location

        @type   revision2: pysvn.Revision
        @param  revision2: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.working ))

        @type   recurse: boolean
        @param  recurse: Whether or not to recurse into sub-directories. (def: True)

        @type   ignore_ancestry: boolean
        @param  ignore_ancestry: Whether or not to recurse into sub-directories. (def: False)

        @type   depth: pysvn.depth enum
        @param  depth: a replacement for recurse

        """

        return self.client.diff_summarize(pure_unicode(url_or_path1),
                                          revision1.primitive(),
                                          pure_unicode(url_or_path2),
                                          revision2.primitive(),
                                          recurse, ignore_ancestry)

    def list(self, url_or_path, revision=Revision("HEAD"), recurse=True):
        url_or_path = helper.urlize(url_or_path)
        return self.client.list(pure_unicode(url_or_path),
                                revision=revision.primitive(), recurse=recurse)

    def mkdir(self, url_or_path, log_message):
        """
        Make a new directory in the repository or working copy

        @type   url_or_path: string
        @param  url_or_path: Url in the repository or path in working copy

        @type   log_message: string
        @param  log_message: A log message to use in your commit

        """

        return self.client.mkdir(pure_unicode(url_or_path),
                                 pure_unicode(log_message))

    def apply_patch(self, patch_file, base_dir):
        """
        Applies a patch created for this WC.

        @type patch_file: string
        @param patch_file: the path to the patch file

        @type base_dir: string
        @param base_dir: the base directory from which to interpret the paths in
                         the patch file
        """

        any_failures = False

        for file, success, rej_file in helper.parse_patch_output(patch_file, base_dir):

            fullpath = os.path.join(base_dir, file)

            event_dict = dict()

            event_dict["path"] = file
            event_dict["mime_type"] = "" # meh

            if success:
                event_dict["action"] = _("Patched") # not in pysvn, but
                                                    # we have a fallback
            else:
                any_failures = True
                event_dict["action"] = _("Patch Failed") # better wording needed?

            # Creates its own notifications.
            self.add_backwards(fullpath)

            if rej_file:
                rej_info = {
                    "path" : rej_file,
                    "action" : _("Rejected Patch"),
                    "mime_type" : None
                }

            if self.client.callback_notify:
                self.client.callback_notify(event_dict)
                if rej_file:
                    self.client.callback_notify(rej_info)



    def is_version_less_than(self, version):
        """
        @type   version: tuple
        @param  version: A version tuple to compare pysvn's version to
        """

        if version[0] > pysvn.version[0]:
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] > pysvn.version[1])):
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] > pysvn.version[2])):
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] == pysvn.version[2])
                and (version[3] > pysvn.version[3])):
            return True

        return False

    def is_version_greater_than(self, version):
        """
        @type   version: tuple
        @param  version: A version tuple to compare pysvn's version to
        """

        if version[0] < pysvn.version[0]:
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] < pysvn.version[1])):
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] < pysvn.version[2])):
            return True

        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] == pysvn.version[2])
                and (version[3] < pysvn.version[3])):
            return True

        return False
