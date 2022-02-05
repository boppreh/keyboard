# -*- coding: utf-8 -*-
import ctypes
import time
from ctypes import (
    c_short,
    c_char,
    c_uint8,
    c_int32,
    c_int,
    c_uint,
    c_uint32,
    c_long,
    byref,
    Structure,
    CFUNCTYPE,
    POINTER,
)
from ctypes.wintypes import DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM

LPMSG = POINTER(MSG)

import atexit

from ._mouse_event import (
    ButtonEvent,
    WheelEvent,
    MoveEvent,
    LEFT,
    RIGHT,
    MIDDLE,
    X,
    X2,
    UP,
    DOWN,
    DOUBLE,
    WHEEL,
    HORIZONTAL,
    VERTICAL,
)

# https://github.com/boppreh/mouse/issues/1
# user32 = ctypes.windll.user32
user32 = ctypes.WinDLL("user32", use_last_error=True)


class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("x", c_long),
        ("y", c_long),
        ("data", c_int32),
        ("reserved", c_int32),
        ("flags", DWORD),
        ("time", c_int),
    ]


LowLevelMouseProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(MSLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
# SetWindowsHookEx.argtypes = [c_int, LowLevelMouseProc, c_int, c_int]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
# CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(MSLLHOOKSTRUCT)]
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

buttons_by_wm_code = {
    WM_LBUTTONDOWN: (DOWN, LEFT),
    WM_LBUTTONUP: (UP, LEFT),
    WM_LBUTTONDBLCLK: (DOUBLE, LEFT),
    WM_RBUTTONDOWN: (DOWN, RIGHT),
    WM_RBUTTONUP: (UP, RIGHT),
    WM_RBUTTONDBLCLK: (DOUBLE, RIGHT),
    WM_MBUTTONDOWN: (DOWN, MIDDLE),
    WM_MBUTTONUP: (UP, MIDDLE),
    WM_MBUTTONDBLCLK: (DOUBLE, MIDDLE),
    WM_XBUTTONDOWN: (DOWN, X),
    WM_XBUTTONUP: (UP, X),
    WM_XBUTTONDBLCLK: (DOUBLE, X),
}

MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x1
MOUSEEVENTF_WHEEL = 0x800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_LEFTDOWN = 0x2
MOUSEEVENTF_LEFTUP = 0x4
MOUSEEVENTF_RIGHTDOWN = 0x8
MOUSEEVENTF_RIGHTUP = 0x10
MOUSEEVENTF_MIDDLEDOWN = 0x20
MOUSEEVENTF_MIDDLEUP = 0x40
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100

simulated_mouse_codes = {
    (WHEEL, HORIZONTAL): MOUSEEVENTF_HWHEEL,
    (WHEEL, VERTICAL): MOUSEEVENTF_WHEEL,
    (DOWN, LEFT): MOUSEEVENTF_LEFTDOWN,
    (UP, LEFT): MOUSEEVENTF_LEFTUP,
    (DOWN, RIGHT): MOUSEEVENTF_RIGHTDOWN,
    (UP, RIGHT): MOUSEEVENTF_RIGHTUP,
    (DOWN, MIDDLE): MOUSEEVENTF_MIDDLEDOWN,
    (UP, MIDDLE): MOUSEEVENTF_MIDDLEUP,
    (DOWN, X): MOUSEEVENTF_XDOWN,
    (UP, X): MOUSEEVENTF_XUP,
}

NULL = c_int(0)

WHEEL_DELTA = 120

init = lambda: None


def listen(queue):
    def low_level_mouse_handler(nCode, wParam, lParam):
        struct = lParam.contents
        # Can't use struct.time because it's usually zero.
        t = time.time()

        if wParam == WM_MOUSEMOVE:
            event = MoveEvent(struct.x, struct.y, t)
        elif wParam == WM_MOUSEWHEEL:
            event = WheelEvent(struct.data / (WHEEL_DELTA * (2 << 15)), t)
        elif wParam in buttons_by_wm_code:
            type, button = buttons_by_wm_code.get(wParam, ("?", "?"))
            if wParam >= WM_XBUTTONDOWN:
                button = {0x10000: X, 0x20000: X2}[struct.data]
            event = ButtonEvent(type, button, t)

        queue.put(event)
        return CallNextHookEx(NULL, nCode, wParam, lParam)

    WH_MOUSE_LL = c_int(14)
    mouse_callback = LowLevelMouseProc(low_level_mouse_handler)
    mouse_hook = SetWindowsHookEx(WH_MOUSE_LL, mouse_callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(UnhookWindowsHookEx, mouse_hook)

    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)


def _translate_button(button):
    if button == X or button == X2:
        return X, {X: 0x10000, X2: 0x20000}[button]
    else:
        return button, 0


def press(button=LEFT):
    button, data = _translate_button(button)
    code = simulated_mouse_codes[(DOWN, button)]
    user32.mouse_event(code, 0, 0, data, 0)


def release(button=LEFT):
    button, data = _translate_button(button)
    code = simulated_mouse_codes[(UP, button)]
    user32.mouse_event(code, 0, 0, data, 0)


def wheel(delta=1):
    code = simulated_mouse_codes[(WHEEL, VERTICAL)]
    user32.mouse_event(code, 0, 0, int(delta * WHEEL_DELTA), 0)


def move_to(x, y):
    user32.SetCursorPos(int(x), int(y))


def move_relative(x, y):
    user32.mouse_event(MOUSEEVENTF_MOVE, int(x), int(y), 0, 0)


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def get_position():
    point = POINT()
    user32.GetCursorPos(byref(point))
    return (point.x, point.y)


if __name__ == "__main__":

    def p(e):
        print(e)

    listen(p)
