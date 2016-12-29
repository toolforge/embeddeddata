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

import os
import subprocess
import tempfile

import pywikibot

from detection.ffmpeg import detect as ffmpeg_detector
from detection.pillow import detect as pillow_detector


def filetype(path, mime=True):
    args = ['file', path, '-b']
    if mime:
        # not '-i' because we don't need '; charset=binary'
        args.append('--mime-type')

    return subprocess.check_output(args).strip()


def detect(f):
    size = os.path.getsize(f)

    hasfound = False
    for detector in [pillow_detector, ffmpeg_detector]:
        detection = detector(f)
        if detection:
            _pos, _posexact = detection
            if not _pos:
                continue

            pos, posexact = _pos, _posexact

            hasfound = True
            if pos < size * 0.8 and posexact:
                break

    if not hasfound:
        pywikibot.warn('FIXME: Unsupported mime: ' + filetype(f))
        return
    elif pos == size:
        return

    pos, posexact = detection

    # Split and analyse
    chunk_size = 1 << 20

    mime = None
    with open(f, 'rb') as fin:
        with tempfile.NamedTemporaryFile() as tmp:
            fin.seek(pos)
            while True:
                read = fin.read(chunk_size)
                if not read:
                    break
                tmp.write(read)

            tmp.flush()

            mime = filetype(tmp.name), filetype(tmp.name, False)
            if mime == ('application/octet-stream', 'data'):
                mime = None

    return {
        'pos': pos,
        'posexact': posexact,
        'mime': mime
    }
