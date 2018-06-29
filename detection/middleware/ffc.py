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

import itertools
import os
import traceback

from detection.by_magic import find_startpos
from detection.middleware import register_detector


retdct = {
    'pos': 0,
    'mime': ('application/x-ffc', 'FFC Camouflaged File')
}


# @register_detector('Anti_FFC',
#                    lambda major, minor: minor in ['jpg', 'jpeg'])
@register_detector('Anti_FFC',
                   lambda major, minor: True)
def anti_ffc(f):
    with open(f, 'rb') as fp:
        for pos in list(find_startpos(fp, b'\xff\xd9\xff\xd9')):
            if try_pos(f, pos):
                return [retdct.copy()]


def try_pos(f, pos):
    with open(f, 'rb') as fp:
        fp.seek(pos, os.SEEK_SET)
        if fp.read(4) != b'\xff\xd9\xff\xd9':
            return

        start = fp.tell()
        for i in range(32):
            if not is_base64(fp):
                length = fp.tell() - start
                break
        else:
            return

        fp.seek(start, os.SEEK_SET)
        try:
            header = fp.read(length).decode('base64')
        except Exception:
            traceback.print_exc()
            return
        if len(header) % 16 != 0 or len(header) <= 16:
            return

        nl = fp.read(2)
        if nl == b'\r\n':
            pass
        elif len(nl) == 1 and nl in b'\r\n':
            fp.seek(-1, os.SEEK_CUR)
        else:
            return

        for i in itertools.count():
            if not is_base64(fp):
                break

        return i > 64


valid_base64set = set(map(chr, sum([
        range(ord(b'0'), ord(b'9')+1),
        range(ord(b'a'), ord(b'z')+1),
        range(ord(b'A'), ord(b'Z')+1),
    ], [])) + [b'+', b'/'])
assert len(valid_base64set) == 64


def is_base64(fp):
    d = fp.read(4)
    if len(d) != 4:
        fp.seek(-len(d), os.SEEK_CUR)
        return False

    allow_padding = True
    ended = False

    for char in d[::-1]:
        if char == b'=' and allow_padding:
            ended = True
            continue
        allow_padding = False
        if char in valid_base64set:
            continue

        # Invalid base64
        fp.seek(-4, os.SEEK_CUR)
        return False

    if ended:
        return False  # valid but ended
    return True
