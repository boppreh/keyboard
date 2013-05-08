from collections import namedtuple, defaultdict
from threading import Thread

KeyboardEvent = namedtuple('KeyboardEvent', ['event_type', 'key_code',
                                             'scan_code', 'alt_pressed',
                                             'time'])

KEY_DOWN = 'key down'
KEY_UP = 'key up'

handlers = []
states = defaultdict(lambda: KEY_UP)

def listen():
    """
    Calls `handlers` for each keyboard event received. This is a blocking call.
    """
    # Adapted from http://www.hackerthreads.org/Topic-42395
    from ctypes import windll, CFUNCTYPE, POINTER, c_int, c_void_p, byref
    import win32con, win32api, win32gui, atexit

    event_types = {win32con.WM_KEYDOWN: KEY_DOWN,
                   win32con.WM_KEYUP: KEY_UP,
                   0x104: KEY_DOWN, # WM_SYSKEYDOWN, used for Alt key.
                   0x105: KEY_UP, # WM_SYSKEYUP, used for Alt key.
                  }

    def low_level_handler(nCode, wParam, lParam):
        """
        Processes a low level Windows keyboard event.
        """
        type = event_types[wParam]
        key_code = lParam[0]
        scan_code = lParam[1]
        alt_pressed = lParam[2] == 32
        time = lParam[3]

        states[key_code] = type

        event = KeyboardEvent(type, key_code, scan_code, alt_pressed, time)
        for handler in handlers:
            handler(event)

        # Be a good neighbor and call the next hook.
        return windll.user32.CallNextHookEx(hook_id, nCode, wParam, lParam)
       
    # Our low level handler signature.
    CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
    # Convert the Python handler into C pointer.
    pointer = CMPFUNC(low_level_handler)

    # Hook both key up and key down events for common keys (non-system).
    hook_id = windll.user32.SetWindowsHookExA(win32con.WH_KEYBOARD_LL, pointer,
                                             win32api.GetModuleHandle(None), 0)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(windll.user32.UnhookWindowsHookEx, hook_id)

    while True:
        msg = win32gui.GetMessage(None, 0, 0)
        win32gui.TranslateMessage(byref(msg))
        win32gui.DispatchMessage(byref(msg))

listening_thread = Thread(target=listen)

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
