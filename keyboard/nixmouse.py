import struct
from subprocess import check_output
import re
from .nixcommon import EventDevice, EV_KEY, EV_REL, EV_MSC, EV_SYN
from .mouse_event import ButtonEvent, WheelEvent, MoveEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN

REL_X = 0x00
REL_Y = 0x01
REL_Z = 0x02
REL_HWHEEL = 0x06
REL_WHEEL = 0x08

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

class X11Mouse(object):
    def __init__(self):
        self._device_id = None

    @property
    def device_id(self):
        if self._device_id is None:
            output = check_output('xinput').decode('utf-8')
            self._device_id = re.search(r'Mouse\s+id=(\d+)', output).group(1)
        return self._device_id

    def get_position(self):
        state = check_output(['xinput', '--query-state', self.device_id]).decode('utf-8')
        pattern = r'valuator\[0\]=(\d+)\n\s*valuator\[1\]=(\d+)'
        str_x, str_y = re.search(pattern, state, re.MULTILINE).groups(1)
        return (int(str_x), int(str_y))
    
    
x11mouse = X11Mouse()
from glob import glob
paths = glob('/dev/input/by-id/*-event-mouse')
if paths:
    device = EventDevice(paths[0])
else:
    device = None

def get_position():
    return x11mouse.get_position()

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
                if code == REL_X:
                    event = MoveEvent(value, 0)
                elif code == REL_Y:
                    event = MoveEvent(0, value)
        
        if event is None:
            # Unknown event type.
            continue
            
        callback(event)

def press(button=LEFT):
    device.write_event(EV_KEY, code_by_button[button], 0x01)

def release(button=LEFT):
    device.write_event(EV_KEY, code_by_button[button], 0x00)

def move_relative(x, y):
    if x < 0:
        x += 2**32
    if y < 0:
        y += 2**32
    device.write_event(EV_REL, REL_X, x)
    device.write_event(EV_REL, REL_Y, y)

def move_to(x, y):
    # We can try to calculate the target position, but because of acceleration
    # there's no way to be sure of the destination.
    #cur_x, cur_y = get_position()
    #move_relative(x - cur_x, y - cur_y)
    raise NotImplementedError('Absolute mouse movement not available at the moment.')

def wheel(delta=1):
    if delta < 0:
        delta += 2**32
    device.write_event(EV_REL, REL_WHEEL, delta)
    

if __name__ == '__main__':
    listen(print)