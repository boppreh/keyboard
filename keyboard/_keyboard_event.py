# -*- coding: utf-8 -*-

from time import time as now
from ._canonical_names import canonical_names

try:
    basestring
except NameError:
    basestring = str

KEY_DOWN = 'down'
KEY_UP = 'up'

class KeyboardEvent(object):
    event_type = None
    scan_code = None
    name = None
    time = None

    def __init__(self, event_type, scan_code, name=None, time=None, device=None, is_keypad=None):
        self.event_type = event_type
        self.scan_code = scan_code
        self.time = now() if time is None else time
        self.device = device
        self.is_keypad = is_keypad
        if name:
            self.name = normalize_name(name)

    def __repr__(self):
        return 'KeyboardEvent({} {})'.format(self.name or 'Unknown {}'.format(self.scan_code), self.event_type)

def normalize_name(name):
    if not name:
        return 'unknown'
    if not isinstance(name, basestring):
        raise ValueError('Can only normalize string names. Unexpected '+ repr(name))

    name = name.lower()
    if name != '_':
        name = name.replace('_', ' ')

    return canonical_names.get(name, name)
