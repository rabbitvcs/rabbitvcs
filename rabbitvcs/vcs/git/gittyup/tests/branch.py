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
from util import touch

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "branch"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print("branch.py clean")
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    g.commit("This is a commit")

    # Create a new branch, don't track it
    g.branch("branch1")
    assert "branch1" in [x['name'] for x in g.branch_list()]

    # Make sure we are still tracking master
    assert (g.is_tracking("refs/heads/master"))

    # Track branch1
    g.track("refs/heads/branch1")
    assert (g.is_tracking("refs/heads/branch1"))
    
    # Rename branch1 to branch1b
    g.branch_rename("branch1", "branch1b")
    assert "branch1b" in [x['name'] for x in g.branch_list()]

    # Make sure we are now tracking branch1b
    assert (g.is_tracking("refs/heads/branch1b"))
    
    # Delete branch1b
    g.branch_delete("branch1b")
    assert ("branch1b" not in g.branch_list())

    # Make sure we are now tracking master
    assert (g.is_tracking("refs/heads/master"))

    print("branch.py pass")
