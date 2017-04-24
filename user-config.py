# -*- coding: utf-8  -*-

family = 'commons'
mylang = 'commons'
usernames['commons']['commons'] = u'Embedded Data Bot'
sysopnames['commons']['commons'] = u'Embedded Data Bot'

with open(__import__('os').path.expanduser('~/.oauth-token.json'), 'r') as _f:
    authenticate['commons.wikimedia.org'] = __import__('json').load(_f)

put_throttle = 1
