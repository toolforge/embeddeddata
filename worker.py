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
from detection.by_ending import ARCHIVE_TYPES


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
            filepage = pywikibot.FilePage(site, title.decode('utf-8'))

            if not filepage.exists():
                continue

            for i in range(8):
                try:
                    filepage.get_file_history()
                except pywikibot.exceptions.PageRelatedError as e:
                    # pywikibot.exceptions.PageRelatedError:
                    # loadimageinfo: Query on ... returned no imageinfo
                    pywikibot.exception(e)
                    site.throttle()
                else:
                    break
            else:
                raise

            if pywikibot.User(site, filepage.latest_file_info.user).editCount(
                    force=True) > 200:
                continue

            pywikibot.output('Working on: %s' % title)

            path = os.path.join(tmpdir, str(uuid.uuid1()))

            # Download
            try:
                for i in range(8):
                    try:
                        success = filepage.download(path)
                    except Exception as e:
                        pywikibot.exception(e)
                        success = False
                    if success:
                        break
                    else:
                        pywikibot.warning(
                            'Possibly corrupted download on attempt %d' % i)
                        site.throttle()
                else:
                    pywikibot.warning('FIXME: Download attempt exhausted')

                res = detect(path)
                if res:
                    msg = []
                    for item in res:
                        pos = '%s (%s bytes, via %s)' % (
                            sizeof_fmt(item['pos']),
                            item['pos'],
                            ','.join(item['via']))
                        if not item['posexact']:
                            pos = 'about ' + pos

                        mime = 'Detected MIME: %s (%s)' % item['mime'] \
                            if item['mime'] else 'Unknown MIME'
                        msg.append('After %s: %s' % (pos, mime))
                    msg = '; '.join(msg)

                    msgprefix = ('This file contains [[COM:CSD#F9|'
                                 'embedded data]]: ')

                    pywikibot.output(u"\n\n>>> %s <<<"
                                     % filepage.title(asLink=True))
                    pywikibot.output(msg)

                    for func in [overwrite, delete, add_speedy]:
                        if func(filepage, msg, msgprefix, res):
                            break

            except Exception:
                traceback.print_exc()
            finally:
                os.remove(path)

        pywikibot.output("Exit - THIS SHOULD NOT HAPPEN")
    finally:
        shutil.rmtree(tmpdir)


def overwrite(filepage, msg, msgprefix, res):
    try:
        if all([item['posexact'] and item['mime'] and
                item['mime'][0] == filepage.latest_file_info.mime
                for item in res]):
            with tempfile.NamedTemporaryFile() as tmp:
                urllib.urlretrieve(filepage.fileUrl(), tmp.name)
                tmp.truncate(res[0]['pos'])
                filepage.upload(tmp.name,
                                comment=msgprefix+msg,
                                ignore_warnings=True)
                return True
    except Exception:
        traceback.print_exc()


def delete(filepage, msg, msgprefix, res):
    try:
        if not any([item['posexact'] and item['mime'] and
                    item['mime'][0] in ARCHIVE_TYPES
                    for item in res]):
                return

        if len(filepage.get_file_history()) != 1:
            return

        add_speedy(filepage, msg, msgprefix, res)
        filepage.delete(msgprefix+msg, prompt=False)
        return True
    except Exception:
        traceback.print_exc()


def add_speedy(filepage, msg, msgprefix, res):
    try:
        # Make sure no edit conflicts happen here
        filepage.save(prependtext='{{embedded data|suspect=1|1=%s}}\n' % msg,
                      summary='Bot: Adding {{[[Template:Embedded data|'
                      'embedded data]]}} to this embedded data suspect.')
        return True
    except Exception:
        traceback.print_exc()


def main():
    pywikibot.handleArgs()
    run_worker()


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
