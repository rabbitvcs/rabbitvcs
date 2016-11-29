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

DIR = "tag"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("tag.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    commit_id = g.commit("First commit", commit_all=True)
    
    tag_id = g.tag("tag1", "Tagging as tag1", track=True)
    assert (g.is_tracking("refs/tags/tag1"))
    
    assert (len(g.tag_list()) == 1)
    
    print("tag.py pass")
