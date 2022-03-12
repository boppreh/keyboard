# -*- coding: utf-8 -*-
"""
This is the Windows backend for keyboard events, and is implemented by
invoking the Win32 API through the ctypes module. This is error prone
and can introduce very unpythonic failure modes, such as segfaults and
low level memory leaks. But it is also dependency-free, very performant
well documented on Microsoft's website and scattered examples.

# TODO:
- Keypad numbers still print as numbers even when numlock is off.
- No way to specify if user wants a keypad key or not in `map_char`.
- Use SendInput instead of keybd_event to work on games (see https://pypi.org/project/PyDirectInput/).
"""
from __future__ import unicode_literals
import re
import atexit
import traceback
from threading import Lock, Event
from collections import defaultdict, namedtuple

from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP
from ._canonical_names import normalize_name

try:
    # Force Python2 to convert to unicode and not to str.
    chr = unichr
except NameError:
    pass

# This part is just declaring Win32 API structures using ctypes. In C
# this would be simply #include "windows.h".

import ctypes
from ctypes import (
    c_short,
    c_char,
    c_uint8,
    c_int32,
    c_int,
    c_uint,
    c_uint32,
    c_long,
    Structure,
    WINFUNCTYPE,
    POINTER,
)
from ctypes.wintypes import (
    WORD,
    DWORD,
    BOOL,
    HHOOK,
    MSG,
    LPWSTR,
    WCHAR,
    WPARAM,
    LPARAM,
    LONG,
    HMODULE,
    LPCWSTR,
    HINSTANCE,
    HWND,
)

LPMSG = POINTER(MSG)
ULONG_PTR = POINTER(DWORD)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.restype = HMODULE
GetModuleHandleW.argtypes = [LPCWSTR]

# https://github.com/boppreh/mouse/issues/1
# user32 = ctypes.windll.user32
user32 = ctypes.WinDLL("user32", use_last_error=True)

VK_PACKET = 0xE7

WH_KEYBOARD_LL = c_int(13)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_KEYDOWN = 0x00
KEYEVENTF_KEYUP = 0x02
KEYEVENTF_UNICODE = 0x04


class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("vk_code", DWORD),
        ("scan_code", DWORD),
        ("flags", DWORD),
        ("time", c_int),
        ("dwExtraInfo", ULONG_PTR),
    ]


# Included for completeness.
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg", DWORD), ("wParamL", WORD), ("wParamH", WORD))


