# -*- coding: utf-8 -*-
"""
Code heavily adapted from http://pastebin.com/wzYZGZrs
"""
import atexit
from threading import Lock
import re

try:
    basestring
except NameError:
    basestring = str

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

KEY_UP = 'up'
KEY_DOWN = 'down'
keyboard_event_types = {
    WM_KEYDOWN: KEY_DOWN,
    WM_KEYUP: KEY_UP,
    WM_SYSKEYDOWN: KEY_DOWN,
    WM_SYSKEYUP: KEY_UP,
}

canonical_names = {
    'escape': 'esc',
    'return': 'enter',
    'del': 'delete',
    'control': 'ctrl',
    'altgr': 'alt gr',

    'left arrow': 'left',
    'up arrow': 'up',
    'down arrow': 'down',
    'right arrow': 'right',

    ' ': 'space', # Prefer to spell out keys that would be hard to read.
    '\x1b': 'esc',
    '\x08': 'backspace',
    '\n': 'enter',
    '\r': 'enter',
    '\t': 'tab',

    'scrlk': 'scroll lock',
    'prtscn': 'print screen',
    'prnt scrn': 'print screen',
    'snapshot': 'print screen',
    'ins': 'insert',
    'pause break': 'pause',
    'ctrll lock': 'caps lock',
    'capslock': 'caps lock',
    'number lock': 'num lock',
    'numlock:': 'num lock',
    'space bar': 'space',
    'spacebar': 'space',
    'linefeed': 'enter',
    'win': 'windows',

    'app': 'menu',
    'apps': 'menu',
    'application': 'menu',
    'applications': 'menu',

    'pagedown': 'page down',
    'pageup': 'page up',
    'pgdown': 'page down',
    'pgup': 'page up',
    'next': 'page down', # This looks wrong, but this is how Linux reports.
    'prior': 'page up',

    'underscore': '_',
    'equal': '=',
    'minplus': '+',
    'plus': '+',
    'add': '+',
    'subtract': '-',
    'minus': '-',
    'multiply': '*',
    'asterisk': '*',
    'divide': '/',

    'question': '?',
    'exclam': '!',
    'slash': '/',
    'bar': '|',
    'backslash': '\\',
    'braceleft': '{',
    'braceright': '}',
    'bracketleft': '[',
    'bracketright': ']',
    'parenleft': '(',
    'parenright': ')',

    'period': '.',
    'dot': '.',
    'comma': ',',
    'semicolon': ';',
    'colon': ':',

    'less': '<',
    'greater': '>',
    'ampersand': '&',
    'at': '@',
    'numbersign': '#',
    'hash': '#',
    'hashtag': '#',

    'dollar': '$',
    'sterling': '£',
    'pound': '£',
    'yen': '¥',
    'euro': '€',
    'cent': '¢',
    'currency': '¤',
    'registered': '®',
    'copyright': '©',
    'notsign': '¬',
    'percent': '%',
    'diaeresis': '"',
    'quotedbl': '"',
    'onesuperior': '¹',
    'twosuperior': '²',
    'threesuperior': '³',
    'onehalf': '½',
    'onequarter': '¼',
    'threequarters': '¾',
    'paragraph': '¶',
    'section': '§',
    'ssharp': '§',
    'division': '÷',
    'questiondown': '¿',
    'exclamdown': '¡',
    'degree': '°',
    'guillemotright': '»',
    'guillemotleft': '«',
    
    'acute': '´',
    'agudo': '´',
    'grave': '`',
    'tilde': '~',
    'asciitilde': '~',
    'til': '~',
    'cedilla': ',',
    'circumflex': '^',
    'apostrophe': '\'',
    
    'adiaeresis': 'ä',
    'udiaeresis': 'ü',
    'odiaeresis': 'ö',
    'oe': 'Œ',
    'oslash': 'ø',
    'ooblique': 'Ø',
    'ccedilla': 'ç',
    'ntilde': 'ñ',
    'eacute': 'é',
    'uacute': 'ú',
    'oacute': 'ó',
    'thorn': 'þ',
    'ae': 'æ',
    'eth': 'ð',
    'masculine': 'º',
    'feminine': 'ª',
    'iacute': 'í',
    'aacute': 'á',
    'mu': 'Μ',
    'aring': 'å',

    'zero': '0',
    'one': '1',
    'two': '2',
    'three': '3',
    'four': '4',
    'five': '5',
    'six': '6',
    'seven': '7',
    'eight': '8',
    'nine': '9',

    'play/pause': 'play/pause media',

    'num multiply': '*',
    'num divide': '/',
    'num add': '+',
    'num plus': '+',
    'num minus': '+',
    'num sub': '-',
    'num enter': 'enter',
    'num 0': '0',
    'num 1': '1',
    'num 2': '2',
    'num 3': '3',
    'num 4': '4',
    'num 5': '5',
    'num 6': '6',
    'num 7': '7',
    'num 8': '8',
    'num 9': '9',

    'left win': 'left windows',
    'right win': 'right windows',
    'left control': 'left ctrl',
    'right control': 'right ctrl',
}

def normalize_name(name):
    if not name:
        return 'unknown'
    if not isinstance(name, basestring):
        raise ValueError('Can only normalize string names. Unexpected '+ repr(name))

    name = name.lower()
    if name != '_':
        name = name.replace('_', ' ')

    return canonical_names.get(name, name)

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
    0x25: ('left arrow', False),
    0x26: ('up arrow', False),
    0x27: ('right arrow', False),
    0x28: ('down arrow', False),
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
    0x6a: ('*', False),
    0x6b: ('+', False),
    0x6c: ('separator', False),
    0x6d: ('-', False),
    0x6e: ('decimal', False),
    0x6f: ('/', False),
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
def setup_tables():
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
            for enhanced in [0, 1]:
                ret = GetKeyNameText(scan_code << 16 | enhanced << 24, name_buffer, 1024)
                if not ret:
                    continue
                name = normalize_name(name_buffer.value)
                from_scan_code[scan_code] = [name, name]

                if name not in to_scan_code:
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
        to_scan_code['alt gr'] = alt_gr_scan_code
    finally:
        tables_lock.release()

previous_name = None
active = False

setup_tables()
activation_hotkey = None

def listen():
    def low_level_keyboard_handler(nCode, wParam, lParam):
        try:
            vk = lParam.contents.vk_code
            # Ignore events generated by SendInput with Unicode.
            if vk != VK_PACKET:
                global active
                global previous_name

                event_type = keyboard_event_types[wParam]
                is_extended = lParam.contents.flags & 1
                scan_code = lParam.contents.scan_code
                if event_type == KEY_DOWN and scan_code == activation_hotkey:
                    active = not active
                    return -1
                if not active or scan_code not in from_scan_code:
                    return CallNextHookEx(NULL, nCode, wParam, lParam)

                name = normalize_name(from_scan_code[scan_code][False])
                if re.search('\bctrl|alt|shift|win\b', name):
                    return CallNextHookEx(NULL, nCode, wParam, lParam)

                should_continue = name == previous_name
                if event_type == KEY_DOWN:
                    if name == previous_name:
                        previous_name = None
                    else:
                        previous_name = name
                if should_continue:
                    return CallNextHookEx(NULL, nCode, wParam, lParam)
                else:
                    return -1
        except KeyboardInterrupt:
            exit(1)
        except Exception as e:
            print('Error in keyboard hook: ', e)

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

if __name__ == '__main__':
    activation_hotkey = to_scan_code['f12'][0]
    from threading import Thread
    t = Thread(target=listen)
    t.daemon = True
    t.start()
    while True:
        t.join(1)
