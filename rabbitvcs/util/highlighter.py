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
Syntax highlighter based on the pygments module.
"""

import six
from rabbitvcs.util.strings import S
from rabbitvcs.util.helper import html_escape
from rabbitvcs.util.settings import SettingsManager
from rabbitvcs.util.log import Log

logger = Log("rabbitvcs.util.highlighter")

HAS_PYGMENTS = True
try:
    import pygments
    import pygments.formatters
    import pygments.formatter
    import pygments.lexers
    import pygments.util
except:
    HAS_PYGMENTS = False


def mklist(arg):
    if not isinstance(arg, list):
        arg = [arg]
    return arg


def no_highlight(lines):
    return [html_escape(S(l), True) for l in mklist(lines)]


if not HAS_PYGMENTS:

    def highlight(filename, sourcelines):
        return no_highlight(sourcelines)

else:
    # Pygments custom formatter generating Pango makup language.

    class PangoMarkupFormatter(pygments.formatter.Formatter):
        def __init__(self, bylines=False, **options):
            pygments.formatter.Formatter.__init__(self, **options)
            self.bylines = bylines
            self.styles = {}
            for token, style in self.style:
                start = end = ""
                if style["color"]:
                    start += ' foreground="#%s"' % style["color"]
                if style["bgcolor"]:
                    start += ' background="#%s"' % style["bgcolor"]
                if style["bold"]:
                    start += ' weight="bold"'
                if style["italic"]:
                    start += ' style="italic"'
                if style["underline"]:
                    start += ' underline="single"'
                if style["sans"]:
                    start += ' face="sans"'
                if style["roman"]:
                    start += ' face="serif"'
                elif style["mono"]:
                    start += ' face="monospace"'

                if start == ' weight="bold"':
                    start, end = "<b>", "</b>"
                elif start == ' style="italic"':
                    start, end = "<i>", "</i>"
                elif start == ' underline="single"':
                    start, end = "<u>", "</u>"
                elif start == ' face="monospace"':
                    start, end = "<tt>", "</tt>"
                elif start:
                    start = "<span%s>" % start
                    end = "</span>"
                self.styles[token] = (start, end)

        def format(self, tokensource, outfile):
            self.lastval = ""
            self.lasttype = None

            def flush(self):
                if self.lastval:
                    stylebegin, styleend = self.styles[self.lasttype]
                    outfile.write(stylebegin + self.lastval + styleend)
                    self.lastval = ""

            def format_single(self, ttype, value):
                value = html_escape(value, True)

                if ttype != self.lasttype:
                    flush(self)
                    self.lasttype = ttype

                self.lastval += value

            for ttype, value in tokensource:
                lines = [value]
                if self.bylines:
                    lines = value.splitlines()
                    if S(value[-1:]) in ["\r", "\n"]:
                        lines.append(value[0:0])

                while not ttype in self.styles:
                    ttype = ttype.parent

                if lines:
                    format_single(self, ttype, lines[0])
                    for line in lines[1:]:
                        flush(self)
                        outfile.write(six.u("\n"))
                        format_single(self, ttype, line)

            flush(self)

    def highlight(filename, sourcelines):
        if not SettingsManager().get("general", "enable_highlighting"):
            return no_highlight(sourcelines)

        sourcelines = mklist(sourcelines)
        source = "\n".join(sourcelines)
        try:
            lexer = pygments.lexers.guess_lexer_for_filename(filename, source)
        except pygments.util.ClassNotFound:
            return no_highlight(sourcelines)

        formatter = PangoMarkupFormatter(bylines=True)
        lines = pygments.highlight(source, lexer, formatter).splitlines()

        # Trailing empty lines may have been lost.
        n = len(sourcelines) - len(lines)
        if n > 0:
            lines += [""] * n

        return lines