class _INPUTunion(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _fields_ = (("type", DWORD), ("union", _INPUTunion))


LowLevelKeyboardProc = WINFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(KBDLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExW
SetWindowsHookEx.argtypes = [c_int, LowLevelKeyboardProc, HINSTANCE, DWORD]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
# CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(KBDLLHOOKSTRUCT)]
CallNextHookEx.restype = c_int

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = BOOL

GetMessage = user32.GetMessageW
GetMessage.argtypes = [LPMSG, HWND, c_uint, c_uint]
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

LLKHF_INJECTED = 0x00000010

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x104  # Used for ALT key
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
    0x03: ("control-break processing", False),
    0x08: ("backspace", False),
    0x09: ("tab", False),
    0x0C: ("clear", False),
    0x0D: ("enter", False),
    0x10: ("shift", False),
    0x11: ("ctrl", False),
    0x12: ("alt", False),
    0x13: ("pause", False),
    0x14: ("caps lock", False),
    0x15: ("ime kana mode", False),
    0x15: ("ime hanguel mode", False),
    0x15: ("ime hangul mode", False),
    0x17: ("ime junja mode", False),
    0x18: ("ime final mode", False),
    0x19: ("ime hanja mode", False),
    0x19: ("ime kanji mode", False),
    0x1B: ("esc", False),
    0x1C: ("ime convert", False),
    0x1D: ("ime nonconvert", False),
    0x1E: ("ime accept", False),
    0x1F: ("ime mode change request", False),
    0x20: ("spacebar", False),
    0x21: ("page up", False),
    0x22: ("page down", False),
    0x23: ("end", False),
    0x24: ("home", False),
    0x25: ("left", False),
    0x26: ("up", False),
    0x27: ("right", False),
    0x28: ("down", False),
    0x29: ("select", False),
    0x2A: ("print", False),
    0x2B: ("execute", False),
    0x2C: ("print screen", False),
    0x2D: ("insert", False),
    0x2E: ("delete", False),
    0x2F: ("help", False),
    0x30: ("0", False),
    0x31: ("1", False),
    0x32: ("2", False),
    0x33: ("3", False),
    0x34: ("4", False),
    0x35: ("5", False),
    0x36: ("6", False),
    0x37: ("7", False),
    0x38: ("8", False),
    0x39: ("9", False),
    0x41: ("a", False),
    0x42: ("b", False),
    0x43: ("c", False),
    0x44: ("d", False),
    0x45: ("e", False),
    0x46: ("f", False),
    0x47: ("g", False),
    0x48: ("h", False),
    0x49: ("i", False),
    0x4A: ("j", False),
    0x4B: ("k", False),
    0x4C: ("l", False),
    0x4D: ("m", False),
    0x4E: ("n", False),
    0x4F: ("o", False),
    0x50: ("p", False),
    0x51: ("q", False),
    0x52: ("r", False),
    0x53: ("s", False),
    0x54: ("t", False),
    0x55: ("u", False),
    0x56: ("v", False),
    0x57: ("w", False),
    0x58: ("x", False),
    0x59: ("y", False),
    0x5A: ("z", False),
    0x5B: ("left windows", False),
    0x5C: ("right windows", False),
    0x5D: ("applications", False),
    0x5F: ("sleep", False),
    0x60: ("0", True),
    0x61: ("1", True),
    0x62: ("2", True),
    0x63: ("3", True),
    0x64: ("4", True),
    0x65: ("5", True),
    0x66: ("6", True),
    0x67: ("7", True),
    0x68: ("8", True),
    0x69: ("9", True),
    0x6A: ("*", True),
    0x6B: ("+", True),
    0x6C: ("separator", True),
    0x6D: ("-", True),
    0x6E: ("decimal", True),
    0x6F: ("/", True),
    0x70: ("f1", False),
    0x71: ("f2", False),
    0x72: ("f3", False),
    0x73: ("f4", False),
    0x74: ("f5", False),
    0x75: ("f6", False),
    0x76: ("f7", False),
    0x77: ("f8", False),
    0x78: ("f9", False),
    0x79: ("f10", False),
    0x7A: ("f11", False),
    0x7B: ("f12", False),
    0x7C: ("f13", False),
    0x7D: ("f14", False),
    0x7E: ("f15", False),
    0x7F: ("f16", False),
    0x80: ("f17", False),
    0x81: ("f18", False),
    0x82: ("f19", False),
    0x83: ("f20", False),
    0x84: ("f21", False),
    0x85: ("f22", False),
    0x86: ("f23", False),
    0x87: ("f24", False),
    0x90: ("num lock", False),
    0x91: ("scroll lock", False),
    0xA0: ("left shift", False),
    0xA1: ("right shift", False),
    0xA2: ("left ctrl", False),
    0xA3: ("right ctrl", False),
    0xA4: ("left menu", False),
    0xA5: ("right menu", False),
    0xA6: ("browser back", False),
    0xA7: ("browser forward", False),
    0xA8: ("browser refresh", False),
    0xA9: ("browser stop", False),
    0xAA: ("browser search key", False),
    0xAB: ("browser favorites", False),
    0xAC: ("browser start and home", False),
    0xAD: ("volume mute", False),
    0xAE: ("volume down", False),
    0xAF: ("volume up", False),
    0xB0: ("next track", False),
    0xB1: ("previous track", False),
    0xB2: ("stop media", False),
    0xB3: ("play/pause media", False),
    0xB4: ("start mail", False),
    0xB5: ("select media", False),
    0xB6: ("start application 1", False),
    0xB7: ("start application 2", False),
    0xBB: ("+", False),
    0xBC: (",", False),
    0xBD: ("-", False),
    0xBE: (".", False),
    # 0xbe:('/', False), # Used for miscellaneous characters; it can vary by keyboard. For the US standard keyboard, the '/?.
    0xE5: ("ime process", False),
    0xF6: ("attn", False),
    0xF7: ("crsel", False),
    0xF8: ("exsel", False),
    0xF9: ("erase eof", False),
    0xFA: ("play", False),
    0xFB: ("zoom", False),
    0xFC: ("reserved ", False),
    0xFD: ("pa1", False),
    0xFE: ("clear", False),
}

# Represents a pressed or released key, along with the state of the keyboard.
# Used to compute key names
KeyInput = namedtuple("KeyInput", "scan_code vk is_extended modifiers")

tables_lock = Lock()
# Maps KeyInputs to a list of names by priority, such as ['space', ' '].
to_names = {}
# Maps KeyInputs to the character that they would type, or empty string.
to_char = {}
# Maps a name to a KeyInput that would generate that key.
from_name = defaultdict(list)
scan_code_to_vk = {}

# Modifier combinations that may result in keys being named differently.
# Since the table of all combinations is pre-computed, we try to avoid useless
# combinations like "ctrl" + something, since it never changes the name of the key.
name_changing_modifiers = [
    (),  # 'a' stays 'a'
    ("shift",),  # 'a' becomes 'A'
    ("alt gr",),  # 'a' becomes 'á'
    ("alt gr", "shift"),  # 'a' becomes 'Á''
    ("num lock",),  # Keypad 7 becomes "home"
    ("shift", "num lock"),  # Keypad "home" stays "home", regardless of "num lock"
    ("caps lock",),  # 'a' becomes 'A'
    ("shift", "caps lock"),  # 'a' becomes 'á'
    ("shift", "alt gr", "caps lock"),  # 'a' becomes 'Á'
]

# Modifiers that change characters typed, but not control keys.
char_modifiers = ["shift", "alt gr", "caps lock", "num lock"]

name_buffer = ctypes.create_unicode_buffer(32)
unicode_buffer = ctypes.create_unicode_buffer(32)
keyboard_state = keyboard_state_type()


def get_event_char(key_input):
    """
    Given information about a pressed key, returns what character it probably
    would have typed (e.g. 'shift+a' -> 'A'), or '' if it's a control character.
    """
    if "windows" in key_input.modifiers:
        return ""

    simplified_input = key_input._replace(modifiers=tuple(m for m in key_input.modifiers if m in char_modifiers))
    if simplified_input in to_char:
        return to_char[simplified_input]

    keyboard_state[0x10] = 0x80 * ("shift" in key_input.modifiers)
    keyboard_state[0x11] = 0x80 * ("alt gr" in key_input.modifiers)
    keyboard_state[0x12] = 0x80 * ("alt gr" in key_input.modifiers)
    keyboard_state[0x14] = 0x01 * ("caps lock" in key_input.modifiers)
    keyboard_state[0x90] = 0x01 * ("num lock" in key_input.modifiers)
    # These modifiers don't affect the typed character.
    # keyboard_state[0x91] = 0x01 * ("scroll lock" in key_input.modifiers)
    # keyboard_state[0x5B] = 0x01 * ("windows" in key_input.modifiers)
    unicode_ret = ToUnicode(key_input.vk, key_input.scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)
    if unicode_ret and unicode_buffer.value:
        char = str(unicode_buffer.value)
        # unicode_ret == -1 -> is dead key
        # ToUnicode has the side effect of setting global flags for dead keys.
        # Therefore we need to call it twice to clear those flags.
        # If your 6 and 7 keys are named "^6" and "^7", this is the reason.
        ToUnicode(key_input.vk, key_input.scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)
    else:
        char = ""

    to_char[simplified_input] = char
    return char


def get_event_names(key_input):
    """
    Given information about a pressed key, returns an ordered list of the
    possible names.
    """
    # Alt gr is way outside the usual range of keys (0..127) and on my
    # computer is named as 'ctrl'. Therefore we add it manually and hope
    # Windows is consistent in its inconsistency.
    if key_input.scan_code == 541 and key_input.vk == 162:
        return ["alt gr"]

    if key_input in to_names:
        return to_names[key_input]

    names = []

    is_keypad = (key_input.scan_code, key_input.vk, key_input.is_extended) in keypad_keys
    is_official = key_input.vk in official_virtual_keys
    if is_keypad and is_official:
        names.append(official_virtual_keys[key_input.vk][0])

    # Prefer reporting 'shift+5' than 'shift+%'. The actual character typed will
    # be stored in a separate field of the event.
    char = get_event_char(key_input._replace(modifiers=()))
    if char:
        names.append(char)

    name_ret = GetKeyNameText(key_input.scan_code << 16 | key_input.is_extended << 24, name_buffer, 1024)
    if name_ret and name_buffer.value:
        # This function returns shouty values such as "SPACE", so we lowercase them.
        names.append(str(name_buffer.value).lower())

    char = user32.MapVirtualKeyW(key_input.vk, MAPVK_VK_TO_CHAR) & 0xFF
    if char != 0:
        names.append(chr(char))

    if not is_keypad and is_official:
        names.append(official_virtual_keys[key_input.vk][0])

    names = [normalize_name(name) for name in names]
    # Remove duplicates while keeping order.
    sorted(set(names), key=names.index)
    to_names[key_input] = names
    return names


def _setup_name_tables():
    """
    Ensures the scan code/virtual key code/name translation tables are
    filled.
    """
    with tables_lock:
        if to_names:
            return

        # Go through every possible scan code, and map them to virtual key codes.
        # Then vice-versa.
        all_scan_codes = [(sc, user32.MapVirtualKeyW(sc, MAPVK_VSC_TO_VK_EX)) for sc in range(0x100)]
        all_vks = [(user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX), vk) for vk in range(0x100)]
        all_pairs = all_scan_codes + all_vks
        # Remove duplicates while keeping order.
        all_pairs = sorted(set(all_pairs), key=all_pairs.index)

        for scan_code, vk in all_pairs:
            # `to_names` and `from_name` entries will be a tuple (scan_code, vk, extended, modifiers).
            if (scan_code, vk, 0, 0, ()) in to_names:
                continue

            if scan_code not in scan_code_to_vk:
                scan_code_to_vk[scan_code] = vk

            # Brute force all combinations to find all possible names.
            for extended in [0, 1]:
                for modifiers in name_changing_modifiers:
                    entry = KeyInput(scan_code, vk, extended, modifiers)
                    # Get key names from ToUnicode, GetKeyNameText, MapVirtualKeyW and official virtual keys.
                    # Note that calling these functions will populate the `to_names` and `to_char` caches.
                    names = list(get_event_names(entry))

                    char = get_event_char(entry)
                    if char:
                        names.append(char)

                    # Remember the "id" of the name, as the first techniques
                    # have better results and therefore priority.
                    for i, name in enumerate(names):
                        from_name[name].append((i, entry))

        # TODO: single quotes on US INTL is returning the dead key (?), and therefore
        # not typing properly.

        # Alt gr is way outside the usual range of keys (0..127) and on my
        # computer is named as 'ctrl'. Therefore we add it manually and hope
        # Windows is consistent in its inconsistency.
        from_name["alt gr"].append((1, (541, 162, 0, ())))

    modifiers_preference = defaultdict(lambda: 10)
    modifiers_preference.update({(): 0, ("shift",): 1, ("alt gr",): 2, ("ctrl",): 3, ("alt",): 4})

    def order_key(line):
        i, entry = line
        scan_code, vk, extended, modifiers = entry
        return modifiers_preference[modifiers], i, extended, vk, scan_code

    for name, entries in list(from_name.items()):
        from_name[name] = sorted(set(entries), key=order_key)


