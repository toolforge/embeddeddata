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

import os


class FileProxy(object):
    CHUNK_SIZE = 1 << 20

    def __init__(self, f, track=True):
        self.__f = f
        self.__pos = self._maxseek = f.tell()
        self.__chunkpos = None
        self.__load_chunk()

        if not track:
            self.__update = lambda: None

    def __load_chunk(self):
        base, ext = divmod(self.__pos, self.CHUNK_SIZE)
        base *= self.CHUNK_SIZE
        if self.__chunkpos == base:
            return

        self.__chunkpos = base
        self.__f.seek(base)
        tell = self.__f.tell()
        self.chunk = self.__f.read(self.CHUNK_SIZE)
        self.__pos = tell + min(len(self.chunk), ext)

    def __update(self):
        self._maxseek = max(self.tell(), self._maxseek)

    def read(self, size=-1):
        ret = ''
        if size < 0:
            while True:
                ext = self.__pos % self.CHUNK_SIZE
                r = self.chunk[ext:]
                self.__pos += len(r)
                self.__load_chunk()
                ret += r
                if not r:
                    break
        elif size == 1:
            ext = self.__pos % self.CHUNK_SIZE
            ret = self.chunk[ext:min(len(self.chunk), ext+1)]
            self.__pos += 1
            self.__load_chunk()
        elif size > 0:
            ret = ''
            while size:
                ext = self.__pos % self.CHUNK_SIZE
                r = self.chunk[ext:min(len(self.chunk), ext+size)]
                self.__pos += len(r)
                size -= len(r)
                self.__load_chunk()
                ret += r
                if not r or not size:
                    break

        self.__update()
        return ret

    def readline(self):
        ret = ''
        while True:
            r = self.read(1)
            ret += r
            if not r or r == '\n':
                break
        return ret

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.__pos = offset
        elif whence == os.SEEK_CUR:
            self.__pos += offset
        elif whence == os.SEEK_END:
            raise NotImplementedError  # This breaks the whole detection logic
        self.__load_chunk()
        self.__update()

    def tell(self):
        return self.__pos

    def close(self):
        return self.__f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
