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

import os.path
import unittest

from datetime import datetime

import rabbitvcs.vcs

from rabbitvcs.util.log import Log
from six.moves import range

log = Log("rabbitvcs.vcs.status")

from rabbitvcs import gettext
_ = gettext.gettext

# These are the statuses that we might represent with icons
status_normal = 'normal'
status_modified = 'modified'
status_added = 'added'
status_deleted = 'deleted'
status_ignored = 'ignored'
status_read_only = 'read-only'
status_locked = 'locked'
status_unknown = 'unknown'
# Specifically: this means something IN A WORKING COPY but not added
status_unversioned = 'unversioned'
status_missing = 'missing'
status_replaced = 'replaced'
# "complicated" = anything we display with that exclamation mark icon
status_complicated = 'complicated'
status_calculating = 'calculating'
status_error = 'error'

MODIFIED_CHILD_STATUSES = [
    status_modified,
    status_added,
    status_deleted,
    status_missing,
    status_replaced
]

class StatusCache(object):
    keys = [
        None,
        status_normal,
        status_modified,
        status_added,
        status_deleted,
        status_ignored,
        status_read_only,
        status_locked,
        status_unknown,
        status_unversioned,
        status_missing,
        status_replaced,
        status_complicated,
        status_calculating,
        status_error
    ]
    
    authors = []
    revisions = []

    def __init__(self):
        self.cache = {}

    def __setitem__(self, path, status):
        try:
            content_index = self.keys.index(status.simple_content_status())
            metadata_index = self.keys.index(status.simple_metadata_status())

            try:
                author_index = self.authors.index(status.author)
            except ValueError as e:
                self.authors.append(status.author)
                author_index = len(self.authors) -1

            try:
                revision_index = self.revisions.index(status.revision)
            except ValueError as e:
                self.revisions.append(status.revision)
                revision_index = len(self.revisions) -1
            
            self.cache[path] = (
                content_index,
                metadata_index,
                revision_index,
                author_index,
                status.date
            )
        except Exception as e:
            log.debug(e)
            
    def __getitem__(self, path):
        try:
            (content_index, metadata_index, revision_index, author_index, date) = self.cache[path]
            
            content = self.keys[content_index]
            metadata = self.keys[metadata_index]
            revision = self.revisions[revision_index]
            author = self.authors[author_index]
            
            return Status(path, content, metadata, revision=revision, 
                author=author, date=date)
        except Exception as e:
            log.debug(e)

    def __delitem__(self, path):
        try:
            del self.cache[path]
        except KeyError as e:
            log.debug(e)

            
    def __contains__(self, path):
        return path in self.cache

    def find_path_statuses(self, path):
        statuses = []
        if os.path.isdir(path):
            for key, value in list(self.cache.items()):
                if key.startswith(path):
                    statuses.append(self.__getitem__(key))
        else:
            statuses.append(self.__getitem__(path))
            
        return statuses

class Status(object):

    @staticmethod
    def status_unknown(path):
        return Status(path, status_unknown, summary = status_unknown)
    
    @staticmethod
    def status_error(path):
        return Status(path, status_error, summary = status_error)
    
    @staticmethod
    def status_calc(path):
        return Status(path, status_calculating, summary = status_calculating)
    
    vcs_type = rabbitvcs.vcs.VCS_DUMMY
 
    clean_statuses = ['unchanged']
    
    content_status_map = None
    metadata_status_map = None
    
    def __init__(self, path, content, metadata=None, summary=None, 
            revision=None, author=None, date=None):

        """
        The status objects accepts the following items
        
        @type   path: string
        @param  path: The path to the item
        
        @type   content: string
        @param  content: The content status
        
        @type   metadata: string
        @param  metadata: The property status

        @type   summary: string
        @param  summary: The summary status
        
        @type   revision: string or int
        @param  revision: The last commit revision of the item
        
        @type   author: string
        @param  author: The commit author
        
        @type   date: int
        @param  date: The timestamp of the commit time
        
        """

        self.path = path
        self.content = content
        self.metadata = metadata
        self.remote_content = None
        self.remote_metadata = None
        self.single = self._make_single_status()
        self.summary = summary
        self.revision = revision
        self.author = author
        self.date = date

    def _make_single_status(self):
        """
        Given our text_status and a prop_status, simplify to a single "simple"
        status. If we don't know how to simplify our particular combination of
        status, call it an error.
        """     
        # Content status dominates
        single = self.simple_content_status() or status_error
        if single in Status.clean_statuses:
            if self.metadata:
                single = self.simple_metadata_status() or status_error
        return single

    def simple_content_status(self):
        if self.content_status_map:
            return self.content_status_map.get(self.content)
        else:
            return self.content
        
    def simple_metadata_status(self):
        if self.metadata and self.metadata_status_map:
            return self.metadata_status_map.get(self.metadata)
        else:
            return self.metadata

    def make_summary(self, child_statuses = []):
        """ Summarises statuses for directories.
        """    
        summary = status_unknown
        
        status_set = set([st.single for st in child_statuses])
        
        if not status_set:
            self.summary = self.single
        
        if status_complicated in status_set:
            self.summary = status_complicated
        elif self.single in ["added", "modified", "deleted"]:
            # These take priority over child statuses
            self.summary = self.single        
        elif len(set(MODIFIED_CHILD_STATUSES) & status_set):
            self.summary = status_modified
        else:
            self.summary = self.single
        
        return summary
    
    def is_versioned(self):
        return self.single is not status_unversioned
            
    def is_modified(self):
        # This may need to be more sophisticated... eg. is read-only modified?
        # Unknown? etc... 
        return self.single is not status_normal
    
    def has_modified(self):
        # Includes self being modified!
        return self.summary is not status_normal    
    
    def __repr__(self):
        return "<%s %s (%s) %s/%s>" % (_("RabbitVCS status for"),
                                        self.path,
                                        self.vcs_type,
                                        self.simple_content_status(),
                                        self.simple_metadata_status())

    def __getstate__(self):
        attrs = self.__dict__.copy()
        attrs['__type__'] = type(self).__name__
        attrs['__module__'] = type(self).__module__
        return attrs
        
    def __setstate__(self, state_dict):
        del state_dict['__type__']
        del state_dict['__module__']
        self.__dict__ = state_dict

