from collections import defaultdict
from threading import Thread

try:
    from winkeyboard import listen, KEY_DOWN, KEY_UP
except:
    raise NotImplementedError('Windows support only for the moment.')

states = defaultdict(lambda: KEY_UP)
def _update_state(event):
    states[event.key_code] = event.type

handlers = [_update_state]
listening_thread = Thread(target=listen, args=(handlers,))

def add_handler(handler):
    handlers.append(handler)

    if not listening_thread.is_alive():
        listening_thread.start()

def remove_handler(handler):
    handlers.remove(handler)

def is_pressed(key_code):
    return states[key_code] == KEY_DOWN

if __name__ == '__main__':
    def print_event(e):
        print e

    add_handler(print_event)
