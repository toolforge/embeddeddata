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
import chunk
import struct
import xml.etree.ElementTree as ET

import pywikibot

from detection.utils import FileProxy  # , BinaryFileProxy


matroska_spec = os.path.join(
    os.path.dirname(__file__), 'matroska_ebml_specdata.xml')
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
                    self.parse_ebml(f, matroska_spec, 2)
                elif parsetype in ['vnd.djvu', 'djvu']:
                    self.parse_djvu(f)
                elif parsetype == 'webp':
                    self.parse_webp(f)
                elif parsetype in ['x-xcf', 'xcf']:
                    self.parse_xcf(f)
                elif parsetype == 'tiff':
                    self.parse_tiff(f)
                elif parsetype == 'png':
                    self.parse_png(f)
                elif parsetype in ['midi', 'mid']:
                    self.parse_midi(f)
                else:
                    raise RuntimeError('Wrong parsetype!')
            except (FileCorrupted, ValueError, TypeError, struct.error):
                __import__('traceback').print_exc()
                pass

            return self.lastgoodpos, True

    def read_chunk(self, f, expect_names=(), bigendian=True, align=False):
        c = chunk.Chunk(f, align=align, bigendian=bigendian)

        if expect_names and c.getname() not in expect_names:
            raise FileCorrupted

        expectpos = f.tell() + c.getsize()

        c.close()
        if f.tell() == expectpos:
            self.lastgoodpos = f.tell()
        else:
            raise FileCorrupted

        return c.getname()

    def parse_ogg(self, f):
        # Based on https://www.xiph.org/ogg/doc/framing.html

        # A page
        while True:
            # Capture pattern
            capture = f.read(4)
            if not capture:
                break
            elif capture != 'OggS':
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
    #         if r >> 2 != 0b11111111111110:
    #             raise FileCorrupted
    #         # Reserved
    #         r & 0b10
    #         # Blocking strategy
    #         variable_blocksize = r & 0b1
    #
    #         r = ord(f.read(1))
    #         # Block size
    #         blocksize = r >> 4
    #         # Sample rate
    #         samplerate = r & 0b1111
    #         if samplerate == 0b1111:
    #             raise FileCorrupted
    #
    #         r = ord(f.read(1))
    #         # Channel assignment
    #         r >> 4
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

    def parse_ebml(self, f, spec, n):
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

        for i in range(n):
            parse(0)

    def parse_djvu(self, f):
        if f.read(4) != 'AT&T':
            raise FileCorrupted

        self.read_chunk(f, expect_names=['FORM'])

    def parse_webp(self, f):
        # Based on https://developers.google.com/speed/webp/docs/riff_container
        # Quick and Dirty
        self.read_chunk(f, expect_names=['RIFF'], bigendian=False)

    def parse_xcf(self, f):
        # Based on http://henning.makholm.net/xcftools/xcfspec-saved
        def try_seek(length, whence=os.SEEK_CUR):
            pos = f.tell() if whence == os.SEEK_CUR else 0
            f.seek(length, whence)
            if f.tell() != pos + length:
                raise FileCorrupted(length)
            update()

        def update():
            self.lastgoodpos = max(self.lastgoodpos, f.tell())

        def string():
            str_len, = struct.unpack('>L', f.read(4))
            try_seek(str_len-1, os.SEEK_CUR)
            if f.read(1) != '\x00':
                raise FileCorrupted

        def property_list():
            # property list
            while True:
                prop_type, = struct.unpack('>L', f.read(4))
                prop_len, = struct.unpack('>L', f.read(4))

                try_seek(prop_len, os.SEEK_CUR)

                if prop_type == 0:
                    break
            update()

        # MASTER #
        # magic
        if not f.read(9) == 'gimp xcf ':
            raise FileCorrupted
        # version
        f.read(4)
        # terminator
        if not f.read(1) == '\x00':
            raise FileCorrupted
        # width
        f.read(4)
        # height
        f.read(4)
        # base type
        f.read(4)
        # property list
        property_list()

        p_layers = set()
        while True:
            p_layer, = struct.unpack('>L', f.read(4))
            if p_layer == 0:
                break
            p_layers.add(p_layer)

        p_channels = set()
        while True:
            p_channel, = struct.unpack('>L', f.read(4))
            if p_channel == 0:
                break
            p_channels.add(p_channel)

        p_hierarchies = set()
        p_levels = {}

        update()

        # LAYER #
        for p_layer in p_layers:
            try_seek(p_layer, os.SEEK_SET)
            # width
            f.read(4)
            # height
            f.read(4)
            # type
            f.read(4)
            # name
            string()
            # property list
            property_list()
            # hierarchy
            p_hierarchy, = struct.unpack('>L', f.read(4))
            p_hierarchies.add(p_hierarchy)
            # mask
            p_mask, = struct.unpack('>L', f.read(4))
            if p_mask != 0:
                p_channels.add(p_mask)

            update()

        # CHANNEL #
        for p_channel in p_channels:
            try_seek(p_channel, os.SEEK_SET)
            # width
            f.read(4)
            # height
            f.read(4)
            # name
            string()
            # property list
            property_list()
            # hierarchy
            p_hierarchy, = struct.unpack('>L', f.read(4))
            p_hierarchies.add(p_hierarchy)

            update()

        # HIERARCHY #
        for p_hierarchy in p_hierarchies:
            try_seek(p_hierarchy, os.SEEK_SET)
            # width
            f.read(4)
            # height
            f.read(4)
            # bytes per pixel
            bpp, = struct.unpack('>L', f.read(4))
            while True:
                p_level, = struct.unpack('>L', f.read(4))
                if p_level == 0:
                    break
                p_levels[p_level] = bpp

            update()

        # LEVEL #
        for p_level, bpp in p_levels.items():
            p_tiles = set()

            try_seek(p_level, os.SEEK_SET)
            # width
            width, = struct.unpack('>L', f.read(4))
            # height
            height, = struct.unpack('>L', f.read(4))
            while True:
                p_tile, = struct.unpack('>L', f.read(4))
                if p_tile == 0:
                    break
                p_tiles.add(p_tile)

            update()

            # # Tiles must be contiguous
            # if p_tiles:
            #     try_seek(min(p_tiles), os.SEEK_SET)
            #     # try_seek(width * height * bpp, os.SEEK_CUR)
            for p_tile in p_tiles:
                try_seek(p_tile, os.SEEK_SET)

    def parse_tiff(self, f):
        # Based on
        # https://web.archive.org/web/20161125012350/https://partners.adobe.com/public/developer/en/tiff/TIFF6.pdf
        # FIXME: Tiff Extensions such as NEF or DNG may be false positives

        datatags = set([
            # (offset, bytecount),
            (0x111, 0x117),  # strip
            (0x120, 0x121),  # free
            (0x144, 0x145),  # tile
        ])

        def try_seek(length, whence=os.SEEK_CUR):
            pos = f.tell() if whence == os.SEEK_CUR else 0
            f.seek(length, whence)
            if f.tell() != pos + length:
                raise FileCorrupted(length)
            update()

        def update():
            self.lastgoodpos = max(self.lastgoodpos, f.tell())

        # byte order
        order = f.read(2)
        if order == '\x49\x49':
            order = '<'
        elif order == '\x4D\x4D':
            order = '>'
        else:
            raise FileCorrupted

        # Version
        version, = struct.unpack(order+'H', f.read(2))
        if version != 42:
            raise FileCorrupted

        offset, = struct.unpack(order+'L', f.read(4))
        update()

        p_datas = [], []

        # IFD
        while offset != 0:
            try_seek(offset, os.SEEK_SET)

            num_directories, = struct.unpack(order+'H', f.read(2))

            # directory
            for i in range(num_directories):
                # tag
                tag, = struct.unpack(order+'H', f.read(2))
                # type
                field_type, = struct.unpack(order+'H', f.read(2))
                # number of values
                num_val, = struct.unpack(order+'L', f.read(4))

                type_len, type_code = {
                    1: (1, 'B'),  # byte
                    2: (1, 'c'),  # ascii
                    3: (2, 'H'),  # short
                    4: (4, 'L'),  # long
                    5: (8, 'Q'),  # rational
                    6: (1, 'b'),  # sbyte
                    7: (1, 'c'),  # undefined
                    8: (2, 'h'),  # sshort
                    9: (4, 'l'),  # slong
                    10: (8, 'q'),  # srational,
                    11: (4, 'f'),  # single
                    12: (8, 'd'),  # double
                }.get(field_type, None)
                if field_type is None:
                    pywikibot.warning(
                        'FIXME: TIFF unknown field_type: {}'.format(
                            field_type))
                    type_len, type_code = 1, 'c'

                field_len = type_len * num_val

                # IFD entry
                values = []
                if field_len <= 4:
                    for i in range(num_val):
                        values.append(struct.unpack(
                            order+type_code, f.read(type_len))[0])
                    try_seek(4 - field_len, os.SEEK_CUR)
                else:
                    dir_offset, = struct.unpack(order+'L', f.read(4))
                    curpos = f.tell()

                    try_seek(dir_offset, os.SEEK_SET)
                    for i in range(num_val):
                        values.append(struct.unpack(
                            order+type_code, f.read(type_len))[0])
                    update()

                    f.seek(curpos)

                for offset_tag, bytecount_tag in datatags:
                    if tag == offset_tag:
                        p_datas[0].extend(values)
                        break
                    elif tag == bytecount_tag:
                        p_datas[1].extend(values)
                        break

            offset, = struct.unpack(order+'L', f.read(4))
            update()

        for data_offset, data_bytecount in zip(*p_datas):
            try_seek(data_offset, os.SEEK_SET)
            try_seek(data_bytecount, os.SEEK_CUR)

        # Remove padding
        f.seek(self.lastgoodpos)
        while True:
            if f.read(1) != '\x00':
                f.seek(-1, os.SEEK_CUR)
                break
            else:
                update()

    def parse_png(self, f):
        # Based on http://www.libpng.org/pub/png/spec/1.2/PNG-Structure.html
        if f.read(8) != '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
            raise FileCorrupted

        first = True
        while True:
            length, = struct.unpack('>L', f.read(4))
            chunk_type = f.read(4)
            # print chunk_type

            if first and chunk_type != 'IHDR':
                raise FileCorrupted
            first = False

            pos = f.tell()
            f.seek(length, os.SEEK_CUR)
            if f.tell() != pos + length:
                raise FileCorrupted(length)

            # crc
            f.read(4)

            self.lastgoodpos = f.tell()

            if chunk_type == 'IEND':
                break

    def parse_midi(self, f):
        # Based on http://www.ccarh.org/courses/253/handout/smf/

        self.read_chunk(f, expect_names=['MThd'])
        while True:
            self.read_chunk(f, expect_names=['MTrk'])
