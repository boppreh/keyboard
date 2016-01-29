from threading import Thread
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, name_to_keycode
try:
    from winkeyboard import listen, press, relese, map_char
except:
    from nixkeyboard import listen, press, relese, map_char

_pressed_events = {}
def _update_state(event):
    if event.event_type == KEY_UP:
        _pressed_events.discard(event.scan_code)
    else:
        _pressed_events.add(event.scan_code)

handlers = [_update_state]

listening_thread = Thread(target=listen, args=(handlers,))
listening_thread.daemon=True
listening_thread.start()

def add_handler(handler):
    """ Adds a function to receive each keyboard event captured. """
    handlers.append(handler)

def remove_handler(handler):
    """ Removes a previously added keyboard event handler. """
    handlers.remove(handler)

def is_pressed(key):
    """ Returns True if the key (by name or code) is pressed. """
    if isinstance(key, int):
        return key in _pressed_events
    else:
        for event in _pressed_events.values():
            if event.matches(key):
                return True
        return False

def register_hotkey(hotkey, callback, args=(), blocking=True):
    """
    Adds a hotkey handler that invokes callback each time the hotkey is
    detected. Returns a handler that can be used to unregister it later. The
    hotkey must be in the format "ctrl+shift+a, s". This would trigger when the
    user presses "ctrl+shift+a", releases, and then presses "s".

    blocking defines if the system should continue processing other hotkeys
    after a match is found.
    """
    keycode_combinations = []
    for combination in hotkey.lower().replace(' ', '').split(','):
        keycode_combination = set(map(name_to_keycode.get, combination.split('+')))
        keycode_combinations.append(keycode_combination)

    current_combination = [0]

    def handler(event):
        if event.event_type == KEY_UP:
            return

        keycodes = keycode_combinations[current_combination[0]]
        if event.keycode in keycodes:
            if pressed_keys.issuperset(keycodes):
                current_combination[0] += 1
                if current_combination[0] == len(keycode_combinations):
                    current_combination[0] = 0
                    callback(*args) 
                    return blocking
        else:
            current_combination[0] = 0
            # The key pressed was not part of the current combination, but it
            # could be of the first combination, so we have to try again.
            if event.keycode in keycode_combinations[0]:
                handler(event)

    add_handler(handler)
    return handler

def write(text):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Composite characters such as à are not available. Raises ValueError
    for unavailable characters.
    """
    for letter in text:
        keycode, shift = map_char(letter)
        if shift:
            press_keycode(name_to_keycode[shift])
        press_keycode(keycode)
        release_keycode(keycode)
        if shift:
            release_keycode(name_to_keycode[shift])
            send('shift+' + letter)

def send(combination):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4", "shift+s"
    """
    names = combination.replace(' ', '').split('+')
    for name in names:
        press_keycode(name_to_keycode[name])
    for name in reversed(names):
        release_keycode(name_to_keycode[name])

def record(until='escape', exclude=[]):
    """
    Records and returns all keyboard events until the user presses the given
    key combination.
    """
    from threading import Lock

    exclude_keycodes = set(map(name_to_keycode.get, exclude))
    if until in name_to_keycode:
        exclude_keycodes.add(until)

    actions = []
    lock = Lock()
    lock.acquire()

    should_stop = [False]

    def stop():
        should_stop[0] = True
    hotkey_id = register_hotkey(until, stop)

    def handler(event):
        if should_stop[0]:
            remove_handler(handler)
            remove_handler(hotkey_id)
            lock.release()
        elif event.keycode not in exclude_keycodes:
            actions.append(event)

    add_handler(handler)
    lock.acquire()
    return actions

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is invalid (<= 0) the actions are replayed
    instantly.
    """
    import time

    if not events:
        return

    last_time = events[0].time
    for event in events:
        if speed_factor > 0:
            time.sleep((event.time - last_time) / speed_factor)
            last_time = event.time

        if event.event_type == KEY_DOWN:
            press_keycode(event.keycode)
        else:
            release_keycode(event.keycode)

def wait(combination):
    """
    Blocks the program execution until a key combination is activated.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    hotkey_handler = register_hotkey(combination, lock.release)
    lock.acquire()
    remove_handler(hotkey_handler)

if __name__ == '__main__':
    print('Press esc twice to replay keyboard actions.')
    play(record('esc, esc'), 3)