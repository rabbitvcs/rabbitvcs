#
# This is an extension to the Nautilus file manager to allow better
# integration with the Subversion source control system.
#
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2010 by Adam Plumb <adamplumb@gmail.com>
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

"""
Unit tests for the top-level rabbitvcs package.

"""
from __future__ import absolute_import

# make sure the current working copy is in sys.path before anything else
from os.path import abspath, dirname, join, normpath
import sys
toplevel = normpath(join(dirname(abspath(__file__)), '..', '..'))
sys.path.insert(0, toplevel)

from unittest import TestCase, main
import traceback

from . import nautilus
import pysvn
import rabbitvcs
from rabbitvcs.util.extensions.nautilus import RabbitVCS


class RabbitVCSTest(TestCase):
    """
    Main RabbitVCS tests.

    """
    def test_package_name(self):
        """Make sure the package name is reported properly."""
        result = rabbitvcs.package_name()
        self.assertEqual(result, "rabbitvcs")

    def test_package_version(self):
        """Make sure the package version is reported properly."""
        result = rabbitvcs.package_version()
        for character in result:
            if not (character.isdigit() or character == '.'):
                self.fail("Not all characters in package version "
                          "'%s' were digits or dots." % result)

    def test_package_identifier(self):
        """Make sure the package identifier is reported properly."""
        result = rabbitvcs.package_identifier()
        version = rabbitvcs.package_version()
        self.assertEqual(result, "rabbitvcs-%s" % version)


class FakeVersion(object):
    """
    Fake revision info for FakeInfo, below.

    """
    def __init__(self, number):
        self.number = number


class FakeInfo(object):
    """
    Fake pysvn.Client.info() response.

    """
    def __init__(self):
        self.data = {'text_status': pysvn.wc_status_kind.none,
                     'commit_revision': FakeVersion(1234),
                     'commit_author': None,
                     'commit_time': 0.0,
                     'url': None,
                     }


class FakeClient(object):
    """
    Fake pysvn.Client that can have its behavior controlled.

    """
    instance_count = 0
    send_empty_info = True

    def __init__(self, *args, **kwargs):
        FakeClient.instance_count += 1

    def info(self, path):
        if self.send_empty_info:
            return None
        else:
            return FakeInfo()

    def status(self, path, recurse=False):
        """Return a fake status, as a list."""
        return [FakeInfo()]


class FakeLog(object):
    """
    Fake logger that allows us to pick the log messages out from
    within unit tests.

    """
    def __init__(self, prefix):
        self.prefix = prefix
        self.messages = []

    def exception(self):
        """
        Log an exception.  Just add the (exc_type, message,
        traceback) tuple onto the list of messages.

        """
        info = sys.exc_info()
        self.messages.append(info)


class RabbitVCSPySvnTest(TestCase):
    """
    RabbitVCS tests that involve pysvn in such a way that we need to
    fiddle with pysvn stuff for the tests to work.

    """
    def setUp(self):
        self.oldClient = pysvn.Client
        pysvn.Client = FakeClient
        FakeClient.instance_count = 0
        self.oldLog = RabbitVCS.log
        self.logger = FakeLog("rabbitvcs")
        RabbitVCS.log = self.logger
        self.nsvn = RabbitVCS.RabbitVCS()

    def test_update_columns_missing_info(self):
        """
        Test the behavior of update_columns() when the info() call
        returns None.
        See http://code.google.com/p/rabbitvcs/issues/detail?id=119

        The desired behavior is that an error message is logged which
        indicates that the given path is not under source control.

        """
        path = "awesomepath"
        FakeClient.send_empty_info = True
        item = nautilus.NautilusVFSFile()
        self.nsvn.update_columns(item, path)
        self.assertEqual(FakeClient.instance_count, 2)
        self.assertEqual(len(self.logger.messages), 1)
        last_message = self.logger.messages[-1]
        self.assertEqual(str(last_message[1]),
                         "The path 'awesomepath' does not "
                         "appear to be under source control.")

    def test_update_columns_correct_info(self):
        """
        Test the side effects of update_columns() when things happen
        normally.

        """
        path = "excellentpath"
        FakeClient.send_empty_info = False
        item = nautilus.NautilusVFSFile()
        self.nsvn.update_columns(item, path)
        self.assertEqual(FakeClient.instance_count, 2)
        if len(self.logger.messages) > 0:
            for e,m,t in self.logger.messages:
                traceback.print_exception(e, m, t)
            self.fail()

    def tearDown(self):
        RabbitVCS.log = self.oldLog
        pysvn.Client = self.oldClient


if __name__ == "__main__":
    main()
