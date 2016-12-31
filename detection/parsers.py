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

# The ptrace part is largely based on:
# https://github.com/haypo/python-ptrace/blob/11a117427faee52ebb54de0bc6fe21738cbff7a4/strace.py

from __future__ import absolute_import

import os

from detection.utils import FileProxy


class FileCorrupted(Exception):
    pass


class ParserDetector(object):
    def __init__(self, f):
        self.path = f
        self.lastgoodpos = 0

    def parse(self, parsetype):
        with FileProxy(open(self.path, 'rb'), track=False) as f:
            try:
                if parsetype == 'ogg':
                    self.parse_ogg(f)
                else:
                    raise RuntimeError('Wrong parsetype!')
            except (FileCorrupted, ValueError, TypeError):
                pass

            return self.lastgoodpos, True

    def parse_ogg(self, f):
        # Based on https://www.xiph.org/ogg/doc/framing.html
        while True:
            # A page

            # Capture pattern
            a = f.read(4)
            if not a == 'OggS':
                raise FileCorrupted
            # Version
            if not f.read(1) == '\x00':
                raise FileCorrupted
            # Header type
            f.seek(1, os.SEEK_CUR)
            # Granule position
            f.seek(8, os.SEEK_CUR)
            # Bitstream serial number
            f.seek(4, os.SEEK_CUR)
            # Page sequence number
            f.seek(4, os.SEEK_CUR)
            # Checksum
            f.seek(4, os.SEEK_CUR)
            # Page segments
            numsegments = ord(f.read(1))
            # Segment table
            numdatas = [ord(f.read(1)) for i in range(numsegments)]
            for numdata in numdatas:
                f.seek(numdata, os.SEEK_CUR)

            self.lastgoodpos = f.tell()
