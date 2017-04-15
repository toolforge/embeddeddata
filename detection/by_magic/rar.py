#! /usr/bin/env python
# -*- coding: UTF-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General License for more details.
#
# You should have received a copy of the GNU General License
# along with self program.  If not, see <http://www.gnu.org/licenses/>
#

from __future__ import absolute_import

import os
import struct

from detection.by_magic import register_detector, FileCorrupted


@register_detector('\x52\x61\x72\x21\x1A\x07\x01\x00')
def rar_v5(f):
    # based on http://www.rarlab.com/technote.htm
    def vint():
        r = 0
        i = 0
        while True:
            b, = struct.unpack('<B', f.read(1))
            cont, d = b & 0x80, b & 0x7F
            r += d << i
            i += 7
            if not cont:
                return r

    f.seek(8, os.SEEK_CUR)  # seek after magic
    while True:
        crc, = struct.unpack('<L', f.read(4))
        head_size = vint()
        pos = f.tell()
        typ, flags = vint(), vint()
        if typ not in [1, 2, 3, 4, 5, 7]:
            raise FileCorrupted
        extra_area_size = vint() if flags & 0x0001 else 0
        data_size = vint() if flags & 0x0002 else 0
        f.try_seek(pos + head_size, os.SEEK_SET)
        f.try_seek(data_size, os.SEEK_CUR)

        f.update_pos()

        if typ == 5:
            break
        elif typ == 4:
            return Ellipsis  # encrypted, assume bad faith

    return True


@register_detector('\x52\x61\x72\x21\x1A\x07\x00')
def rar_v4(f):
    # based on http://www.forensicswiki.org/wiki/RAR
    # and http://acritum.com/winrar/rar-format
    while True:
        pos = f.tell()
        crc, typ, flags, size = struct.unpack('<HBHH', f.read(7))
        if flags & 0x8000:
            size += struct.unpack('<L', f.read(4))[0]
        if not 0x72 <= typ <= 0x7b:
            raise FileCorrupted
        f.try_seek(pos + size, os.SEEK_SET)
        # f.try_seek(size, os.SEEK_CUR)
        f.update_pos()
        if typ == 0x7b:
            break
        elif typ == 0x73 and flags & 0x80:
            return Ellipsis  # encrypted, assume bad faith
    return True


@register_detector('\x52\x45\x7E\x5E')
def rar_old(f):
    return
