from __future__ import absolute_import
from __future__ import print_function
#
# test/pull.py
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

DIR = "pull"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("pull.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    g = GittyupClient(DIR, create=True)
    g.remote_add("origin", "git://github.com/adamplumb/gittyup.git")
    g.pull("origin", "master")

    print("pull.py pass")
