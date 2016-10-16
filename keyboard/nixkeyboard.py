# -*- coding: utf-8 -*-
import struct
import traceback
from time import time as now
from collections import namedtuple
from .keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
from .nixcommon import EV_KEY, aggregate_devices

import os
if os.geteuid() != 0:
    raise ImportError('You must be root to use this library on linux.')

# TODO: start by reading current keyboard state, as to not missing any already pressed keys.
# See: http://stackoverflow.com/questions/3649874/how-to-get-keyboard-state-in-linux

def cleanup_key(name):
    """ Formats a dumpkeys format to our standard. """
    name = name.lstrip('+')
    is_keypad = name.startswith('KP_')
    for mod in ('Meta_', 'Control_', 'dead_', 'KP_'):
        if name.startswith(mod):
            name = name[len(mod):]

    # Dumpkeys is weird like that.
    if name == 'Remove':
        name = 'Delete'
    elif name == 'Delete':
        name = 'Backspace'

    return normalize_name(name), is_keypad

def cleanup_modifier(modifier):
    expected = ('alt', 'ctrl', 'shift', 'alt gr')
    modifier = normalize_name(modifier)
    if modifier in expected:
        return modifier
    if modifier[:-1] in expected:
        return modifier[:-1]
    raise ValueError('Unknown modifier {}'.format(modifier))

"""
Use `dumpkeys --keys-only` to list all scan codes and their names. We
then parse the output and built a table. For each scan code and modifiers we
have a list of names and vice-versa.
"""
from subprocess import check_output
import re

to_name = {}
from_name = {}

keycode_template = r'^(.*?)keycode\s+(\d+)\s+=(.*?)$'
dump = check_output(['dumpkeys', '--keys-only'], universal_newlines=True)
for str_modifiers, str_scan_code, str_names in re.findall(keycode_template, dump, re.MULTILINE):
    if not str_names: continue
    modifiers = tuple(sorted(set(cleanup_modifier(m) for m in str_modifiers.strip().split())))
    scan_code = int(str_scan_code)
    name, is_keypad = cleanup_key(str_names.strip().split()[0])
    to_name[(scan_code, modifiers)] = name
    if name not in from_name or len(modifiers) < len(from_name[name][1]):
        from_name[name] = (scan_code, modifiers)

# TODO: name normalization is discarding uppercase letters, thus this hack.
from string import ascii_uppercase
for letter in ascii_uppercase:
    if letter not in from_name:
        scan_code, modifiers = from_name[letter.lower()]
        from_name[letter] = (scan_code, modifiers + ('shift',))

device = aggregate_devices('kbd')

pressed_modifiers = set()

def listen(callback):
    while True:
        time, type, code, value = device.read_event()
        if type != EV_KEY:
            continue

        scan_code = code
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD

        try:
            name = to_name[(scan_code, tuple(sorted(pressed_modifiers)))]
        except KeyError:
            name = to_name[(scan_code, ())]
            
        if name in ('alt', 'alt gr', 'ctrl', 'shift'):
            if event_type == KEY_DOWN:
                pressed_modifiers.add(name)
            else:
                pressed_modifiers.remove(name)

        event = KeyboardEvent(event_type, scan_code, name, time)
        blocking = callback(event)
        # Unfortunately we don't have a way to block events, so this feature
        # is not available on nix.


def write_event(scan_code, is_down):
    device.write_event(EV_KEY, scan_code, int(is_down))

def map_char(character):
    try:
        return from_name[character]
    except KeyError:
        raise ValueError('Character {} is not mapped to any known key.'.format(repr(character)))

def press(scan_code):
    write_event(scan_code, True)

def release(scan_code):
    write_event(scan_code, False)

def type_unicode(character):
    codepoint = ord(character)
    hexadecimal = hex(codepoint)[len('0x'):]

    for key in ['ctrl', 'shift', 'u']:
        scan_code, _ = map_char(key)
        press(scan_code)

    for key in hexadecimal:
        scan_code, _ = map_char(key)
        press(scan_code)
        release(scan_code)

    for key in ['ctrl', 'shift', 'u']:
        scan_code, _ = map_char(key)
        release(scan_code)

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
