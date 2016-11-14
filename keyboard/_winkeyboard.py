# -*- coding: utf-8 -*-
"""
Code heavily adapted from http://pastebin.com/wzYZGZrs
"""
import atexit
from threading import Lock
import re

from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name

import ctypes
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_uint32, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import WORD, DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM, LONG
LPMSG = POINTER(MSG)
ULONG_PTR = POINTER(DWORD)

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

virtual_key_to_name = {
    0x03: 'control-break processing',
    0x08: 'backspace',
    0x09: 'tab',
    0x0c: 'clear',
    0x0d: 'enter',
    0x10: 'shift',
    0x11: 'ctrl',
    0x12: 'alt',
    0x13: 'pause',
    0x14: 'caps lock',
    0x15: 'ime kana mode',
    0x15: 'ime hanguel mode',
    0x15: 'ime hangul mode',
    0x17: 'ime junja mode',
    0x18: 'ime final mode',
    0x19: 'ime hanja mode',
    0x19: 'ime kanji mode',
    0x1b: 'esc',
    0x1c: 'ime convert',
    0x1d: 'ime nonconvert',
    0x1e: 'ime accept',
    0x1f: 'ime mode change request',
    0x20: 'spacebar',
    0x21: 'page up',
    0x22: 'page down',
    0x23: 'end',
    0x24: 'home',
    0x25: 'left arrow',
    0x26: 'up arrow',
    0x27: 'right arrow',
    0x28: 'down arrow',
    0x29: 'select',
    0x2a: 'print',
    0x2b: 'execute',
    0x2c: 'print screen',
    0x2d: 'ins',
    0x2e: 'del',
    0x2f: 'help',
    0x30: '0',
    0x31: '1',
    0x32: '2',
    0x33: '3',
    0x34: '4',
    0x35: '5',
    0x36: '6',
    0x37: '7',
    0x38: '8',
    0x39: '9',
    0x41: 'a',
    0x42: 'b',
    0x43: 'c',
    0x44: 'd',
    0x45: 'e',
    0x46: 'f',
    0x47: 'g',
    0x48: 'h',
    0x49: 'i',
    0x4a: 'j',
    0x4b: 'k',
    0x4c: 'l',
    0x4d: 'm',
    0x4e: 'n',
    0x4f: 'o',
    0x50: 'p',
    0x51: 'q',
    0x52: 'r',
    0x53: 's',
    0x54: 't',
    0x55: 'u',
    0x56: 'v',
    0x57: 'w',
    0x58: 'x',
    0x59: 'y',
    0x5a: 'z',
    0x5b: 'windows',
    0x5c: 'windows',
    0x5d: 'applications',
    0x5f: 'sleep',
    0x60: '0',
    0x61: '1',
    0x62: '2',
    0x63: '3',
    0x64: '4',
    0x65: '5',
    0x66: '6',
    0x67: '7',
    0x68: '8',
    0x69: '9',
    0x6a: 'multiply',
    0x6b: 'add',
    0x6c: 'separator',
    0x6d: 'subtract',
    0x6e: 'decimal',
    0x6f: 'divide',
    0x70: 'f1',
    0x71: 'f2',
    0x72: 'f3',
    0x73: 'f4',
    0x74: 'f5',
    0x75: 'f6',
    0x76: 'f7',
    0x77: 'f8',
    0x78: 'f9',
    0x79: 'f10',
    0x7a: 'f11',
    0x7b: 'f12',
    0x7c: 'f13',
    0x7d: 'f14',
    0x7e: 'f15',
    0x7f: 'f16',
    0x80: 'f17',
    0x81: 'f18',
    0x82: 'f19',
    0x83: 'f20',
    0x84: 'f21',
    0x85: 'f22',
    0x86: 'f23',
    0x87: 'f24',
    0x90: 'num lock',
    0x91: 'scroll lock',
    0xa0: 'left shift',
    0xa1: 'right shift',
    0xa2: 'left control',
    0xa3: 'right control',
    0xa4: 'left menu',
    0xa5: 'right menu',
    0xa6: 'browser back',
    0xa7: 'browser forward',
    0xa8: 'browser refresh',
    0xa9: 'browser stop',
    0xaa: 'browser search key ',
    0xab: 'browser favorites',
    0xac: 'browser start and home',
    0xad: 'volume mute',
    0xae: 'volume down',
    0xaf: 'volume up',
    0xb0: 'next track',
    0xb1: 'previous track',
    0xb2: 'stop media',
    0xb3: 'play/pause media',
    0xb4: 'start mail',
    0xb5: 'select media',
    0xb6: 'start application 1',
    0xb7: 'start application 2',
    0xbb: '+',
    0xbc: ',',
    0xbd: '-',
    0xbe: '.',
    0xe5: 'ime process',
    0xf6: 'attn',
    0xf7: 'crsel',
    0xf8: 'exsel',
    0xf9: 'erase eof',
    0xfa: 'play',
    0xfb: 'zoom',
    0xfc: 'reserved ',
    0xfd: 'pa1',
    0xfe: 'clear',
}

