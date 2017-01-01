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
import xml.etree.ElementTree as ET

from detection.utils import FileProxy  # , BinaryFileProxy


matroska_spec = os.path.join(
    os.path.dirname(__file__), 'matroska_embl_specdata.xml')
matroska_spec = ET.parse(matroska_spec).getroot()
matroska_spec = [node.attrib for node in matroska_spec.iter('element')]
matroska_spec = {int(typ['id'], 0): {
    'name': typ['name'],
    'level': int(typ['level']),
    'id': int(typ['id'], 0),
    'type': typ['type'],
} for typ in matroska_spec}


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
                # elif parsetype == 'flac':
                #     self.parse_flac(f)
                elif parsetype == 'webm':
                    self.parse_embl(f, matroska_spec)
                else:
                    raise RuntimeError('Wrong parsetype!')
            except (FileCorrupted, ValueError, TypeError):
                pass

            return self.lastgoodpos, True

    def parse_ogg(self, f):
        # Based on https://www.xiph.org/ogg/doc/framing.html

        # A page
        while True:
            # Capture pattern
            if not f.read(4) == 'OggS':
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

    # def parse_flac(self, f):
    #     # Based on https://xiph.org/flac/format.html
    #
    #     if not f.read(4) == 'fLaC':
    #         raise FileCorrupted
    #         # But how did the file pass MIME?
    #
    #     # METADATA_BLOCK
    #     while True:
    #         r = ord(f.read(1))
    #         last, typ = r & 128, r & 127
    #         if typ == 127:
    #             raise FileCorrupted
    #
    #         lenblock = reduce(lambda x, r: (x << 8) + r, map(ord, f.read(3)))
    #         f.seek(lenblock, os.SEEK_CUR)
    #
    #         if last:
    #             break
    #
    #     # FRAME
    #     while True:
    #         # FRAME_HEADER
    #         r = reduce(lambda x, r: (x << 8) + r, map(ord, f.read(2)))
    #         # Sync code
    #         if (r & 0b1111111111111100) ^ 0b1111111111111000:
    #             raise FileCorrupted
    #         # Reserved
    #         r & 0b10
    #         # Blocking strategy
    #         variable_blocksize = r & 0b1
    #
    #         r = ord(f.read(1))
    #         # Block size
    #         blocksize = (r & 0b11110000) >> 4
    #         # Sample rate
    #         samplerate = (r & 0b1111)
    #         if samplerate == 0b1111:
    #             raise FileCorrupted
    #
    #         r = ord(f.read(1))
    #         # Channel assignment
    #         (r & 0b11110000) >> 4
    #         # Sample size in bits
    #         (r & 0b1110) >> 1
    #         # Reserved
    #         r & 0b1
    #
    #         if variable_blocksize:
    #             f.seek(6, os.SEEK_CUR)
    #         else:
    #             f.seek(5, os.SEEK_CUR)
    #
    #         if blocksize == 0b0110:
    #             f.seek(1, os.SEEK_CUR)
    #         elif blocksize == 0b0111:
    #             f.seek(2, os.SEEK_CUR)
    #
    #         if samplerate == 0b1100:
    #             f.seek(1, os.SEEK_CUR)
    #         elif (samplerate & 0b1100) == 0b1100:
    #             f.seek(2, os.SEEK_CUR)
    #
    #         # CRC-8
    #         f.seek(1, os.SEEK_CUR)
    #
    #         # SUBFRAME
    #         # SUBFRAME_HEADER
    #         p = BinaryFileProxy(f)
    #         # Zero bit padding
    #         if p.read(1):
    #             raise FileCorrupted
    #
    #         # Subframe type
    #         subframetype = p.read(6)
    #         if subframetype & 100000:
    #             # SUBFRAME_LPC
    #             pass
    #         elif subframetype & 10000:
    #             # reserved
    #             raise FileCorrupted
    #         elif subframetype & 1000:
    #             #
    #             pass
    #         elif subframetype & 100:
    #             # reserved
    #             pass
    #         elif subframetype & 10:
    #             # reserved
    #             pass
    #         elif subframetype & 1:
    #             # SUBFRAME_VERBATIM
    #             pass
    #         else:
    #             # SUBFRAME_CONSTANT
    #             pass
    #         # FRAME_FOOTER
    #         f.seek(2, os.SEEK_CUR)
    #
    #         break

    def parse_embl(self, f, spec):
        # Based on http://matroska-org.github.io/libebml/specs.html

        def seperate(maxsize, includelead):
            t = ord(f.read(1))
            test = 0b10000000
            for i in range(maxsize):
                if t & test:
                    size = i
                    break
                test = (test >> 1)
            else:
                raise FileCorrupted

            return chr(t if includelead else t & ~test) + f.read(size)

        def parse(lvl):
            # A node

            # Element ID
            nodeid = seperate(4, True)
            nodeid = reduce(lambda x, r: (x << 8) + r, map(ord, nodeid))
            # print hex(nodeid)

            # Data size
            datasize = seperate(8, False)
            datasize = reduce(lambda x, r: (x << 8) + r, map(ord, datasize))
            # print hex(datasize), hex(f.tell())

            try:
                nodetype = spec[nodeid]
            except KeyError:
                # These exist, for some reason
                nodetype = {
                    'name': '?',
                    'level': -1,
                    'id': nodeid,
                    'type': '?',
                }
                # raise FileCorrupted

            # print nodetype['name']

            if nodetype['level'] != lvl and nodetype['level'] > 0:
                raise FileCorrupted

            if nodetype['type'] == 'master':
                pos = f.tell()
                while f.tell() < pos + datasize:
                    parse(lvl+1)
                if f.tell() != pos + datasize:
                    raise FileCorrupted
            else:
                f.seek(datasize, os.SEEK_CUR)

            if lvl == 0 and nodetype['name'] != '?':
                self.lastgoodpos = f.tell()

        while True:
            parse(0)
