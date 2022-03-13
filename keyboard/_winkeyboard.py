# -*- coding: utf-8 -*-
"""
This is the Windows backend for keyboard events, and is implemented by
invoking the Win32 API through the ctypes module. This is error prone
and can introduce very unpythonic failure modes, such as segfaults and
low level memory leaks. But it is also dependency-free, very performant
well documented on Microsoft's website and scattered examples.

# TODO:
- Numpad numbers still print as numbers even when numlock is off.
- No way to specify if user wants a numpad key or not in `map_char`.
- Use SendInput instead of keybd_event to work on games (see https://pypi.org/project/PyDirectInput/).
"""
from __future__ import unicode_literals
import re
import atexit
import traceback
import itertools
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

######
# This marks the end of Win32 API declarations. The rest is ours.
######

# Represents a pressed or released key, along with the state of the keyboard.
# Used to compute key names
KeyInput = namedtuple("KeyInput", "scan_code vk is_extended modifiers")


class KeyMapper(object):
    """
    Class to group all the hardcoded lists and runtime tables need to identify key events.
    """

    # List taken from the official documentation, but stripped of the OEM-specific keys.
    # Used for naming keys and
    official_virtual_keys = {
        0x03: "control-break processing",
        0x08: "backspace",
        0x09: "tab",
        0x0C: "clear",
        0x0D: "enter",
        0x10: "shift",
        0x11: "ctrl",
        0x12: "alt",
        0x13: "pause",
        0x14: "caps lock",
        0x15: "ime kana mode",
        0x15: "ime hanguel mode",
        0x15: "ime hangul mode",
        0x17: "ime junja mode",
        0x18: "ime final mode",
        0x19: "ime hanja mode",
        0x19: "ime kanji mode",
        0x1B: "esc",
        0x1C: "ime convert",
        0x1D: "ime nonconvert",
        0x1E: "ime accept",
        0x1F: "ime mode change request",
        0x20: "spacebar",
        0x21: "page up",
        0x22: "page down",
        0x23: "end",
        0x24: "home",
        0x25: "left",
        0x26: "up",
        0x27: "right",
        0x28: "down",
        0x29: "select",
        0x2A: "print",
        0x2B: "execute",
        0x2C: "print screen",
        0x2D: "insert",
        0x2E: "delete",
        0x2F: "help",
        0x30: "0",
        0x31: "1",
        0x32: "2",
        0x33: "3",
        0x34: "4",
        0x35: "5",
        0x36: "6",
        0x37: "7",
        0x38: "8",
        0x39: "9",
        0x41: "a",
        0x42: "b",
        0x43: "c",
        0x44: "d",
        0x45: "e",
        0x46: "f",
        0x47: "g",
        0x48: "h",
        0x49: "i",
        0x4A: "j",
        0x4B: "k",
        0x4C: "l",
        0x4D: "m",
        0x4E: "n",
        0x4F: "o",
        0x50: "p",
        0x51: "q",
        0x52: "r",
        0x53: "s",
        0x54: "t",
        0x55: "u",
        0x56: "v",
        0x57: "w",
        0x58: "x",
        0x59: "y",
        0x5A: "z",
        0x5B: "left windows",
        0x5C: "right windows",
        0x5D: "applications",
        0x5F: "sleep",
        0x60: "0",
        0x61: "1",
        0x62: "2",
        0x63: "3",
        0x64: "4",
        0x65: "5",
        0x66: "6",
        0x67: "7",
        0x68: "8",
        0x69: "9",
        0x6A: "*",
        0x6B: "+",
        0x6C: "separator",
        0x6D: "-",
        0x6E: "decimal",
        0x6F: "/",
        0x70: "f1",
        0x71: "f2",
        0x72: "f3",
        0x73: "f4",
        0x74: "f5",
        0x75: "f6",
        0x76: "f7",
        0x77: "f8",
        0x78: "f9",
        0x79: "f10",
        0x7A: "f11",
        0x7B: "f12",
        0x7C: "f13",
        0x7D: "f14",
        0x7E: "f15",
        0x7F: "f16",
        0x80: "f17",
        0x81: "f18",
        0x82: "f19",
        0x83: "f20",
        0x84: "f21",
        0x85: "f22",
        0x86: "f23",
        0x87: "f24",
        0x90: "num lock",
        0x91: "scroll lock",
        0xA0: "left shift",
        0xA1: "right shift",
        0xA2: "left ctrl",
        0xA3: "right ctrl",
        0xA4: "left menu",
        0xA5: "right menu",
        0xA6: "browser back",
        0xA7: "browser forward",
        0xA8: "browser refresh",
        0xA9: "browser stop",
        0xAA: "browser search key",
        0xAB: "browser favorites",
        0xAC: "browser start and home",
        0xAD: "volume mute",
        0xAE: "volume down",
        0xAF: "volume up",
        0xB0: "next track",
        0xB1: "previous track",
        0xB2: "stop media",
        0xB3: "play/pause media",
        0xB4: "start mail",
        0xB5: "select media",
        0xB6: "start application 1",
        0xB7: "start application 2",
        0xBB: "+",
        0xBC: ",",
        0xBD: "-",
        0xBE: ".",
        # 0xbe: '/',, # Used for miscellaneous characters; it can vary by keyboard. For the US standard keyboard, the '/?.
        0xE5: "ime process",
        0xF6: "attn",
        0xF7: "crsel",
        0xF8: "exsel",
        0xF9: "erase eof",
        0xFA: "play",
        0xFB: "zoom",
        0xFC: "reserved ",
        0xFD: "pa1",
        0xFE: "clear",
    }

    # List created manually.
    numpad_keys = [
        # (scan_code, virtual_key_code, is_extended)
        (126, 194, 0),
        (28, 13, 1),
        (53, 111, 1),
        (69, 144, 1),
        (55, 106, 0),
        (71, 103, 0),
        (71, 36, 0),
        (72, 104, 0),
        (72, 38, 0),
        (73, 105, 0),
        (73, 33, 0),
        (74, 109, 0),
        (75, 100, 0),
        (75, 37, 0),
        (76, 101, 0),
        (76, 12, 0),
        (77, 102, 0),
        (77, 39, 0),
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

    # Scan codes that have an "extended version", and we actually prefer using the extended key.
    # More info on extended keys: https://docs.microsoft.com/en-us/windows/win32/inputdev/about-keyboard-input#extended-key-flag
    prefer_extended_scan_codes = {
        69,  # num lock
        55,  # print screen (the non-extended print screen is seen when pressing alt+print screen)
        82,  # insert
        71,  # home
        73,  # page up
        83,  # delete
        79,  # end
        81,  # page down
        72,  # up
        75,  # left
        80,  # down
        77,  # right
        93,  # menu
    }

    # Modifier combinations that may result in keys being named or typed differently.
    # Since the table of all combinations is pre-computed, we try to avoid useless
    # combinations like "ctrl" + something, since it never changes the name of the key.
    char_modifiers = {"shift", "alt gr", "caps lock", "numlock"}

    # Modifiers that, when present, signal that no char will be typed.
    non_char_modifiers = {"ctrl", "alt", "windows"}

    # Modifiers that don't affect a key's name, or the character typed. Listed here just for completeness.
    # ignored_modifiers = ['scroll lock']

    def __init__(self):
        # Maps KeyInputs to the character that they would type, or empty string if unknown/no characters would be typed.
        # Used by the Listener class.
        self.input_to_char = {}
        # Maps scan codes (or negative vks) to the name of the key, usually what is printed on it, or None if unknown.
        # Used by the `press` and `release` functions, that are provided only scan codes.
        self.scan_code_to_name = {}
        # Maps each name to the preferred key and way to input it.
        # Used by `map_name` function.
        self.name_to_inputs = defaultdict(list)

        # All combinations of modifiers that may affect the name or character typed by a key.
        # This complicated looking code is generating the powerset.
        modifiers_length_range = range(len(self.char_modifiers) + 1)
        modifiers_combinations_by_range = (
            itertools.combinations(sorted(self.char_modifiers), r) for r in modifiers_length_range
        )
        char_modifier_combinations = list(itertools.chain.from_iterable(modifiers_combinations_by_range))

        # List all keys by scan code, to cache their names. This cover all keys
        # except media and IME keys.
        for scan_code in range(0x01, 0x80):
            vk = user32.MapVirtualKeyW(scan_code, MAPVK_VSC_TO_VK_EX)
            if not vk:
                continue
            is_extended = (scan_code, vk) in self.prefer_extended_scan_codes
            key_input = KeyInput(scan_code, vk, is_extended, modifiers=())
            # Cache name.
            self.get_name_by_input(key_input)

            # For non-keypad keys, map what other characters they can type with
            # different modifiers.
            if not is_extended:
                for modifier_combination in char_modifier_combinations:
                    modified_input = key_input._replace(is_extended=False, modifiers=modifier_combination)
                    # Cache char.
                    self.get_char_by_input(modified_input)

        # Map the other keys that have only virtual key codes.
        for vk, ms_name in self.official_virtual_keys.items():
            scan_code = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX)
            if scan_code in self.scan_code_to_name:
                continue

            name = normalize_name(ms_name)
            self.scan_code_to_name[scan_code] = name
            self.scan_code_to_name[-vk] = name
            key_input = KeyInput(scan_code, vk, is_extended=False, modifiers=())
            self.name_to_inputs[name].append(key_input)

        for scan_code, vk, is_extended in self.numpad_keys:
            key_input = KeyInput(scan_code, vk, is_extended, ())
            # Cache name with extended flag.
            self.get_name_by_input(key_input)

            char = self.get_char_by_input(key_input)
            if char:
                # Manually cache "numpad N" versions.
                self.name_to_inputs["numpad " + char].append(key_input)

        # My alt gr has the VK of left control and an extremely high scan code.
        alt_gr_input = KeyInput(scan_code=541, vk=162, is_extended=False, modifiers=())
        self.input_to_char[alt_gr_input] = ""
        self.name_to_inputs["alt gr"].append(alt_gr_input)
        self.scan_code_to_name[alt_gr_input.scan_code] = "alt gr"

    def get_inputs_by_name(self, name):
        return self.name_to_inputs.get(name, [])

    def get_input_by_scan_code(self, scan_code):
        return self.name_to_inputs[self.scan_code_to_name[scan_code]][0]

    def get_name_by_input(self, key_input):
        """
        Given an input, returns what's the name of the key.
        """
        scan_code = self.input_to_scan_code(key_input)
        if scan_code in self.scan_code_to_name:
            return self.scan_code_to_name[scan_code]

        simplified_input = key_input._replace(modifiers=())
        char = self.get_char_by_input(simplified_input)
        if char:
            name = normalize_name(char)
        elif key_input.vk in self.official_virtual_keys:
            name = normalize_name(self.official_virtual_keys[key_input.vk])
        else:
            name = None

        if name and self.is_input_numpad(key_input):
            name = "numpad " + name

        self.scan_code_to_name[scan_code] = name
        self.name_to_inputs[name].append(simplified_input)
        return name

    def is_input_numpad(self, key_input):
        return (key_input.scan_code, key_input.vk, key_input.is_extended) in self.numpad_keys

    def modifier_name_to_vk(self, modifier_name):
        return [vk for vk, name in self.official_virtual_keys.items() if modifier_name in name]

    def get_char_by_input(self, key_input):
        """
        Given information about a pressed key, returns what character it probably
        would have typed (e.g. 'shift+a' -> 'A'), or empty string '' if it's unknown
        or a control character.

        Since ToUnicode makes this function impure, values are heavily cached to
        minimize side-effects.
        """
        if self.non_char_modifiers & set(key_input.modifiers):
            # This key combination will not type anything.
            return ""

        simplified_input = key_input._replace(
            modifiers=tuple(m for m in key_input.modifiers if m in self.char_modifiers)
        )
        if simplified_input in self.input_to_char:
            # We found the typed character cache when unnecessary modifiers are ignored.
            return self.input_to_char[simplified_input]

        # Buffers used during naming initialization. Created once and reused.
        unicode_buffer = ctypes.create_unicode_buffer(32)
        keyboard_state = keyboard_state_type()

        keyboard_state[0x10] = 0x80 * ("shift" in key_input.modifiers)
        keyboard_state[0x11] = 0x80 * ("alt gr" in key_input.modifiers)
        keyboard_state[0x12] = 0x80 * ("alt gr" in key_input.modifiers)
        keyboard_state[0x14] = 0x01 * ("caps lock" in key_input.modifiers)
        keyboard_state[0x90] = 0x01 * ("num lock" in key_input.modifiers)
        unicode_ret = ToUnicode(
            key_input.vk, key_input.scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0
        )
        if unicode_ret and unicode_buffer.value:
            char = unicode_buffer.value

            # unicode_ret == -1 -> is dead key, but currently we don't keep track of that.

            # ToUnicode has the side effect of setting global flags for dead keys.
            # Therefore we need to call it twice to clear those flags.
            # If your 6 and 7 keys are named "^6" and "^7", this is the reason.
            ToUnicode(key_input.vk, key_input.scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)
        else:
            char = ""

        self.input_to_char[simplified_input] = char
        if char:
            self.name_to_inputs[normalize_name(char)].append(simplified_input)
        return char

    def input_to_scan_code(self, key_input):
        if self.is_input_numpad(key_input) or not key_input.scan_code:
            # Force -vk for numpad items so that numpad differences are visible
            # in upper levels of the library.
            return -key_input.vk
        else:
            return key_input.scan_code


