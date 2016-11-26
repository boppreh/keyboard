# -*- coding: utf-8 -*-
import struct
import traceback
from time import time as now
from collections import namedtuple
from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
from ._nixcommon import EV_KEY, aggregate_devices, ensure_root

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
keypad_scan_codes = set()

def register_key(key_and_modifiers, name):
    to_name[key_and_modifiers] = name
    from_name[name] = key_and_modifiers

def build_tables():
    if to_name and from_name: return
    ensure_root()

    keycode_template = r'^(.*?)keycode\s+(\d+)\s+=(.*?)$'
    dump = check_output(['dumpkeys', '--keys-only'], universal_newlines=True)
    for str_modifiers, str_scan_code, str_names in re.findall(keycode_template, dump, re.MULTILINE):
        if not str_names: continue
        modifiers = tuple(sorted(set(cleanup_modifier(m) for m in str_modifiers.strip().split())))
        scan_code = int(str_scan_code)
        name, is_keypad = cleanup_key(str_names.strip().split()[0])
        to_name[(scan_code, modifiers)] = name
        if is_keypad:
            keypad_scan_codes.add(scan_code)
            from_name['keypad ' + name] = (scan_code, ())
        if name not in from_name or len(modifiers) < len(from_name[name][1]):
            from_name[name] = (scan_code, modifiers)

    # Assume Shift uppercases keys that are single characters.
    # Hackish, but a good heuristic so far.
    for name, (scan_code, modifiers) in list(from_name.items()):
        upper = name.upper()
        if len(name) == 1 and upper not in from_name:
            register_key((scan_code, modifiers + ('shift',)), upper)

    # dumpkeys consistently misreports the Windows key, sometimes
    # skipping it completely or reporting as 'alt. 125 = left win,
    # 126 = right win.
    if (125, ()) not in to_name or to_name[(125, ())] == 'alt':
        register_key((125, ()), 'windows')
    if (126, ()) not in to_name or to_name[(126, ())] == 'alt':
        register_key((126, ()), 'windows')

    # The menu key is usually skipped altogether, so we also add it manually.
    if (127, ()) not in to_name:
        register_key((127, ()), 'menu')

    synonyms_template = r'^(\S+)\s+for (.+)$'
    dump = check_output(['dumpkeys', '--long-info'], universal_newlines=True)
    for synonym_str, original_str in re.findall(synonyms_template, dump, re.MULTILINE):
        synonym, _ = cleanup_key(synonym_str)
        original, _ = cleanup_key(original_str)
        try:
            from_name[synonym] = from_name[original]
        except KeyError:
            # Dumpkeys reported a synonym to an unknown key.
            pass

device = None
def build_device():
    global device
    if device: return
    ensure_root()
    device = aggregate_devices('kbd')

pressed_modifiers = set()

def listen(queue):
    build_device()
    build_tables()

    while True:
        time, type, code, value, device_id = device.read_event()
        if type != EV_KEY:
            continue

        scan_code = code
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD

        try:
            name = to_name[(scan_code, tuple(sorted(pressed_modifiers)))]
        except KeyError:
            name = to_name.get((scan_code, ()), 'unknown')
            
        if name in ('alt', 'alt gr', 'ctrl', 'shift'):
            if event_type == KEY_DOWN:
                pressed_modifiers.add(name)
            else:
                pressed_modifiers.discard(name)

        is_keypad = scan_code in keypad_scan_codes
        queue.put(KeyboardEvent(event_type=event_type, scan_code=scan_code, name=name, time=time, device=device_id, is_keypad=is_keypad))

def write_event(scan_code, is_down):
    build_device()
    device.write_event(EV_KEY, scan_code, int(is_down))

def map_char(name):
    build_tables()
    if name in from_name:
        return from_name[name]

    parts = name.split(' ', 1)
    if (name.startswith('left ') or name.startswith('right ')) and parts[1] in from_name:
        return from_name[parts[1]]
    else:
        raise ValueError('Name {} is not mapped to any known key.'.format(repr(name)))

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
