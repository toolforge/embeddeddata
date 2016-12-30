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


def find_marker(markers):
    longestmarker = max(map(lambda m: len(m), markers))

    def detect(f):
        search = ''
        lastpos = None
        try:
            with open(f, 'rb') as f:
                while True:
                    r = f.read(1)
                    search += r
                    search = search[-longestmarker:]

                    if any(map(lambda m: m in search[-len(m):], markers)):
                        lastpos = f.tell()
                    elif lastpos:
                        break

                    if not r:
                        break

            if lastpos:
                return lastpos, True
        except Exception:
            traceback.print_exc()
            return

    return detect
