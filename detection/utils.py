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

from ptrace.debugger import (PtraceDebugger, ProcessExit,
                             ProcessSignal, NewProcessEvent, ProcessExecution)
from ptrace.func_call import FunctionCallOptions
from ptrace.debugger.child import createChild


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
            ret = self.chunk[ext:ext+1]
            self.__pos += 1
            self.__load_chunk()
        elif size > 0:
            ret = ''
            while size:
                ext = self.__pos % self.CHUNK_SIZE
                r = self.chunk[ext:ext+size]
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


class BinaryFileProxy(object):
    def __init__(self, f):
        self.__f = f
        self.__pos = 0
        self.__load_byte()

    def __load_byte(self):
        self.curbyte = ord(self.__f.read(1))

    def read(self, size):
        if size < 0:
            raise NotImplementedError
        elif size == 1:
            if not self.__pos:
                self.__load_byte()
                self.__pos = 8
            self.__pos -= 1

            return (self.curbyte & (1 << self.__pos)) >> self.__pos

        elif size > 1:
            ret = 0
            for i in range(size):
                ret = ret << 1 | self.read(1)
            return ret
        return 0

    def seek(self, offset, whence=os.SEEK_SET):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def close(self):
        return self.__f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SubFileProxy(object):
    def __init__(self, f, start, size):
        self.__f = f
        self.__start = start
        self.__end = start + size
        f.seek(start)

    def read(self, size=-1):
        if size < 0:
            return self.__f.read(self.__end - self.__f.tell())
        elif size > 0:
            return self.__f.read(min(size, self.__end - self.__f.tell()))
        return ''

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.__f.seek(self.__start + offset)
        elif whence == os.SEEK_CUR:
            pos = self.__f.tell() + offset
            pos = min(max(pos, self.__start), self.__end)
            self.__f.seek(pos)
        elif whence == os.SEEK_END:
            assert offset <= 0
            self.__f.seek(self.__end + offset)

    def tell(self):
        return self.__f.tell() - self.__start

    def close(self):
        return self.__f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SyscallTracer(object):
    def __init__(self, program, syscallHandler):
        self.program = program
        self.syscallHandler = syscallHandler

    def syscallTrace(self, process):
        # First query to break at next syscall
        self.prepareProcess(process)

        while True:
            # No more process? Exit
            if not self.debugger:
                break

            # Wait until next syscall enter
            try:
                event = self.debugger.waitSyscall()
                process = event.process
            except ProcessExit as event:
                continue
            except ProcessSignal as event:
                event.display()
                process.syscall(event.signum)
                continue
            except NewProcessEvent as event:
                process = event.process
                self.prepareProcess(process)
                process.parent.syscall()
                continue
            except ProcessExecution as event:
                process = event.process
                process.syscall()
                continue

            # Process syscall enter or exit
            self.syscall(process)

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(self.syscall_options)
        if syscall and syscall.result is not None:
            self.syscallHandler(syscall)

        # Break at next syscall
        process.syscall()

    def prepareProcess(self, process):
        process.syscall()

    def runDebugger(self):
        # Create debugger and traced process
        process = self.createProcess()
        if not process:
            return

        self.syscall_options = FunctionCallOptions()

        self.syscallTrace(process)

    def main(self):
        self.debugger = PtraceDebugger()
        try:
            self.runDebugger()
        except ProcessExit:
            pass
        self.debugger.quit()

    def createProcess(self):
        pid = self.createChild(self.program)
        is_attached = True
        return self.debugger.addProcess(pid, is_attached=is_attached)

    def createChild(self, arguments, env=None):
        return createChild(arguments, False, env)
