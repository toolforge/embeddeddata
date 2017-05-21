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
import mimetypes
import subprocess
import tempfile


def remux_detect(f):
    from detection.utils import filetype

    f = os.path.abspath(f)
    mime = filetype(f)
    ext = mimetypes.guess_extension(mime, strict=False)
    if ext:
        if ext[0] == '.':
            ext = ext[1:]
        if ext == 'ogx':
            ext = 'ogg'
    else:
        # naive get extension from mime
        ext = mime.split('/')[1]
        if ext[:2] == 'x-':
            ext = ext[2:]
    with tempfile.NamedTemporaryFile(suffix='.'+ext) as tmp:
        args = ['ffmpeg',
                '-loglevel', 'warning',
                '-y',
                '-i', f,
                '-c', 'copy',
                tmp.name]
        subprocess.call(args)

        size = os.path.getsize(tmp.name)
        if size:
            return size, False


def strace_detect(f):
    from detection.by_ending.utils import SyscallTracer

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
