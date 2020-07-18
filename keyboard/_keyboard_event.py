# -*- coding: utf-8 -*-

import json
from time import time as now

from ._canonical_names import normalize_name

KEY_DOWN = 'down'
KEY_UP = 'up'

class KeyboardEvent(object):
    event_type = None
    scan_code = None
    name = None
    time = None
    device = None
    modifiers = None
    is_keypad = None
    suppressed = None

    def __init__(self, event_type, scan_code, name=None, time=None, device=None, modifiers=None, is_keypad=None, suppressed=False):
        self.event_type = event_type
        self.scan_code = scan_code
        self.time = now() if time is None else time
        self.device = device
        self.is_keypad = is_keypad
        self.modifiers = modifiers
        self.suppressed = suppressed
        if name:
            self.name = normalize_name(name)

    def to_json(self, ensure_ascii=False):
        attrs = dict(
            (attr, getattr(self, attr)) for attr in ['event_type', 'scan_code', 'name', 'time', 'device', 'is_keypad']
            if not attr.startswith('_') and getattr(self, attr) is not None
        )
        return json.dumps(attrs, ensure_ascii=ensure_ascii)

    def __repr__(self):
        return 'KeyboardEvent({} {})'.format(self.name or 'Unknown {}'.format(self.scan_code), self.event_type)

    def __eq__(self, other):
        return (
            isinstance(other, KeyboardEvent)
            and self.event_type == other.event_type
            and (
                not self.scan_code or not other.scan_code or self.scan_code == other.scan_code
            ) and (
                not self.name or not other.name or self.name == other.name
            )
        )
