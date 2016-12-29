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

import traceback

from PIL import Image
from PIL import ImageFile

ImageFile.MAXBLOCK = 1


class FileProxy(object):
    def __init__(self, f):
        self.f = f
        self._maxseek = self.tell()

    def __update(self):
        self._maxseek = max(self.tell(), self._maxseek)

    def read(self, size):
        ret = self.f.read(size)
        self.__update()
        return ret

    def seek(self, offset):
        ret = self.f.seek(offset)
        self.__update()
        return ret

    def tell(self):
        return self.f.tell()


def detect(f):
    f = FileProxy(open(f, 'rb'))
    try:
        image = Image.open(f)

        image.tobytes()
        image._getexif()
    except Exception:
        traceback.print_exc()
        return

    return f._maxseek, True
