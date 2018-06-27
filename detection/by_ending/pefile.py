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

import contextlib
import traceback

import pefile

pefile.fast_load = True


def detect(f):
    with contextlib.closing(pefile.PE(f)) as f:
        try:
            return max(section.PointerToRawData+section.SizeOfRawData
                       for section in f.sections), True
        except Exception:
            traceback.print_exc()
            return
