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

DIR = "move"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("move.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    g = GittyupClient(DIR, create=True)
    
    touch(DIR + "/test.txt")
    
    # Stage and commit the file
    g.stage([DIR+"/test.txt"])
    g.commit("Adding test.txt")
    
    st = g.status()

    # Move file explicity test
    os.mkdir(DIR+"/fol")
    g.move(DIR+"/test.txt", DIR+"/fol/test.txt")
    st = g.status()
    assert (not os.path.exists(DIR+"/test.txt"))
    assert (os.path.exists(DIR+"/fol/test.txt"))
    assert (g.is_staged(DIR+"/fol/test.txt"))
    assert (st[0] == RemovedStatus)
    assert (st[1] == AddedStatus)

    # Move as children test
    touch(DIR + "/test2.txt")
    g.stage([DIR+"/test2.txt"])
    g.commit("Adding test2.txt")
    g.move(DIR+"/test2.txt", DIR+"/fol")
    st = g.status()
    assert (not os.path.exists(DIR+"/test2.txt"))
    assert (os.path.exists(DIR+"/fol/test2.txt"))
    assert (g.is_staged(DIR+"/fol/test2.txt"))
    assert (st[1] == RemovedStatus)
    assert (st[2] == AddedStatus)
    g.commit("Committing the test2 move")

    g.move(DIR+"/fol", DIR+"/bar")
    st = g.status()
    assert (os.path.exists(DIR+"/bar/test.txt"))
    assert (st[0] == RemovedStatus)
    assert (st[2] == AddedStatus)

    print("move.py pass")
