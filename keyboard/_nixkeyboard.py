# -*- coding: utf-8 -*-
import struct
import traceback
from time import time as now
from collections import namedtuple
from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP
from ._canonical_names import all_modifiers, normalize_name
from ._nixcommon import EV_KEY, aggregate_devices

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

    if name.endswith('_r'):
        name = 'right ' + name[:-2]
    if name.endswith('_l'):
        name = 'left ' + name[:-2]


    return normalize_name(name), is_keypad

def cleanup_modifier(modifier):
    modifier = normalize_name(modifier)
    if modifier in all_modifiers:
        return modifier
    if modifier[:-1] in all_modifiers:
        return modifier[:-1]
    raise ValueError('Unknown modifier {}'.format(modifier))

"""
Use `dumpkeys --keys-only` to list all scan codes and their names. We
then parse the output and built a table. For each scan code and modifiers we
have a list of names and vice-versa.
"""
from subprocess import check_output, CalledProcessError, PIPE
from collections import defaultdict
import re

to_name = defaultdict(list)
from_name = defaultdict(list)
keypad_scan_codes = set()

def register_key(key_and_modifiers, name):
    if name not in to_name[key_and_modifiers]:
        to_name[key_and_modifiers].append(name)
    if key_and_modifiers not in from_name[name]:
        from_name[name].append(key_and_modifiers)

def build_tables():
    if to_name and from_name: return

    modifiers_bits = {
        'shift': 1,
        'alt gr': 2,
        'ctrl': 4,
        'alt': 8,
    }
    keycode_template = r'^keycode\s+(\d+)\s+=(.*?)$'
    try:
        dump = check_output(['dumpkeys', '--keys-only'], universal_newlines=True)
    except CalledProcessError as e:
        if e.returncode == 1:
            raise ValueError('Failed to run dumpkeys to get key names. Check if your user is part of the "tty" group, and if not, add it with "sudo usermod -a -G tty USER".')
        else:
            raise


    for str_scan_code, str_names in re.findall(keycode_template, dump, re.MULTILINE):
        scan_code = int(str_scan_code)
        for i, str_name in enumerate(str_names.strip().split()):
            modifiers = tuple(sorted(modifier for modifier, bit in modifiers_bits.items() if i & bit))
            name, is_keypad = cleanup_key(str_name)
            register_key((scan_code, modifiers), name)
            if is_keypad:
                keypad_scan_codes.add(scan_code)
                register_key((scan_code, modifiers), 'keypad ' + name)

    # dumpkeys consistently misreports the Windows key, sometimes
    # skipping it completely or reporting as 'alt. 125 = left win,
    # 126 = right win.
    if (125, ()) not in to_name or to_name[(125, ())] == ['alt']:
        to_name[(125, ())].clear()
        if (125, ()) in from_name['alt']:
            from_name['alt'].remove((125, ()))
        register_key((125, ()), 'windows')
    if (126, ()) not in to_name or to_name[(126, ())] == ['alt']:
        to_name[(126, ())].clear()
        if (126, ()) in from_name['alt']:
            from_name['alt'].remove((126, ()))
        register_key((126, ()), 'windows')

    # The menu key is usually skipped altogether, so we also add it manually.
    if (127, ()) not in to_name:
        register_key((127, ()), 'menu')

    synonyms_template = r'^(\S+)\s+for (.+)$'
    dump = check_output(['dumpkeys', '--long-info'], universal_newlines=True)
    for synonym_str, original_str in re.findall(synonyms_template, dump, re.MULTILINE):
        synonym, _ = cleanup_key(synonym_str)
        original, _ = cleanup_key(original_str)
        if synonym != original:
            from_name[original].extend(from_name[synonym])
            from_name[synonym].extend(from_name[original])

device = None
def build_device():
    global device
    if device: return
    device = aggregate_devices('kbd')

def init():
    build_device()
    build_tables()

pressed_modifiers = set()

def listen(callback):
    build_device()
    build_tables()

    while True:
        time, type, code, value, device_id = device.read_event()
        if type != EV_KEY:
            continue

        scan_code = code
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD

        pressed_modifiers_tuple = tuple(sorted(pressed_modifiers))
        names = to_name[(scan_code, pressed_modifiers_tuple)] or to_name[(scan_code, ())] or ['unknown']
        name = names[0]
            
        if name in all_modifiers:
            if event_type == KEY_DOWN:
                pressed_modifiers.add(name)
            else:
                pressed_modifiers.discard(name)

        is_keypad = scan_code in keypad_scan_codes
        callback(KeyboardEvent(event_type=event_type, scan_code=scan_code, name=name, time=time, device=device_id, is_keypad=is_keypad, modifiers=pressed_modifiers_tuple))

def write_event(scan_code, is_down):
    build_device()
    device.write_event(EV_KEY, scan_code, int(is_down))

def map_name(name):
    build_tables()
    for entry in from_name[name]:
        yield entry

    parts = name.split(' ', 1)
    if len(parts) > 1 and parts[0] in ('left', 'right'):
        for entry in from_name[parts[1]]:
            yield entry

def press(scan_code):
    write_event(scan_code, True)

def release(scan_code):
    write_event(scan_code, False)

def type_unicode(character):
    codepoint = ord(character)
    hexadecimal = hex(codepoint)[len('0x'):]

    for key in ['ctrl', 'shift', 'u']:
        scan_code, _ = next(map_name(key))
        press(scan_code)

    for key in hexadecimal:
        scan_code, _ = next(map_name(key))
        press(scan_code)
        release(scan_code)

    for key in ['ctrl', 'shift', 'u']:
        scan_code, _ = next(map_name(key))
        release(scan_code)

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
