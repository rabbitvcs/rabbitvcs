#
# objects.py
#


class GittyupStatus(object):
    path = None
    is_staged = False

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return "<Status %s %s>" % (self.path, self.identifier)

    def __eq__(self, other):
        return self.identifier == other.identifier


class NormalStatus(GittyupStatus):
    identifier = "normal"


class AddedStatus(GittyupStatus):
    identifier = "added"


class RenamedStatus(GittyupStatus):
    identifier = "renamed"


class RemovedStatus(GittyupStatus):
    identifier = "removed"


class ModifiedStatus(GittyupStatus):
    identifier = "modified"


class KilledStatus(GittyupStatus):
    identifier = "killed"


class UntrackedStatus(GittyupStatus):
    identifier = "untracked"


class MissingStatus(GittyupStatus):
    identifier = "missing"


class IgnoredStatus(GittyupStatus):
    identifier = "ignored"


class NoStatus(GittyupStatus):
    identifier = ""

    def __eq__(self, other):
        return self.path == other.path


class GittyupObject(object):
    def __init__(self, sha, obj):
        self.sha = sha
        self.obj = obj


class Commit(GittyupObject):
    def __init__(self, sha, obj, changed_paths=[]):
        self.sha = sha
        self.obj = obj
        self.changed_paths = changed_paths

    def __repr__(self):
        return "<Commit %s>" % self.sha

    @property
    def parents(self):
        return self.obj.parents

    @property
    def author(self):
        return self.obj.author

    @property
    def committer(self):
        return self.obj.committer

    @property
    def message(self):
        return self.obj.message

    @property
    def commit_time(self):
        return self.obj.commit_time

    @property
    def commit_timezone(self):
        return self.obj.commit_timezone

    @property
    def author_time(self):
        return self.obj.author_time

    @property
    def author_timezone(self):
        return self.obj.author_timezone

    @property
    def encoding(self):
        return self.obj.encoding

    def __eq__(self, other):
        return self.sha == other.sha


class Tag(GittyupObject):
    def __repr__(self):
        return "<Tag %s>" % self.sha

    @property
    def name(self):
        return self.obj.name

    @property
    def tag_type(self):
        return self.obj.type

    @property
    def message(self):
        return self.obj.message

    @property
    def tagger(self):
        return self.obj.tagger

    @property
    def tag_time(self):
        return self.obj.tag_time

    @property
    def tag_timezone(self):
        return self.obj.tag_timezone


class CommitTag(Commit):
    def __init__(self, name, sha, obj):
        self._name = name
        self.sha = sha
        self.obj = obj

    def __repr__(self):
        return "<Tag %s %s>" % (self.name, self.sha)

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return self.name == other

    @property
    def tag_type(self):
        return ""

    @property
    def message(self):
        return self.obj.message

    @property
    def tagger(self):
        return self.obj.committer

    @property
    def tag_time(self):
        return self.obj.commit_time

    @property
    def tag_timezone(self):
        return self.obj.commit_timezone


class Tree(GittyupObject):
    def __repr__(self):
        return "<Tree %s>" % self.sha


class Branch(Commit):
    def __init__(self, name, sha, obj):
        self._name = name
        self.sha = sha
        self.obj = obj

    def __repr__(self):
        return "<Branch %s %s>" % (self.name, self.sha)

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return self.name == other
