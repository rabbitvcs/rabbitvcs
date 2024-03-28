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

Everything related retrieving and storing configuration keys.

"""
from __future__ import absolute_import
from __future__ import print_function

__all__ = ['get_home_folder', 'SettingsManager']

import os
from os.path import dirname

import shutil
import configobj
import validate
import re

from rabbitvcs import package_prefix

MULTILINE_ESCAPE_RE = re.compile(r"""([\\'"])""")
MULTILINE_UNESCAPE_RE = re.compile(r"\\(.)")


def get_home_folder():
    """
    Returns the location of the hidden folder we use in the home dir.
    This is used for storing things like previous commit messages and
    previously used repositories.

    @rtype:     string
    @return:    The location of our main user storage folder.

    """

    # Make sure we adher to the freedesktop.org XDG Base Directory
    # Specifications. $XDG_CONFIG_HOME if set, by default ~/.config
    xdg_config_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
    )
    config_home = os.path.join(xdg_config_home, "rabbitvcs")

    # Make sure the directories are there
    if not os.path.isdir(config_home):
        # FIXME: what if somebody places a file in there?
        os.makedirs(config_home, 0o700)

    return config_home


SETTINGS_FILE = "%s/settings.conf" % get_home_folder()


def find_configspec():
    # Search the following paths for a configspec file
    configspec_paths = [
        os.path.join(dirname(__file__), "configspec/configspec.ini"),
        os.path.join(package_prefix(), "share/rabbitvcs/configspec.ini"),
        "/usr/share/rabbitvcs/configspec.ini",
        "/usr/local/share/rabbitvcs/configspec.ini",
    ]

    for path in configspec_paths:
        if os.path.exists(path):
            return path

    raise IOError("Cannot find a configspec.ini file")


SETTINGS_SPEC = find_configspec()


class SettingsManager(object):
    """
    This class provides an shallow interface for the rest of the program to use
    to interact with our configuration file.

    Usage::

        Get settings:
            sm = SettingsManager()
            diff_tool = sm.get("external", "diff_tool")

        Set settings:
            sm = SettingsManager()
            sm.set("external", "diff_tool", "/usr/bin/meld")
            sm.write()
    """

    def __init__(self):

        self.settings = configobj.ConfigObj(
            infile=SETTINGS_FILE,
            create_empty=True,
            indent_type="    ",
            configspec=SETTINGS_SPEC,
        )

        self.validator = validate.Validator()

        valid = self.settings.validate(self.validator)

        # We cannot use "if not valid" here, since validate() returns a dict
        # if validation fails!
        # See:
        # http://www.voidspace.org.uk/python/articles/configobj.shtml#validation
        if valid is not True:
            # What to do here?
            # We could only get to this point if:
            #   1. The user config file existed
            #   2. It was invalid
            # One option is to copy it to a different file and recreate it...
            log.warning("User configuration not valid. Backing up and recreating.")
            self.backup_and_rewrite_config()

    def get(self, section=None, keyword=None):
        """
        Get the settings for a section and/or keyword
        If no arguments are given, it just returns all settings

        @type section:  string
        @param section: A settings section.

        @type keyword:  string
        @param keyword: A particular setting in a section.

        @rtype:         dictionary or string
        @return:        Either a dictionary or string with setting(s).

        """

        if section is None:
            return self.settings

        if keyword is None:
            return self.settings[section]

        returner = ""
        try:
            returner = self.settings[section][keyword]
        except KeyError:
            print("Error: section %s:%s doesn't exist" % (section, keyword))

        return returner

    def set(self, section, keyword, value=""):
        """
        Set settings for a particular section and keyword

        @type section:  string
        @param section: A settings section.

        @type keyword:  string
        @param keyword: A particular setting in a section.

        @type value:    string or dictionary
        @param value:   Setting value.

        """

        if section not in self.settings:
            self.settings[section] = {}

        self.settings[section][keyword] = value

    # Multilines are escaped to allow them containing '''
    def get_multiline(self, section=None, keyword=None):
        return MULTILINE_UNESCAPE_RE.sub(r"\1", self.get(section, keyword))

    def set_multiline(self, section, keyword, value=""):
        self.set(section, keyword, MULTILINE_ESCAPE_RE.sub(r"\\\1", value))

    def set_comments(self, section, comments=[]):
        """
        Set multi-line comments for a section

        @type section:      string
        @param section:     A settings section.

        @type comments:     list
        @param comments:    A list of strings.

        """

        self.settings.comments[section] = comments

    def set_inline_comments(self, section, comments=""):
        """
        Set inline comments for a section

        @type section:      string
        @param section:     A settings section.

        @type comments:     string
        @param comments:    A single line comment.

        """

        self.settings.inline_comments[section] = comments

    def write(self):
        """
        Write the settings and comments to the settings file

        """

        self.settings.write()

    def clear(self):
        """
        Clear the settings object so that all sections/keywords are gone
        This function does not write-to-file.  Only clears from memory.

        """
        self.settings = configobj.ConfigObj(indent_type="    ")
        self.settings.filename = SETTINGS_FILE
        # Maybe we should use self.settings.reset()?

    def use_default_settings(self):
        """
        Specify a set of default settings and write to file.
        Called when there is no settings.conf present.

        """

        self.settings = configobj.ConfigObj(DEFAULT_SETTINGS, indent_type="    ")
        self.settings.filename = SETTINGS_FILE

    def get_default(self, section, keyword):
        """
        Get the default settings for a section and/or keyword
        If no arguments are given, it just returns all settings

        @type section:  string
        @param section: A settings section.

        @type keyword:  string
        @param keyword: A particular setting in a section.

        @rtype:         dictionary or string
        @return:        Either a dictionary or string with setting(s).

        """

        if section is None:
            return DEFAULT_SETTINGS

        if keyword is None:
            return DEFAULT_SETTINGS[section]

        returner = None
        try:
            returner = DEFAULT_SETTINGS[section][keyword]
        except KeyError:
            print("Error: section %s:%s doesn't exist" % (section, keyword))

        return returner

    def backup_and_rewrite_config(self):
        """
        Backs up the user configuration file (for debugging) and rewrites a
        valid config file.

        The name of the backup file is the name of the settings file plus an
        incremental count.

        """
        # We need to check that the file doesn't already exist, in case this has
        # happened before.
        new_file_free = False
        renumber = 0

        while not new_file_free:
            new_name = "%s.%02i" % (SETTINGS_FILE, renumber)

            # FIXME: is this too paranoid?
            if not os.path.exists(new_name):

                new_file_free = True

                created = False

                try:
                    os.rename(SETTINGS_FILE, new_name)
                    created = True
                except IOError:
                    # Paranoid again?
                    print("Could not back up user configuration.")

                if created:
                    self.settings.reset()
                    self.write()
            else:
                renumber += 1


if __name__ == "__main__":
    pass
