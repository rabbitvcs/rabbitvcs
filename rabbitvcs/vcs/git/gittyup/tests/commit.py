from __future__ import absolute_import
from __future__ import print_function
#
# test/stage.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from gittyup.client import GittyupClient
from gittyup.objects import *
from util import touch, change

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "commit"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("commit.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    g.commit("First commit", commit_all=True)
    
    change(DIR + "/test1.txt")
    g.stage([DIR+"/test1.txt"])
    g.commit("Second commit", author="Alex Plumb <alexplumb@gmail.com>")
    
    print("commit.py pass")
