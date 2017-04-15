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

import collections

from detection.by_ending import detect as ending_detect
from detection.by_magic import detect as magic_detect


def detect(f):
    ret = collections.defaultdict(lambda: {
        'posexact': False,
        'via': [],
        'mime': ('?/?', '?')
    })
    for item in ending_detect(f):
        ret[item['pos']]['pos'] = item['pos']
        ret[item['pos']]['posexact'] |= item['posexact']
        ret[item['pos']]['via'].append('Ending')
        ret[item['pos']]['mime'] = item['mime']
    for item in magic_detect(f):
        ret[item['pos']]['pos'] = item['pos']
        ret[item['pos']]['posexact'] = True
        ret[item['pos']]['via'].append('Magic')
        ret[item['pos']]['mime'] = item['mime']
    return collections.OrderedDict(
        sorted(ret.items(), key=lambda (k, v): k)).values()
