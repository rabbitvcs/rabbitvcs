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

import os
import gettext as _gettext
from locale import getlocale

# Hack to make RabbitVCS win in the battle against TortoiseHg
try:
    import mercurial.demandimport

    mercurial.demandimport.enable = lambda: None
except Exception as e:
    pass

version = "0.19"
APP_NAME = "RabbitVCS"
TEMP_DIR_PREFIX = "rabbitvcs-"
LOCALE_DIR = "%s/locale" % os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if not os.path.exists(LOCALE_DIR):
    LOCALE_DIR = "/usr/share/locale"

WEBSITE = "http://www.rabbitvcs.org/"

langs = []
language = os.environ.get("LANGUAGE", None)
if language:
    langs += language.split(":")
if getlocale()[0] != None:
    langs += [getlocale()[0]]

_gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
_gettext.textdomain(APP_NAME)
current_translation = None


class gettext(object):
    @staticmethod
    def set_language(langs):
        global current_translation
        current_translation = _gettext.translation(
            APP_NAME, LOCALE_DIR, languages=langs, fallback=True
        )

    @staticmethod
    def gettext(message):
        if not current_translation:
            return message
        return current_translation.gettext(message)

    @staticmethod
    def ngettext(msgid1, msgid2, n):
        return gettext.gettext(msgid1 if n == 1 else msgid2)


gettext.set_language(langs)


def package_name():
    """
    Report the application name in a form appropriate for building
    package files.

    """
    return APP_NAME.lower()


def package_version():
    """
    Report the version number of the application, minus any name
    extensions.

    """
    app_version = version.split("-")[0]
    # TODO: sanity-check app_version: make sure it's just digits and dots
    return app_version


def package_identifier():
    """
    Return a package identifier suitable for use in a package file.

    """
    return "%s-%s" % (package_name(), package_version())


def package_prefix():
    """
    Return the prefix of the local RabbitVCS installation

    """

    try:
        from rabbitvcs.buildinfo import rabbitvcs_prefix

        return rabbitvcs_prefix
    except ImportError as e:
        return ""


def get_icon_path():
    """
    Return the path to the icon folder

    """

    try:
        from rabbitvcs.buildinfo import icon_path

        return icon_path
    except ImportError as e:
        return "%s/data/icons/hicolor" % os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))
        )
