from __future__ import absolute_import
from __future__ import print_function
#!/usr/bin/env python

# If you didn't know already, this is a Python distutils setup script. It borrows
# heavily from Phatch's (see: http://photobatch.stani.be/).
#
# There's a lot of comments here (on purpose) so people can actually learn from
# this and don't have to figure out everything on their own.
#
# This setup script is used to build distribution specific packages.
#
# For more information see: http://docs.python.org/dist/dist.html
#

# TODO: this all feels just a little too shell scripty, refactoring it later 
# might be a good idea.

# NOTES:
# System-wide directories:
# Scalable emblems go in: /usr/share/icons/hicolor/scalable/emblems
#
# User-specific directories:
# Scalable emblems go in: ~/.icons/hicolor/scalable
#
# Common directories
# See: http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
# Configuration information goes in: ~/.config/rabbitvcs/
# Data goes in: ~/.local/share/rabbitvcs

import sys
import os
import os.path
import subprocess
from distutils.core import setup
import distutils.sysconfig

PREFIX = sys.prefix

# If the user passed --prefix=... then use the new prefix
for c in sys.argv:
    if c.startswith("--prefix"):
        PREFIX = c.split("=")[1].lstrip().rstrip()

#==============================================================================
# Variables
#==============================================================================

# Some descriptive variables
# This will eventually be passed to the setup function, but we already need them
# for doing some other stuff so we have to declare them here.
name                = "rabbitvcs"
version             = "0.16.0"
description         = "Easy version control"
long_description    = """RabbitVCS is a set of graphical tools written to provide simple and straightforward access to the version control systems you use."""
author              = "Bruce van der Kooij"
author_email        = "brucevdkooij@gmail.com"
url                 = "http://www.rabbitvcs.org"
license             = "GNU General Public License version 2 or later"

#==============================================================================
# Paths
#==============================================================================

icon_theme_directory = "share/icons/hicolor"
locale_directory = "share/locale"

#==============================================================================
# Helper functions
#==============================================================================

def include_by_pattern(directory, directory_to_install, pattern):
    files_to_include = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(pattern):
                files_to_include.append((
                    root.replace(directory, directory_to_install),
                    [os.path.join(root, file)]
                ))
    return files_to_include

#==============================================================================
# Gather all the files that need to be included
#==============================================================================

# Packages
packages = []
for root, dirs, files in os.walk("rabbitvcs"):
    if "__init__.py" in files:
        packages.append(root.replace(os.path.sep, "."))

# Translation
translations = include_by_pattern("locale", locale_directory, ".mo")

# Icons
icons = include_by_pattern("data/icons/hicolor", icon_theme_directory, ".svg")
icons += include_by_pattern("data/icons/hicolor", icon_theme_directory, ".png")

# Config parsing specification
config_spec = [(
    "share/rabbitvcs",
    ["rabbitvcs/util/configspec/configspec.ini"]
)]

# Documentation
documentation = [("share/doc/rabbitvcs", [
    "AUTHORS",
    "MAINTAINERS"
])]

# Save build information so we can access the prefix later
path = "rabbitvcs/buildinfo.py"
buildinfo = '''rabbitvcs_prefix = "%s"
icon_path = "%s/%s"
''' % (PREFIX, PREFIX, icon_theme_directory)
fh = open(path, "w")
fh.write(buildinfo)
fh.close()

#==============================================================================
# Ready to install
#==============================================================================

# Calling the setup function will actually install RabbitVCS and also creates 
# an .egg-info file in /usr/lib/python<version>/site-packages/ or 
# /usr/share/python-support/rabbitvcs when generating a Debian package.
dist = setup(
    # The following arguments will be included in the .egg.info file,
    # for a list of available arguments and their descriptions see:
    # - http://docs.python.org/dist/module-distutils.core.html
    name=name,
    version=version,
    description=description,
    long_description=long_description,
    author=author,
    author_email=author_email,
    url=url,
    license=license,

    # There are actually several arguments that are used to install files:
    # - py_modules: installs specific modules to site-packages
    # - packages: install complete packages (directories with an __init__.py
    #   file) into site-packages
    # - data_files: any file you want, anywhere you want it
    packages=packages,
    package_data={
        "rabbitvcs": [
            # Include our GtkBuilder UI files right into the package
            "ui/xml/*.xml",
            "ui/xml/dialogs/*.xml"
        ]
    },
    data_files=translations + icons + documentation + config_spec
)

#
# Post installation
#

# Make sure the icon cache is deleted and recreated
if sys.argv[1] == "install":

    if os.uname()[0] != 'Darwin':
        print("Running gtk-update-icon-cache-3.0")
        
        subprocess.Popen(
            ["gtk-update-icon-cache-3.0", icon_theme_directory], 
            stdout=subprocess.PIPE
        ).communicate()[0]
