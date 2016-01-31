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

# Taken from include/linux/input.h
EV_SYN = 0x01
EV_KEY = 0x01

import glob
import atexit
LowLevelEvent = namedtuple('LowLevelEvent', 'seconds microseconds type code value')
class InputFile(object):
    event_bin_format = 'llHHI'

    instances = {}

    @staticmethod
    def instance(filepath='/dev/input/by-id/*-event-kbd'):
        if not filepath in InputFile.instances:
            input_file = InputFile(filepath)
            InputFile.instances[filepath] = input_file
            atexit.register(input_file.close)
        return InputFile.instances[filepath]

    def __init__(self, filepath):
        full_path =  glob.glob(filepath)[0]
        self.file_read = open(full_path, 'rb')
        self.file_write = open(full_path, 'wb')

    def close(self, *args):
        self.file_read.close()
        self.file_write.close()

    def read_one(self):
        data = self.file_read.read(struct.calcsize(InputFile.event_bin_format))
        return LowLevelEvent(*struct.unpack(InputFile.event_bin_format, data))

    def read_all(self, type=EV_KEY):
        while True:
            event = self.read_one()
            print(event)
            if event.type == EV_KEY:
                yield event

    def write(self, scan_code, is_down):
        time = now()
        value = int(is_down)
        integer, fraction = divmod(now(), 1)
        seconds = int(integer)
        microseconds = int(fraction * 1e6)
        data = struct.pack(InputFile.event_bin_format, seconds, microseconds, EV_KEY, scan_code, value)
        self.file_write.write(data)

        # Send a sync event to ensure other programs update.
        data = struct.pack(InputFile.event_bin_format, seconds, microseconds, EV_SYN, 0, 0)
        self.file_write.write(data)

def listen(callback):
    for low_event in InputFile.instance().read_all():
        time = low_event.seconds + low_event.microseconds / 1e6
        scan_code = low_event.code
        event_type = KEY_DOWN if low_event.value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
        entries = scan_code_table[scan_code]
        is_keypad = entries[0][1]
        names = [name for name, is_keypad in entries]
        
        event = KeyboardEvent(event_type, scan_code, is_keypad, names, time)
        callback(event)

def map_char(char):
    return scan_code_table[normalize_name(char)][0][0], char.isupper()

def press(scan_code):
    InputFile.instance().write(scan_code, True)

def release(scan_code):
    InputFile.instance().write(scan_code, False)

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
