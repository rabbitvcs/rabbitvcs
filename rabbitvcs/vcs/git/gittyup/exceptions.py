#
# exceptions.py
#

class NotRepositoryError(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupCommandError(Exception):
    """Indicates a command returned an error"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
