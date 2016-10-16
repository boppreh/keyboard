# -*- coding: utf-8 -*-
import struct
from subprocess import check_output
import re
from ._nixcommon import EV_KEY, EV_REL, EV_MSC, EV_SYN, EV_ABS, aggregate_devices
from ._mouse_event import ButtonEvent, WheelEvent, MoveEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN

import ctypes
import ctypes.util
from ctypes import c_uint32, c_uint, c_int, byref

x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library('X11'))
# Required because we will have multiple threads calling x11,
# such as the listener thread and then main using "move_to".
x11.XInitThreads()
display = x11.XOpenDisplay(None)
# Known to cause segafult in Fedora 23 64bits
# http://stackoverflow.com/questions/35137007/get-mouse-position-on-linux-pure-python
window = x11.XDefaultRootWindow(display)

def get_position():
    root_id, child_id = c_uint32(), c_uint32()
    root_x, root_y, win_x, win_y = c_int(), c_int(), c_int(), c_int()
    mask = c_uint()
    ret = x11.XQueryPointer(display, c_uint32(window), byref(root_id), byref(child_id),
                            byref(root_x), byref(root_y),
                            byref(win_x), byref(win_y), byref(mask))
    return root_x.value, root_y.value

def move_to(x, y):
    x11.XWarpPointer(display, None, window, 0, 0, 0, 0, x, y)
    x11.XFlush(display)

REL_X = 0x00
REL_Y = 0x01
REL_Z = 0x02
REL_HWHEEL = 0x06
REL_WHEEL = 0x08

ABS_X = 0x00
ABS_Y = 0x01

BTN_MOUSE = 0x110
BTN_LEFT = 0x110
BTN_RIGHT = 0x111
BTN_MIDDLE = 0x112
BTN_SIDE = 0x113
BTN_EXTRA = 0x114

button_by_code = {
    BTN_LEFT: LEFT,
    BTN_RIGHT: RIGHT,
    BTN_MIDDLE: MIDDLE,
    BTN_SIDE: X,
    BTN_EXTRA: X2,
}
code_by_button = {button: code for code, button in button_by_code.items()}
    
    
device = aggregate_devices('mouse')

def listen(callback):
    while True:
        time, type, code, value = device.read_event()
        if type == EV_SYN or type == EV_MSC:
            continue

        event_type = None
        arg = None

        if type == EV_KEY:
            event = ButtonEvent(DOWN if value else UP, button_by_code.get(code, '?'))
        elif type == EV_REL:
            value, = struct.unpack('i', struct.pack('I', value))

            if code == REL_WHEEL:
                event = WheelEvent(value)
            elif code in (REL_X, REL_Y):
                event = MoveEvent(*get_position())
        
        if event is None:
            # Unknown event type.
            continue
            
        callback(event)

def press(button=LEFT):
    device.write_event(EV_KEY, code_by_button[button], 0x01)

def release(button=LEFT):
    device.write_event(EV_KEY, code_by_button[button], 0x00)

def move_relative(x, y):
    # Note relative events are not in terms of pixels, but millimeters.
    if x < 0:
        x += 2**32
    if y < 0:
        y += 2**32
    device.write_event(EV_REL, REL_X, x)
    device.write_event(EV_REL, REL_Y, y)

def wheel(delta=1):
    if delta < 0:
        delta += 2**32
    device.write_event(EV_REL, REL_WHEEL, delta)
    

if __name__ == '__main__':
    #listen(print)
    move_to(100, 200)
