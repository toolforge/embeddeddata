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
import shutil
import tempfile
import traceback
import urllib
import uuid

import pywikibot
from redis import Redis

from config import REDIS_KEY
from detection import detect


def sizeof_fmt(num, suffix='B'):
    # Source: http://stackoverflow.com/a/1094933
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def run_worker():
    try:
        tmpdir = tempfile.mkdtemp()

        site = pywikibot.Site(user="Embedded Data Bot")
        redis = Redis(host="tools-redis")

        while True:
            _, title = redis.blpop(REDIS_KEY)
            pywikibot.output('Received: %s' % title)
            filepage = pywikibot.FilePage(site, title)

            if not filepage.exists():
                continue

            if filepage.getLatestUploader().editCount(force=True) > 200:
                continue

            path = os.path.join(tmpdir, uuid.uuid1())

            # Download
            try:
                urllib.urlretrieve(filepage.fileUrl, path)

                res = detect(path)
                if res:
                    pos = '%s (%s bytes)' % (sizeof_fmt(res['pos']),
                                             res['pos'])
                    if not res['posexact']:
                        pos = 'about ' + pos

                    mime = 'Detected MIME: %s (%s)' % res['mime'] \
                        if res['mime'] else ''
                    msg = ('File suspected to contain [[COM:CSD#F9|'
                           'embedded data]] after %s. %s' % (
                                pos, mime
                           ))

                    # for now: add a {{speedy}}
                    filepage.text = ('{{speedy|1=%s}}\n' % msg) + filepage.text
                    filepage.save('Bot: Adding {{[[Template:speedy|speedy]]}} '
                                  'to this embedded data suspect.')
            except Exception:
                traceback.print_exc()
            finally:
                os.remove(path)

        pywikibot.output("Exit - THIS SHOULD NOT HAPPEN")
    finally:
        shutil.rmtree(tmpdir)


def main():
    pywikibot.handleArgs()
    run_worker()

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
