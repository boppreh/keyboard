import time
import platform
if platform.system() == 'Windows':
    import winmouse as os_mouse
else:
    import nixmouse as os_mouse
from mouse_event import MouseEvent, MOVE, WHEEL, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, HORIZONTAL, DOUBLE

from generic import GenericListener

listening = False

_pressed_events = set()
class MouseListener(GenericListener):
    def callback(self, event):
        if event.event_type in (UP, DOUBLE):
            _pressed_events.discard(event.arg)
        elif event.event_type == DOWN:
            _pressed_events.add(event.arg)

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
    os_mouse.press(button)

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
            return

        steps = 120.0
        for i in range(int(steps)):
            move(start_x + dx*i/steps, start_y + dy*i/steps)
            time.sleep(duration/steps)
    else:
        if absolute:
            os_mouse.move_to(x, y)
        else:
            os_mouse.move_relative(x, y)

@listener.wrap
def on_button(callback, args=(), buttons=(LEFT, MIDDLE, RIGHT, X, X2), target_types=(UP, DOWN, DOUBLE)):
    """ Invokes `callback` with `args` when the specified event happens. """
    if not isinstance(buttons, (tuple, list)):
        buttons = (buttons,)
    if not isinstance(target_types, (tuple, list)):
        target_types = (target_types,)

    def handler(event):
        if event.event_type in target_types and event.arg in buttons:
            callback(*args)
    listener.add_handler(handler)
    return handler

@listener.wrap
def on_click(callback, args=()):
    """ Invokes `callback` with `args` when the left button is clicked. """
    return on_button(callback, args, [LEFT], target_types=[DOWN])

@listener.wrap
def on_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [LEFT], target_types=[DOUBLE])

@listener.wrap
def on_right_click(callback, args=()):
    """ Invokes `callback` with `args` when the right button is clicked. """
    return on_button(callback, args, [RIGHT], target_types=[DOWN])

@listener.wrap
def on_middle_click(callback, args=()):
    """ Invokes `callback` with `args` when the middle button is clicked. """
    return on_button(callback, args, [MIDDLE], target_types=[DOWN])

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
    move(10, 10, False, 1)
    double_click()
    print(get_position())