# Called by keyboard/__init__.py
def init():
    with tables_lock:
        to_names.clear()
        to_char.clear()
        from_name.clear()
        scan_code_to_vk.clear()
    _setup_name_tables()


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


class Listener(object):
    def __init__(self):
        self.shift_is_pressed = False
        self.altgr_is_pressed = False
        self.win_is_pressed = False
        self.ignore_next_right_alt = False
        self.shift_vks = {vk for vk, (name, _) in official_virtual_keys.items() if "shift" in name}
        self.win_vks = {vk for vk, (name, _) in official_virtual_keys.items() if "windows" in name}
        self.cancelled = False

    def on_exit(self):
        if self.cancelled:
            return
        UnhookWindowsHookEx(self.hook_id)
        self.cancelled = True

    def stop(self):
        if hasattr(atexit, "unregister"):
            # Python3
            atexit.unregister(self.on_exit)
        UnhookWindowsHookEx(self.hook_id)
        self.cancelled = True

    def listen(self, callback):
        """
        Registers a Windows low level keyboard hook. The provided callback will
        be invoked for each high-level keyboard event, and is expected to return
        True if the key event should be passed to the next program, or False if
        the event is to be blocked.
        """
        _setup_name_tables()

        def process_key(event_type, vk, scan_code, is_extended):
            # print(event_type, vk, scan_code, is_extended)

            # Pressing alt-gr also generates an extra "right alt" event
            if vk == 0xA5 and self.ignore_next_right_alt:
                self.ignore_next_right_alt = False
                return True

            modifiers = (
                ("shift",) * self.shift_is_pressed
                + ("alt gr",) * self.altgr_is_pressed
                + ("windows",) * self.win_is_pressed
                + ("num lock",) * (user32.GetKeyState(0x90) & 1)
                + ("caps lock",) * (user32.GetKeyState(0x14) & 1)
                + ("scroll lock",) * (user32.GetKeyState(0x91) & 1)
            )

            entry = KeyInput(scan_code, vk, is_extended, modifiers)
            name = (get_event_names(entry) or [None])[0]
            char = get_event_char(entry)

            # TODO: inaccurate when holding multiple different shifts.
            if vk in self.shift_vks:
                self.shift_is_pressed = event_type == KEY_DOWN
            if vk in self.win_vks:
                self.win_is_pressed = event_type == KEY_DOWN
            if scan_code == 541 and vk == 162:
                self.ignore_next_right_alt = True
                self.altgr_is_pressed = event_type == KEY_DOWN

            is_keypad = (scan_code, vk, is_extended) in keypad_keys
            return callback(
                KeyboardEvent(
                    event_type=event_type,
                    scan_code=scan_code or -vk,
                    name=name,
                    char=char,
                    is_keypad=is_keypad,
                    modifiers=modifiers,
                )
            )

        def low_level_keyboard_handler(nCode, wParam, lParam):
            try:
                vk = lParam.contents.vk_code
                # Ignore the second `alt` DOWN observed in some cases.
                fake_alt = LLKHF_INJECTED | 0x20
                # Ignore events generated by SendInput with Unicode.
                if vk != VK_PACKET and lParam.contents.flags & fake_alt != fake_alt:
                    event_type = keyboard_event_types[wParam]
                    is_extended = lParam.contents.flags & 1
                    scan_code = lParam.contents.scan_code
                    should_continue = process_key(event_type, vk, scan_code, is_extended)
                    if not should_continue:
                        return -1
            except Exception as e:
                print("Error in keyboard hook:")
                traceback.print_exc()

            return CallNextHookEx(None, nCode, wParam, lParam)

        self.keyboard_callback = LowLevelKeyboardProc(low_level_keyboard_handler)
        handle = GetModuleHandleW(None)
        thread_id = DWORD(0)
        self.hook_id = SetWindowsHookEx(WH_KEYBOARD_LL, self.keyboard_callback, handle, thread_id)

        # Register to remove the hook when the interpreter exits. Unfortunately a
        # try/finally block doesn't seem to work here.
        atexit.register(self.on_exit)

        msg = LPMSG()
        while not GetMessage(msg, 0, 0, 0) and not self.cancelled:
            TranslateMessage(msg)
            DispatchMessage(msg)


