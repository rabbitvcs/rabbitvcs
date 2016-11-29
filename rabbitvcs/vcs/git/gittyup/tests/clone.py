from __future__ import absolute_import
from __future__ import print_function
#
# test/clone.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from gittyup.client import GittyupClient
from util import touch

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "clone"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("clone.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    g = GittyupClient()
    g.clone("git://github.com/adamplumb/sprout.git", DIR)


    print("clone.py pass")