class SVNStatus(Status):

    vcs_type = rabbitvcs.vcs.VCS_SVN
    
    content_status_map = {
        'normal': status_normal,
        'added': status_added,
        'missing': status_missing,
        'unversioned': status_unversioned,
        'deleted': status_deleted,
        'replaced': status_modified,
        'modified': status_modified,
        'merged': status_modified,
        'conflicted': status_complicated,
        'ignored': status_ignored,
        'obstructed': status_complicated,
        # FIXME: is this the best representation of 'externally populated'?
        'external': status_normal,
        'incomplete': status_complicated
    }
    
    metadata_status_map = {
        'normal': status_normal,
        'none': status_normal,
        'modified': status_modified
        }
    
#external - an unversioned path populated by an svn:external property
#incomplete - a directory doesn't contain a complete entries list
    
    def __init__(self, pysvn_status):
        revision = author = date = None
        if pysvn_status.entry:
            revision = int(pysvn_status.entry.commit_revision.number)
            author = pysvn_status.entry.commit_author
            date = int(pysvn_status.entry.commit_time)

        # There is a potential problem here: I'm pretty sure that PySVN statuses
        # do NOT have translatable representations, so this will always come out
        # to be 'normal', 'modified' etc
        Status.__init__(
            self,
            pysvn_status.path,
            content=str(pysvn_status.text_status),
            metadata=str(pysvn_status.prop_status),
            revision=revision,
            author=author,
            date=date
        )

        # self.remote_content = getattr(pysvn_status, "repos_text_status", None)
        # self.remote_metadata = getattr(pysvn_status, "repos_prop_status", None)

        self.remote_content = str(pysvn_status.repos_text_status)
        self.remote_metadata = str(pysvn_status.repos_prop_status)

class GitStatus(Status):

    vcs_type = 'git'
    
    content_status_map = {
        'normal': status_normal,
        'added': status_added,
        'missing': status_missing,
        'untracked': status_unversioned,
        'removed': status_deleted,
        'modified': status_modified,
        'renamed': status_modified,
        'ignored': status_ignored
    }
    
    metadata_status_map = {
        'normal': status_normal,
        None: status_normal
    }

    def __init__(self, gittyup_status):
        super(GitStatus, self).__init__(
            gittyup_status.path,
            content=str(gittyup_status.identifier),
            metadata=None)

class MercurialStatus(Status):
    vcs_type = 'mercurial'
    
    content_status_map = {
        'clean': status_normal,
        'added': status_added,
        'missing': status_missing,
        'unknown': status_unversioned,
        'removed': status_deleted,
        'modified': status_modified,
        'ignored': status_ignored
    }
    
    metadata_status_map = {
        'normal': status_normal,
        None: status_normal
    }

    def __init__(self, mercurial_status):
        super(MercurialStatus, self).__init__(
            mercurial_status["path"],
            content=str(mercurial_status["content"]),
            metadata=None)

STATUS_TYPES = [
    Status,
    SVNStatus,
    GitStatus,
    MercurialStatus
]

class TestStatusObjects(unittest.TestCase):
    
    base = "/path/to/test"
        
    children = [
        os.path.join(base, chr(x)) for x in range(97,123) 
                ]
    
    def testsingle_clean(self):
        status = Status(self.base, status_normal)
        self.assertEqual(status.single, status_normal)
        
    def testsingle_changed(self):
        status = Status(self.base, status_modified)
        self.assertEqual(status.single, status_modified)
        
    def testsingle_propclean(self):
        status = Status(self.base, status_normal, status_normal)
        self.assertEqual(status.single, status_normal)

    def testsingle_propchanged(self):
        status = Status(self.base, status_normal, status_modified)
        self.assertEqual(status.single, status_modified)
        
    def testsummary_clean(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_normal)

    def testsummary_changed(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_modified)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_modified)

    def testsummary_added(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_added)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_modified)

    def testsummary_complicated(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_complicated)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_complicated)

    def testsummary_propchange(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path,
                              status_normal,
                              status_modified)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_modified)

    def testsummary_bothchange(self):
        top_status = Status(self.base, status_normal)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path,
                              status_complicated,
                              status_modified)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_complicated)

    def testsummary_topadded(self):
        top_status = Status(self.base, status_added)
        child_sts = [Status(path, status_normal) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_modified, status_modified)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_added)

if __name__ == "__main__":
    unittest.main()
