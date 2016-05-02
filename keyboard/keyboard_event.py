# -*- coding: utf-8 -*-

from time import time as now

KEY_DOWN = 'down'
KEY_UP = 'up'

class KeyboardEvent(object):
    def __init__(self, event_type, scan_code, is_keypad=False, names=[], time=None):
        self.event_type = event_type
        self.scan_code = scan_code
        self.is_keypad = is_keypad
        self.time = now() if time is None else time
        self.names = names

    def matches(self, description):
        if isinstance(description, int):
            return self.scan_code == description
        else:
            normalized = normalize_name(description)
            return (
                normalized in self.names
                or 'left ' + normalized in self.names
                or 'right ' + normalized in self.names
            )

    def __repr__(self):
        name = self.names[0] if len(self.names) else 'Unknown {}'.format(self.scan_code)
        return 'KeyboardEvent({} {})'.format(name, self.event_type)

canonical_names = {
    'escape': 'esc',
    'return': 'enter',
    'del': 'delete',
    'control': 'ctrl',
    'altgr': 'alt gr',

    '\x1b': 'esc',
    '\x08': 'backspace',
    '\n': 'enter',
    '\t': 'tab',

    'scrlk': 'scroll lock',
    'prtscn': 'print screen',
    'prnt scrn': 'print screen',
    'snapshot': 'print screen',
    'ins': 'insert',
    'pause break': 'pause',
    'ctrll lock': 'caps lock',
    'number lock': 'num lock',
    'numlock:': 'num lock',

    ' ': 'space',
    'underscore': '_',

    'equal': '=',
    'add': '+',
    'subtract': '-',
    'minus': '-',
    'multiply': '*',
    'divide': '/',

    'question': '?',
    'exclam': '!',
    'slash': '/',
    'backslash': '\\',
    'braceleft': '{',
    'braceright': '}',
    'bracketleft': '[',
    'bracketright': ']',

    'period': '.',
    'comma': ',',
    'semicolon': ';',
    'colon': ':',

    'less': '<',
    'greater': '>',
    'ampersand': '&',
    'at': '@',
    'numbersign': '#',
    'hash': '#',
    'hashtag': '#',
    'dollar': '$',
    'sterling': '£',
    'cent': '¢',
    'notsign': '¬',
    'percent': '%',
    'diaeresis': '"',
    'quotedbl': '"',
    
    'acute': '´',
    'agudo': '´',
    'grave': '`',
    'tilde': '~',
    'til': '~',
    'apostrophe': '\'',
    
    'ccedilla': 'ç',
    'ae': 'æ',
    'eth': 'ð',
    'masculine': 'º',
    'feminine': 'ª',

    'zero': '0',
    'one': '1',
    'two': '2',
    'three': '3',
    'four': '4',
    'five': '5',
    'six': '6',
    'seven': '7',
    'eight': '8',
    'nine': '9',
}

def normalize_name(name):
    name = name.lower()
    if name != '_':
        name = name.replace('_', ' ')
    return canonical_names.get(name, name)
