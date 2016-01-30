import struct
import traceback
from time import time as now
from collections import namedtuple
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name

import os
if os.getuid() != 0:
    raise ImportError('Must be super user to use this module.')

scan_code_table = {}

def _populate_scan_code_table():
    """
    Use `dumpkeys --keys-only` to list all scan codes and their names. We
    then parse the output and built a table. For each scan code we have
    a list of names, and if each name is in the keypad or not.
    """
    from subprocess import check_output
    import re
    keycode_template = r'\nkeycode\s+(\d+) = (.+)'
    dump = check_output(['dumpkeys', '--keys-only'], universal_newlines=True)
    for str_scan_code, str_names in re.findall(keycode_template, dump):
        scan_code = int(str_scan_code)
        scan_code_table[scan_code] = []
        for name in re.split(r'\s{2,}', str_names):
            if not name: continue

            name = name.lstrip('+')
            is_keypad = name.startswith('KP_')
            for mod in ('Meta_', 'Control_', 'dead_', 'KP_'):
                if name.startswith(mod):
                    name = name[len(mod):]
            pair = (normalize_name(name), is_keypad)
            if pair not in scan_code_table[scan_code]:
                scan_code_table[scan_code].append(pair)
_populate_scan_code_table()

class LowLevelEvent(namedtuple('LowLevelEvent', 'seconds microseconds type code value')):
    event_bin_format = 'llHHI'

    @staticmethod
    def from_scan_code(self, scan_code, is_down=True):
        integer, fraction = divmod(now(), 1)
        return LowLevelEvent(int(integer), int(fraction*1e6), EV_KEY, scan_code, is_down)

    @staticmethod
    def from_file(file):
        data = file.read(struct.calcsize(LowLevelEvent.event_bin_format))
        return LowLevelEvent(*struct.unpack(LowLevelEvent.event_bin_format, data))

    def write_to_file(self, file):
        data = struct.pack(LowLevelEvent.event_bin_format, self.seconds, self.microseconds, self.type, self.code, self.value)
        return file.write(data)

# Taken from include/linux/input.h
EV_KEY = 0x01

def _read_input_file(filename_pattern='*-event-kbd'):
    import glob
    event_file = glob.glob('/dev/input/by-id/' + filename_pattern)[0]
    with open(event_file, 'rb') as events:
        while True:
            yield LowLevelEvent.from_file(events)

def listen(handlers):
    for low_event in _read_input_file():
        if low_event.type != EV_KEY:
            continue
        
        time = low_event.seconds + low_event.microseconds / 1e6
        scan_code = low_event.code
        event_type = KEY_DOWN if low_event.value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
        entries = scan_code_table[scan_code]
        is_keypad = entries[0][1]
        names = [name for name, is_keypad in entries]
        
        event = KeyboardEvent(event_type, scan_code, is_keypad, names, time)
        
        for handler in handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                traceback.print_exc()

def map_char(char):
    return map_name_to_scancode(normalize_name(char)), char.isupper()

def press(scan_code):
    raise NotImplementedError()

def release(scan_code):
    raise NotImplementedError()

if __name__ == '__main__':
    def p(e):
        print(e)
    listen([p])