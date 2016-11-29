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

DIR = "remove"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("remove.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test.txt")
    
    # Stage and commit the file
    g.stage([DIR+"/test.txt"])
    g.commit("Adding test.txt")
    
    g.remove([DIR+"/test.txt"])
    st = g.status()
    assert (not os.path.exists(DIR+"/test.txt"))
    assert (g.is_staged(DIR+"/test.txt"))
    assert (st[0] == RemovedStatus)
    
    g.unstage([DIR+"/test.txt"])
    st = g.status()
    assert (not os.path.exists(DIR+"/test.txt"))
    assert (not g.is_staged(DIR+"/test.txt"))
    assert (st[0] == MissingStatus)

    g.checkout([DIR+"/test.txt"])
    st = g.status()
    assert (os.path.exists(DIR+"/test.txt"))
    assert (not g.is_staged(DIR+"/test.txt"))
    assert (st[0] == NormalStatus)
    
    print("remove.py pass")
