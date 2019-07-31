from __future__ import absolute_import
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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from collections import defaultdict
import rabbitvcs.ui
import rabbitvcs.ui.widget

import rabbitvcs.vcs
from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
from rabbitvcs.ui import STATUS_EMBLEMS

from rabbitvcs.util.strings import S
from rabbitvcs.util.log import Log
log = Log("rabbitvcs.ui.property_page")

from rabbitvcs import gettext
_ = gettext.gettext

class PropertyPage(rabbitvcs.ui.GtkBuilderWidgetWrapper):

    gtkbuilder_filename = "property_page"
    gtkbuilder_id = "prop_page_scroller"

    def __init__(self, paths, vcs=None, claim_domain=True):
        rabbitvcs.ui.GtkBuilderWidgetWrapper.__init__(self,
                                                 claim_domain=claim_domain)
        self.paths = paths
        self.vcs = vcs or rabbitvcs.vcs.VCS()

        self.info_pane = rabbitvcs.ui.widget.Box(self.get_widget("property_page"), vertical = True)

        if len(paths) == 1:
            file_info = FileInfoPane(paths[0], self.vcs,
                                     claim_domain=self.claim_domain)
            self.info_pane.pack_start(file_info.get_widget(),
                                        expand=False,
                                        fill=False,
                                        padding=0)
        elif len(paths) > 1:
            try:
                for path in paths:
                    expander = FileInfoExpander(path, self.vcs,
                                                claim_domain=self.claim_domain,
                                                indent=12)
                    self.info_pane.pack_start(expander.get_widget(),
                                        expand=False,
                                        fill=False,
                                        padding=0)
            except Exception as ex:
                log.exception(ex)
                raise

class FileInfoPane(rabbitvcs.ui.GtkBuilderWidgetWrapper):

    gtkbuilder_filename = "property_page"
    gtkbuilder_id = "file_info_table"

    def __init__(self, path, vcs=None, claim_domain=True):
        rabbitvcs.ui.GtkBuilderWidgetWrapper.__init__(self,
                                                 claim_domain=claim_domain)

        self.path = path
        self.vcs = vcs or rabbitvcs.vcs.VCS()
        self.checker = StatusChecker()

        self.get_widget("file_name").set_text(S(os.path.basename(path)).display())

        self.status = self.checker.check_status(path,
                                                recurse = False,
                                                invalidate = False,
                                                summary = False)

        self.get_widget("vcs_type").set_text(S(self.status.vcs_type).display())

        self.get_widget("content_status").set_text(S(self.status.simple_content_status()).display())
        self.get_widget("prop_status").set_text(S(self.status.simple_metadata_status()).display())


        self.set_icon_from_status(self.get_widget("content_status_icon"),
                                                  self.status.simple_content_status())

        self.set_icon_from_status(self.get_widget("prop_status_icon"),
                                                  self.status.simple_metadata_status())



        self.set_icon_from_status(self.get_widget("vcs_icon"),
                                  self.status.single, Gtk.IconSize.DIALOG)

        additional_info = self.get_additional_info()
        if additional_info:
            additional_props_table = rabbitvcs.ui.widget.KeyValueTable(
                                        additional_info)
            additional_props_table.show()

            file_info_table = rabbitvcs.ui.widget.Box(self.get_widget("file_info_table"), vertical = True)
            file_info_table.pack_start(additional_props_table,
                                       expand=False,
                                       fill=False,
                                       padding=0)

    def set_icon_from_status(self, icon, status, size=Gtk.IconSize.BUTTON):
        if status in rabbitvcs.ui.STATUS_EMBLEMS:
            icon.set_from_icon_name("emblem-" + STATUS_EMBLEMS[status], size)

    def get_additional_info(self):
        vcs_type = rabbitvcs.vcs.guess_vcs(self.path)['vcs']

        if(vcs_type == rabbitvcs.vcs.VCS_SVN):
            return self.get_additional_info_svn()
        elif(vcs_type == rabbitvcs.vcs.VCS_GIT):
            return self.get_additional_info_git()
        else:
            return []

    def get_additional_info_svn(self):

        repo_url = S(self.vcs.svn().get_repo_url(self.path))

        return [
            (_("Repository URL"), repo_url)]

    def get_additional_info_git(self):

        repo_url = S(self.vcs.git().config_get(("remote", "origin"), "url"))
        return [
            (_("Repository URL"), repo_url)]


class FileInfoExpander(rabbitvcs.ui.GtkBuilderWidgetWrapper):

    gtkbuilder_filename = "property_page"
    gtkbuilder_id = "file_info_expander"

    def __init__(self, path, vcs=None, claim_domain=True, indent=0):

        # Might be None, but that's okay, only subclasses use it
        self.vcs = vcs

        rabbitvcs.ui.GtkBuilderWidgetWrapper.__init__(self,
                                                 claim_domain=claim_domain)
        self.path = path
        self.get_widget("file_expander_path").set_label(path)

        # Do a lazy evaluate for this
        self.file_info = None

        self.expander = self.get_widget()
        self.indent = indent

        # There seems to be no easy way to connect to this in Gtkbuilder
        self.expander.connect("notify::expanded", self.on_expand)

    def on_expand(self, param_spec, user_data):
        if self.expander.get_expanded() and not self.file_info:
            self.file_info = FileInfoPane(self.path, self.vcs,
                                          claim_domain=self.claim_domain
                                          ).get_widget()
            self.file_info.set_margin_start(self.indent)
            self.expander.add(self.file_info)

class PropertyPageLabel(rabbitvcs.ui.GtkBuilderWidgetWrapper):
    gtkbuilder_filename = "property_page"
    gtkbuilder_id = "property_page_label"
