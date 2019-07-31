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
Concrete VCS implementation for Git functionality.
"""
from __future__ import absolute_import

import os.path
from datetime import datetime

from .gittyup.client import GittyupClient
from .gittyup import objects

from rabbitvcs.util import helper
from rabbitvcs.util.strings import S

import rabbitvcs.vcs
import rabbitvcs.vcs.status
import rabbitvcs.vcs.log
from rabbitvcs.vcs.branch import BranchEntry
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.vcs.git")

from rabbitvcs import gettext
_ = gettext.gettext

class Revision:
    """
    Implements a simple revision object as a wrapper around the gittyup revision
    object.  This allows us to provide a standard interface to the object data.
    """

    def __init__(self, kind, value=None):
        self.kind = kind.upper()
        self.value = value

        if self.kind == "HEAD":
            self.value = "HEAD"

        self.is_revision_object = True

    def __str__(self):
        if self.value:
            return S(self.value)
        return  S(self.kind)

    def __unicode__(self):
        return self.__str__().unicode()

    def short(self):
        if self.value:
            return S(self.value)[0:7]
        else:
            return self.kind

    def __repr__(self):
        return self.__str__()

    def primitive(self):
        return self.value

class Git:
    STATUS = {
        "normal":       gittyup.objects.NormalStatus,
        "added":        gittyup.objects.AddedStatus,
        "renamed":      gittyup.objects.RenamedStatus,
        "removed":      gittyup.objects.RemovedStatus,
        "modified":     gittyup.objects.ModifiedStatus,
        "killed":       gittyup.objects.KilledStatus,
        "untracked":    gittyup.objects.UntrackedStatus,
        "missing":      gittyup.objects.MissingStatus
    }

    STATUS_REVERSE = {
        gittyup.objects.NormalStatus:       "normal",
        gittyup.objects.AddedStatus:        "added",
        gittyup.objects.RenamedStatus:      "renamed",
        gittyup.objects.RemovedStatus:      "removed",
        gittyup.objects.ModifiedStatus:     "modified",
        gittyup.objects.KilledStatus:       "killed",
        gittyup.objects.UntrackedStatus:    "untracked",
        gittyup.objects.MissingStatus:      "missing"
    }

    STATUSES_FOR_REVERT = [
        "missing",
        "renamed",
        "modified",
        "removed"
    ]

    STATUSES_FOR_ADD = [
        "untracked"
    ]

    STATUSES_FOR_COMMIT = [
        "untracked",
        "missing",
        "renamed",
        "modified",
        "added",
        "removed"
    ]

    STATUSES_FOR_STAGE = [
        "untracked"
    ]

    STATUSES_FOR_UNSTAGE = [
        "added"
    ]

    def __init__(self, repo=None):
        self.vcs = rabbitvcs.vcs.VCS_GIT
        self.interface = "gittyup"
        if repo:
            self.client = GittyupClient(repo)
        else:
            self.client = GittyupClient()

        self.cache = rabbitvcs.vcs.status.StatusCache()

    def set_repository(self, path):
        self.client.set_repository(path)
        self.config = self.client.config

    def config_get(self, key1, key2):
        return self.client._config_get(key1, key2)

    def get_repository(self):
        return self.client.get_repository()

    def find_repository_path(self, path):
        return self.client.find_repository_path(path)

    #
    # Status Methods
    #

    def statuses(self, path, recurse=False, invalidate=False):
        """
        Generates a list of GittyupStatus objects for the specified file.

        @type   path: string
        @param  path: The file to look up.  If the file is a directory, it will
            return a recursive list of child path statuses

        """

        if path in self.cache:
            if invalidate:
                del self.cache[path]
            else:
                return self.cache.find_path_statuses(path)

        gittyup_statuses = self.client.status(path)

        if not len(gittyup_statuses):
            return [rabbitvcs.vcs.status.Status.status_unknown(path)]
        else:
            statuses = []
            for st in gittyup_statuses:
                # gittyup returns status paths relative to the repository root
                # so we need to convert the path to an absolute path
                st.path = self.client.get_absolute_path(st.path)

                # If not recursing, only return the item in question (if a file)
                # or items directly under the path (if a directory)
                cmp_path = os.path.join(path, os.path.basename(st.path))
                if not recurse and cmp_path != st.path and st.path != path:
                    continue

                rabbitvcs_status = rabbitvcs.vcs.status.GitStatus(st)
                self.cache[st.path] = rabbitvcs_status

                statuses.append(rabbitvcs_status)

            return statuses

    def status(self, path, summarize=True, invalidate=False):
        if path in self.cache:
            if invalidate:
                del self.cache[path]
            else:
                st = self.cache[path]
                if summarize:
                    st.summary = st.single
                return st

        all_statuses = self.statuses(path, invalidate=invalidate)

        if summarize:
            path_status = None
            for st in all_statuses:
                if st.path == path:
                    path_status = st
                    break

            if path_status:
                path_status.summary = path_status.single
            else:
                path_status = rabbitvcs.vcs.status.Status.status_unknown(path)
        else:
            path_status = all_statuses[0]

        return path_status

    def is_working_copy(self, path):
        if (os.path.isdir(path) and
                os.path.isdir(os.path.join(path, ".git"))):
            return True
        return False

    def is_in_a_or_a_working_copy(self, path):
        if self.is_working_copy(path):
            return True

        return (self.find_repository_path(os.path.split(path)[0]) != "")

    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True

        st = self.status(path)
        try:
            return st.is_versioned()
        except Exception as e:
            log.error(e)
            return False

        return False

    def is_locked(self, path):
        return False

    def get_items(self, paths, statuses=[]):
        """
        Retrieves a list of files that have one of a set of statuses

        @type   paths:      list
        @param  paths:      A list of paths or files.

        @type   statuses:   list
        @param  statuses:   A list of statuses.

        @rtype:             list
        @return:            A list of GittyupStatus objects.

        """

        if paths is None:
            return []

        items = []
        for path in paths:
            st = self.statuses(path, recurse=True, invalidate=True)
            for st_item in st:
                if st_item.content == "modified" and os.path.isdir(st_item.path):
                    continue

                if st_item.content in statuses or len(statuses) == 0:
                    items.append(st_item)

        return items

    def revision(self, value):
        """
        Create a revision object usable by pysvn

        @type   kind:   string
        @param  kind:   HEAD or a sha1 hash

        @type   value: integer
        @param  value: Used for kind=number, specifies the revision hash.

        @rtype:         Revision object
        @return:        A Revision object.

        """
        if value is None:
            return Revision("WORKING")

        value_upper = value.upper()
        if value_upper == "HEAD" or value_upper == "BASE":
            return Revision("HEAD")
        elif value_upper == "WORKING":
            return Revision("WORKING")
        else:
            return Revision("hash", value)

    def add(self, paths, recurse=True):
        """
        Add files to a git repository.

        @type   paths:      list
        @param  paths:      A list of paths or files.

        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children

        """

        return self.stage(paths)

    def is_tracking(self, name):
        return self.client.is_tracking("refs/heads/%s" % name)


    #
    # Action Methods
    #

    def initialize_repository(self, path, bare=False):
        """
        Initialize a Git repository

        @type   path: string
        @param  path: The folder to initialize as a repository

        @type   bare: boolean
        @param  bare: Whether the repository should be "bare" or not

        """

        return self.client.initialize_repository(path, bare)

    def stage(self, paths):
        """
        Stage files to be committed or tracked

        @type   paths: list
        @param  paths: A list of files

        """

        return self.client.stage(paths)

    def stage_all(self):
        """
        Stage all files in a repository to be committed or tracked

        """

        return self.client.stage_all()

    def unstage(self, paths):
        """
        Unstage files so they are not committed or tracked

        @type   paths: list
        @param  paths: A list of files

        """

        return self.client.unstage(paths)

    def unstage_all(self):
        """
        Unstage all files so they are not committed or tracked

        @type   paths: list
        @param  paths: A list of files

        """

        return self.client.unstage_all()

    def branch(self, name, revision=Revision("head"), track=False):
        """
        Create a new branch

        @type   name: string
        @param  name: The name of the new branch

        @type   revision: git.Revision
        @param  revision: A revision to branch from.

        @type   track: boolean
        @param  track: Whether or not to track the new branch, or just create it

        """

        return self.client.branch(name, revision.primitive(), track)

    def branch_delete(self, name):
        """
        Delete a branch

        @type   name: string
        @param  name: The name of the branch

        """

        return self.client.branch_delete(name)

    def branch_rename(self, old_name, new_name):
        """
        Rename a branch

        @type   old_name: string
        @param  old_name: The name of the branch to be renamed

        @type   new_name: string
        @param  new_name: The name of the new branch

        """

        return self.client.branch_rename(old_name, new_name)

    def branch_list(self, revision=None):
        """
        List all branches

        """

        revision_str = None
        if revision:
            revision_str = revision.primitive()

        results = self.client.branch_list(revision_str)
        branches = []
        for result in results:
            branches.append(BranchEntry(
                result["name"],
                result["tracking"],
                result["revision"],
                result["message"]
            ))

        return branches

    def get_active_branch(self):
        results = self.client.branch_list()
        for result in results:
            if result["tracking"]:
                return BranchEntry(
                    result["name"],
                    result["tracking"],
                    result["revision"],
                    result["message"]
                )

        return None

    def checkout(self, paths=[], revision=Revision("HEAD")):
        """
        Checkout a series of paths from a tree or commit.  If no tree or commit
        information is given, it will check out the files from head.  If no
        paths are given, all files will be checked out from head.

        @type   paths: list
        @param  paths: A list of files to checkout

        @type   revision: git.Revision
        @param  revision: The revision object or branch to checkout

        """

        return self.client.checkout(paths, revision.primitive())

    def clone(self, host, path, bare=False, origin="origin"):
        """
        Clone a repository

        @type   host: string
        @param  host: The url of the git repository

        @type   path: string
        @param  path: The path to clone to

        @type   bare: boolean
        @param  bare: Create a bare repository or not

        @type   origin: string
        @param  origin: Specify the origin of the repository

        """

        return self.client.clone(host, path, bare, origin)

    def commit(self, message, parents=None, committer=None, commit_time=None,
            commit_timezone=None, author=None, author_time=None,
            author_timezone=None, encoding=None, commit_all=False):
        """
        Commit staged files to the local repository

        @type   message: string
        @param  message: The log message

        @type   parents: list
        @param  parents: A list of parent SHAs.  Defaults to head.

        @type   committer: string
        @param  committer: The person committing.  Defaults to
            "user.name <user.email>"

        @type   commit_time: int
        @param  commit_time: The commit time.  Defaults to time.time()

        @type   commit_timezone: int
        @param  commit_timezone: The commit timezone.
            Defaults to (-1 * time.timezone)

        @type   author: string
        @param  author: The author of the file changes.  Defaults to
            "user.name <user.email>"

        @type   author_time: int
        @param  author_time: The author time.  Defaults to time.time()

        @type   author_timezone: int
        @param  author_timezone: The author timezone.
            Defaults to (-1 * time.timezone)

        @type   encoding: string
        @param  encoding: The encoding of the commit.  Defaults to UTF-8.

        @type   commit_all: boolean
        @param  commit_all: Stage all changed files before committing

        """

        return self.client.commit(message, parents, committer, commit_time,
            commit_timezone, author, author_time, author_timezone, encoding,
            commit_all)

    def remove(self, paths):
        """
        Remove path from the repository.  Also deletes the local file.

        @type   paths: list
        @param  paths: A list of paths to remove

        """

        return self.client.remove(paths)

    def move(self, source, dest):
        """
        Move a file within the repository

        @type   source: string
        @param  source: The source file

        @type   dest: string
        @param  dest: The destination.  If dest exists as a directory, source
            will be added as a child.  Otherwise, source will be renamed to
            dest.

        """

        return self.client.move(source, dest)

    def pull(self, repository="origin", refspec="master", options=None):
        """
        Fetch objects from a remote repository and merge with the local
            repository

        @type   repository: string
        @param  repository: The name of the repository

        @type   refspec: string
        @param  refspec: The branch name to pull from

        """

        return self.client.pull(repository, refspec, options)

    def push(self, repository="origin", refspec="master", tags=True, force_with_lease=False):
        """
        Push objects from the local repository into the remote repository
            and merge them.

        @type   repository: string
        @param  repository: The name of the repository

        @type   refspec: string
        @param  refspec: The branch name to pull from

        @type   tags: boolean
        @param  tags: True to include tags in push, False to omit

        """

        return self.client.push(repository, refspec, tags, force_with_lease)

    def fetch_all(self):
        """
        Fetch objects from all remote repositories.  This will not merge the files
        into the local working copy, use pull for that.
        """

        return self.client.fetch_all()

    def fetch(self, repository, branch=None):
        """
        Fetch objects from a remote repository.  This will not merge the files
        into the local working copy, use pull for that.

        If branch if provided, fetch only for that branch.

        @type   repository: string
        @param  repository: The git remote from which to fetch

        @type   branch: string
        @param  branch: The branch from which to fetch

        """

        return self.client.fetch(repository, branch)

    def merge(self, branch):
        return self.client.merge(branch.primitive())

    def remote_add(self, name, host):
        """
        Add a remote repository

        @type   name: string
        @param  name: The name to give to the remote repository

        @type   host: string
        @param  host: The git url to add

        """

        return self.client.remote_add(name, host)

    def remote_delete(self, name):
        """
        Remove a remote repository

        @type   name: string
        @param  name: The name of the remote repository to remove

        """

        return self.client.remote_delete(name)

    def remote_rename(self, current_name, new_name):
        """
        Rename a remote repository

        @type   current_name: string
        @param  current_name: The current name of the repository

        @type   new_name: string
        @param  new_name: The name to give to the remote repository

        """

        return self.client.remote_rename(current_name, new_name)

    def remote_set_url(self, name, url):
        """
        Change a remote repository's url

        @type   name: string
        @param  name: The name of the repository

        @type   url: string
        @param  url: The url for the repository

        """

        return self.client.remote_set_url(name, url)

    def remote_list(self):
        """
        Return a list of the remote repositories

        @rtype  list
        @return A list of dicts with keys: remote, url, fetch

        """

        return self.client.remote_list()

    def tag(self, name, message, revision):
        """
        Create a tag object

        @type   name: string
        @param  name: The name to give the tag

        @type   message: string
        @param  message: A log message

        @type   revision: git.Revision
        @param  revision: The revision to tag.  Defaults to HEAD

        """

        return self.client.tag(name, message, revision.primitive())

    def tag_delete(self, name):
        """
        Delete a tag

        @type   name: string
        @param  name: The name of the tag to delete

        """

        return self.client.tag_delete(name)

    def tag_list(self):
        """
        Return a list of Tag objects

        """

        return self.client.tag_list()


    def log(self, path=None, skip=0, limit=None, revision=Revision("HEAD"), showtype="all"):
        """
        Returns a revision history list

        @type   path    string
        @param  path    If a path is specified, return commits that contain
                        changes to the specified path only

        @type   revision git.Revision
        @param  revision Determines which branch to find commits for

        @type   start_point sha1 hash string
        @param  start_point Start at a given revision

        @type   limit   int
        @param  limit   If given, returns a limited number of commits

        @type   refspec string
        @param  refspec Return commits in this refspec only

        @type   showtype string
        @type   showtype Determines which revisions to show.  "all" shows all revisions,
            "branch" shows just the branch given in refspec

        @returns    A list of commits

        """

        # The strptime method relies on locales to work, and may not work with non en_US locales
        # Temporarily change the locale to en_US so strptime can work consistently
        # Then change it back at the end of the method
        import locale
        current_locale = locale.getlocale()
        if current_locale[0] is not None:
            locale.setlocale(locale.LC_ALL, "C")

        items = self.client.log(path, skip, limit, revision.primitive(), showtype)
        returner = []
        for item in items:
            revision = self.revision(item["commit"])
            date = datetime.strptime(item["commit_date"][0:-6], "%a %b %d %H:%M:%S %Y")

            author = _("(no author)")
            if "committer" in item:
                author = item["committer"]
                pos = author.find("<")
                if pos != -1:
                    author = author[0:pos-1]

            message = ""
            if "message" in item:
                message = item["message"]

            changed_paths = []
            if "changed_paths" in item:
                for changed_path in item["changed_paths"]:
                    action = "+%s/-%s" % (changed_path["additions"], changed_path["removals"])

                    changed_paths.append(rabbitvcs.vcs.log.LogChangedPath(
                        changed_path["path"],
                        action,
                        "", ""
                    ))

            parents = []
            if "parents" in item:
                for parent in item["parents"]:
                    parents.append(self.revision(parent))

            head = False
            if item["commit"] == self.client.head():
                head = True

            returner.append(rabbitvcs.vcs.log.Log(
                date,
                revision,
                author,
                message,
                changed_paths,
                parents,
                head
            ))

        locale.setlocale(locale.LC_ALL, current_locale)

        return returner

    def diff_summarize(self, path1, revision_obj1, path2=None, revision_obj2=None):
        """
        Returns a diff summary between the path(s)/revision(s)

        @type   path1: string
        @param  path1: The absolute path to a file

        @type   revision_obj1: git.Revision()
        @param  revision_obj1: The revision object for path1

        @type   path2: string
        @param  path2: The absolute path to a file

        @type   revision_obj2: git.Revision()
        @param  revision_obj2: The revision object for path2

        """

        summary_raw = self.client.diff_summarize(path1, revision_obj1.primitive(),
            path2, revision_obj2.primitive())

        summary = []
        for item in summary_raw:
            summary.append(rabbitvcs.vcs.log.LogChangedPath(item["path"], item["action"], "", ""))

        return summary

    def annotate(self, path, revision_obj=Revision("head")):
        """
        Returns an annotation for a specified file

        @type   path: string
        @param  path: The absolute path to a tracked file

        @type   revision: string
        @param  revision: HEAD or a sha1 hash

        """

        return self.client.annotate(path, revision_obj.primitive())

    def show(self, path, revision_obj):
        """
        Returns a particular file at a given revision object.

        @type   path: string
        @param  path: The absolute path to a file

        @type   revision_obj: git.Revision()
        @param  revision_obj: The revision object for path

        """

        return self.client.show(path, revision_obj.primitive())

    def diff(self, path1, revision_obj1, path2=None, revision_obj2=None):
        """
        Returns the diff between the path(s)/revision(s)

        @type   path1: string
        @param  path1: The absolute path to a file

        @type   revision_obj1: git.Revision()
        @param  revision_obj1: The revision object for path1

        @type   path2: string
        @param  path2: The absolute path to a file

        @type   revision_obj2: git.Revision()
        @param  revision_obj2: The revision object for path2

        """

        return self.client.diff(path1, revision_obj1.primitive(), path2,
            revision_obj2.primitive())

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

        for file, success, rej_file in helper.parse_patch_output(patch_file, base_dir, 1):

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

    def export(self, path, dest_path, revision):
        """
        Exports a file or directory from a given revision

        @type   path: string
        @param  path: The source file/folder to export

        @type   dest_path: string
        @param  dest_path: The path to put the exported file(s)

        @type   revision: git.Revision
        @param  revision: The revision/tree/commit of the source file being exported

        """

        return self.client.export(path, dest_path, revision.primitive())

    def clean(self, path, remove_dir=True, remove_ignored_too=False,
            remove_only_ignored=False, dry_run=False, force=True):

        return self.client.clean(path, remove_dir, remove_ignored_too,
            remove_only_ignored, dry_run, force)

    def reset(self, path, revision, type=None):
        """
        Reset repository to a specified state

        @type   path: string
        @param  path: The repository file/folder

        @type   revision: git.Revision
        @param  revision: The revision/tree/commit to reset to

        @type   type: string
        @param  type: The type of reset to do.  Can be mixed, soft, hard, merge
        """

        return self.client.reset(path, revision.primitive(), type)

    def get_ignore_files(self, path):
        paths = []
        paths.append(self.client.get_local_ignore_file(path))
        paths += self.client.get_global_ignore_files()

        return paths

    def get_config_files(self, path):
        paths = [self.client.get_local_config_file()]

        return paths

    def set_callback_notify(self, func):
        self.client.set_callback_notify(func)

    def set_callback_progress_update(self, func):
        self.client.set_callback_progress_update (func)

    def set_callback_get_user(self, func):
        self.client.set_callback_get_user(func)

    def set_callback_get_cancel(self, func):
        self.client.set_callback_get_cancel(func)

    def set_callback_cancel(self, func):
        self.client.callback_cancel = func
