from __future__ import absolute_import
#
# command.py
#

import subprocess
import fcntl
import select
import os

from .exceptions import GittyupCommandError

def notify_func(data):
    pass

def cancel_func():
    return False

class GittyupCommand:
    def __init__(self, command, cwd=None, notify=None, cancel=None):
        self.command = command
        
        self.notify = notify_func
        if notify:
            self.notify = notify

        self.get_cancel = cancel_func
        if cancel:
            self.get_cancel = cancel

        self.cwd = cwd
        if not self.cwd:
            self.cwd = os.getcwd()
    
    def get_lines(self, val):
        returner = []
        lines = val.rstrip("\n").split("\n")
        for line in lines:
            returner.append(line.rstrip("\x1b[K\n"))
        
        return returner 

    def execute(self):
        env = os.environ.copy()
        env["LANG"] = "C";
        proc = subprocess.Popen(self.command,
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE,
                                env=env,
                                close_fds=True,
                                preexec_fn=os.setsid,
                                universal_newlines=True)

        stdout = []

        while True:
            line = proc.stdout.readline()

            if line == '':
                break
            line = line.rstrip('\n') # Strip trailing newline.
            self.notify(line)
            stdout.append(line)

            if self.get_cancel():
                proc.kill()

        return (0, stdout, None)
