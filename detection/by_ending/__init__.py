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
import tempfile

import pywikibot

from detection.utils import filetype
from detection.by_ending.ffmpeg import strace_detect as ffmpeg_detector
from detection.by_ending.pillow import detect as pillow_detector
from detection.by_ending.wave import detect as wave_detector
from detection.by_ending.marker import find_marker, seek_trailers
from detection.by_ending.parsers import ParserDetector

UNKNOWN_TYPES = ['application/octet-stream', 'text/plain']
ARCHIVE_TYPES = ['application/x-rar',
                 'application/zip',
                 'application/x-7z-compressed',
                 'application/x-freearc',
                 'application/vnd.ms-cab-compressed']


def detect(f):
    trailers = ['\x00', '\x20', '\r', '\n', '\r\n']

    size = os.path.getsize(f)

    major, minor = filetype(f).split('/')

    detector = None
    if minor in [
        'jpg', 'jpeg',
        'gif'
    ]:
        detector = pillow_detector
    elif minor in ['x-flac', 'flac']:
        detector = ffmpeg_detector
    elif minor in [
        'ogg',
        'webm',
        'vnd.djvu', 'djvu',
        'webp',
        'x-xcf', 'xcf',
        'tiff',
        'png',
        'midi', 'mid',
    ]:
        detector = lambda f: ParserDetector(f).parse(minor)
    elif minor in ['x-wav', 'wav']:
        detector = wave_detector
    elif minor == 'pdf':
        # ISO 32000-1:2008
        # 7.5.5. File Trailer
        # The trailer of a PDF file enables a conforming reader to quickly
        # find the cross-reference table and certain special objects.
        # Conforming readers should read a PDF file from its end. The last
        # line of the file shall contain only the end-of-file marker, %%EOF.
        detector = find_marker(['%%EOF'], cont=True)
    elif minor in ['svg+xml', 'svg', 'xml']:
        # The closing xml tag of svg files
        detector = find_marker([
            '</svg>', '</svg>\n', '</svg>\r\n', '</svg>\r',
            '</SVG>', '</SVG>\n', '</SVG>\r\n', '</SVG>\r',
        ])
    elif minor in [typ.split('/')[1] for typ in ARCHIVE_TYPES]:
        # Recursed archival formats
        return
    elif minor in [typ.split('/')[1] for typ in UNKNOWN_TYPES]:
        # Recursed unknown formats
        return
    else:
        pywikibot.warning('FIXME: Unexpected mime: ' + filetype(f))
        return
    if not detector:
        pywikibot.warning('FIXME: Unsupported mime: ' + filetype(f))
        return

    detection = detector(f)
    if not detection:
        pywikibot.warning('FIXME: Failed detection')
        return

    pos, posexact = detection
    if pos == size:
        return
    elif not pos:
        pywikibot.warning('FIXME: Failed detection')
        return

    if minor in ['jpg', 'jpeg']:
        trailers.append('\xff\xd9')

    pos = seek_trailers(f, pos, trailers)
    if pos == size:
        return

    # Split and analyze
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
            # __import__('shutil').copyfile(tmp.name, '/tmp/test')
            mime = filetype(tmp.name), filetype(tmp.name, False)
            if mime[0] in UNKNOWN_TYPES:
                if pos > 0.8 * size:
                    return
                if minor == 'jpeg' and pos > 0.5 * size:
                    return
            elif size - pos < 512:
                return

            ret = detect(tmp.name) or []
            for item in ret:
                item['pos'] += pos

    return [{
        'pos': pos,
        'posexact': posexact,
        'mime': mime
    }] + ret
