"""
Code heavily adapted from http://pastebin.com/wzYZGZrs
"""

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import DWORD, BOOL, HHOOK, LPMSG, LPWSTR, WCHAR, WPARAM, LPARAM

import atexit

from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
from mouse_event import MouseEvent

user32 = ctypes.windll.user32

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vk_code", DWORD),
                ("scan_code", DWORD),
                ("flags", DWORD),
                ("time", c_int),]

class MSLLHOOKSTRUCT(Structure):
    _fields_ = [("x", c_long),
                ("y", c_long),
                ('data', c_int32),
                ('reserved', c_int32),
                ("flags", DWORD),
                ("time", c_int),
                ]

LowLevelKeyboardProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(KBDLLHOOKSTRUCT))
LowLevelMouseProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(MSLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
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

MAPVK_VSC_TO_VK = 1

scan_code_table = {}
keycode_by_scan_code = {}

name_buffer = ctypes.create_unicode_buffer(32)

def register_names(scan_code, add, enhanced):
    ret = GetKeyNameText(scan_code << 16 | enhanced << 24, name_buffer, 1024)
    name = normalize_name(name_buffer.value)
    if ret and name.isprintable():
        if name.startswith('num ') and name != 'num lock':
            is_keypad = True
            name = name[len('num '):]
        else:
            is_keypad = False

        if name.startswith('left ') or name.startswith('right '):
            side, name = name.split(' ', 1)
            name = normalize_name(name)
            add((name, is_keypad))
            add((side + ' '+ name, is_keypad))
        else:
            add((name, is_keypad))

for scan_code in range(2**(23-16)):
    entries = []
    add = lambda v: entries.append(v) if v not in entries else None
    register_names(scan_code, add, 1)
    register_names(scan_code, add, 0)
    if entries:
        scan_code_table[scan_code] = entries

    ret = MapVirtualKey(scan_code, MAPVK_VSC_TO_VK)
    if ret:
        keycode_by_scan_code[scan_code] = ret

VkKeyScan = user32.VkKeyScanW
VkKeyScan.argtypes = [WCHAR]
VkKeyScan.restype = c_short

def listen(on_keyboard, on_mouse):
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

    # Beware, as of 2016-01-30 the official docs have a very incomplete list.
    # This one was compiled from experience and may be incomplete.
    WM_MOUSEMOVE = 0x200
    WM_LBUTTONDOWN = 0x201
    WM_LBUTTONUP = 0x202
    WM_LBUTTONDBLCLK = 0x203
    WM_RBUTTONDOWN = 0x204
    WM_RBUTTONUP = 0x205
    WM_RBUTTONDBLCLK = 0x206
    WM_MBUTTONDOWN = 0x207
    WM_MBUTTONUP = 0x208
    WM_MBUTTONDBLCLK = 0x209
    WM_MOUSEWHEEL = 0x20A
    WM_XBUTTONDOWN = 0x20B
    WM_XBUTTONUP = 0x20C
    WM_XBUTTONDBLCLK = 0x20D
    WM_NCXBUTTONDOWN = 0x00AB
    WM_NCXBUTTONUP = 0x00AC
    WM_NCXBUTTONDBLCLK = 0x00AD
    WM_MOUSEHWHEEL = 0x20E
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    WM_MOUSEMOVE = 0x0200
    WM_MOUSEWHEEL = 0x020A
    WM_MOUSEHWHEEL = 0x020E
    WM_RBUTTONDOWN = 0x0204
    WM_RBUTTONUP = 0x0205

    mouse_message_codes = {
        WM_MOUSEMOVE: ('move', ''),

        WM_MOUSEWHEEL: ('wheel', ''),
        WM_MOUSEHWHEEL: ('wheel', 'horizontal'),

        WM_LBUTTONDOWN: ('left', 'down'),
        WM_LBUTTONUP: ('left', 'up'),
        WM_LBUTTONDBLCLK: ('left', 'double click'),
        
        WM_RBUTTONDOWN: ('right', 'down'),
        WM_RBUTTONUP: ('right', 'up'),
        WM_RBUTTONDBLCLK: ('right', 'double click'),

        WM_MBUTTONDOWN: ('middle', 'down'),
        WM_MBUTTONUP: ('middle', 'up'),
        WM_MBUTTONDBLCLK: ('middle', 'double click'),

        WM_XBUTTONDOWN: ('x', 'down'),
        WM_XBUTTONUP: ('x', 'up'),
        WM_XBUTTONDBLCLK: ('x', 'double click'),

        WM_NCXBUTTONDOWN: ('x', 'down'), # NC = non-client
        WM_NCXBUTTONUP: ('x', 'up'),
        WM_NCXBUTTONDBLCLK: ('x', 'double click'),
    }


    def low_level_keyboard_handler(nCode, wParam, lParam):
        # You may be tempted to use ToUnicode to extract the character from
        # this event. Do not. ToUnicode breaks dead keys.

        scan_code = lParam.contents.scan_code

        if scan_code in scan_code_table:
            entries = scan_code_table[scan_code]
            is_keypad = entries[0][1]
            names = [name for name, is_keypad in entries]
        else:
            is_keypad = False
            names = []

        event = KeyboardEvent(keyboard_event_types[wParam], scan_code, is_keypad, names)
        
        if not on_keyboard(event):
            return CallNextHookEx(NULL, nCode, wParam, lParam)

    def low_level_mouse_handler(nCode, wParam, lParam):
        struct = lParam.contents

        type, arg = mouse_message_codes.get(wParam, ('?', ''))

        wheel_delta = 0

        if wParam >= WM_XBUTTONDOWN:
            # There are actually two 'X' button.
            type = {0x10000: 'x', 0x20000: 'x2'}[struct.data]
        elif wParam == WM_MOUSEWHEEL or wParam == WM_MOUSEHWHEEL:
            wheel_delta = struct.data // (120 * 0x10000)

        event = MouseEvent(type, arg, struct.x, struct.y, wheel_delta)
        
        if on_mouse(event):
            return 1
        else:
            return CallNextHookEx(NULL, nCode, wParam, lParam)

    WH_KEYBOARD_LL = c_int(13)
    keyboard_callback = LowLevelKeyboardProc(low_level_keyboard_handler)
    keyboard_hook = SetWindowsHookEx(WH_KEYBOARD_LL, keyboard_callback, NULL, NULL)

    WH_MOUSE_LL = c_int(14)
    mouse_callback = LowLevelMouseProc(low_level_mouse_handler)
    mouse_hook = SetWindowsHookEx(WH_MOUSE_LL, mouse_callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(UnhookWindowsHookEx, keyboard_callback)
    atexit.register(UnhookWindowsHookEx, mouse_hook)

    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)

def map_char(char):
    ret = VkKeyScan(WCHAR(char))
    if ret == -1:
        raise ValueError('Cannot type character ' + char)
    keycode = ret & 0x00FF
    shift = ret & 0xFF00
    scan_code = next(k for k, v in keycode_by_scan_code.items() if v == keycode)
    return scan_code, shift

def press(scan_code):
    user32.keybd_event(keycode_by_scan_code[scan_code], 0, 0, 0)

def release(scan_code):
    user32.keybd_event(keycode_by_scan_code[scan_code], 0, 2, 0)

if __name__ == '__main__':
    listen(lambda e: None, print)