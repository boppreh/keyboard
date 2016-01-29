"""
Code adapted from http://pastebin.com/wzYZGZrs
"""

from ctypes import c_int, Structure, CFUNCTYPE, POINTER, windll
from ctypes.wintypes import DWORD, BOOL, HHOOK, LPMSG

import atexit

from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vk_code", DWORD),
                ("scan_code", DWORD),
                ("flags", DWORD),
                ("time", c_int),]

LowLevelKeyboardProc = CFUNCTYPE(c_int, c_int, c_int, POINTER(KBDLLHOOKSTRUCT))

SetWindowsHookEx          = windll.user32.SetWindowsHookExA
SetWindowsHookEx.argtypes = [c_int, LowLevelKeyboardProc, c_int, c_int]
SetWindowsHookEx.restype  = HHOOK

CallNextHookEx          = windll.user32.CallNextHookEx
CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(KBDLLHOOKSTRUCT)]
CallNextHookEx.restype  = c_int

UnhookWindowsHookEx          = windll.user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype  = BOOL

GetMessage          = windll.user32.GetMessageW
GetMessage.argtypes = [LPMSG, c_int, c_int, c_int]
GetMessage.restype  = BOOL

TranslateMessage          = windll.user32.TranslateMessage
TranslateMessage.argtypes = [LPMSG]
TranslateMessage.restype  = BOOL

DispatchMessage          = windll.user32.DispatchMessageA
DispatchMessage.argtypes = [LPMSG]

def listen(handlers):
    NULL = c_int(0)

    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x104 # Used for ALT key
    WM_SYSKEYUP = 0x105

    event_types = {
        WM_KEYDOWN: KEY_DOWN,
        WM_KEYUP: KEY_UP,
        WM_SYSKEYDOWN: KEY_DOWN,
        WM_SYSKEYUP: KEY_UP,
    }

    def low_level_handler(ncode, wParam, lParam):
        key_code = lParam.contents.vk_code
        scan_code = lParam.contents.scan_code
        event = KeyboardEvent(event_types[wParam], key_code, scan_code)
        for handler in handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                print(e)
        return CallNextHookEx(NULL, ncode, wParam, lParam)
    
    callback = LowLevelKeyboardProc(low_level_handler)
    WH_KEYBOARD_LL = c_int(13)
    hook = SetWindowsHookEx(WH_KEYBOARD_LL, callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(windll.user32.UnhookWindowsHookEx, hook)

    msg  = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)
    UnhookWindowsHookEx(hook)

def press_keycode(keycode):
    windll.user32.keybd_event(keycode, 0, 0, 0)

def release_keycode(keycode):
    windll.user32.keybd_event(keycode, 0, 0x2, 0)


if __name__ == '__main__':
    listen([print])