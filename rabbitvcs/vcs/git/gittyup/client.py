#
# client.py
#

import os
import os.path
import re
import shutil
import fnmatch
import time
from datetime import datetime
from mimetypes import guess_type

import subprocess

import dulwich.errors
import dulwich.repo
import dulwich.porcelain
import dulwich.objects
from dulwich.pack import Pack
from dulwich.index import commit_index, write_index_dict, SHA1Writer
#from dulwich.patch import write_tree_diff

from exceptions import *
import util
from objects import *
from command import GittyupCommand

import Tkinter
import tkMessageBox

ENCODING = "UTF-8"

def callback_notify_null(val):
    pass

def callback_get_cancel():
    return False

def get_tmp_path(filename):
    tmpdir = "/tmp/rabbitvcs"
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)

class GittyupClient:
    def __init__(self, path=None, create=False):
        self.callback_notify = callback_notify_null
        self.callback_progress_update = None
        self.callback_get_cancel = callback_get_cancel

        self.global_ignore_patterns = []
        
        self.git_version = None

        self.numberOfCommandStages = 0
        self.numberOfCommandStagesExecuted = 0

        if path:
            try:
                self.repo = dulwich.repo.Repo(path)
                self._load_config()
                self.global_ignore_patterns = self._get_global_ignore_patterns()
            except dulwich.errors.NotGitRepository:
                if create:
                    self.initialize_repository(path)
                    self.global_ignore_patterns = self._get_global_ignore_patterns()
                else:
                    raise NotRepositoryError()
        else:
            self.repo = None

    #
    # Start Private Methods
    #

    def _initialize_index(self):
        index_path = self.repo.index_path()
        f = open(index_path, "wb")
        try:
            f = SHA1Writer(f)
            write_index_dict(f, {})
        finally:
            f.close()

    def _get_index(self):
        if not self.repo.has_index():
            self._initialize_index()
        
        return self.repo.open_index()
    
    def _get_tree_at_head(self):
        try:
            tree = self.repo[self.repo[self.repo.head()].tree]
        except KeyError, e:
            tree = dulwich.objects.Tree()

        return tree

    def _get_working_tree(self):
        return self.repo[commit_index(self.repo.object_store, self._get_index())]

    def _get_tree_from_sha1(self, sha1):
        return self.repo[self.repo[sha1].tree]

    def _get_tree_index(self, tree=None):
        if tree is None:
            tree = self._get_tree_at_head()

        tree_index = {}
        if tree:
            for item in self.repo.object_store.iter_tree_contents(tree.id):
                tree_index[item[0]] = (item[1], item[2])
        return tree_index

    def _get_git_version(self):
        """
        Gets the local git version
        """
        
        if self.git_version:
            return self.git_version
        else:
            try:
                proc = subprocess.Popen(["git", "--version"], stdout=subprocess.PIPE)
                response = proc.communicate()[0].split()
                version = response[2].split(".")
                self.git_version = version
                return self.git_version
            except Exception, e:
                return None

    def _version_greater_than(self, version1, version2):
        len1 = len(version1)
        len2 = len(version2)
        
        max = 5

        # Pad the version lists so they are the same length
        if max > len1:
            version1 += [0] * (max-len1)
        if max > len2:
            version2 += [0] * (max-len2)

        if version1[0] > version2[0]:
            return True

        if (version1[0] == version2[0]
                and version1[1] > version2[1]):
            return True

        if (version1[0] == version2[0]
                and version1[1] == version2[1]
                and version1[2] > version2[2]):
            return True

        if (version1[0] == version2[0]
                and version1[1] == version2[1]
                and version1[2] == version2[2]
                and version1[3] > version2[3]):
            return True

        if (version1[0] == version2[0]
                and version1[1] == version2[1]
                and version1[2] == version2[2]
                and version1[3] == version2[3]
                and version1[4] > version2[4]):
            return True

        return False

    def _get_global_ignore_patterns(self):
        """
        Get ignore patterns from $GIT_DIR/info/exclude then from
        core.excludesfile in gitconfig.
        
        """
        patterns = []
        
        files = self.get_global_ignore_files()
        for path in files:
            patterns += self.get_ignore_patterns_from_file(path)

        return patterns
    
    def get_global_ignore_files(self):
        """
        Returns a list of ignore files possible for this repository
        """
    
        try:
            git_dir = os.environ["GIT_DIR"]
        except KeyError:
            git_dir = os.path.join(self.repo.path, ".git")

        files = []

        excludefile = os.path.join(git_dir, "info", "exclude")
        files.append(excludefile)
        
        try:
            core_excludesfile = self.config.get(("core", ), "excludesfile")
            if core_excludesfile:
                files.append(core_excludesfile)
        except KeyError:
            pass

        return files
    
    def get_local_ignore_file(self, path):
        if not os.path.exists(path):
            return []
        
        if os.path.isfile(path):
            path = os.path.basename(path)
    
        return os.path.join(path, ".gitignore")
    
    def get_ignore_patterns_from_file(self, path):
        """
        Read in an ignore patterns file (i.e. .gitignore, $GIT_DIR/info/exclude)
        and return a list of patterns
        """
        
        patterns = []
        if os.path.isfile(path):
            file = open(path, "r")
            try:
                for line in file:
                    if line == "" or line.startswith("#"):
                        continue

                    patterns.append(line.rstrip("\n"))
            finally:
                file.close()
        
        return patterns

    def get_local_config_file(self):
        try:
            git_dir = os.environ["GIT_DIR"]
        except KeyError:
            git_dir = os.path.join(self.repo.path, ".git")
            
        return git_dir + "/config"

    def _ignore_file(self, patterns, filename):
        """
        Determine whether the given file should be ignored

        """
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern) and not pattern.startswith("!"):
                return True

        return False
    
    def _read_directory_tree(self, path, show_ignored_files=False):
        files = []
        directories = []
        for root, dirs, filenames in os.walk(path, topdown=True):
            try:
                dirs.remove(".git")
                removed_git_dir = True
            except ValueError:
                pass

            # Find the relative root path of this folder
            if root == self.repo.path:
                rel_root = ""
            else:
                rel_root = self.get_relative_path(root)

            for filename in filenames:
                files.append(os.path.join(rel_root, filename))
        
            for _d in dirs:
                directories.append(os.path.join(rel_root, _d))

            directories.append(rel_root)
        
        #Remove duplicates in list
        directories=list(set(directories))
        return (sorted(files), directories)

    def _get_blob_from_file(self, path):
        file = open(path, "rb")
        try:
            blob = dulwich.objects.Blob.from_string(file.read())
        finally:
            file.close()
        
        return blob

    def _write_blob_to_file(self, path, blob):
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
    
        file = open(path, "wb")
        try:
            file.write(blob.data)
        finally:
            file.close()

    def _load_config(self):
        self.config = self.repo.get_config_stack()

   
    def _write_packed_refs(self, refs):
        packed_refs_str = ""
        for ref,sha in refs.items():
            packed_refs_str = "%s %s\n" % (sha, ref)
        
        fd = open(os.path.join(self.repo.controldir(), "packed-refs"), "wb")
        fd.write(packed_refs_str)
        fd.close()
    
    def _remove_from_index(self, index, key):
        del index._byname[key]
    
    #
    # Start Public Methods
    #
    
    def initialize_repository(self, path, bare=False):
        if not os.path.isdir(path):
            os.mkdir(path)

        if bare:
            dulwich.repo.Repo.init_bare(path)
        else:
            dulwich.repo.Repo.init(path)
        self.set_repository(path)

    def set_repository(self, path):
        try:
            self.repo = dulwich.repo.Repo(path)
            self._load_config()
        except dulwich.errors.NotGitRepository:
            raise NotRepositoryError()

    def get_repository(self):
        return self.repo.path

    def find_repository_path(self, path):
        path_to_check = path
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".git")):
                return path_to_check
            
            path_to_check = os.path.split(path_to_check)[0]
        
        return None

    def get_relative_path(self, path):
        if path == self.repo.path:
            return ""

        return util.relativepath(self.repo.path, path)
    
    def get_absolute_path(self, path):
        return os.path.join(self.repo.path, path).rstrip("/")

    def track(self, name):
        self.repo.refs.set_symbolic_ref("HEAD", name)

    def is_tracking(self, name):
        return (self.repo.refs.read_ref("HEAD")[5:] == name)

    def tracking(self):
        return self.repo.refs.read_ref("HEAD")[5:]
    
    def head(self):
        return self.repo.refs["HEAD"]
    
    def get_sha1_from_refspec(self, refspec):
        if refspec in self.repo.refs:
            return self.repo.refs[refspec]
        else:
            return None
    
    def stage(self, paths):
        """
        Stage files to be committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        index = self._get_index()
        to_stage = []

        if type(paths) in (str, unicode):
            paths = [paths]

        for path in paths:
            relative_path = self.get_relative_path(path)
            absolute_path = self.get_absolute_path(path)

            self.notify({
                "action": "Staged",
                "path": absolute_path,
                "mime_type": guess_type(absolute_path)[0]
            })
            to_stage.append(path)
        self.repo.stage(to_stage)
    
    def stage_all(self):
        """
        Stage all files in a repository to be committed or tracked
        
        """
        
        index = self._get_index()
        for status in self.status():
            if status in [AddedStatus, RemovedStatus, ModifiedStatus]:
                abs_path = self.get_absolute_path(status.path)
                if os.path.isfile(abs_path):
                    self.stage(abs_path)

            if status == MissingStatus:
                self._remove_from_index(index, status.path)
                index.write()

    def unstage(self, paths):
        """
        Unstage files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        index = self._get_index()
        tree = self._get_tree_index()

        if type(paths) in (str, unicode):
            paths = [paths]

        for path in paths:
            relative_path = self.get_relative_path(path)
            if relative_path in index:
                if relative_path in tree:
                    (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
                    (mode, blob_id) = tree[relative_path]
                    
                    # If the file is locally modified, set these vars to 0
                    # I'm not sure yet why this needs to happen, but it does
                    # in order for the file to appear modified and not normal
                    blob = self._get_blob_from_file(path)
                    if blob.id != blob_id:
                        ctime = 0
                        mtime = 0
                        dev = 0
                        ino = 0
                        uid = 0
                        gid = 0
                        size = 0
                    
                    index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags)
                else:
                    self._remove_from_index(index, relative_path)
            else:
                if relative_path in tree:
                    index[relative_path] = (0, 0, 0, 0, tree[relative_path][0], 0, 0, 0, tree[relative_path][1], 0)

        self.notify({
            "action": "Unstaged",
            "path": path,
            "mime_type": guess_type(path)[0]
        })
        index.write()
            
    def unstage_all(self):
        """
        Unstage all files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        index = self._get_index()
        for status in self.status():
            abs_path = self.get_absolute_path(status.path)
            if os.path.isfile(abs_path):
                self.unstage(abs_path)
    
    def get_staged(self):
        """
        Gets a list of files that are staged
        
        """

        staged = []
        tree = self._get_tree_at_head()
        index = self._get_index()

        if len(tree) > 0:
            for item in index.changes_from_tree(self.repo.object_store, tree.id):
                ((old_name, new_name), (old_mode, new_mode), (old_sha, new_sha)) = item

                if new_name:
                    staged.append(new_name)
                if old_name and old_name != new_name:
                    staged.append(old_name)
        else:
            for path in index:
                staged.append(path)

        return staged

    def is_staged(self, path, staged_files=None):
        """
        Determines if the specified path is staged
        
        @type   path: string
        @param  path: A file path
        
        @rtype  boolean
        
        """
        
        if not staged_files:
            staged_files = self.get_staged()
        
        relative_path = self.get_relative_path(path)
        return (relative_path in staged_files)
    
    def branch(self, name, commit_sha=None, track=False):
        """
        Create a new branch
        
        @type   name: string
        @param  name: The name of the new branch
        
        @type   commit_sha: string
        @param  commit_sha: A commit sha to branch from.  If None, branches
                    from head
        
        @type   track: boolean
        @param  track: Whether or not to track the new branch, or just create it
        
        """

        cmd = ["git", "branch"]
        if track:
            cmd.append("-t")

        if commit_sha is None:
            commit_sha = self.repo.head()

        cmd += [name, commit_sha]

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

    def branch_delete(self, name):
        """
        Delete a branch
        
        @type   name: string
        @param  name: The name of the branch
        
        """
        
        ref_name = "refs/heads/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            if self.is_tracking(ref_name):
                self.track("refs/heads/master")
        
            del self.repo.refs[ref_name]

    def branch_rename(self, old_name, new_name):
        """
        Rename a branch

        @type   old_name: string
        @param  old_name: The name of the branch to be renamed

        @type   new_name: string
        @param  new_name: The name of the new branch

        """
        
        old_ref_name = "refs/heads/%s" % old_name
        new_ref_name = "refs/heads/%s" % new_name
        refs = self.repo.get_refs()
        if old_ref_name in refs:
            self.repo.refs[new_ref_name] = self.repo.refs[old_ref_name]
            if self.is_tracking(old_ref_name):
                self.track(new_ref_name)
            
            del self.repo.refs[old_ref_name]

    def branch_list(self, commit_sha=None):
        """
        List all branches
        
        """
        """
        refs = self.repo.get_refs()
        branches = []
        for ref,branch_sha in refs.items():
            if ref.startswith("refs/heads"):
                branch = Branch(ref[11:], branch_sha, self.repo[branch_sha])
                branches.append(branch)
        
        return branches
        """
        cmd = ["git", "branch", "-lv", "--no-abbrev"]
        if commit_sha:
            cmd += ["--contains", commit_sha]

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

        branches = []
        for line in stdout:
            if not line:
                continue
            
            components = line.split()
            if components[0] != "*":
                components.insert(0, "")
            tracking = components.pop(0) == "*" and True or False
            if components[0] == "(no":
                name = components.pop(0) + " " + components.pop(0)
            else:
               name = components.pop(0)
            revision = components.pop(0)
            message = " ".join(components)
            
            branches.append({
                "tracking": tracking,
                "name": name,
                "revision": revision,
                "message": message
            })
        
        return branches

    def checkout(self, paths=[], revision="HEAD"):
        """
        Checkout a series of paths from a tree or commit.  If no tree or commit
        information is given, it will check out the files from head.  If no
        paths are given, all files will be checked out from head.
        
        @type   paths: list
        @param  paths: A list of files to checkout
        
        @type   revision: string
        @param  revision: The sha or branch to checkout

        """

        if len(paths) == 1 and paths[0] == self.repo.path:
            paths = []

        cmd = ["git", "checkout", "-m", revision] + paths

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
        
    
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

        self.numberOfCommandStages = 3

        more = ["-o", "origin","--progress"]
        if bare:
            more.append("--bare")
    
        base_dir = os.path.split(path)[0]
    
        cmd = ["git", "clone", host, path] + more
        
        isUsername = False
        isPassword = False
        self.modifiedHost = host

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=base_dir, notify=self.notify_and_parse_progress, cancel=self.get_cancel).execute()

            if stdout[1].find('could not read Username') > -1:
                # Prompt for username if it does not exist in the url.
                isUsername, originalRemoteUrl = self.promptUsername(self.modifiedHost)

                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl2 = self.promptPassword(self.modifiedHost)
            elif stdout[1].find('could not read Password') > -1:
                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl = self.promptPassword(self.modifiedHost)

            if isUsername == True or isPassword == True:
                # Update the cmd with the username and password.
                cmd = ["git", "clone", self.modifiedHost, path] + more

                # Try again.
                (status, stdout, stderr) = GittyupCommand(cmd, cwd=base_dir, notify=self.notify_and_parse_progress, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

        # If we prompted for a username or password then it will now be written to the config. Remove it now before continuing.
        if isUsername == True or isPassword == True:
            # Load new config.
            self.repo = dulwich.repo.Repo(path)
            self._load_config()

            # Write original url back to config.
            self.config.set("remote \"origin\"", "url", host)
            self.config.write()            
    
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
        if commit_all:
            self.stage_all()

        initial_commit = False

        if encoding is None:
            encoding = ENCODING

        commit_id = self.repo.do_commit(message=message, committer=committer,
                commit_timestamp=commit_time, commit_timezone=commit_timezone,
                author=author, author_timestamp=author_time,
                author_timezone=author_timezone, encoding=encoding,
                merge_heads=parents)

        branch_full = self.repo.refs.read_ref("HEAD")

        if branch_full is not None:
            branch_components = re.search("refs/heads/(.+)", branch_full)

            if (branch_components != None):
                branch = branch_components.group(1)

                self.notify("[" + commit_id + "] -> " + branch)
                self.notify("To branch: " + branch)

        #Print tree changes.
        #dulwich.patch.write_tree_diff(sys.stdout, self.repo.object_store, commit.tree, commit.id)

        return commit_id

    def remove(self, paths):
        """
        Remove path from the repository.  Also deletes the local file.
        
        @type   paths: list
        @param  paths: A list of paths to remove
        
        """
        
        if type(paths) in (str, unicode):
            paths = [paths]

        index = self._get_index()
        
        for path in paths:
            relative_path = self.get_relative_path(path)
            if relative_path in index:
                self._remove_from_index(index, relative_path)
                os.remove(path)

        index.write()        
    
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
        
        index = self._get_index()
        relative_source = self.get_relative_path(source)
        relative_dest = self.get_relative_path(dest)

        # Get a list of affected files so we can update the index
        source_files = []
        if os.path.isdir(source):
            for name in index:
                if name.startswith(relative_source):
                    source_files.append(name)
        else:
            source_files.append(self.get_relative_path(source))

        # Rename the affected index entries
        for source_file in source_files:
            new_path = source_file.replace(relative_source, relative_dest)            
            if os.path.isdir(dest):
                new_path = os.path.join(new_path, os.path.basename(source_file))

            index[new_path] = index[source_file]
            self._remove_from_index(index, source_file)

        index.write()
        
        # Actually move the file/folder
        shutil.move(source, dest)

    def pull(self, repository="origin", refspec="master", options=None):
        """
        Fetch objects from a remote repository and merge with the local 
            repository
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """
        self.numberOfCommandStages = 2

        cmd = ["git", "pull", "--progress"]

        if options != None:
            if options.count("rebase"):
                cmd.append("--rebase")

            if options.count("all"):
                cmd.append("--all")
            else:
                cmd.append (repository)
                cmd.append (refspec)

        # Setup the section name in the config for the remote target.
        remoteKey = "remote \"" + repository + "\""
        isUsername = False
        isPassword = False

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify_and_parse_git_push, cancel=self.get_cancel).execute()
            if stdout[0].find('could not read Username') > -1:
                # Prompt for username if it does not exist in the url.
                isUsername, originalRemoteUrl = self.promptUsername(remoteKey)

                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl2 = self.promptPassword(remoteKey)
            elif stdout[0].find('could not read Password') > -1:
                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl = self.promptPassword(remoteKey)

            if isUsername == True or isPassword == True:
                # Try again.
                (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify_and_parse_git_push, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

        # If we prompted for a password and write it to the config, remove it now before continuing.
        if isUsername == True or isPassword == True:
            # Write original url back to config.
            self.config.set(remoteKey, "url", originalRemoteUrl)
            self.config.write()

    def push(self, repository="origin", refspec="master"):
        """
        Push objects from the local repository into the remote repository
            and merge them.
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """

        self.numberOfCommandStages = 2

        cmd = ["git", "push", "--progress", repository, refspec]

        # Setup the section name in the config for the remote target.
        remoteKey = "remote \"" + repository + "\""
        isUsername = False
        isPassword = False

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify_and_parse_git_push, cancel=self.get_cancel).execute()
            if stdout[0].find('could not read Username') > -1:
                # Prompt for username if it does not exist in the url.
                isUsername, originalRemoteUrl = self.promptUsername(remoteKey)

                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl2 = self.promptPassword(remoteKey)
            elif stdout[0].find('could not read Password') > -1:
                # Prompt for password if a username exists in the remote url without a password.
                isPassword, originalRemoteUrl = self.promptPassword(remoteKey)

            if isUsername == True or isPassword == True:
                # Try again.
                (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify_and_parse_git_push, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

        # If we prompted for a password and write it to the config, remove it now before continuing.
        if isUsername == True or isPassword == True:
            # Write original url back to config.
            self.config.set(remoteKey, "url", originalRemoteUrl)
            self.config.write()

    def onUsername(self, window, username, remoteKey, originalRemoteUrl, isOk):
        if isOk == True:
            if username == "":
                tkMessageBox.showinfo("debug", "Please enter a username.", parent=window)
                return
            else:
                # Insert password into url.
                newRemoteUrl = originalRemoteUrl.replace("://", "://" + username + "@")

                if remoteKey.find("://") == -1:
                    # Write url temporarily back to config.
                    self.config.set(remoteKey, "url", newRemoteUrl)
                    self.config.write()
                else:
                    # Change the url in memory, since we don't have a config yet.
                    self.modifiedHost = newRemoteUrl

        # Close dialog.
        window.destroy()

    def onPassword(self, window, password, remoteKey, originalRemoteUrl, isOk):
        if isOk == True:
            if password == "":
                tkMessageBox.showinfo("debug", "Please enter a password.", parent=window)
                return
            else:
                # Insert password into url.
                newRemoteUrl = originalRemoteUrl.replace("@", ":" + password + "@")

                if remoteKey.find("://") == -1:
                    # Write url temporarily back to config.
                    self.config.set(remoteKey, "url", newRemoteUrl)
                    self.config.write()
                else:
                    # Change the url in memory, since we don't have a config yet.
                    self.modifiedHost = newRemoteUrl

        # Close dialog.
        window.destroy()

    def promptUsername(self, remoteKey):
        """
        If the github url contains no username, prompt for one and write the url back to the config.
        Note, we'll set the url back to its original (without the password) after the call completes.
        https://user@github.com/path/repositoryName.git
        """
        isUsername = False
        originalRemoteUrl = remoteKey
        self.modifiedHost = originalRemoteUrl

        if remoteKey.find("://") == -1:
            # Get existing url from config, otherwise just use what was provided (the url from cloning, etc).
            originalRemoteUrl = self.config.get(remoteKey, "url")

        if originalRemoteUrl.find('@') == -1:
            # No username or password. Prompt for both. Create dialog.
            window = Tkinter.Tk()

            window.title("Please enter your username")
            window.resizable(0,0)
            window["padx"] = 40
            window["pady"] = 20
            textFrame = Tkinter.Frame(window)

            # Create textbox label.
            entryLabel = Tkinter.Label(textFrame)
            entryLabel["text"] = "Username:"
            entryLabel.pack(side=Tkinter.LEFT)

            # Create textbox.
            entryWidget = Tkinter.Entry(textFrame)
            entryWidget["width"] = 25
            entryWidget.bind("<Return>", (lambda event: self.onUsername(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            entryWidget.bind("<KP_Enter>", (lambda event: self.onUsername(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            entryWidget.pack(side=Tkinter.LEFT)
            entryWidget.focus();

            textFrame.pack()

            # Create OK button.
            button = Tkinter.Button(window, width=5, text="OK", command = (lambda: self.onUsername(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            button.pack(side=Tkinter.RIGHT)

            # Create Cancel button.
            button = Tkinter.Button(window, width=5, text="Cancel", command = (lambda: self.onUsername(window, entryWidget.get(), remoteKey, originalRemoteUrl, False)))
            button.pack(side=Tkinter.RIGHT)

            # Show dialog.
            window.mainloop()

            isUsername = True
    
        return isUsername, originalRemoteUrl

    def promptPassword(self, remoteKey):
        """
        If a username exists in the github url without a password, prompt the user and write the url back to the config.
        Note, we'll set the url back to its original (without the password) after the call completes.
        https://user@github.com/path/repositoryName.git
        """
        isPassword = False
        originalRemoteUrl = remoteKey
        self.modifiedHost = originalRemoteUrl

        if remoteKey.find("://") == -1:
            # Get existing url from config, otherwise just use what was provided (the url from cloning, etc).
            originalRemoteUrl = self.config.get(remoteKey, "url")

        # If the url contains a username (@) without a password (:), then prompt for a password.
        if originalRemoteUrl.find('@') > -1 and originalRemoteUrl.rfind(':') <= 5:
            # Prompt for password. Create dialog.
            window = Tkinter.Tk()

            window.title("Please enter your password")
            window.resizable(0,0)
            window["padx"] = 40
            window["pady"] = 20
            textFrame = Tkinter.Frame(window)

            # Create textbox label.
            entryLabel = Tkinter.Label(textFrame)
            entryLabel["text"] = "Password:"
            entryLabel.pack(side=Tkinter.LEFT)

            # Create textbox.
            entryWidget = Tkinter.Entry(textFrame)
            entryWidget["show"] = "*"
            entryWidget["width"] = 25
            entryWidget.bind("<Return>", (lambda event: self.onPassword(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            entryWidget.bind("<KP_Enter>", (lambda event: self.onPassword(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            entryWidget.pack(side=Tkinter.LEFT)
            entryWidget.focus();

            textFrame.pack()

            # Create OK button.
            button = Tkinter.Button(window, width=5, text="OK", command = (lambda: self.onPassword(window, entryWidget.get(), remoteKey, originalRemoteUrl, True)))
            button.pack(side=Tkinter.RIGHT)

            # Create Cancel button.
            button = Tkinter.Button(window, width=5, text="Cancel", command = (lambda: self.onPassword(window, entryWidget.get(), remoteKey, originalRemoteUrl, False)))
            button.pack(side=Tkinter.RIGHT)

            # Show dialog.
            window.mainloop()

            isPassword = True

        return isPassword, originalRemoteUrl

    def fetch(self, host):
        """
        Fetch objects from a remote repository.  This will not merge the files
            into the local working copy, use pull for that.
        
        @type   host: string
        @param  host: The git url from which to fetch
        
        """
        
        client, host_path = util.get_transport_and_path(host)

        graphwalker = self.repo.get_graph_walker()
        f, commit = self.repo.object_store.add_pack()
        refs = client.fetch_pack(host_path, self.repo.object_store.determine_wants_all, 
                          graphwalker, f.write, self.callback_notify)

        commit()
        
        return refs
    
    def merge(self, branch):
        cmd = ["git", "merge", branch]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
    
    def remote_add(self, name, host):
        """
        Add a remote repository
        
        @type   name: string
        @param  name: The name to give to the remote repository
                
        @type   host: string
        @param  host: The git url to add
        
        """
        
        cmd = ["git", "remote", "add", name, host]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
    
    def remote_rename(self, current_name, new_name):
        """
        Rename a remote repository
        
        @type   current_name: string
        @param  current_name: The current name of the repository
        
        @type   new_name: string
        @param  new_name: The name to give to the remote repository
        
        """
        
        cmd = ["git", "remote", "rename", current_name, new_name]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
    
    def remote_set_url(self, name, url):
        """
        Change a remote repository's url
        
        @type   name: string
        @param  name: The name of the repository
        
        @type   url: string
        @param  url: The url for the repository
        
        """
        
        cmd = ["git", "remote", "set-url", name, url]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
    
    def remote_delete(self, name):
        """
        Remove a remote repository
        
        @type   name: string
        @param  name: The name of the remote repository to remove

        """
        
        cmd = ["git", "remote", "rm", name]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
    
    def remote_list(self):
        """
        Return a list of the remote repositories
        
        @rtype  list
        @return A list of dicts with keys: remote, url, fetch
            
        """
        
        cmd = ["git", "remote", "-v"]

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            stdout = []
            
        returner = []
        for line in stdout:
            components = line.split()
            if components:
                name = components[0]
                host = components[1]
                
                add = True
                for item in returner:
                    if item["name"] == name:
                        add = False
                
                if add: 
                    returner.append({
                        "name": name,
                        "host": host
                    })
                    
        return returner
    
    def tag(self, name, message, revision="HEAD"):
        """
        Create a tag object
        
        @type   name: string
        @param  name: The name to give the tag
        
        @type   message: string
        @param  message: A log message
                
        @type   revision: string
        @param  revision: The revision to tag.  Defaults to HEAD
        
        """
        dulwich.porcelain.tag(self.repo, name, objectish=revision, message=message)

    def tag_delete(self, name):
        """
        Delete a tag
        
        @type   name: string
        @param  name: The name of the tag to delete
        
        """
        
        ref_name = "refs/tags/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            del self.repo.refs[ref_name]
    
    def tag_list(self):
        """
        Return a list of Tag objects

        """
        for name, tag_sha in self.repo.refs.as_dict("refs/tags"):
            if type(self.repo[tag_sha]) == dulwich.objects.Commit:
                tag = CommitTag(name, tag_sha, self.repo[tag_sha])
            else:
                tag = Tag(tag_sha, self.repo[tag_sha])
            tags.append(tag)

        return tags

    def status_porcelain(self, path):
        if os.path.isdir(path):
            (files, directories) = self._read_directory_tree(path)
        else:
            files = [self.get_relative_path(path)]
            directories = []

        files_hash = {}
        for file in files:
            files_hash[file] = True

        cmd = ["git", "status", "--porcelain", path]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
        
        statuses = []
        modified_files = []
        for line in stdout:
            components = re.match("^([\sA-Z\?]+)\s(.*?)$", line)
            if components:
                status = components.group(1)
                strip_status = status.strip()
                path = components.group(2)
               
                if status == " D":
                    statuses.append(MissingStatus(path))
                elif strip_status in ["M", "R", "U"]:
                    statuses.append(ModifiedStatus(path))
                elif strip_status in ["A", "C"]:
                    statuses.append(AddedStatus(path))
                elif strip_status == "D":
                    statuses.append(RemovedStatus(path))
                elif strip_status == "??":
                    statuses.append(UntrackedStatus(path))
                
                modified_files.append(path)
                try:
                    del files_hash[path]
                except Exception, e:
                    pass

        # Determine untracked directories
        cmd = ["git", "clean", "-nd", self.repo.path]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)

        untracked_directories = []
        for line in stdout:
            components = re.match("^(Would remove)\s(.*?)$", line)
            if components:
                untracked_path = components.group(2)
                if untracked_path[-1]=='/':
                    untracked_directories.append(untracked_path[:-1])

        #Determine the ignored files and directories in Repo
        cmd = ["git", "clean", "-ndX", self.repo.path]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
        ignored_directories=[]
        for line in stdout:
            components = re.match("^(Would remove)\s(.*?)$", line)
            if components:
                ignored_path=components.group(2)
                if ignored_path[-1]=='/':
                    ignored_directories.append(ignored_path[:-1])
                    next
                statuses.append(IgnoredStatus(ignored_path))
                self.ignored_paths.append(ignored_path)
                try:
                    del files_hash[ignored_path]
                except Exception, e:
                    pass
        for file,data in files_hash.items():
            ignore_file=False
            untracked_file=False
            for ignored_path in ignored_directories:
                if ignored_path in file:
                    ignore_file=True
                    break
            for untracked_path in untracked_directories:
                if untracked_path in file:
                    untracked_file=True
                    break
            if untracked_file==True:
                statuses.append(UntrackedStatus(file))
                if ignore_file==True:
                    self.ignored_paths.append(file)
            elif ignore_file==True:
                statuses.append(IgnoredStatus(file))
                self.ignored_paths.append(file)
            else:
                statuses.append(NormalStatus(file))

        # Determine status of folders based on child contents
        for d in directories:
            d_status = NormalStatus(d)

            # Check if directory is untracked or a sub-directory of an untracked directory
            for untracked_path in untracked_directories:
                if untracked_path in d:
                    d_status = UntrackedStatus(d)
                    break

            # Check if directory includes modified files
            for file in modified_files:
                if file.startswith(d):
                    d_status = ModifiedStatus(d)
                    break

            # Check if directory is ignored
            for ignored_path in ignored_directories:
                if ignored_path in d:
                    d_status = IgnoredStatus(d)
                    break
            statuses.append(d_status)


        return statuses

    def status_dulwich(self, path):
        tree = self._get_tree_index()        
        index = self._get_index()
        
        if os.path.isdir(path):
            (files, directories) = self._read_directory_tree(path)
        else:
            files = [self.get_relative_path(path)]
            directories = []

        files_hash = {}
        for file in files:
            files_hash[file] = True
        
        statuses = []
        # Calculate statuses for files in the current HEAD
        modified_files = []
        for name in tree:
            try:
                if index[name]:
                    inIndex = True
            except Exception, e:
                inIndex = False

            if inIndex:
                absolute_path = self.get_absolute_path(name)
                if os.path.isfile(absolute_path):
                    # Cached, determine if modified or not
                    blob = self._get_blob_from_file(absolute_path)
                    if blob.id == tree[name][1]:
                        statuses.append(NormalStatus(name))
                    else:
                        modified_files.append(name)
                        statuses.append(ModifiedStatus(name))
                else:
                    modified_files.append(name)
                    statuses.append(MissingStatus(name))
            else:
                modified_files.append(name)
                statuses.append(RemovedStatus(name))

            try:
                del files_hash[name]
            except Exception, e:
                pass

        # Calculate statuses for untracked files
        for name,data in files_hash.items():
            try:
                inTreeIndex = tree[name]
            except Exception, e:
                inTreeIndex = False
            
            try:
                inIndex = index[name]
            except Exception, e:
                inIndex = False
            
            if inIndex and not inTreeIndex:
                modified_files.append(name)
                statuses.append(AddedStatus(name))
                continue

            # Generate a list of appropriate ignore patterns
            patterns = []
            path_to_check = os.path.dirname(self.get_absolute_path(name))
            while path_to_check != self.repo.path:
                patterns += self.get_ignore_patterns_from_file(self.get_local_ignore_file(path_to_check))
                path_to_check = os.path.split(path_to_check)[0]

            patterns += self.get_ignore_patterns_from_file(self.get_local_ignore_file(self.repo.path))
            patterns += self.global_ignore_patterns
            
            if not self._ignore_file(patterns, os.path.basename(name)):
                statuses.append(UntrackedStatus(name))
            else:
                self.ignored_paths.append(name)

        # Determine status of folders based on child contents
        for d in directories:
            d_status = NormalStatus(d)
            
            for file in modified_files:
                if os.path.join(d, os.path.basename(file)) == file:
                    d_status = ModifiedStatus(d)
                    break
            
            statuses.append(d_status)

        return statuses

    def get_all_ignore_file_paths(self, path):
        return self.ignored_paths


    def status(self, path):
        # TODO - simply get this from the status implementation / avoid global state
        self.ignored_paths = []
        version = self._get_git_version()
        if version and self._version_greater_than(version, [1,7,-1]):
            return self.status_porcelain(path)
        else:
            return self.status_dulwich(path)

    def log(self, path="", skip=0, limit=None, revision="", showtype="all"):
        
        cmd = ["git", "--no-pager", "log", "--numstat", "--parents", "--pretty=fuller", 
            "--date-order", "--date=default"]

        if showtype == "all":
            cmd.append("--all")

        if limit:
            cmd.append("-%s" % limit)
        if skip:
            cmd.append("--skip=%s" % skip)
        if revision:
            cmd.append(revision)

        if path == self.repo.path:
            path = ""        
        if path:
            cmd += ["--", path]

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            return []

        revisions = []
        revision = {}
        changed_file = {}
        for line in stdout:
            if line == "":
                continue
            
            if line[0:6] == "commit":
                if revision:
                    if "changed_paths" not in revision:
                        revision["changed_paths"] = {}
                    revisions.append(revision)
            
                revision = {}
                changed_file = {}
                commit_line = line.split(" ")
                revision["commit"] = commit_line[1]
                revision["parents"] = []
                for parent in commit_line[2:]:
                    revision["parents"].append(parent)
            elif line[0:7] == "Author:":
                revision["author"] = line[7:].strip()
            elif line[0:11] == "AuthorDate:":
                revision["author_date"] = line[11:].strip()
            elif line[0:7] == "Commit:":
                revision["committer"] = line[7:].strip()
            elif line[0:11] == "CommitDate:":
                revision["commit_date"] = line[11:].strip()
            elif line[0:4] == "    ":
                message = line[4:]
                if "message" not in revision:
                    revision["message"] = ""
                else:
                    revision["message"] += "\n"
                    
                revision["message"] = revision["message"] + message
            elif line[0].isdigit() or line[0] in "-":
                file_line = line.split("\t")
                if not changed_file:
                    revision["changed_paths"] = []

                if len(file_line) == 3:
                    changed_file = {
                        "additions": file_line[0],
                        "removals": file_line[1],
                        "path": file_line[2]
                    }
                    revision["changed_paths"].append(changed_file)

        if revision:
            revisions.append(revision)

        return revisions
        
    def annotate(self, path, revision_obj="HEAD"):
        """
        Returns an annotation for a specified file
            
        @type   path: string
        @param  path: The absolute path to a tracked file
        
        @type   revision: string
        @param  revision: HEAD or a sha1 hash
        
        """

        relative_path = self.get_relative_path(path)

        cmd = ["git", "annotate", "-l", revision_obj, relative_path]

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            stdout = []

        returner = []
        for line in stdout:
            components = re.split("\t", line, 3)
            if len(components) < 4:
                continue

            dt = datetime(*time.strptime(components[2][:-6],"%Y-%m-%d %H:%M:%S")[:-2])

            message = components[3].split(")", 1)
            code = message[1]
            if len(components) == 5:
                code = components[4]
                
            returner.append({
                "revision": components[0],
                "author": components[1][1:],
                "date": dt,
                "line": code,
                "number": message[0]
            })
        
        return returner

    def show(self, path, revision_obj):
        """
        Returns a particular file at a given revision object.
        
        @type   path: string
        @param  path: The absolute path to a file

        @type   revision_obj: git.Revision()
        @param  revision_obj: The revision object for path
        
        """
        if not revision_obj:
            revision_obj = "HEAD"

        relative_path = self.get_relative_path(path)

        cmd = ["git", "show", "%s:%s" % (revision_obj, relative_path)]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            stdout = []

        return "\n".join(stdout)

    def diff(self, path1, revision_obj1, path2=None, revision_obj2=None, summarize=False):
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
        relative_path1 = None
        relative_path2 = None
        if path1:
            relative_path1 = self.get_relative_path(path1)
        if path2:
            relative_path2 = self.get_relative_path(path2)

        cmd = ["git", "diff"]
        if revision_obj1:
            cmd += [revision_obj1]
        if revision_obj2 and path2:
            cmd += [revision_obj2]
        if relative_path1:
            cmd += [relative_path1]
        if relative_path2 and relative_path2 != relative_path1:
            cmd += [relative_path2]

        if summarize:
            cmd.append("--name-status")
            
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            stdout = []
        
        return "\n".join(stdout)

    def diff_summarize(self, path1, revision_obj1, path2=None, revision_obj2=None):
        results = self.diff(path1, revision_obj1, path2, revision_obj2, True)
        summary = []
        for line in results.split("\n"):
            if not line:
                continue
                
            (action, path) = line.split("\t")
            summary.append({
                "action": action,
                "path": path
            })
        
        return summary

    def export(self, path, dest_path, revision):
        """
        Exports a file or directory from a given revision
        
        @type   path: string
        @param  path: The source file/folder to export
        
        @type   dest_path: string
        @param  dest_path: The path to put the exported file(s)
        
        @type   revision: string
        @param  revision: The revision/tree/commit of the source file being exported

        """
        
        tmp_file = get_tmp_path("rabbitvcs-git-export.tar")
        cmd1 = ["git", "archive", "--format", "tar", "-o", tmp_file, revision, path]
        cmd2 = ["tar", "-xf", tmp_file, "-C", dest_path]
        
        if not os.path.isdir(dest_path):
            os.mkdir(dest_path)

        try:
            (status, stdout, stderr) = GittyupCommand(cmd1, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
            (status, stdout, stderr) = GittyupCommand(cmd2, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            stdout = []
            
        self.notify("%s at %s exported to %s" % (path, revision, dest_path))
        return "\n".join(stdout)      
    
    def clean(self, path, remove_dir=True, remove_ignored_too=False, 
            remove_only_ignored=False, dry_run=False, force=True):
        
        cmd = ["git", "clean"]
        if remove_dir:
            cmd.append("-d")
        
        if remove_ignored_too:
            cmd.append("-x")
        
        if remove_only_ignored:
            cmd.append("-X")
        
        if dry_run:
            cmd.append("-n")
        
        if force:
            cmd.append("-f")
    
        relative_path = self.get_relative_path(path)
        cmd.append(relative_path)
        
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            return

    def reset(self, path, revision, type=None):        
        relative_path = self.get_relative_path(path)
        
        cmd = ["git", "reset"]
        if type:
            cmd.append("--%s" % type)
        
        cmd.append(revision)
        if relative_path:
            cmd.append(relative_path)

        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path, notify=self.notify, cancel=self.get_cancel).execute()
        except GittyupCommandError, e:
            self.callback_notify(e)
            return

    def set_callback_notify(self, func):
        self.callback_notify = func

    def set_callback_progress_update(self, func):
        self.callback_progress_update = func

    def set_callback_get_cancel(self, func):
        self.callback_get_cancel = func
    
    def notify(self, data):
        self.callback_notify(data)
    
    def notify_and_parse_progress(self, data):
        # When progress is requested to a git command, it will
        # respond with the current operation, and that operations current progress
        # in the following format: "<Command>: <percentage>% (<pieces compeated>/<num pieces>)".
        #
        # When a command has reached 100% the format of this final message assumes the formatt:
        #  "<Command>: 100% (<num pieces>/<num pieces>), <total size> <unit>, done."


        returnData = {"action":"","path":"","mime_type":""}

        #print "parsing message: " + str(data)

        # If data is already a dict, we'll assume it's already been parsed, and return.
        if isinstance (data, dict):
            self.notify (data);
            return

        # Is this an error?
        message_components = re.search("^([eE]rror|[fF]atal): (.+)", data)

        if message_components != None:
            returnData["action"] = "Error"
            returnData["path"] = message_components.group(2)
            self.notify (returnData)
            return

        # Check to see if this is a remote command.
        remote_check = re.search("^(remote: )(.+)$", data)

        if remote_check != None:
            returnData["action"] = "Remote"
            message = remote_check.group(2)

        else:
            message = data

        # First, we'll test to see if this is a progress notification.
        if "%" not in message:
            # No, this is just a regular message.
            # Some messages have a strage tendancy to append a non-printable character,
            # followed by a right square brace and a capitol "K".  This tests for, and
            # strips these superfluous characters.
            message_components = re.search("^(.+).\[K", message)
            if message_components != None:
                returnData["path"] = message_components.group(1)
            else:
                returnData["path"] = message

            self.notify (returnData)
            return

        # Extract the percentage, which will be all numerals directly
        # prior to '%'.
        message_components = re.search("^(.+): +([0-9]+)%", message)
        
        if message_components == None:
            print "Error: failed to parse git string: " + data
            return

        fraction = float(message_components.group(2)) / 100 # Convert percentage to fraction.
        current_action = message_components.group(1)

        # If we're at 0%, then we want to notify which action we're performing.
        if fraction == 0:
                returnData["path"] = current_action
                self.notify(returnData)

        #print "stage fraction: " + str (fraction)

        # If we're using a number of stages, adjust the fraction acordingly.
        if self.numberOfCommandStages > 0:
            fraction = (self.numberOfCommandStagesExecuted + fraction) / self.numberOfCommandStages
            
        # If we've finished the current stage (100%).
        if "done" in message:
            self.numberOfCommandStagesExecuted += 1

        # If we've registered a callback for progress, update with the new fraction.
        if self.callback_progress_update != None:
            #print "setting pbar: " + str(fraction)
            self.callback_progress_update(fraction)

        # If we've finished the whole command (all stages).
        if fraction == 1 and "done" in message:
            # Reset stage variables.
            self.numberOfCommandStages = 0
            self.numberOfCommandStagesExecuted = 0

    def notify_and_parse_git_pull (self, data):
        return_data = {"action":"","path":"","mime_type":""}

        message_parsed = False

        # Look for "From" line (e.g. "From ssh://server:22/my_project")
        message_components = re.search("^From (.+)", data)

        if message_components != None:
            return_data["action"] = "From"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Look for "Branch" line (e.g. "* branch   master   -> FETCH_HEAD")
        message_components = re.search("\* branch +([A-z0-9]+) +-> (.+)", data)

        if message_components != None:
            return_data["action"] = "Branch"
            return_data["path"] = message_components.group(1) + " -> " + message_components.group(2)
            message_parsed = True

        # Look for a file line (e.g. "src/somefile.py       | 5 -++++")
        message_components = re.search(" +(.+) +\| *([0-9]+) ([+-]+)", data)

        if message_components != None:
            return_data["action"] = "Modified"
            return_data["path"] = message_components.group(1)
            return_data["mime_type"] = message_components.group(2) + " " + message_components.group(3)
            message_parsed = True

        # Look for a updating line (e.g. "Updating ffffff..ffffff")
        message_components = re.search("^Updating ([a-f0-9.]+)", data)

        if message_components != None:
            return_data["action"] = "Updating"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Look for a "create mode" line (e.g. "create mode 100755 file.py")
        message_components = re.search("create mode ([0-9]+) (.+)", data)

        if message_components != None:
            return_data["action"] = "Create"
            return_data["path"] = message_components.group(2)
            return_data["mime_type"] = "mode: " + message_components.group(1)
            message_parsed = True

        # Look for a "delete mode" line (e.g. "create mode 100755 file.py")
        message_components = re.search("delete mode ([0-9]+) (.+)", data)

        if message_components != None:
            return_data["action"] = "Delete"
            return_data["path"] = message_components.group(2)
            return_data["mime_type"] = "mode: " + message_components.group(1)
            message_parsed = True

        # Look for an "Auto-merging" line (e.g. "Auto-merging src/file.py")
        message_components = re.search("^Auto-merging (.+)", data)

        if message_components != None:
            return_data["action"] = "Merging"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Look for a "binary" line (e.g. "icons/file.png"    | Bin 0 -> 55555 bytes)
        message_components = re.search("^[ ](.+) +\| Bin ([0-9]+ -> [0-9]+ bytes)", data)

        if message_components != None:
            return_data["action"] = "Binary"
            return_data["path"] = message_components.group(1)
            return_data["mime_type"] = message_components.group(2)
            message_parsed = True

        # Look for a "rename" line (e.g. "rename src/{foo.py => bar.py} (50%)")
        message_components = re.search("rename (.+}) \([0-9]+%\)", data)

        if message_components != None:
            return_data["action"] = "Rename"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Look for a "copy" line (e.g. "copy src/{foo.py => bar.py} (50%)")
        message_components = re.search("copy (.+}) \([0-9]+%\)", data)

        if message_components != None:
            return_data["action"] = "Copy"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Prepend "Error" to conflict lines. e.g. :
        # CONFLICT (content): Merge conflict in file.py.
        # Automatic merge failed; fix conflicts and then commit the result.
        message_components = re.search("^CONFLICT \(|Automatic merge failed", data)

        if message_components != None:
            return_data["action"] = "Error"
            return_data["path"] = data
            message_parsed = True

        if message_parsed == False:
            return_data = data

        self.notify_and_parse_progress (return_data)

    def notify_and_parse_git_push (self, data):
        return_data = {"action":"","path":"","mime_type":""}

        message_parsed = False

        # Look for to line. e.g. "To gitosis@server.org:project.git". Exclude any
        # lines that include a space (as this could be a message about something else)
        message_components = re.search("^To ([^ ]+$)", data)

        if message_components != None:
            return_data["action"] = "To"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        # Look for "new branch" line. e.g. " * [new branch]   master -> master"
        message_components = re.search("^ \* \[new branch\] +(.+) -> (.+)", data)

        if message_components != None:
            return_data["action"] = "New Branch"
            return_data["path"] = message_components.group(1) + " -> " + message_components.group(2)
            message_parsed = True

        # Look for "rejected" line. e.g. " ![rejected]   master -> master (non-fast-forward)".
        message_components = re.search("!\[rejected\] +(.+)", data)

        if message_components != None:
            return_data["action"] = "Rejected"
            return_data["path"] = message_components.group(1)
            message_parsed = True

        if message_parsed == False:
            return_data = data

        self.notify_and_parse_progress (return_data)
    
    def get_cancel(self):
        return self.callback_get_cancel
