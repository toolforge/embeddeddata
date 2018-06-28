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

from detection.utils import filetype

middlewares = {}


def register_detector(name, accepts):
    def decorator(f):
        middlewares[f] = accepts
        f.middleware_name = name
        return f
    return decorator


def detect(f):
    ret = []
    major, minor = filetype(f).split('/')

    for middleware, accepts in middlewares.items():
        if accepts(major, minor):
            try:
                for item in middleware(f) or []:
                    item['middleware'] = middleware.middleware_name
                    ret.append(item)
            except Exception:
                traceback.print_exc()

    return ret


for lib in ['ffmpeg', 'pdfminer', 'ffc']:
    __import__('detection.middleware.' + lib)
