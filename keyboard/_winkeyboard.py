# -*- coding: utf-8 -*-
"""
This is the Windows backend for keyboard events, and is implemented by
invoking the Win32 API through the ctypes module. This is error prone
and can introduce very unpythonic failure modes, such as segfaults and
low level memory leaks. But it is also dependency-free, very performant
well documented on Microsoft's webstie and scattered examples.

# TODO:
- Decimal point in keypad doesn't have a name.
- Keypad numbers still print as numbers even when nunlock is off.
- No way to specify if user wants a keypad key or not in `map_char`.
"""
import atexit
from threading import Lock
import re

from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name

# This part is just declaring Win32 API structures using ctypes. In C
# this would be simply #include "windows.h".

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_uint32, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import WORD, DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM, LONG
LPMSG = POINTER(MSG)
ULONG_PTR = POINTER(DWORD)

#https://github.com/boppreh/mouse/issues/1
#user32 = ctypes.windll.user32
user32 = ctypes.WinDLL('user32', use_last_error = True)

VK_PACKET = 0xE7

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_KEYUP = 0x02
KEYEVENTF_UNICODE = 0x04

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vk_code", DWORD),
                ("scan_code", DWORD),
                ("flags", DWORD),
                ("time", c_int),
                ("dwExtraInfo", ULONG_PTR)]

