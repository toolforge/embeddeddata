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

import json
import signal

from redis import Redis

import pywikibot
from pywikibot.comms.eventstreams import site_rc_listener

from config import REDIS_KEY

TIMEOUT = 60  # We expect at least one rc entry every minute


class TimeoutError(Exception):
    pass


def on_timeout(signum, frame):
    raise TimeoutError


def run_watcher():
    site = pywikibot.Site(user="Embedded Data Bot")
    redis = Redis(host="tools-redis")

    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(TIMEOUT)

    rc = site_rc_listener(site)
    for change in rc:
        signal.alarm(TIMEOUT)

        if (
            change['type'] == 'log' and
            change['namespace'] == 6 and
            change['log_type'] == 'upload'
        ):
            redis.rpush(REDIS_KEY, json.dumps(change))

    pywikibot.output("Exit - THIS SHOULD NOT HAPPEN")


def main():
    pywikibot.handleArgs()
    run_watcher()


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
