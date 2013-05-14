# Adapted from http://www.hackerthreads.org/Topic-42395
from ctypes import windll, CFUNCTYPE, POINTER, c_int, c_void_p, byref, c_char, c_uint, addressof
import win32con, win32api, win32gui, atexit
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

def press_keycode(keycode):
    win32api.keybd_event(keycode, 0, 0, 0)

def release_keycode(keycode):
    win32api.keybd_event(keycode, 0, 0x2, 0)

def _to_ascii(keycode, scancode):
    state = (c_char * 256)()
    windll.user32.GetKeyboardState(byref(state))
    lpChar = (c_char * 2)()
    #nSize = windll.user32.ToAsciiEx(c_uint(keycode),
    nSize = windll.user32.ToAscii(c_uint(keycode),
                                  c_uint(scancode),
                                  addressof(state),
                                  addressof(lpChar),
                                   #c_uint(windll.user32.GetKeyboardLayout(0)),
                                  None)

    if nSize >= 1:
        return u''.join(map(unichr, filter(lambda i: i, map(ord, lpChar))))
    else:
        return None

def listen(handlers):
    """
    Calls `handlers` for each keyboard event received. This is a blocking call.
    """
    event_types = {win32con.WM_KEYDOWN: KEY_DOWN,
                   win32con.WM_KEYUP: KEY_UP,
                   0x104: KEY_DOWN, # WM_SYSKEYDOWN, used for Alt key.
                   0x105: KEY_UP, # WM_SYSKEYUP, used for Alt key.
                  }

    def low_level_handler(nCode, wParam, lParam):
        """
        Processes a low level Windows keyboard event.
        """
        event_type = event_types[wParam]
        keycode = lParam[0]
        scancode = lParam[1]
        alt_pressed = lParam[2] == 32
        time = lParam[3]
        char = _to_ascii(keycode, scancode)

        event = KeyboardEvent(event_type, keycode, scancode, char,
                              alt_pressed, time)

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