def map_name(name):
    _setup_name_tables()

    entries = from_name.get(name)
    if not entries:
        raise ValueError("Key name {} is not mapped to any known key.".format(repr(name)))
    for i, entry in entries:
        scan_code, vk, is_extended, modifiers = entry
        yield scan_code or -vk, modifiers


def _send_event(code, event_type):
    if code == 541:
        # Alt-gr is made of ctrl+alt. Just sending even 541 doesn't do anything.
        user32.keybd_event(0x11, code, event_type, 0)
        user32.keybd_event(0x12, code, event_type, 0)
    elif code > 0:
        vk = scan_code_to_vk.get(code, 0)
        user32.keybd_event(vk, code, event_type, 0)
    else:
        # Negative scan code is a way to indicate we don't have a scan code,
        # and the value actually contains the Virtual key code.
        user32.keybd_event(-code, 0, event_type, 0)


def press(code):
    _send_event(code, KEYEVENTF_KEYDOWN)


def release(code):
    _send_event(code, KEYEVENTF_KEYUP)


def type_unicode(character):
    # This code and related structures are based on
    # http://stackoverflow.com/a/11910555/252218
    surrogates = bytearray(character.encode("utf-16le"))
    presses = []
    releases = []
    for i in range(0, len(surrogates), 2):
        higher, lower = surrogates[i : i + 2]
        structure = KEYBDINPUT(0, (lower << 8) + higher, KEYEVENTF_UNICODE, 0, None)
        presses.append(INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure)))
        structure = KEYBDINPUT(0, (lower << 8) + higher, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        releases.append(INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure)))
    inputs = presses + releases
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = c_int(ctypes.sizeof(INPUT))
    SendInput(nInputs, pInputs, cbSize)


if __name__ == "__main__":
    _setup_name_tables()
    import pprint

    pprint.pprint(to_char)
    pprint.pprint(to_names)
    pprint.pprint(from_name)
    # listen(lambda e: print(e.to_json()) or True)
