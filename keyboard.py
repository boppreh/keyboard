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
    handlers.append(handler)

    if not listening_thread.is_alive():
        listening_thread.start()

def remove_handler(handler):
    handlers.remove(handler)

def is_pressed(key):
    if isinstance(key, int):
        return states[key] == KEY_DOWN
    else:
        return states[name_to_keycode(key)] == KEY_DOWN

def add_word_handler(word_handler):
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

if __name__ == '__main__':
    def p(word): print word
    add_word_handler(p)
