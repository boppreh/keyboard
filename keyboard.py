from itertools import imap
from collections import defaultdict
from threading import Thread
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP
from keyboard_event import name_to_keycode, keycode_to_name

keycode_to_char = KeyboardEvent.keycode_to_char
keycode_to_name = KeyboardEvent.keycode_to_name
name_to_keycode = KeyboardEvent.name_to_keycode

try:
    from winkeyboard import listen
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
    """ Invokes the given function each time a word is typed. """
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

def register_hotkey(hotkey, callback):
    """
    Adds a hotkey handler that invokes callback each time the hotkey is
    detected.
    """
    keycodes = map(name_to_keycode, hotkey.split('+') )

    def handler(event):
        if event.event_type == KEY_DOWN:
            if all(imap(is_pressed, keycodes)):
               callback() 

    add_handler(handler)

if __name__ == '__main__':
    def p(s='Hello'): print s
    register_hotkey('ctrl+shift+alt+a', p)
