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

from detection.by_magic import register_detector


@register_detector('7z\xBC\xAF\x27\x1C')
def seven_z(f):
    # Based on
    # https://st.aticpan.org/source/BJOERN/Compress-Deflate7-1.0/7zip/DOC/7zFormat.txt
    # and http://www.romvault.com/Understanding7z.pdf
    f.seek(6, os.SEEK_CUR)

    # SignatureHeader
    Major, Minor = struct.unpack('>BB', f.read(2))
    StartHeaderCRC, = struct.unpack('<L', f.read(4))
    NextHeaderOffset, NextHeaderSize, NextHeaderCRC = struct.unpack(
        '<QQL', f.read(20))
    f.update_pos()

    # skip PackedStreams & PackedStreamsForHeaders

    # Header
    f.try_seek(NextHeaderOffset, os.SEEK_CUR)
    f.update_pos()
    f.try_seek(NextHeaderSize, os.SEEK_CUR)
    f.update_pos()

    return True
