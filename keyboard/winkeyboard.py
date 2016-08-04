"""
Code heavily adapted from http://pastebin.com/wzYZGZrs
"""
import atexit

import re

from .keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_uint32, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM
LPMSG = POINTER(MSG)

user32 = ctypes.windll.user32

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vk_code", DWORD),
                ("scan_code", DWORD),
                ("flags", DWORD),
                ("time", c_int),]

LowLevelKeyboardProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(KBDLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
#SetWindowsHookEx.argtypes = [c_int, LowLevelKeyboardProc, c_int, c_int]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
#CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(KBDLLHOOKSTRUCT)]
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

GetKeyboardState = user32.GetKeyboardState
GetKeyboardState.argtypes = [keyboard_state_type]
GetKeyboardState.restype = BOOL

GetKeyNameText = user32.GetKeyNameTextW
GetKeyNameText.argtypes = [c_long, LPWSTR, c_int]
GetKeyNameText.restype = c_int

MapVirtualKey = user32.MapVirtualKeyW
MapVirtualKey.argtypes = [c_uint, c_uint]
MapVirtualKey.restype = c_uint

ToUnicode = user32.ToUnicode
ToUnicode.argtypes = [c_uint, c_uint, keyboard_state_type, LPWSTR, c_int, c_uint]
ToUnicode.restype = c_int

MAPVK_VSC_TO_VK = 1

VkKeyScan = user32.VkKeyScanW
VkKeyScan.argtypes = [WCHAR]
VkKeyScan.restype = c_short

NULL = c_int(0)

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x104 # Used for ALT key
WM_SYSKEYUP = 0x105

keyboard_event_types = {
    WM_KEYDOWN: KEY_DOWN,
    WM_KEYUP: KEY_UP,
    WM_SYSKEYDOWN: KEY_DOWN,
    WM_SYSKEYUP: KEY_UP,
}

from_scan_code = {}
to_scan_code = {}

name_buffer = ctypes.create_unicode_buffer(32)
keyboard_state = keyboard_state_type()
for scan_code in range(2**(23-16)):
    from_scan_code[scan_code] = (['', ''], False)

    # Get pure key name, such as "shift".
    for enhanced in [1, 0]:
        ret = GetKeyNameText(scan_code << 16 | enhanced << 24, name_buffer, 1024)
        if not ret:
            continue
        name = name_buffer.value
        if name.startswith('Num ') and name != 'Num Lock':
            is_keypad = True
            name = name[len('Num '):]
        else:
            is_keypad = False

        name = normalize_name(name.replace('Right ', '').replace('Left ', ''))
        from_scan_code[scan_code] = ([name, name], is_keypad)
        to_scan_code[name] = (scan_code, False)

    # Get associated character, such as "^", possibly overwriting the pure key name.
    for shift_state in [0, 1]:
        keyboard_state[0x10] = shift_state * 0xFF
        key_code = MapVirtualKey(scan_code, MAPVK_VSC_TO_VK)
        ret = ToUnicode(key_code, scan_code, keyboard_state, name_buffer, len(name_buffer) * 2, 0)
        if ret:
            # Sometimes two characters are written before the char we want,
            # usually an accented one such as Â. Couldn't figure out why.
            char = name_buffer.value[-1]
            to_scan_code[char] = (scan_code, bool(shift_state))
            from_scan_code[scan_code][0][shift_state] = char


shift_is_pressed = False

def listen(handler):
    def low_level_keyboard_handler(nCode, wParam, lParam):
        # You may be tempted to use ToUnicode to extract the character from
        # this event with more precision. Do not. ToUnicode breaks dead keys.

        scan_code = lParam.contents.scan_code
        event_type = keyboard_event_types[wParam]

        names, is_keypad = from_scan_code[scan_code]

        global shift_is_pressed
        name = names[shift_is_pressed]
        if event_type == KEY_DOWN and name == 'shift':
            shift_is_pressed = True
        elif event_type == KEY_UP and name == 'shift':
            shift_is_pressed = False

        event = KeyboardEvent(event_type, scan_code, is_keypad, name)
        
        if handler(event):
            return 1
        else:
            return CallNextHookEx(NULL, nCode, wParam, lParam)

    WH_KEYBOARD_LL = c_int(13)
    keyboard_callback = LowLevelKeyboardProc(low_level_keyboard_handler)
    keyboard_hook = SetWindowsHookEx(WH_KEYBOARD_LL, keyboard_callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(UnhookWindowsHookEx, keyboard_callback)

    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)

def map_char(character):
    try:
        return to_scan_code[character]
    except KeyError:
        raise ValueError('Character {} is not mapped to any known key.'.format(repr(character)))

def press(scan_code):
    user32.keybd_event(MapVirtualKey(scan_code, MAPVK_VSC_TO_VK), 0, 0, 0)

def release(scan_code):
    user32.keybd_event(MapVirtualKey(scan_code, MAPVK_VSC_TO_VK), 0, 2, 0)

def type_unicode(character):
    # TODO
    # http://stackoverflow.com/questions/22291282/using-sendinput-to-send-unicode-characters-beyond-uffff
    raise NotImplemented('Typing of arbitrary characters is not currently implemented.')

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
