from __future__ import absolute_import
import locale
import os

from rabbitvcs.util.log import Log
import rabbitvcs.util.settings
import rabbitvcs.util.helper

log = Log("rabbitvcs.util.locale")

def initialize_locale():
    try:
        settings = rabbitvcs.util.settings.SettingsManager()

        sane_default = locale.getdefaultlocale(['LANG', 'LANGUAGE'])

        # Just try to set the default locale for the user
        locale.setlocale(locale.LC_ALL, sane_default)

        # Now, if the user has set a default, try to apply that
        user_default = settings.get("general", "language")
        if user_default:
            locale.setlocale(locale.LC_ALL, (user_default, sane_default[1]))
    except locale.Error:
        # If the user's environment does not specify an encoding, Python will
        # pick a default which might not be available. It seems to pick
        # ISO8859-1 (latin1), but UTF8 is a better idea on GNU/Linux.
        log.warning("Could not set default locale (LANG: %s)" % os.environ.get("LANG"))
        
        (loc, enc) = sane_default
        
        # We should only try this if we have a region to set as well.
        if loc and enc != "UTF8":
            try:
                locale.setlocale(locale.LC_ALL, (loc, "UTF8"))
                log.warning("Manually set encoding to UTF-8")
            except locale.Error:
                # Nope, no UTF8 either.
                log.warning("Could not set user's locale to UTF-8")
