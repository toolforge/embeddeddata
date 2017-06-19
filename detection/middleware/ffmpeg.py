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
import subprocess
import tempfile

from detection.by_magic import detect as magic_detect
from detection.middleware import register_detector


@register_detector('Remux_Matroska',
                   lambda major, minor:
                   major in ['audio', 'video'] and minor not in ['midi', 'mid']
                   or minor in ['ogg'])
def ffmpeg_remux_mkv(f):
    with tempfile.NamedTemporaryFile(suffix='.mkv') as tmp:
        args = ['ffmpeg',
                '-loglevel', 'warning',
                '-y',
                '-i', f,
                '-c', 'copy',
                tmp.name]
        subprocess.call(args)

        size = os.path.getsize(tmp.name)
        if size:
            return magic_detect(tmp.name)
