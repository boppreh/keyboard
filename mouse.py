import time
try:
    from winmouse import listen, press, release, move_to, move_relative
except:
    from nixmouse import listen, press, release, move
from mouse_event import MouseEvent, MOVE, WHEEL, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, HORIZONTAL, DOUBLE
from generic import add_handler, remove_handler, start_listening

class _Position(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __repr__(self):
        return '({}, {})'.format(self.x, self.y)

# The current cursor position. The object is kept updated, not replaced.
position = _Position(0, 0)

_pressed_events = set()
def _update_state(event):
    position.x = event.x
    position.y = event.y
    if event.event_type in (UP, DOUBLE):
        _pressed_events.discard(event.event_type)
    elif event.event_type == DOWN:
        _pressed_events.add(event.event_type)

def click(button=LEFT):
    """ Sends a click with the given button. """
    press(button)
    release(button)

def double_click(button=LEFT):
    """ Sends a double click with the given button. """
    click(button)
    click(button)

def right_click():
    """ Sends a right click with the given button. """
    click(RIGHT)
    click(RIGHT)

def move(x, y, absolute=True, duration=0):
    """
    Moves the mouse. If `absolute`, to position (x, y), otherwise move relative
    to the current position. If `duration` is non-zero, animates the movement.
    """
    x = int(x)
    y = int(y)

    if duration:
        if not absolute:
            x = position.x + x
            y = position.y + y

        start_x = position.x
        start_y = position.y
        dx = x - start_x
        dy = y - start_y

        if dx == 0 and dy == 0:
            time.sleep(duration)
            return

        steps = 120
        for i in range(steps):
            move(start_x + dx*i/steps, start_y + dy*i/steps, absolute=absolute)
            time.sleep(duration/steps)
    else:
        if absolute:
            move_to(x, y)
            position.x = x
            position.y = y
        else:
            move_relative(x, y)
            position.x += x
            position.y += y

def on_button(callback, args=(), buttons=(LEFT, MIDDLE, RIGHT, X, X2), target_types=(UP, DOWN, DOUBLE)):
    """ Invokes `callback` with `args` when the specified event happens. """
    if not isinstance(buttons, (tuple, list)):
        buttons = (buttons,)
    if not isinstance(target_types, (tuple, list)):
        target_types = (target_types,)

    def handler(event):
        if event.event_type in target_types and event.arg in buttons:
            callback(*args)
    add_handler(handler)
    return handler

def on_click(callback, args=()):
    """ Invokes `callback` with `args` when the left button is clicked. """
    return on_button(callback, args, [LEFT], target_types=[DOWN])

def on_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [LEFT], target_types=[DOUBLE])

def on_right_click(callback, args=()):
    """ Invokes `callback` with `args` when the right button is clicked. """
    return on_button(callback, args, [RIGHT], target_types=[DOWN])

def on_middle_click(callback, args=()):
    """ Invokes `callback` with `args` when the middle button is clicked. """
    return on_button(callback, args, [MIDDLE], target_types=[DOWN])


def wait(button=LEFT, target_types=(UP, DOWN, DOUBLE)):
    """
    Blocks program execution until the given button performs an event.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    handler = on_button(lock.release, (), [button], target_types)
    lock.acquire()
    remove_handler(handler)

add_handler(_update_state)
start_listening(listen)

if __name__ == '__main__':
    wait()
    move(100, 100, True, 1)
    print(position)