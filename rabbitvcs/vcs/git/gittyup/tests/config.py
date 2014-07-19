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
from gittyup.config import GittyupLocalFallbackConfig, GittyupConfig, GittyupSystemConfig

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "config"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print "config.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    g = GittyupClient(DIR, create=True)
    c = GittyupLocalFallbackConfig(DIR)
    
    # Create config items
    c.set(("core", ), "filemode", "True")
    c.set(("core", ), "repositoryformatversion", "0")

    # Create new section/items and then rename them
    c.set(("newsection", ), "newitem", "Val A")
    c.rename_section(("newsection", ), ("newsection-RE", ))
    c.rename(("newsection-RE", ), "newitem", "newitem-RE")
    c.write()

    del c
    
    c = GittyupLocalFallbackConfig(DIR)

    assert (c.has(("newsection-re", ), "newitem-re")), c._local._config
    
    del c

    c = GittyupConfig("./data/config/config.example")
    
    assert (c.has(("diff", ), "renames"))
    
    del c
    
    c = GittyupSystemConfig()
    c.set(("section", ), "key", "value")
    try:
        c.write()
    except OSError:
        # This requires write access to system config, so allow it to fail.
        pass

    print "config.py pass"
