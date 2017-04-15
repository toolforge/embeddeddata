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

from PIL import Image
from PIL import ImageFile

from detection.utils import FileProxy

ImageFile.MAXBLOCK = 1


def detect(f):
    with FileProxy(open(f, 'rb')) as f:
        try:
            image = Image.open(f)

            image.tobytes()

            try:
                image._getexif()
            except AttributeError:
                # Some images do not have this method
                pass

            try:
                while True:
                    try:
                        image.seek(image.tell() + 1)
                    except EOFError:
                        break
            except AttributeError:
                # non-gifs
                pass
        except Exception:
            traceback.print_exc()
            return

        return f._maxseek, True
