# -*- coding: utf-8 -*-
"""
This is the Windows backend for keyboard events, and is implemented by
invoking the Win32 API through the ctypes module. This is error prone
and can introduce very unpythonic failure modes, such as segfaults and
low level memory leaks. But it is also dependency-free, very performant
well documented on Microsoft's webstie and scattered examples.
"""
import atexit
from threading import Lock
import re

from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
from ._suppress import KeyTable

# This part is just declaring Win32 API structures using ctypes. In C
# this would be simply #include "windows.h".

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_uint32, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import WORD, DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM, LONG
LPMSG = POINTER(MSG)
ULONG_PTR = POINTER(DWORD)

# Shortcut.
user32 = ctypes.windll.user32

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

MAPVK_VK_TO_VSC = 0
MAPVK_VSC_TO_VK = 1

VkKeyScan = user32.VkKeyScanW
VkKeyScan.argtypes = [WCHAR]
VkKeyScan.restype = c_short

NULL = c_int(0)

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
from_virtual_key = {
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
    0xaa: ('browser search key ', False),
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
    # 0xbe: ('/', False), # Used for miscellaneous characters; it can vary by keyboard. For the US standard keyboard, the '/?' key.
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

# Exceptions to our logic. Still trying to figure out what is happening.
possible_extended_keys = [0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0xc, 0x6b, 0x2e, 0x2d, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f]
reversed_extended_keys = [0x6f, 0xd]

from_scan_code = {}
to_scan_code = {}
vk_to_scan_code = {}
scan_code_to_vk = {}
tables_lock = Lock()

# Alt gr is way outside the usual range of keys (0..127) and on my
# computer is named as 'ctrl'. Therefore we add it manually and hope
# Windows is consistent in its inconsistency.
alt_gr_scan_code = 541

# These tables are used as backup when a key name can not be found by virtual
# key code.
def _setup_tables():
    """
    Ensures the scan code/virtual key code/name translation tables are
    filled.
    """
    tables_lock.acquire()

    try:
        if from_scan_code and to_scan_code: return

        for vk in range(0x01, 0x100):
            scan_code = MapVirtualKey(vk, MAPVK_VK_TO_VSC)
            if not scan_code: continue

            # Scan codes may map to multiple virtual key codes.
            # In this case prefer the officially defined ones.
            if scan_code_to_vk.get(scan_code, 0) not in from_virtual_key:
                scan_code_to_vk[scan_code] = vk
            vk_to_scan_code[vk] = scan_code

        name_buffer = ctypes.create_unicode_buffer(32)
        keyboard_state = keyboard_state_type()
        for scan_code in range(2**(23-16)):
            from_scan_code[scan_code] = ['unknown', 'unknown']

            # Get pure key name, such as "shift". This depends on locale and
            # may return a translated name.
            for enhanced in [1, 0]:
                ret = GetKeyNameText(scan_code << 16 | enhanced << 24, name_buffer, 1024)
                if not ret:
                    continue
                name = normalize_name(name_buffer.value)
                from_scan_code[scan_code] = [name, name]
                to_scan_code[name] = (scan_code, False)

            if scan_code not in scan_code_to_vk: continue
            # Get associated character, such as "^", possibly overwriting the pure key name.
            for shift_state in [0, 1]:
                keyboard_state[0x10] = shift_state * 0xFF
                vk = scan_code_to_vk.get(scan_code, 0)
                ret = ToUnicode(vk, scan_code, keyboard_state, name_buffer, len(name_buffer), 0)
                if ret:
                    # Sometimes two characters are written before the char we want,
                    # usually an accented one such as Â. Couldn't figure out why.
                    char = name_buffer.value[-1]
                    if char not in to_scan_code:
                        to_scan_code[char] = (scan_code, bool(shift_state))
                    from_scan_code[scan_code][shift_state] = char

        from_scan_code[alt_gr_scan_code] = ['alt gr', 'alt gr']
        to_scan_code['alt gr'] = (alt_gr_scan_code, False)
    finally:
        tables_lock.release()

shift_is_pressed = False
alt_gr_is_pressed = False

init = _setup_tables

def prepare_intercept(callback):
    """
    Registers a Windows low level keyboard hook. The provided callback will
    be invoked for each high-level keyboard event, and is expected to return
    True if the key event should be passed to the next program, or False if
    the event is to be blocked.

    No event is processed until the Windows messages are pumped (see
    start_intercept).
    """
    _setup_tables()
    
    def process_key(event_type, vk, scan_code, is_extended):
        global alt_gr_is_pressed
        global shift_is_pressed

        name = 'unknown'
        is_keypad = False
        if scan_code == alt_gr_scan_code:
            alt_gr_is_pressed = event_type == KEY_DOWN
            name = 'alt gr'
        else:
            if vk in from_virtual_key:
                # Pressing AltGr also triggers "right menu" quickly after. We
                # try to filter out this event. The `alt_gr_is_pressed` flag
                # is to avoid messing with keyboards that don't even have an
                # alt gr key.
                if vk == 165:
                    return True

                name, is_keypad = from_virtual_key[vk]
                if vk in possible_extended_keys and not is_extended:
                    is_keypad = True
                # What the hell Windows?
                if vk in reversed_extended_keys and is_extended:
                    is_keypad = True                
            
            elif scan_code in from_scan_code:
                name = from_scan_code[scan_code][shift_is_pressed]
            
        if event_type == KEY_DOWN and name == 'shift':
            shift_is_pressed = True
        elif event_type == KEY_UP and name == 'shift':
            shift_is_pressed = False

        return callback(KeyboardEvent(event_type=event_type, scan_code=scan_code, name=name, is_keypad=is_keypad))

    def low_level_keyboard_handler(nCode, wParam, lParam):
        try:
            vk = lParam.contents.vk_code
            # Ignore events generated by SendInput with Unicode.
            if vk != VK_PACKET:
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

def _start_intercept():
    """
    Starts pumping Windows messages, which invokes the registered low
    level keyboard hook.
    """
    # TODO: why does this work, without the whole Translate/Dispatch dance?
    GetMessage(LPMSG(), NULL, NULL, NULL)
    #msg = LPMSG()
    #while not GetMessage(msg, NULL, NULL, NULL):
    #    TranslateMessage(msg)
    #    DispatchMessage(msg)

def listen(callback):
    prepare_intercept(callback)
    _start_intercept()

def map_char(name):
    _setup_tables()

    wants_keypad = name.startswith('keypad ')
    if wants_keypad:
        name = name[len('keypad '):]

    for vk in from_virtual_key:
        candidate_name, is_keypad = from_virtual_key[vk]
        if candidate_name in (name, 'left ' + name, 'right ' + name) and is_keypad == wants_keypad:
            # HACK: use negative scan codes to identify virtual key codes.
            # This is required to correctly associate media keys, since they report a scan
            # code of 0 but still have valid virtual key codes. It also helps standardizing
            # the key names, since the virtual key code table is constant.
            return -vk, []

    if name in to_scan_code:
        scan_code, shift = to_scan_code[name]
        return scan_code, ['shift'] if shift else []
    else:
        raise ValueError('Key name {} is not mapped to any known key.'.format(repr(name)))

# For pressing and releasing, we need both the scan code and virtual key code.
# Only one is necessary most of the time, but some intrusive software require both.
def _send_event(code, event_type):
    if code < 0:
        vk = -code
        code = vk_to_scan_code[vk]
    else:
        vk = scan_code_to_vk.get(code, 0)
    user32.keybd_event(vk, code, event_type, 0)

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
    import keyboard
    def p(event):
        print(event)
    keyboard.hook(p)
    input()