# Included for completeness.
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (('dx', LONG),
                ('dy', LONG),
                ('mouseData', DWORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (('wVk', WORD),
                ('wScan', WORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (('uMsg', DWORD),
                ('wParamL', WORD),
                ('wParamH', WORD))

class _INPUTunion(ctypes.Union):
    _fields_ = (('mi', MOUSEINPUT),
                ('ki', KEYBDINPUT),
                ('hi', HARDWAREINPUT))

class INPUT(ctypes.Structure):
    _fields_ = (('type', DWORD),
                ('union', _INPUTunion))

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

SendInput = user32.SendInput
SendInput.argtypes = [c_uint, POINTER(INPUT), c_int]
SendInput.restype = c_uint

# https://msdn.microsoft.com/en-us/library/windows/desktop/ms646307(v=vs.85).aspx
MAPVK_VK_TO_CHAR = 2
MAPVK_VK_TO_VSC = 0
MAPVK_VSC_TO_VK = 1
MAPVK_VK_TO_VSC_EX = 4
MAPVK_VSC_TO_VK_EX = 3 

VkKeyScan = user32.VkKeyScanW
VkKeyScan.argtypes = [WCHAR]
VkKeyScan.restype = c_short

NULL = c_int(0)

LLKHF_INJECTED = 0x00000010

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x104 # Used for ALT key
WM_SYSKEYUP = 0x105


# This marks the end of Win32 API declarations. The rest is ours.

keyboard_event_types = {
    WM_KEYDOWN: KEY_DOWN,
    WM_KEYUP: KEY_UP,
    WM_SYSKEYDOWN: KEY_DOWN,
    WM_SYSKEYUP: KEY_UP,
}

# List taken from the official documentation, but stripped of the OEM-specific keys.
# Keys are virtual key codes, values are pairs (name, is_keypad).
official_virtual_keys = {
    0x03: ('control-break processing', False),
    0x08: ('backspace', False),
    0x09: ('tab', False),
    0x0c: ('clear', False),
    0x0d: ('enter', False),
    0x10: ('shift', False),
    0x11: ('ctrl', False),
    0x12: ('alt', False),
    0x13: ('pause', False),
    0x14: ('caps lock', False),
    0x15: ('ime kana mode', False),
    0x15: ('ime hanguel mode', False),
    0x15: ('ime hangul mode', False),
    0x17: ('ime junja mode', False),
    0x18: ('ime final mode', False),
    0x19: ('ime hanja mode', False),
    0x19: ('ime kanji mode', False),
    0x1b: ('esc', False),
    0x1c: ('ime convert', False),
    0x1d: ('ime nonconvert', False),
    0x1e: ('ime accept', False),
    0x1f: ('ime mode change request', False),
    0x20: ('spacebar', False),
    0x21: ('page up', False),
    0x22: ('page down', False),
    0x23: ('end', False),
    0x24: ('home', False),
    0x25: ('left', False),
    0x26: ('up', False),
    0x27: ('right', False),
    0x28: ('down', False),
    0x29: ('select', False),
    0x2a: ('print', False),
    0x2b: ('execute', False),
    0x2c: ('print screen', False),
    0x2d: ('insert', False),
    0x2e: ('delete', False),
    0x2f: ('help', False),
    0x30: ('0', False),
    0x31: ('1', False),
    0x32: ('2', False),
    0x33: ('3', False),
    0x34: ('4', False),
    0x35: ('5', False),
    0x36: ('6', False),
    0x37: ('7', False),
    0x38: ('8', False),
    0x39: ('9', False),
    0x41: ('a', False),
    0x42: ('b', False),
    0x43: ('c', False),
    0x44: ('d', False),
    0x45: ('e', False),
    0x46: ('f', False),
    0x47: ('g', False),
    0x48: ('h', False),
    0x49: ('i', False),
    0x4a: ('j', False),
    0x4b: ('k', False),
    0x4c: ('l', False),
    0x4d: ('m', False),
    0x4e: ('n', False),
    0x4f: ('o', False),
    0x50: ('p', False),
    0x51: ('q', False),
    0x52: ('r', False),
    0x53: ('s', False),
    0x54: ('t', False),
    0x55: ('u', False),
    0x56: ('v', False),
    0x57: ('w', False),
    0x58: ('x', False),
    0x59: ('y', False),
    0x5a: ('z', False),
    0x5b: ('left windows', False),
    0x5c: ('right windows', False),
    0x5d: ('applications', False),
    0x5f: ('sleep', False),
    0x60: ('0', True),
    0x61: ('1', True),
    0x62: ('2', True),
    0x63: ('3', True),
    0x64: ('4', True),
    0x65: ('5', True),
    0x66: ('6', True),
    0x67: ('7', True),
    0x68: ('8', True),
    0x69: ('9', True),
    0x6a: ('*', True),
    0x6b: ('+', True),
    0x6c: ('separator', True),
    0x6d: ('-', True),
    0x6e: ('decimal', True),
    0x6f: ('/', True),
    0x70: ('f1', False),
    0x71: ('f2', False),
    0x72: ('f3', False),
    0x73: ('f4', False),
    0x74: ('f5', False),
    0x75: ('f6', False),
    0x76: ('f7', False),
    0x77: ('f8', False),
    0x78: ('f9', False),
    0x79: ('f10', False),
    0x7a: ('f11', False),
    0x7b: ('f12', False),
    0x7c: ('f13', False),
    0x7d: ('f14', False),
    0x7e: ('f15', False),
    0x7f: ('f16', False),
    0x80: ('f17', False),
    0x81: ('f18', False),
    0x82: ('f19', False),
    0x83: ('f20', False),
    0x84: ('f21', False),
    0x85: ('f22', False),
    0x86: ('f23', False),
    0x87: ('f24', False),
    0x90: ('num lock', False),
    0x91: ('scroll lock', False),
    0xa0: ('left shift', False),
    0xa1: ('right shift', False),
    0xa2: ('left ctrl', False),
    0xa3: ('right ctrl', False),
    0xa4: ('left menu', False),
    0xa5: ('right menu', False),
    0xa6: ('browser back', False),
    0xa7: ('browser forward', False),
    0xa8: ('browser refresh', False),
    0xa9: ('browser stop', False),
    0xaa: ('browser search key', False),
    0xab: ('browser favorites', False),
    0xac: ('browser start and home', False),
    0xad: ('volume mute', False),
    0xae: ('volume down', False),
    0xaf: ('volume up', False),
    0xb0: ('next track', False),
    0xb1: ('previous track', False),
    0xb2: ('stop media', False),
    0xb3: ('play/pause media', False),
    0xb4: ('start mail', False),
    0xb5: ('select media', False),
    0xb6: ('start application 1', False),
    0xb7: ('start application 2', False),
    0xbb: ('+', False),
    0xbc: (',', False),
    0xbd: ('-', False),
    0xbe: ('.', False),
    #0xbe:('/', False), # Used for miscellaneous characters; it can vary by keyboard. For the US standard keyboard, the '/?.
    0xe5: ('ime process', False),
    0xf6: ('attn', False),
    0xf7: ('crsel', False),
    0xf8: ('exsel', False),
    0xf9: ('erase eof', False),
    0xfa: ('play', False),
    0xfb: ('zoom', False),
    0xfc: ('reserved ', False),
    0xfd: ('pa1', False),
    0xfe: ('clear', False),
}

tables_lock = Lock()
to_name = {}
from_name = {}
scan_code_to_vk = {}
vk_to_scan_code = {}

name_buffer = ctypes.create_unicode_buffer(32)
unicode_buffer = ctypes.create_unicode_buffer(32)
keyboard_state = keyboard_state_type()
def get_event_names(scan_code, vk, is_extended, shift_state, altgr_state):
    keyboard_state[0x10] = shift_state * 0x80
    keyboard_state[0x11] = altgr_state * 0x80
    keyboard_state[0x12] = altgr_state * 0x80
    unicode_ret = ToUnicode(vk, scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)
    if unicode_ret and unicode_buffer.value:
        yield unicode_buffer.value
        # unicode_ret == -1 -> is dead key
        # ToUnicode has the side effect of setting global flags for dead keys.
        # Therefore we need to call it twice to clear those flags.
        # If your 6 and 7 keys are named "^6" and "^7", this is the reason.
        ToUnicode(vk, scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)

    name_ret = GetKeyNameText(scan_code << 16 | is_extended << 24, name_buffer, 1024)
    if name_ret and name_buffer.value:
        yield name_buffer.value

    char = chr(user32.MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR) & 0xFF)
    if char != '\x00' and char:
        yield char

    if vk in official_virtual_keys:
        yield official_virtual_keys[vk][0]

def _setup_name_tables():
    """
    Ensures the scan code/virtual key code/name translation tables are
    filled.
    """
    with tables_lock:
        if to_name: return

        # Go through every possible scan code, and map them to virtual key codes.
        # Then vice-versa.
        all_scan_codes = [(sc, user32.MapVirtualKeyExW(sc, MAPVK_VSC_TO_VK_EX, 0) & 0xFF) for sc in range(0x100)]
        all_vks =        [(user32.MapVirtualKeyExW(vk, MAPVK_VK_TO_VSC_EX, 0) & 0xFF, vk) for vk in range(0x100)]
        for scan_code, vk in all_scan_codes + all_vks:
            # `to_name` and `from_name` entries will be a tuple (scan_code, vk, extended, shift_state).
            if (scan_code, vk, 0, 0, 0) in to_name:
                continue

            if scan_code not in scan_code_to_vk:
                scan_code_to_vk[scan_code] = vk
            if vk not in vk_to_scan_code:
                vk_to_scan_code[vk] = scan_code

            # Brute force all combinations to find all possible names.
            for extended in [0, 1]:
                for shift_state in [0, 1]:
                    for altgr_state in [0] if shift_state else [0, 1]:
                        entry = (scan_code, vk, extended, shift_state, altgr_state)
                        # Get key names from ToUnicode, GetKeyNameText, MapVirtualKeyW and official virtual keys.
                        names = list(get_event_names(*entry))
                        if names:
                            to_name[entry] = names
                            # Remember the "id" of the name, as the first techniques
                            # have better results and therefore priority.
                            for i, name in enumerate(map(normalize_name, names)):
                                from_name.setdefault(name, set()).add((i, entry))

        # TODO: single quotes on US INTL is returning the dead key (?), and therefore
        # not typing properly.

        # Alt gr is way outside the usual range of keys (0..127) and on my
        # computer is named as 'ctrl'. Therefore we add it manually and hope
        # Windows is consistent in its inconsistency.
        from_name['alt gr'] = []
        for extended in [0, 1]:
            for shift_state in [0, 1]:
                for altgr_state in [0, 1]:
                    to_name[(541, 162, extended, shift_state, altgr_state)] = ['alt gr']
                    from_name['alt gr'].append((541, 162, extended, shift_state, altgr_state))

# Called by keyboard/__init__.py
init = _setup_name_tables

# List created manually.
keypad_keys = [
    # (scan_code, virtual_key_code, is_extended)
    (126, 194, 0),
    (126, 194, 0),
    (28, 13, 1),
    (28, 13, 1),
    (53, 111, 1),
    (53, 111, 1),
    (55, 106, 0),
    (55, 106, 0),
    (69, 144, 1),
    (69, 144, 1),
    (71, 103, 0),
    (71, 36, 0),
    (72, 104, 0),
    (72, 38, 0),
    (73, 105, 0),
    (73, 33, 0),
    (74, 109, 0),
    (74, 109, 0),
    (75, 100, 0),
    (75, 37, 0),
    (76, 101, 0),
    (76, 12, 0),
    (77, 102, 0),
    (77, 39, 0),
    (78, 107, 0),
    (78, 107, 0),
    (79, 35, 0),
    (79, 97, 0),
    (80, 40, 0),
    (80, 98, 0),
    (81, 34, 0),
    (81, 99, 0),
    (82, 45, 0),
    (82, 96, 0),
    (83, 110, 0),
    (83, 46, 0),
]

shift_is_pressed = False
altgr_is_pressed = False
shift_vks = set([0x10, 0xa0, 0xa1])
def prepare_intercept(callback):
    """
    Registers a Windows low level keyboard hook. The provided callback will
    be invoked for each high-level keyboard event, and is expected to return
    True if the key event should be passed to the next program, or False if
    the event is to be blocked.

    No event is processed until the Windows messages are pumped (see
    start_intercept).
    """
    _setup_name_tables()
    
    def process_key(event_type, vk, scan_code, is_extended):
        global shift_is_pressed, altgr_is_pressed

        # Pressing AltGr also triggers "right menu" quickly after. We
        # try to filter out this event.
        if vk == 165:
            return True

        entry = (scan_code, vk, is_extended, shift_is_pressed, altgr_is_pressed)
        if entry not in to_name:
            to_name[entry] = list(get_event_names(*entry))
        names = to_name[entry]
        name = names[0] if names else None
            
        # TODO: inaccurate when holding multiple different shifts.
        if event_type == KEY_DOWN and vk in shift_vks:
            shift_is_pressed = True
        elif event_type == KEY_UP and vk in shift_vks:
            shift_is_pressed = False

        if event_type == KEY_DOWN and scan_code == 541:
            altgr_is_pressed = True
        elif event_type == KEY_UP and scan_code == 541:
            altgr_is_pressed = False

        is_keypad = (scan_code, vk, is_extended) in keypad_keys
        return callback(KeyboardEvent(event_type=event_type, scan_code=scan_code, name=name, is_keypad=is_keypad))

    def low_level_keyboard_handler(nCode, wParam, lParam):
        try:
            vk = lParam.contents.vk_code
            # Ignore the second `alt` DOWN observed in some cases.
            fake_alt = (LLKHF_INJECTED | 0x20)
            # Ignore events generated by SendInput with Unicode.
            if vk != VK_PACKET and lParam.contents.flags & fake_alt != fake_alt:
                event_type = keyboard_event_types[wParam]
                is_extended = lParam.contents.flags & 1
                scan_code = lParam.contents.scan_code
                should_continue = process_key(event_type, vk, scan_code, is_extended)
                if not should_continue:
                    return -1
        except Exception as e:
            print('Error in keyboard hook: ', e)

        return CallNextHookEx(NULL, nCode, wParam, lParam)

    WH_KEYBOARD_LL = c_int(13)
    keyboard_callback = LowLevelKeyboardProc(low_level_keyboard_handler)
    keyboard_hook = SetWindowsHookEx(WH_KEYBOARD_LL, keyboard_callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(UnhookWindowsHookEx, keyboard_callback)

def listen(callback):
    prepare_intercept(callback)
    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)

def map_char(name):
    _setup_name_tables()
    if from_name.get(name):
        i, entry = sorted(from_name[name])[0]
        scan_code, vk, is_extended, shift, altgr = entry
        return scan_code or -vk, (['shift'] * shift) + (['alt gr'] * altgr)
    else:
        raise ValueError('Key name {} is not mapped to any known key.'.format(repr(name)))

def _send_event(code, event_type):
    if code > 0:
        vk = scan_code_to_vk.get(code, 0)
        user32.keybd_event(vk, code, event_type, 0)
    else:
        # Negative scan code is a way to indicate we don't have a scan code,
        # and the value actually contains the Virtual key code.
        user32.keybd_event(-code, 0, event_type, 0)

def press(code):
    _send_event(code, 0)

def release(code):
    _send_event(code, 2)

def type_unicode(character):
    # This code and related structures are based on
    # http://stackoverflow.com/a/11910555/252218
    inputs = []
    surrogates = bytearray(character.encode('utf-16le'))
    for i in range(0, len(surrogates), 2):
        higher, lower = surrogates[i:i+2]
        structure = KEYBDINPUT(0, (lower << 8) + higher, KEYEVENTF_UNICODE, 0, None)
        inputs.append(INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure)))
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = c_int(ctypes.sizeof(INPUT))
    SendInput(nInputs, pInputs, cbSize)

if __name__ == '__main__':
    _setup_name_tables()
    import pprint
    pprint.pprint(to_name)
    pprint.pprint(from_name)
    #listen(lambda e: print(e.to_json()) or True)
