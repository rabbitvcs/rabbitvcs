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

Additional strings support.

"""

import sys
import codecs
import re
import six
import locale

__all__ = ["S", "IDENTITY_ENCODING", "UTF8_ENCODING", "SURROGATE_ESCAPE"]

unicode_null_string = six.u("")
non_alpha_num_re = re.compile("[^A-Za-z0-9]+")
SURROGATE_BASE = 0xDC00
RE_SURROGATE = re.compile(six.u("[") + six.unichr(SURROGATE_BASE + 0x80) +
                          six.u("-") + six.unichr(SURROGATE_BASE + 0xFF) +
                          six.u("]"))
RE_UTF8 = re.compile("^[Uu][Tt][Ff][ _-]?8$")

#   Codec that maps ord(byte) == ord(unicode_char).

IDENTITY_ENCODING = "latin-1"



#   An UTF-8 codec that implements surrogates, even in Python 2.

UTF8_ENCODING = "rabbitvcs-utf8"

def utf8_decode(input, errors="strict"):
    return codecs.utf_8_decode(input, errors, True)


def utf8_encode(input, errors="strict"):
    output = b''
    pos = 0
    end = len(input)
    eh = None
    while pos < end:
        n = end
        m = RE_SURROGATE.search(input, pos)
        if m:
            n = m.start()
        if n > pos:
            p, m = codecs.utf_8_encode(input[pos:n], errors)
            output += p
            pos = n
        if pos < end:
            e = UnicodeEncodeError(UTF8_ENCODING,
                                   input, pos, pos + 1,
                                   "surrogates not allowed")
            if not eh:
                eh = codecs.lookup_error(errors)
            p, n = eh(e)
            output += p
            if n <= pos:
                n = pos + 1
            pos = n
    return (output, len(input))

class Utf8IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return utf8_encode(input, self.errors)[0]

class Utf8IncrementalDecoder(codecs.BufferedIncrementalDecoder):
    _buffer_decode = codecs.utf_8_decode

class Utf8StreamWriter(codecs.StreamWriter):
    def encode(self, input, errors='strict'):
        return utf8_encode(input, errors)

class Utf8StreamReader(codecs.StreamReader):
    decode = codecs.utf_8_decode


def utf8_search(encoding):
    encoding = non_alpha_num_re.sub("-", encoding).strip("-").lower()
    if encoding != UTF8_ENCODING:
        return None
    return codecs.CodecInfo(
                   name=UTF8_ENCODING,
                   encode=utf8_encode,
                   decode=utf8_decode,
                   incrementalencoder=Utf8IncrementalEncoder,
                   incrementaldecoder=Utf8IncrementalDecoder,
                   streamwriter=Utf8StreamWriter,
                   streamreader=Utf8StreamReader
    )

codecs.register(utf8_search)


#   Emulate surrogateescape codecs error handler because it is not available
#   Before Python 3.1

SURROGATE_ESCAPE = "rabbitvcs-surrogateescape"

def rabbitvcs_surrogate_escape(e):
    if not isinstance(e, UnicodeError):
        raise e
    input = e.object[e.start:e.end]
    if isinstance(e, UnicodeDecodeError):
        output = [six.unichr(b) if b < 0x80 else                             \
                  six.unichr(SURROGATE_BASE + b) for b in bytearray(input)]
        return (unicode_null_string.join(output), e.end)
    if isinstance(e, UnicodeEncodeError):
        output = b""
        for c in input:
            b = ord(c) - SURROGATE_BASE
            if not 0x80 <= b <= 0xFF:
                raise e
            output += six.int2byte(b)
        return (output, e.end)
    raise e

codecs.register_error(SURROGATE_ESCAPE, rabbitvcs_surrogate_escape)


class S(str):
    """
    Stores a string in native form: unicode with surrogates in Python 3 and
        utf-8 in Python 2.
    Provides the following methods:
    encode: overloaded to use UTF8_ENCODING and SURROGATE_ESCAPE error handler.
    decode: overloaded to use UTF8_ENCODING and SURROGATE_ESCAPE error handler.
    bytes: get the string as bytes.
    unicode: get the string as unicode.
    display: get the string in native form, without surrogates.
    """

    if str == bytes:
        # Python 2.
        def __new__(cls, value, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            if isinstance(value, bytearray):
                value = bytes(value)
            if isinstance(value, str):
                encoding, errors = S._codeargs(encoding, errors)
                if encoding.lower() != UTF8_ENCODING:
                    value = value.decode(encoding, errors)
            if isinstance(value, six.text_type):
                value = value.encode(UTF8_ENCODING, SURROGATE_ESCAPE)
            elif not isinstance(value, str):
                value = str(value)
            return str.__new__(cls, value)

        def encode(self, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            encoding, errors = self._codeargs(encoding, errors)
            if encoding.lower() == UTF8_ENCODING:
                return self
            value = super(S, self).decode(UTF8_ENCODING, SURROGATE_ESCAPE)
            return value.encode(encoding, errors)

        def decode(self, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            encoding, errors = self._codeargs(encoding, errors)
            return super(S, self).decode(encoding, errors)

        def display(self, encoding=None, errors='replace'):
            encoding, errors = self._codeargs(encoding, errors)
            if encoding.lower() == UTF8_ENCODING:
                return self
            value = super(S, self).decode(UTF8_ENCODING, 'replace')
            return value.encode(encoding, errors)

    else:
        # Python 3.
        def __new__(cls, value, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            if isinstance(value, bytearray):
                value = bytes(value)
            if isinstance(value, bytes):
                encoding, errors = S._codeargs(encoding, errors)
                value = value.decode(encoding, errors)
            elif not isinstance(value, str):
                value = str(value)
            return str.__new__(cls, value)

        def encode(self, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            encoding, errors = self._codeargs(encoding, errors)
            return super(S, self).encode(encoding, errors)

        def decode(self, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
            return self;

        def display(self, encoding=None, errors='replace'):
            return RE_SURROGATE.sub(six.unichr(0xFFFD), self)

    def bytes(self, encoding=UTF8_ENCODING, errors=SURROGATE_ESCAPE):
        return self.encode(encoding, errors)

    def unicode(self):
        return self.decode()

    def valid(self, encoding=None, errors=SURROGATE_ESCAPE):
        return self.display(encoding, errors) == self

    @staticmethod
    def _codeargs(encoding, errors):
        if not encoding:
            encoding = locale.getlocale(locale.LC_MESSAGES)[1]
            if not encoding:
                encoding = sys.getdefaultencoding()
        if RE_UTF8.match(encoding):
            encoding = UTF8_ENCODING
        if errors.lower() == 'strict':
            errors = SURROGATE_ESCAPE
        return encoding, errors