key_mapper = None

# Called by keyboard/__init__.py
def init():
    global key_mapper
    key_mapper = KeyMapper()


# Maps Windows' event types to this libraries types.
keyboard_event_types = {
    WM_KEYDOWN: KEY_DOWN,
    WM_KEYUP: KEY_UP,
    WM_SYSKEYDOWN: KEY_DOWN,
    WM_SYSKEYUP: KEY_UP,
}


class Listener(object):
    def __init__(self):
        self.shift_is_pressed = False
        self.altgr_is_pressed = False
        self.win_is_pressed = False
        self.ignore_next_right_alt = False
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

        def process_key(event_type, vk, scan_code, is_extended):
            # Pressing alt-gr also generates an extra "menu" event
            if vk in key_mapper.modifier_name_to_vk("menu") and self.ignore_next_right_alt:
                self.ignore_next_right_alt = False
                return True

            modifiers = tuple(
                sorted(
                    ("shift",) * self.shift_is_pressed
                    + ("alt gr",) * self.altgr_is_pressed
                    + ("windows",) * self.win_is_pressed
                    + ("num lock",) * (user32.GetKeyState(key_mapper.modifier_name_to_vk("num lock")[0]) & 1)
                    + ("caps lock",) * (user32.GetKeyState(key_mapper.modifier_name_to_vk("caps lock")[0]) & 1)
                    + ("scroll lock",) * (user32.GetKeyState(key_mapper.modifier_name_to_vk("scroll lock")[0]) & 1)
                )
            )

            key_input = KeyInput(scan_code, vk, is_extended, modifiers)
            name = key_mapper.get_name_by_input(key_input)
            char = key_mapper.get_char_by_input(key_input)

            # TODO: inaccurate when holding multiple different shifts.
            if vk in key_mapper.modifier_name_to_vk("shift"):
                self.shift_is_pressed = event_type == KEY_DOWN
            if vk in key_mapper.modifier_name_to_vk("windows"):
                self.win_is_pressed = event_type == KEY_DOWN
            if scan_code == 541 and vk == 162:
                self.ignore_next_right_alt = True
                self.altgr_is_pressed = event_type == KEY_DOWN

            scan_code = key_mapper.input_to_scan_code(key_input)

            is_numpad = key_mapper.is_input_numpad(key_input)
            # print(name, char, scan_code, key_mapper.is_input_numpad(key_input), key_input)
            return callback(
                KeyboardEvent(
                    event_type=event_type,
                    scan_code=scan_code,
                    name=name,
                    char=char,
                    is_numpad=is_numpad,
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
    if not key_mapper:
        init()

    key_inputs = key_mapper.get_inputs_by_name(name)
    if not key_inputs:
        raise ValueError("Key name {} is not mapped to any known key.".format(repr(name)))
    for key_input in key_inputs:
        yield key_mapper.input_to_scan_code(key_input), key_input.modifiers


def _send_event(code, event_type_flag):
    if not key_mapper:
        init()

    if code == 541:
        # Alt-gr is made of ctrl+alt. Just sending even 541 doesn't do anything.
        user32.keybd_event(0x11, 0, event_type_flag, 0)
        user32.keybd_event(0x12, 0, event_type_flag, 0)
    else:
        key_input = key_mapper.get_input_by_scan_code(code)
        user32.keybd_event(key_input.vk, key_input.scan_code, key_input.is_extended | event_type_flag, 0)


def list_available_keys():
    if not key_mapper:
        init()

    return {
        name: set(key_mapper.input_to_scan_code(key_input) for key_input in key_inputs)
        for name, key_inputs in key_mapper.name_to_inputs.items()
    }


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
    init()
    from pprint import pprint

    pprint(key_mapper.name_to_inputs)
    # listen(lambda e: print(e.to_json()) or True)
