# -*- coding: utf-8 -*-

from time import time as now
import json
from ._canonical_names import canonical_names, normalize_name

try:
    basestring
except NameError:
    basestring = str

KEY_DOWN = "down"
KEY_UP = "up"


class KeyboardEvent(object):
    event_type = None
    scan_code = None
    name = None
    time = None
    device = None
    modifiers = None
    is_keypad = None

    def __init__(
        self,
        event_type,
        scan_code,
        name=None,
        time=None,
        device=None,
        modifiers=None,
        is_keypad=None,
    ):
        self.event_type = event_type
        self.scan_code = scan_code
        self.time = now() if time is None else time
        self.device = device
        self.is_keypad = is_keypad
        if name:
            self.name = normalize_name(name)

    def to_json(self, ensure_ascii=False):
        attrs = dict(
            (attr, getattr(self, attr))
            for attr in [
                "event_type",
                "scan_code",
                "name",
                "time",
                "device",
                "is_keypad",
                "modifiers",
            ]
            if not attr.startswith("_")
        )
        return json.dumps(attrs, ensure_ascii=ensure_ascii)

    def __hash__(self):
        return hash((self.event_type, self.scan_code, self.time, self.device))

    def __repr__(self):
        return "KeyboardEvent({} {} at {})".format(
            self.name or "Unknown {}".format(self.scan_code), self.event_type, self.time
        )

    def __eq__(self, other):
        return (
            isinstance(other, KeyboardEvent)
            and self.event_type == other.event_type
            and self.time == other.time
            and self.device == other.device
            and self.scan_code == other.scan_code
            and self.name == other.name
        )
