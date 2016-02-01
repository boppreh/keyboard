import time

import platform
if platform.system() == 'Windows':
    import keyboard.winmouse as os_mouse
else:
    import keyboard.nixmouse as os_mouse

from .mouse_event import ButtonEvent, MoveEvent, WheelEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE
from .generic import GenericListener

listening = False

_pressed_events = set()
class MouseListener(GenericListener):
    def callback(self, event):
        if isinstance(event, ButtonEvent):
            if event.type in (UP, DOUBLE):
                _pressed_events.discard(event.button)
            elif event.type == DOWN:
                _pressed_events.add(event.button)

        return self.invoke_handlers(event)

    def listen(self):
        os_mouse.listen(self.callback)

listener = MouseListener()

@listener.wrap
def is_pressed(button=LEFT):
    """ Returns True if the given button is currently pressed. """
    return button in _pressed_events

@listener.wrap
def press(button=LEFT):
    """ Presses the given button (but doesn't release). """
    os_mouse.press(button)

@listener.wrap
def release(button=LEFT):
    """ Releases the given button. """
    os_mouse.release(button)

@listener.wrap
def click(button=LEFT):
    """ Sends a click with the given button. """
    os_mouse.press(button)
    os_mouse.release(button)

@listener.wrap
def double_click(button=LEFT):
    """ Sends a double click with the given button. """
    click(button)
    click(button)

@listener.wrap
def right_click():
    """ Sends a right click with the given button. """
    click(RIGHT)

@listener.wrap
def move(x, y, absolute=True, duration=0):
    """
    Moves the mouse. If `absolute`, to position (x, y), otherwise move relative
    to the current position. If `duration` is non-zero, animates the movement.
    """
    x = int(x)
    y = int(y)

    if duration:
        position_x, position_y = get_position()

        if not absolute:
            x = position_x + x
            y = position_y + y

        start_x = position_x
        start_y = position_y
        dx = x - start_x
        dy = y - start_y

        if dx == 0 and dy == 0:
            time.sleep(duration)
        else:
            # 120 movements per second.
            # Round and keep float to ensure float division in Python 2
            steps = max(1.0, float(int(duration * 120.0)))
            for i in range(int(steps)+1):
                move(start_x + dx*i/steps, start_y + dy*i/steps)
                time.sleep(duration/steps)
    else:
        if absolute:
            os_mouse.move_to(x, y)
        else:
            os_mouse.move_relative(x, y)

@listener.wrap
def on_button(callback, args=(), buttons=(LEFT, MIDDLE, RIGHT, X, X2), types=(UP, DOWN, DOUBLE)):
    """ Invokes `callback` with `args` when the specified event happens. """
    if not isinstance(buttons, (tuple, list)):
        buttons = (buttons,)
    if not isinstance(types, (tuple, list)):
        types = (types,)

    def handler(event):
        if isinstance(event, ButtonEvent):
            if event.type in types and event.button in buttons:
                callback(*args)
    listener.add_handler(handler)
    return handler

@listener.wrap
def on_click(callback, args=()):
    """ Invokes `callback` with `args` when the left button is clicked. """
    return on_button(callback, args, [LEFT], [UP])

@listener.wrap
def on_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [LEFT], [DOUBLE])

@listener.wrap
def on_right_click(callback, args=()):
    """ Invokes `callback` with `args` when the right button is clicked. """
    return on_button(callback, args, [RIGHT], [UP])

@listener.wrap
def on_middle_click(callback, args=()):
    """ Invokes `callback` with `args` when the middle button is clicked. """
    return on_button(callback, args, [MIDDLE], [UP])

@listener.wrap
def wait(button=LEFT, target_types=(UP, DOWN, DOUBLE)):
    """
    Blocks program execution until the given button performs an event.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    handler = on_button(lock.release, (), [button], target_types)
    lock.acquire()
    listener.remove_handler(handler)

@listener.wrap
def get_position():
    """ Returns the (x, y) mouse position. """
    return os_mouse.get_position()

if __name__ == '__main__':
    print('Move the cursor somewhere and left-click.')
    wait()
    move(100, 100, False)
    double_click()
    print(get_position())