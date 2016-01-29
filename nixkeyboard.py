import struct
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

event_bin_format = 'llhhi'

def _read_device_file():
    import glob
    event_files = glob.glob('/dev/input/by-id/*-event-kbd')

    for event_file in event_files:
        if '-if01-' not in event_file:
            break

    with open(event_file, 'rb') as events:
        while True:
            yield events.read(struct.calcsize(event_bin_format))

def listen(handlers):
    import time
    for input in _read_device_file():
        s, ms, type, scancode, value = struct.unpack(event_bin_format, input)
        
        if scancode == 0 or value > 2:
            # Three events appear for event recognizable key event. I still
            # don't know what are those. The first has a very large "value" and
            # appears before the proper event, and the second has zero code and
            # value, appearing after the event. I'll just ignore them for now.
            continue

        keycode = KeyboardEvent.name_to_keycode(char) or 0
        time = s + ms/1e6
        event_type = KEY_DOWN if value else KEY_UP # 0 = UP, 1 = DOWN, 2 = HOLD
        event = KeyboardEvent(event_type, keycode, scancode, time)
        
        for handler in handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                print(e)

def press_keycode(keycode):
    raise NotImplementedError()

def release_keycode(keycode):
    raise NotImplementedError()

if __name__ == '__main__':
    listen([])
