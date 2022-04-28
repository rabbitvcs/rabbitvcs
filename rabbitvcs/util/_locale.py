from __future__ import absolute_import
import locale
import os

from rabbitvcs.util.log import Log
import rabbitvcs.util.settings
import rabbitvcs.util.helper
from rabbitvcs import gettext

log = Log("rabbitvcs.util.locale")


def get_locale():
    loc = locale.getlocale(locale.LC_MESSAGES)
    if loc[0] is None and loc[1] is None:
        locale.setlocale(locale.LC_MESSAGES, "")
        loc = locale.getlocale(locale.LC_MESSAGES)
        locale.setlocale(locale.LC_MESSAGES, (None, None))
    return (loc[0] or "", loc[1] or "")


def set_locale(language, encoding):
    sane_default = get_locale()
    loc = language
    if not encoding:
        if not language:
            return sane_default
        encoding = sane_default[1]
    if not loc:
        loc = sane_default[0]

    try:
        locale.setlocale(locale.LC_ALL, (loc, encoding))
    except locale.Error:
        # If the user's environment does not specify an encoding, Python will
        # pick a default which might not be available. It seems to pick
        # ISO8859-1 (latin1), but UTF8 is a better idea on GNU/Linux.
        log.warning("Could not set locale (%s, %s)" % (loc, encoding))

        # We should only try this if we have a region to set as well.
        if language and encoding != "UTF-8":
            try:
                locale.setlocale(locale.LC_ALL, (language, "UTF-8"))
                log.warning("Manually set encoding to UTF-8")
            except locale.Error:
                # Nope, no UTF-8 either.
                log.warning("Could not set user's locale to UTF-8")

    loc = locale.getlocale(locale.LC_MESSAGES)
    langs = []
    if loc[0]:
        langs.append(loc[0])
    gettext.set_language(langs)
    return loc


def initialize_locale():
    sane_default = locale.getdefaultlocale(["LANG", "LANGUAGE"])
    # Just try to set the default locale for the user
    set_locale(*sane_default)
