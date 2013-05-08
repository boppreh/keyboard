from collections import namedtuple
import atexit

KeyboardEvent = namedtuple('KeyboardEvent', ['event_type', 'key_code',
                                             'scan_code', 'alt_pressed',
                                             'time'])

def listen(handler):
    """
    Calls `handler` for each keyboard event received. This is a blocking call.
    """
    # Adapted from http://www.hackerthreads.org/Topic-42395
    from ctypes import windll, CFUNCTYPE, POINTER, c_int, c_void_p, byref
    import win32con, win32api, win32gui

    # Used for receiving ALT key presses.
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105

    def low_level_handler(nCode, wParam, lParam):
        """
        Processes a low level window keyboard event.
        """
        if wParam in [win32con.WM_KEYDOWN, WM_SYSKEYDOWN]:
            event_type = 'key down'
        if wParam in [win32con.WM_KEYUP, WM_SYSKEYUP]:
            event_type = 'key up'

        event = KeyboardEvent(event_type, lParam[0], lParam[1],
                              lParam[2] == 32, lParam[3])
        handler(event)
        return windll.user32.CallNextHookEx(kbHook, nCode, wParam, lParam)
       
    # Our low level handler signature.
    CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
    # Convert the Python handler into C pointer.
    pointer = CMPFUNC(low_level_handler)

    # Hook both key up and key down events for common keys (non-system).
    kbHook = windll.user32.SetWindowsHookExA(win32con.WH_KEYBOARD_LL, pointer,
                                             win32api.GetModuleHandle(None), 0)
    # Alt keypresses are not logged by KEYBOARD_LL, so we need SYSKEY* too.
    kbHook = windll.user32.SetWindowsHookExA(WM_SYSKEYDOWN, pointer,
                                             win32api.GetModuleHandle(None), 0)
    # And now do the same for the release events.
    kbHook = windll.user32.SetWindowsHookExA(WM_SYSKEYUP, pointer,
                                             win32api.GetModuleHandle(None), 0)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(windll.user32.UnhookWindowsHookEx, kbHook)
    while True:
        msg = win32gui.GetMessage(None, 0, 0)
        win32gui.TranslateMessage(byref(msg))
        win32gui.DispatchMessage(byref(msg))

def print_event(e):
    print e
listen(print_event)
