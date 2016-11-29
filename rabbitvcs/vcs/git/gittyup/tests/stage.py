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

DIR = "stage"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("stage.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    # Stage both files
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status(DIR)
    assert (st[0] == AddedStatus), st
    assert (st[1] == AddedStatus)
    assert (st[0].is_staged)
    
    # Unstage both files
    g.unstage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status(DIR)
    assert (st[0] == UntrackedStatus)
    assert (st[1] == UntrackedStatus)
    assert (not st[0].is_staged)
    
    # Untracked files should not be staged
    g.stage_all()
    st = g.status(DIR)
    assert (st[0] == UntrackedStatus)
    assert (st[1] == UntrackedStatus)
    
    # test1.txt is changed, so it should get staged and set as Modified
    g.stage([DIR+"/test1.txt"])
    g.commit("Test commit")
    change(DIR+"/test1.txt")
    st = g.status(DIR)
    assert (st[0] == ModifiedStatus)
    g.stage_all()
    st = g.status(DIR)
    assert (st[0] == ModifiedStatus)
    assert (g.is_staged(DIR+"/" + st[0].path))
    assert (not g.is_staged(DIR+"/" + st[1].path))

    # Unstage all staged files
    g.unstage_all()
    st = g.status(DIR)
    assert (not g.is_staged(DIR+"/" + st[0].path))
    assert (not g.is_staged(DIR+"/" + st[1].path))
    assert (st[0] == ModifiedStatus)
    assert (st[1] == UntrackedStatus)
    
    print("stage.py pass")
