"""
Dummy nautilus module for testing.  It should provide the bare minimum
to get the RabbitVCS extension to load properly.

"""


class InfoProvider(object):
    pass


class MenuProvider(object):
    pass


class ColumnProvider(object):
    pass


class NautilusVFSFile(object):
    def add_string_attribute(self, key, value):
        """Pretend to add a string attribute."""
        pass
