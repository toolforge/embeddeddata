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

import traceback

from detection.utils import FileProxy

CHUNK_SIZE = 1 << 16


def search(search, substr, back=True, reverse=False):
    ret = search.rfind(substr) if reverse else search.find(substr)
    if ret >= 0 and back:
        ret += len(substr)
    return ret


def find_marker(markers, startpos=0, cont=False):
    def detect(f):
        readpos = 0
        chunks = ('', '')
        lastpos = None
        try:
            with FileProxy(open(f, 'rb'), track=False) as f:
                while True:
                    r = f.read(CHUNK_SIZE)
                    readpos += len(chunks[0])
                    chunks = chunks[1], r

                    pos = max([search(''.join(chunks), m, True, cont)
                               for m in markers])
                    if pos >= 0:
                        lastpos = pos + readpos
                    elif lastpos and not cont:
                        break

                    if not r:
                        break

            if lastpos:
                return lastpos, True
        except Exception:
            traceback.print_exc()
            return

    return detect


def seek_trailers(f, pos, trailers):
    if not trailers:
        return pos

    trailers.sort(key=lambda i: len(i), reverse=True)
    try:
        curtrailer = None
        with FileProxy(open(f, 'rb'), track=False) as f:
            f.seek(pos)
            testdata = f.read(len(trailers[0]))
            for trailer in trailers:
                if testdata.startswith(trailer):
                    curtrailer = trailer
                    break
            else:
                return pos

            size = max(CHUNK_SIZE//len(curtrailer), 1) * len(curtrailer)
            f.seek(pos)
            while True:
                r = f.read(size)

                for i in range(0, len(r), len(curtrailer)):
                    if r[i:i+len(curtrailer)] == curtrailer:
                        pos += len(curtrailer)
                    else:
                        return pos

                if not r:
                    return pos

        return pos
    except Exception:
        traceback.print_exc()
        return pos
