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

"""
Use `dumpkeys --keys-only` to list all scan codes and their names. We
then parse the output and built a table. For each scan code we have
a list of names, and if each name is in the keypad or not.
"""
from subprocess import check_output
import re

from_scan_code = {}
to_scan_code = {}

keycode_template = r'\nkeycode\s+(\d+) = (\S+)(?: {2,}(\S+))?'
dump = check_output(['dumpkeys', '--keys-only'], universal_newlines=True)
for str_scan_code, str_regular_name, str_shifted_name in re.findall(keycode_template, dump):
    scan_code = int(str_scan_code)
    regular_name, is_keypad_regular = cleanup_key(str_regular_name)
    if str_shifted_name:
        shifted_name, is_keypad_shifted = cleanup_key(str_shifted_name)
    else:
        shifted_name, is_keypad_shifted = regular_name, is_keypad_regular
    assert is_keypad_regular == is_keypad_shifted

    from_scan_code[scan_code] = ([regular_name, shifted_name], is_keypad_regular)

    # Non-keypad keys are preferred.
    if not is_keypad_regular or regular_name not in to_scan_code:
        to_scan_code[regular_name] = (scan_code, False)

    # Capitalize letters correctly to help reverse mapping.
    if len(shifted_name) == 1:
        shifted_name = shifted_name.upper()

    if not is_keypad_regular or shifted_name not in to_scan_code:
        to_scan_code[shifted_name] = (scan_code, True)

device = aggregate_devices('kbd')

shift_is_pressed = False

def listen(callback):
    while True:
        time, type, code, value = device.read_event()
        if type != EV_KEY:
            continue

        scan_code = code
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD

        names, is_keypad = from_scan_code[scan_code]

        global shift_is_pressed
        name = names[shift_is_pressed]
        if event_type == KEY_DOWN and name == 'shift':
            shift_is_pressed = True
        elif event_type == KEY_UP and name == 'shift':
            shift_is_pressed = False

        event = KeyboardEvent(event_type, scan_code, is_keypad, name, time)
        callback(event)


def write_event(scan_code, is_down):
    device.write_event(EV_KEY, scan_code, int(is_down))

def map_char(character):
    try:
        return to_scan_code[character]
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