from_scan_code = {}
to_scan_code = {}
tables_lock = Lock()

def setup_tables():
    tables_lock.acquire()

    try:
        if from_scan_code and to_scan_code: return

        name_buffer = ctypes.create_unicode_buffer(32)
        keyboard_state = keyboard_state_type()
        for scan_code in range(2**(23-16)):
            from_scan_code[scan_code] = (['', ''], False)

            # Get associated virtual key code (if any) and map to fixed table of
            # names. Necessary for non-English versions of Windows where the
            # other functions return localized names. This is done first to
            # allow the next functions to overwrite with something more
            # accurate in the from_scan_code table, but leaving a useful
            # to_scan_code entry.
            key_code = MapVirtualKey(scan_code, MAPVK_VSC_TO_VK)
            if key_code and key_code in virtual_key_to_name:
                name = normalize_name(virtual_key_to_name[key_code])
                from_scan_code[scan_code] = ([name, name], None)
                to_scan_code[name] = (scan_code, False) 

            # Get pure key name, such as "shift". This depends on locale and
            # may return a translated name.
            for enhanced in [0, 1]:
                ret = GetKeyNameText(scan_code << 16 | enhanced << 24, name_buffer, 1024)
                if not ret:
                    continue
                name = name_buffer.value
                if name.lower().startswith('num ') and name.lower() != 'num lock':
                    is_keypad = True
                    name = name[len('NUM '):]
                else:
                    is_keypad = False

                name = normalize_name(re.sub(r'(right|left)\s+', '', name.lower()))
                from_scan_code[scan_code] = ([name, name], is_keypad)

                if name not in to_scan_code or not is_keypad:
                    to_scan_code[name] = (scan_code, False)

            # Get associated character, such as "^", possibly overwriting the pure key name.
            for shift_state in [0, 1]:
                keyboard_state[0x10] = shift_state * 0xFF
                ret = ToUnicode(key_code, scan_code, keyboard_state, name_buffer, len(name_buffer), 0)
                if ret:
                    # Sometimes two characters are written before the char we want,
                    # usually an accented one such as Â. Couldn't figure out why.
                    char = name_buffer.value[-1]
                    if name not in to_scan_code or not is_keypad:
                        to_scan_code[char] = (scan_code, bool(shift_state))
                    from_scan_code[scan_code][0][shift_state] = char

        # Alt GR is way outside the usual range of keys (0..127) and on my
        # computer is named as 'ctrl'. Therefore we add it manually and hope
        # Windows is consistent in its inconsistency.
        alt_gr_scan_code = 541
        from_scan_code[alt_gr_scan_code] = (['alt gr', 'alt gr'], False)
        to_scan_code['alt gr'] = alt_gr_scan_code
    finally:
        tables_lock.release()

shift_is_pressed = False
alt_gr_is_pressed = False

def listen(queue):
    setup_tables()

    def low_level_keyboard_handler(nCode, wParam, lParam):
        # Call next hook as soon as possible to reduce delays.
        ret = CallNextHookEx(NULL, nCode, wParam, lParam)

        # You may be tempted to use ToUnicode to extract the character from
        # this event with more precision. Do not. ToUnicode breaks dead keys.

        # Ignore events generated by SendInput with Unicode.
        if lParam.contents.vk_code != VK_PACKET:
            scan_code = lParam.contents.scan_code
            event_type = keyboard_event_types[wParam]

            names, is_keypad = from_scan_code[scan_code]

            global shift_is_pressed
            global alt_gr_is_pressed
            name = names[shift_is_pressed]
            
            is_extended = lParam.contents.flags & 1
            if name == 'alt' and is_extended and alt_gr_is_pressed:
                # Pressing AltGr also triggers regular alt quickly after. We
                # try to filter out this event. The `alt_gr_is_pressed` flag
                # is to avoid messing with keyboards that don't even have an
                # alt gr key.
                return

            if event_type == KEY_DOWN and name == 'shift':
                shift_is_pressed = True
            elif event_type == KEY_UP and name == 'shift':
                shift_is_pressed = False

            queue.put(KeyboardEvent(event_type=event_type, scan_code=scan_code, name=name, is_keypad=is_keypad))

        return ret

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

def map_char(name):
    setup_tables()
    try:
        scan_code, shift = to_scan_code[name]
        return scan_code, ['shift'] if shift else []
    except KeyError:
        raise ValueError('Key name {} is not mapped to any known key.'.format(repr(name)))

def press(scan_code):
    user32.keybd_event(MapVirtualKey(scan_code, MAPVK_VSC_TO_VK), 0, 0, 0)

def release(scan_code):
    user32.keybd_event(MapVirtualKey(scan_code, MAPVK_VSC_TO_VK), 0, 2, 0)

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
