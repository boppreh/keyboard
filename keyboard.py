from itertools import imap
from collections import defaultdict
from threading import Thread
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP
from keyboard_event import name_to_keycode, keycode_to_name

keycode_to_char = KeyboardEvent.keycode_to_char
keycode_to_name = KeyboardEvent.keycode_to_name
name_to_keycode = KeyboardEvent.name_to_keycode

try:
    from winkeyboard import listen, press_keycode, release_keycode
except:
    raise NotImplementedError('Windows support only for the moment.')

states = defaultdict(lambda: KEY_UP)
def _update_state(event):
    states[event.keycode] = event.event_type

handlers = [_update_state]
listening_thread = Thread(target=listen, args=(handlers,))

def add_handler(handler):
    """ Adds a function to receive each keyboard event captured. """
    handlers.append(handler)

    if not listening_thread.is_alive():
        listening_thread.start()

def remove_handler(handler):
    """ Removes a previously added keyboard event handler. """
    handlers.remove(handler)

def is_pressed(key):
    """ Returns True if the key (by name or code) is pressed. """
    code = key if isinstance(key, int) else name_to_keycode(key)
    return states[code] == KEY_DOWN

def add_word_handler(word_handler):
    """
    Invokes the given function each time a word is typed.
    Returns a handler that can be used to stop.
    """
    # TODO: caps lock, shift + number
    letters = []

    def handler(event):
        char = event.char
        l = letters

        if event.event_type == KEY_UP or event.char is None:
            return
        elif char.isspace() and len(l):
            word_handler(''.join(l))
            l[:] = []
            return
        else:
            if is_pressed('lshift') or is_pressed('rshift'):
                char = char.upper()
            else:
                char = char.lower()

            letters.append(char)

    add_handler(handler)
    return handler

def register_hotkey(hotkey, callback, args=()):
    """
    Adds a hotkey handler that invokes callback each time the hotkey is
    detected. Returns a handler that can be used to unregister it later.
    """
    keycodes = map(name_to_keycode, hotkey.split('+') )

    def handler(event):
        if event.event_type == KEY_DOWN:
            if all(imap(is_pressed, keycodes)):
               callback(*args) 

    add_handler(handler)
    return handler

def write(text):
    """
    Sends artifical keyboard events to the OS, simulating the typing of a given
    text. Very limited character set.
    """
    for letter in text:
        if letter.isalpha() and letter == letter.upper():
            send('shift+' + letter)
        else:
            press_keycode(name_to_keycode(letter))
            release_keycode(name_to_keycode(letter))

def send(combination):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4", "shift+s"
    """
    names = combination.replace(' ', '').split('+')
    for name in names:
        press_keycode(name_to_keycode(name))
    for name in reversed(names):
        release_keycode(name_to_keycode(name))

def send_keys(keycodes):
    """
    Simulates the sequential pressing and releasing of a list of keycodes.
    """
    for keycode in keycodes:
        press_keycode(keycode)
        release_keycode(keycode)

def record(until='escape'):
    """
    Records and returns all keyboard events until the user presses the given
    key combination.
    """
    from threading import Lock

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
        else:
            actions.append(event)

    add_handler(handler)
    lock.acquire()
    return actions

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals.
    """
    import time

    if not events:
        return

    last_time = events[0].time
    for event in events:
        time.sleep((event.time - last_time) / 1000.0 / speed_factor)
        last_time = event.time

        if event.event_type == KEY_UP:
            release_keycode(event.keycode)
        else:
            press_keycode(event.keycode)

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
    play(record(), 3)
