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
from detection.marker import find_marker


def filetype(path, mime=True):
    args = ['file', path, '-b']
    if mime:
        # not '-i' because we don't need '; charset=binary'
        args.append('--mime-type')

    return subprocess.check_output(args).strip()


def detect(f):
    size = os.path.getsize(f)

    major, minor = filetype(f).split('/')

    detector = None
    if minor in [
        'jpg', 'jpeg',
        'png',
        'tiff',
        'gif'
    ]:
        detector = pillow_detector
    elif minor in [
        'ogg',
        'wav',
        'x-flac', 'flac',
        'webm'
    ]:
        detector = ffmpeg_detector
    elif minor == 'pdf':
        # ISO 32000-1:2008
        # 7.5.5. File Trailer
        # The trailer of a PDF file enables a conforming reader to quickly
        # find the cross-reference table and certain special objects.
        # Conforming readers should read a PDF file from its end. The last
        # line of the file shall contain only the end-of-file marker, %%EOF.
        detector = find_marker(['%%EOF', '%%EOF\n', '%%EOF\r\n', '%%EOF\r'])
    elif minor in ['svg+xml', 'svg']:
        # The closing xml tag of svg files
        detector = find_marker([
            '</svg>', '</svg>\n', '</svg>\r\n', '</svg>\r',
            '</SVG>', '</SVG>\n', '</SVG>\r\n', '</SVG>\r',
        ])
    elif minor in ['vnd.djvu', 'djvu']:
        pass  # FIXME
    elif minor in ['x-xcf', 'xcf']:
        pass  # FIXME
    elif minor == ['midi', 'mid']:
        pass  # FIXME
    else:
        pywikibot.warn('FIXME: Unexpected mime: ' + filetype(f))
        return
    if not detector:
        pywikibot.warn('FIXME: Unsupported mime: ' + filetype(f))
        return

    detection = detector(f)
    if not detection:
        pywikibot.warn('FIXME: Failed detection')
        return

    pos, posexact = detection
    if pos == size:
        return
    elif not pos:
        pywikibot.warn('FIXME: Failed detection')
        return

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
            __import__('shutil').copyfile(tmp.name, '/tmp/test')
            mime = filetype(tmp.name), filetype(tmp.name, False)
            if mime[0] in ['application/octet-stream', 'text/plain']:
                mime = None

                if pos > 0.8 * size:
                    return
            elif size - pos < 512:
                return

    return {
        'pos': pos,
        'posexact': posexact,
        'mime': mime
    }
