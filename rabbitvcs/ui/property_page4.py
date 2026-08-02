#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2010 by Jason Heeris <jason.heeris@gmail.com>
#
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#
import os
import os.path
from gi.repository import Gtk
from rabbitvcs import gettext
from rabbitvcs.util.strings import S
from rabbitvcs.ui import STATUS_EMBLEMS
from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
import rabbitvcs.vcs

_ = gettext.gettext

class FileInfo():

    def __init__(self, path, vcs=None, claim_domain=True):
        self.path = path
        self.vcs = vcs or rabbitvcs.vcs.VCS()
        self.checker = StatusChecker()

    def get_status(self, path):
        status = self.checker.check_status(
            path, recurse=False, invalidate=False, summary=False
        )
        return status

    def get_additional_info(self):
        vcs_type = rabbitvcs.vcs.guess_vcs(self.path)["vcs"]

        if vcs_type == rabbitvcs.vcs.VCS_SVN:
            return self.get_additional_info_svn()
        elif vcs_type == rabbitvcs.vcs.VCS_GIT:
            return self.get_additional_info_git()
        else:
            return None, None

    def get_additional_info_svn(self):
        repo_url = S(self.vcs.svn().get_repo_url(self.path))
        repo_path = self.vcs.svn().find_repository_path(self.path)
        return repo_url, repo_path

    def get_additional_info_git(self):
        repo_url = S(self.vcs.git().config_get(("remote", "origin"), "url"))
        repo_path = self.vcs.git().find_repository_path(self.path)
        return repo_url, repo_path