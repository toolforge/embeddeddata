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

import pywikibot
from pywikibot.comms.rcstream import site_rc_listener

from redis import Redis
from config import REDIS_KEY


def run_watcher():
    site = pywikibot.Site(user="Embedded Data Bot")
    redis = Redis(host="tools-redis")

    rc = site_rc_listener(site)

    for change in rc:
        # Uploads from non-bots
        if not change['bot'] and \
                change['namespace'] == 6 and \
                change['type'] == 'log' and \
                change['log_type'] == 'upload':
            redis.rpush(REDIS_KEY, change['title'])

    pywikibot.output("Exit - THIS SHOULD NOT HAPPEN")


def main():
    pywikibot.handleArgs()
    run_watcher()

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
