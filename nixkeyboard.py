import struct
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

event_bin_format = 'llhhi'

def _read_device_file():
    from pathlib import Path
    event_files = Path('/dev/input/by-id').glob('*-event-kbd')

    for event_file in event_files:
        if '-if01-' not in event_file.name:
            break

    with event_file.open('rb') as events:
        while True:
            yield events.read(struct.calcsize(event_bin_format))

def listen(handlers):
    import time
    for input in _read_device_file():
        s, ms, type, scancode, value = struct.unpack(event_bin_format, input)
        #print(type, scancode, value)
        if scancode == 0 or value > 2:
            # Three events appear for event recognizable key event. I still
            # don't know what are those. The first has a very large "value" and
            # appears before the proper event, and the second has zero code and
            # value, appearing after the event. I'll just ignore them for now.
            continue
        #char = scancode_to_char.get(scancode, '')
        char = scancode_to_char[scancode]
        keycode = KeyboardEvent.name_to_keycode(char) or 0
        time = s + ms/1e6
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
        event = KeyboardEvent(event_type, keycode, scancode, False, time, char)
        #print(event)
        for handler in handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                print(e)

# Codes taken from
# https://github.com/openstenoproject/plover/blob/master/plover/oslayer/winkeyboardcontrol.py
scancode_to_char = {
    0x01: 'ESC',
    0x02: '1',
    0x03: '2',
    0x04: '3',
    0x05: '4',
    0x06: '5',
    0x07: '6',
    0x08: '7',
    0x09: '8',
    0x0A: '9',
    0x0B: '0',
    0x0C: '- _',
    0x0D: '= +',
    0x0E: 'BKSP',
    0x0F: 'Tab',
    0x10: 'Q',
    0x11: 'W',
    0x12: 'E',
    0x13: 'R',
    0x14: 'T',
    0x15: 'Y',
    0x16: 'U',
    0x17: 'I',
    0x18: 'O',
    0x19: 'P',
    0x1A: '[ {',
    0x1B: '] }',
    0x1C: 'Enter',
    0x1D: 'Ctrl',
    0x1E: 'A',
    0x1F: 'S',
    0x20: 'D',
    0x21: 'F',
    0x22: 'G',
    0x23: 'H',
    0x24: 'J',
    0x25: 'K',
    0x26: 'L',
    0x27: '; :',
    0x28: '\' "',
    0x29: '` ~',
    0x2A: 'L SH',
    0x2B: '\ |',
    0x2C: 'Z',
    0x2D: 'X',
    0x2E: 'C',
    0x2F: 'V',
    0x30: 'B',
    0x31: 'N',
    0x32: 'M',
    0x33: ',',
    0x34: '.',
    0x35: '/ ?',
    0x36: 'R SH',
    0x37: 'PtScr',
    0x38: 'Alt',
    0x39: 'Spc',
    0x3A: 'CpsLk',
    0x3B: 'F1',
    0x3C: 'F2',
    0x3D: 'F3',
    0x3E: 'F4',
    0x3F: 'F5',
    0x40: 'F6',
    0x41: 'F7',
    0x42: 'F8',
    0x43: 'F9',
    0x44: 'F10',
    0x45: 'Num Lk',
    0x46: 'Scrl Lk',
    0x47: 'Home',
    0x48: 'Up Arrow',
    0x49: 'Pg Up',
    0x4A: '- (num)',
    0x4B: '4 Left Arrow',
    0x4C: '5 (num)',
    0x4D: '6 Rt Arrow',
    0x4E: '+ (num)',
    0x4F: '1 End',
    0x50: '2 Dn Arrow',
    0x51: '3 Pg Dn',
    0x52: '0 Ins',
    0x53: 'Del .',
    0x54: 'SH F1',
    0x55: 'SH F2',
    0x56: 'SH F3',
    0x57: 'SH F4',
    0x58: 'SH F5',
    0x59: 'SH F6',
    0x5A: 'SH F7',
    0x5B: 'SH F8',
    0x5C: 'SH F9',
    0x5D: 'SH F10',
    0x5E: 'Ctrl F1',
    0x5F: 'Ctrl F2',
    0x60: 'Ctrl F3',
    0x61: 'Ctrl F4',
    0x62: 'Ctrl F5',
    0x63: 'Ctrl F6',
    0x64: 'Ctrl F7',
    0x65: 'Ctrl F8',
    0x66: 'Ctrl F9',
    0x67: 'Ctrl F10',
    0x68: 'Alt F1',
    0x69: 'Alt F2',
    0x6A: 'Alt F3',
    0x6B: 'Alt F4',
    0x6C: 'Alt F5',
    0x6D: 'Alt F6',
    0x6E: 'Alt F7',
    0x6F: 'Alt F8',
    0x70: 'Alt F9',
    0x71: 'Alt F10',
    0x72: 'Ctrl PtScr',
    0x73: 'Ctrl L Arrow',
    0x74: 'Ctrl R Arrow',
    0x75: 'Ctrl End',
    0x76: 'Ctrl PgDn',
    0x77: 'Ctrl Home',
    0x78: 'Alt 1',
    0x79: 'Alt 2',
    0x7A: 'Alt 3',
    0x7B: 'Alt 4',
    0x7C: 'Alt 5',
    0x7D: 'Alt 6',
    0x7E: 'Alt 7',
    0x7F: 'Alt 8',
    0x80: 'Alt 9',
    0x81: 'Alt 0',
    0x82: 'Alt =',
    0x82: 'Alt',
    0x84: 'Ctrl PgUp',
    0x85: 'F11',
    0x86: 'F12',
    0x87: 'SH F11',
    0x88: 'SH F12',
    0x89: 'Ctrl F11',
    0x8A: 'Ctrl F12',
    0x8B: 'Alt F11',
    0x8C: 'Alt F12',
    0x8C: 'Ctrl Up Arrow',
    0x8E: 'Ctrl - (num)',
    0x8F: 'Ctrl 5 (num)',
    0x90: 'Ctrl + (num)',
    0x91: 'Ctrl Dn    Arrow',
    0x92: 'Ctrl Ins',
    0x93: 'Ctrl Del',
    0x94: 'Ctrl Tab',
    0x95: 'Ctrl / (num)',
    0x96: 'Ctrl * (num)',
    0x97: 'Alt Home',
    0x98: 'Alt Up Arrow',
    0x99: 'Alt PgUp',
    0x9B: 'Alt Left Arrow',
    0x9D: 'Alt Rt Arrow',
    0x9F: 'Alt End',
    0xA0: 'Alt Dn Arrow  ',
    0xA1: 'Alt PgDn',
    0xA2: 'Alt Ins  ',
    0xA3: 'Alt Del  ',
    0xA4: 'Alt / (num)  ',
    0xA5: 'Alt Tab  ',
    0xA6: 'Alt Enter (num)',
}

def press_keycode(keycode):
    raise NotImplementedError()

def release_keycode(keycode):
    raise NotImplementedError()

if __name__ == '__main__':
    listen([])
