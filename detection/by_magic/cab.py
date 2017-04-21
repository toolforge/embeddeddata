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


@register_detector('MSCF\x00\x00\x00\x00')
def ms_cab(f):
    # Based on https://msdn.microsoft.com/en-us/library/bb417343.aspx
    f.seek(8, os.SEEK_CUR)
    cbCabinet, reserved2 = struct.unpack('<LL', f.read(8))
    if reserved2 != 0:
        raise FileCorrupted

    f.try_seek(cbCabinet - 16, os.SEEK_CUR)
    f.update_pos()

    return True
