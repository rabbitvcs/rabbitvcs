from __future__ import absolute_import
#
# util.py
#

import os

def touch(fname, times = None):
    with open(fname, 'a'):
        os.utime(fname, times)

def change(path):
    f = open(path, "a")
    f.write("1")
    f.close()
