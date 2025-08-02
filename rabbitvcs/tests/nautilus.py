"""
Dummy nautilus module for testing.  It should provide the bare minimum
to get the RabbitVCS extension to load properly.

"""


class InfoProvider:
    pass


class MenuProvider:
    pass


class ColumnProvider:
    pass


class NautilusVFSFile:
    def add_string_attribute(self, key, value):
        """Pretend to add a string attribute."""
        pass
