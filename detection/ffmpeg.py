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

# The ptrace part is largely based on:
# https://github.com/haypo/python-ptrace/blob/11a117427faee52ebb54de0bc6fe21738cbff7a4/strace.py

from __future__ import absolute_import, print_function

import os

from ptrace.debugger import (PtraceDebugger, ProcessExit,
                             ProcessSignal, NewProcessEvent, ProcessExecution)
from ptrace.func_call import FunctionCallOptions
from ptrace.debugger.child import createChild


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


def detect(f):
    # matroska supports (almost?) all codecs
    f = os.path.abspath(f)
    args = ['ffmpeg',
            '-loglevel', 'warning',
            '-y',
            '-i', f,
            '-c', 'copy',
            '-f', 'matroska',
            '/dev/null']

    quotedf = "'%s'" % f  # HACK

    fhs = [None, None]  # [in, out] file handlers
    recordstate = {
        'active': True,
        'maxpos': 0,
        'pos': None,
    }

    def update():
        recordstate['maxpos'] = max(recordstate['pos'], recordstate['maxpos'])

    def syscallHandler(syscall):
        # HACK

        # __import__('code').interact('Shell: ', local=locals())
        if syscall.name == 'open':
            path = syscall.arguments[0].format()
            if path == quotedf:
                fhs[0] = syscall.result
                recordstate['pos'] = 0
            elif path == "'/dev/null'":
                fhs[1] = syscall.result
        elif syscall.name == 'close':
            fh = syscall.arguments[0].value
            if fh == fhs[0]:
                fhs[0] = None
            elif fh == fhs[1]:
                fhs[1] = None
        elif syscall.name == 'lseek' and syscall.arguments[0].value == fhs[0]:
            recordstate['pos'] = syscall.result
            # print(recordstate['pos'])
        elif syscall.name == 'read' and syscall.arguments[0].value == fhs[0]:
            if syscall.result:
                recordstate['pos'] += syscall.result
            else:
                recordstate['active'] = False
        elif syscall.name == 'write' and syscall.arguments[0].value == fhs[1]:
            if syscall.result and recordstate['active']:
                recordstate['maxpos'] = max(recordstate['pos'],
                                            recordstate['maxpos'])

    SyscallTracer(args, syscallHandler).main()
    return recordstate['maxpos'], False
