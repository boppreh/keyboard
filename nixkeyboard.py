import struct
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

def _read_device_file():
    from pathlib import Path
    event_files = Path('/dev/input/by-id').glob('*-event-kbd')

    for event_file in event_files:
        if '-if01-' not in event_file.name:
            break

    with event_file.open('rb') as events:
        while True:
            yield events.read(16)

def listen(handlers):
    import time
    for input in _read_device_file():
        s, ms, type, scancode, value = struct.unpack('llhhi', input)
        print(type, scancode, value)
        if scancode == 0 or value > 2:
            # Three events appear for event recognizable key event. I still
            # don't know what are those. The first has a very large "value" and
            # appears before the proper event, and the second has zero code and
            # value, appearing after the event. I'll just ignore them for now.
            continue
        char = scancode_to_char.get(scancode, '')
        keycode = KeyboardEvent.name_to_keycode(char) or 0
        time = s + ms/1e6
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
        event = KeyboardEvent(event_type, keycode, scancode, False, time, char)
        print(event)
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
    41: '`', 2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7',
    9: '8', 10: '9', 11: '0', 12: '-', 13: '=', 16: 'q',
    17: 'w', 18: 'e', 19: 'r', 20: 't', 21: 'y', 22: 'u', 23: 'i',
    24: 'o', 25: 'p', 26: '[', 27: ']', 43: '\\',
    30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g', 35: 'h', 36: 'j',
    37: 'k', 38: 'l', 39: ';', 40: '\'', 44: 'z', 45: 'x',
    46: 'c', 47: 'v', 48: 'b', 49: 'n', 50: 'm', 51: ',',
    52: '.', 53: '/', 57: ' ',
}

if __name__ == '__main__':
    listen([])
