"""
Code adapted from http://pastebin.com/wzYZGZrs
"""

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int, c_uint, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import DWORD, BOOL, HHOOK, LPMSG, LPWSTR, WCHAR

import atexit

from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

user32 = ctypes.windll.user32

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vk_code", DWORD),
                ("scan_code", DWORD),
                ("flags", DWORD),
                ("time", c_int),]

LowLevelKeyboardProc = CFUNCTYPE(c_int, c_int, c_int, POINTER(KBDLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
SetWindowsHookEx.argtypes = [c_int, LowLevelKeyboardProc, c_int, c_int]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(KBDLLHOOKSTRUCT)]
CallNextHookEx.restype = c_int

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = BOOL

GetMessage = user32.GetMessageW
GetMessage.argtypes = [LPMSG, c_int, c_int, c_int]
GetMessage.restype = BOOL

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [LPMSG]
TranslateMessage.restype = BOOL

DispatchMessage = user32.DispatchMessageA
DispatchMessage.argtypes = [LPMSG]

keyboard_state_type = c_uint8 * 256

ToUnicode = user32.ToUnicode
ToUnicode.argtypes = [c_int, c_int, keyboard_state_type, LPWSTR, c_int, c_uint]
DispatchMessage.restype = c_int

GetKeyboardState = user32.GetKeyboardState
GetKeyboardState.argtypes = [keyboard_state_type]
GetKeyboardState.restype = BOOL

GetKeyNameText = user32.GetKeyNameTextW
GetKeyNameText.argtypes = [c_long, LPWSTR, c_int]
GetKeyNameText.restype = c_int

MapVirtualKey = user32.MapVirtualKeyW
MapVirtualKey.argtypes = [c_uint, c_uint]
MapVirtualKey.restype = c_uint

MAPVK_VSC_TO_VK = 1
keycode_by_scan_code = {}
scan_code_by_name = {}

name_buffer = ctypes.create_unicode_buffer(32)
for scan_code in range(2**(23-16)):
    ret = GetKeyNameText(scan_code << 16 | 1 << 24, name_buffer, 1024)
    if ret:
        scan_code_by_name[name_buffer.value] = scan_code
    ret = GetKeyNameText(scan_code << 16 | 0 << 24, name_buffer, 1024)
    if ret:
        scan_code_by_name[name_buffer.value] = scan_code

    ret = MapVirtualKey(scan_code, MAPVK_VSC_TO_VK)
    if ret:
        keycode_by_scan_code[scan_code] = ret    


VkKeyScan = user32.VkKeyScanW
VkKeyScan.argtypes = [WCHAR]
VkKeyScan.restype = c_short

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
        keycode = lParam.contents.vk_code
        scan_code = lParam.contents.scan_code

        keyboard_state = keyboard_state_type()
        assert GetKeyboardState(keyboard_state)
        # 32 is a completely arbitrary size that should contain any "character" typed.
        char_buffer = ctypes.create_unicode_buffer(32)
        chars_written = user32.ToUnicode(keycode, scan_code, keyboard_state, char_buffer, len(char_buffer), 0)
        if chars_written > 0:
            char = char_buffer.value
        else:
            char = None

        names = [k for k, v in scan_code_by_name.items() if v == scan_code and k.isprintable()]
        non_num_names = [name for name in names if not name.startswith('Num')]

        if names:
            if non_num_names:
                name = non_num_names[0]
            else:
                name = names[0]
        else:
            name = None

        event = KeyboardEvent(event_types[wParam], keycode, scan_code, name=name, char=char)
        
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
    atexit.register(user32.UnhookWindowsHookEx, hook)

    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)
    UnhookWindowsHookEx(hook)

def press_keycode(keycode):
    user32.keybd_event(keycode, 0, 0, 0)

def release_keycode(keycode):
    user32.keybd_event(keycode, 0, 0x2, 0)

def get_keyshift_from_char(char):
    ret = VkKeyScan(WCHAR(char))
    if ret == -1:
        raise ValueError('Cannot type character ' + char)
    keycode = ret & 0x00FF
    shift = ret & 0xFF00
    return keycode, shift

def press(scan_code):
    user32.keybd_event(keycode_by_scan_code[scan_code], 0, 0, 0)

def release(scan_code):
    user32.keybd_event(keycode_by_scan_code[scan_code], 0, 2, 0)

if __name__ == '__main__':
    listen([lambda e: print(e.name)])