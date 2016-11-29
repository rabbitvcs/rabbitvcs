from __future__ import absolute_import
#!/usr/bin/python

from sys import argv
import os
import subprocess

def cleanup(modules):
    for module in modules:
        subprocess.call(["python", module, "--cleanup"])

modules = [
    "branch.py", 
    "stage.py",
    "commit.py",
    "tag.py",
    "remove.py",
    "clone.py",
    "move.py",
    "pull.py",
    "remote.py"
]

if len(argv) == 2 and  argv[1] == "--cleanup":
    cleanup(modules)

for module in modules:
    if subprocess.call(["python", module]) == 1:
        raise SystemExit("Module test failed")

cleanup(modules)
