from __future__ import absolute_import
# This file was originally obtained from:
# http://git.gnome.org/cgit/meld/tree/meld/ui/wraplabel.py
# ...and added here by Jason
#
# Copyright (c) 2005 VMware, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Python translation from wrapLabel.{cc|h} by Gian Mario Tagliaretti
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Pango

from rabbitvcs.util.strings import S

class WrapLabel(Gtk.Label):
    __gtype_name__ = 'WrapLabel'

    def __init__(self, str=None):
        Gtk.Label.__init__(self)

        self.__wrap_width = 0
        self.layout = self.get_layout()
        self.layout.set_wrap(Pango.WrapMode.WORD_CHAR)

        if str != None:
            self.set_text(S(str).display())

        self.set_alignment(0.0, 0.0)

    def do_size_request(self, requisition):
        layout = self.get_layout()
        width, height = layout.get_pixel_size()
        requisition.width = 0
        requisition.height = height

    def do_size_allocate(self, allocation):
        Gtk.Label.do_size_allocate(self, allocation)
        self.__set_wrap_width(allocation.width)

    def set_text(self, str):
        Gtk.Label.set_text(self, S(str).display())
        self.__set_wrap_width(self.__wrap_width)

    def set_markup(self, str):
        Gtk.Label.set_markup(self, str)
        self.__set_wrap_width(self.__wrap_width)

    def __set_wrap_width(self, width):
        if width == 0:
            return
        layout = self.get_layout()
        layout.set_width(width * Pango.SCALE)
        if self.__wrap_width != width:
            self.__wrap_width = width
            self.queue_resize()
