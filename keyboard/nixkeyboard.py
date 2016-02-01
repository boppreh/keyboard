import struct
import traceback
from time import time as now
from collections import namedtuple
from .keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
from .generic import GenericScanCodeTable

class ScanCodeTable(GenericScanCodeTable):
    def populate(self):
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
            self.table[scan_code] = []
            for name in re.split(r'\s{2,}', str_names):
                if not name: continue

                name = name.lstrip('+')
                is_keypad = name.startswith('KP_')
                for mod in ('Meta_', 'Control_', 'dead_', 'KP_'):
                    if name.startswith(mod):
                        name = name[len(mod):]
                pair = (normalize_name(name), is_keypad)
                if pair not in self.table[scan_code]:
                    self.table[scan_code].append(pair)

scan_code_table = ScanCodeTable()

# Taken from include/linux/input.h
EV_SYN = 0x01
EV_KEY = 0x01

event_bin_format = 'llHHI'

from glob import glob
paths = glob('/dev/input/by-id/*-event-kbd')
KEYBOARD_PATH = paths[0] if paths else None

def listen(callback):
    with open(KEYBOARD_PATH, 'rb') as events_file:
        while True:
            data = events_file.read(struct.calcsize(event_bin_format))
            seconds, microseconds, type, code, value = struct.unpack(event_bin_format, data)
            if type != EV_KEY:
                continue

            time = seconds + microseconds / 1e6
            scan_code = code
            event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
            entries = scan_code_table.get_name_keypad(scan_code)
            is_keypad = entries[0][1]
            names = [name for name, is_keypad in entries]
            
            event = KeyboardEvent(event_type, scan_code, is_keypad, names, time)
            callback(event)

def write_event(scan_code, is_down):
    with open(KEYBOARD_PATH, 'wb') as events_file:
        value = int(is_down)
        integer, fraction = divmod(now(), 1)
        seconds = int(integer)
        microseconds = int(fraction * 1e6)
        data = struct.pack(event_bin_format, seconds, microseconds, EV_KEY, scan_code, value)
        events_file.write(data)

        # Send a sync event to ensure other programs update.
        data = struct.pack(event_bin_format, seconds, microseconds, EV_SYN, 0, 0)
        events_file.write(data)

def map_char(char):
    return scan_code_table.get_scan_code(char), char.isupper()

def press(scan_code):
    write_event(scan_code, True)

def release(scan_code):
    write_event(scan_code, False)

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
