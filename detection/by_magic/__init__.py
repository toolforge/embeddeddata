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
import tempfile
import traceback

import pywikibot

from detection.utils import FileProxy, filetype

detectors = {}

CHUNK_SIZE = 1 << 20


class FileCorrupted(Exception):
    pass


class UpdatingFileProxy(FileProxy):
    def __init__(self, f):
        super(UpdatingFileProxy, self).__init__(f, track=False)
        self.unset_pos()

    def update_pos(self, pos=None):
        if pos is None:
            self.last_good_pos = self.tell()
        else:
            self.last_good_pos = pos

    def unset_pos(self):
        self.last_good_pos = None

    def try_seek(self, length, whence=os.SEEK_CUR):
        pos = self.tell() if whence == os.SEEK_CUR else 0
        self.seek(length, whence)
        if self.tell() != pos + length:
            raise FileCorrupted(length)


def register_detector(magic):
    def decorator(f):
        detectors[f] = magic
        return f
    return decorator


def findall(string, substr):
    index = 0
    length = len(substr)
    while index < len(string):
        index = string.find(substr, index)
        if index == -1:
            break
        yield index
        index += length


def find_startpos(f, magic):
    readpos = 0
    chunks = ('', '')
    poss = set()
    try:
        while True:
            r = f.read(CHUNK_SIZE)
            readpos += len(chunks[0])
            chunks = chunks[1], r

            for pos in findall(''.join(chunks), magic):
                pos += readpos
                if pos not in poss:
                    yield pos
                    poss.add(pos)

            if not r:
                break
    except Exception:
        traceback.print_exc()
        return


def detect(f):
    with UpdatingFileProxy(open(f, 'rb')) as f:
        ret = []
        for detector, magic in detectors.items():
            f.unset_pos()
            f.seek(0, os.SEEK_SET)

            # search for magic
            for startpos in list(find_startpos(f, magic)):
                # print detector, magic, startpos
                f.seek(startpos)
                try:
                    out = detector(f)
                except (FileCorrupted, ValueError, TypeError):
                    traceback.print_exc()
                    out = True

                endpos = f.last_good_pos
                if not out or endpos is None:
                    pywikibot.warning('Really corrupted file?!')
                    continue

                size = endpos - startpos
                if out is not Ellipsis and size < 128:
                    pywikibot.warning('Very small file?!')
                    continue

                with tempfile.NamedTemporaryFile() as tmp:
                    f.seek(startpos)
                    while True:
                        read = f.read(CHUNK_SIZE)
                        if not read:
                            break
                        tmp.write(read)

                    tmp.flush()
                    mime = filetype(tmp.name), filetype(tmp.name, False)

                ret.append({
                    'pos': startpos,
                    'len': size,
                    'mime': mime
                })

        return ret


__import__('detection.by_magic.rar')
