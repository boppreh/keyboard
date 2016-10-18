# -*- coding: utf-8 -*-
import time as _time

import platform as _platform
if _platform.system() == 'Windows':
    from. import _winmouse as _os_mouse
else:
    from. import _nixmouse as _os_mouse

from ._mouse_event import ButtonEvent, MoveEvent, WheelEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE
from ._generic import GenericListener as _GenericListener

_pressed_events = set()
class _MouseListener(_GenericListener):
    def callback(self, event):
        if isinstance(event, ButtonEvent):
            if event.event_type in (UP, DOUBLE):
                _pressed_events.discard(event.button)
            elif event.event_type == DOWN:
                _pressed_events.add(event.button)

        return self.invoke_handlers(event)

    def listen(self):
        _os_mouse.listen(self.callback)

_listener = _MouseListener()

def is_pressed(button=LEFT):
    """ Returns True if the given button is currently pressed. """
    _listener.start_if_necessary()
    return button in _pressed_events

def press(button=LEFT):
    """ Presses the given button (but doesn't release). """
    _os_mouse.press(button)

def release(button=LEFT):
    """ Releases the given button. """
    _os_mouse.release(button)

def click(button=LEFT):
    """ Sends a click with the given button. """
    _os_mouse.press(button)
    _os_mouse.release(button)

def double_click(button=LEFT):
    """ Sends a double click with the given button. """
    click(button)
    click(button)

def right_click():
    """ Sends a right click with the given button. """
    click(RIGHT)

def move(x, y, absolute=True, duration=0):
    """
    Moves the mouse. If `absolute`, to position (x, y), otherwise move relative
    to the current position. If `duration` is non-zero, animates the movement.
    """
    x = int(x)
    y = int(y)

    # Requires an extra system call on Linux, but `move_relative` is measured
    # in millimiters so we would lose precision.
    position_x, position_y = get_position()

    if not absolute:
        x = position_x + x
        y = position_y + y

    if duration:
        start_x = position_x
        start_y = position_y
        dx = x - start_x
        dy = y - start_y

        if dx == 0 and dy == 0:
            _time.sleep(duration)
        else:
            # 120 movements per second.
            # Round and keep float to ensure float division in Python 2
            steps = max(1.0, float(int(duration * 120.0)))
            for i in range(int(steps)+1):
                move(start_x + dx*i/steps, start_y + dy*i/steps)
                _time.sleep(duration/steps)
    else:
        _os_mouse.move_to(x, y)

def on_button(callback, args=(), buttons=(LEFT, MIDDLE, RIGHT, X, X2), types=(UP, DOWN, DOUBLE)):
    """ Invokes `callback` with `args` when the specified event happens. """
    if not isinstance(buttons, (tuple, list)):
        buttons = (buttons,)
    if not isinstance(types, (tuple, list)):
        types = (types,)

    def handler(event):
        if isinstance(event, ButtonEvent):
            if event.event_type in types and event.button in buttons:
                callback(*args)
    _listener.add_handler(handler)
    return handler

def on_click(callback, args=()):
    """ Invokes `callback` with `args` when the left button is clicked. """
    return on_button(callback, args, [LEFT], [UP])

def on_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [LEFT], [DOUBLE])

def on_right_click(callback, args=()):
    """ Invokes `callback` with `args` when the right button is clicked. """
    return on_button(callback, args, [RIGHT], [UP])

def on_middle_click(callback, args=()):
    """ Invokes `callback` with `args` when the middle button is clicked. """
    return on_button(callback, args, [MIDDLE], [UP])

def wait(button=LEFT, target_types=(UP, DOWN, DOUBLE)):
    """
    Blocks program execution until the given button performs an event.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    handler = on_button(lock.release, (), [button], target_types)
    lock.acquire()
    _listener.remove_handler(handler)

def get_position():
    """ Returns the (x, y) mouse position. """
    _listener.start_if_necessary()
    return _os_mouse.get_position()

def hook(callback):
    """
    Installs a global listener on all available mouses, invoking `callback`
    each time it is moved, a key status changes or the wheel is spun. A mouse
    event is passed as argument, with type either `mouse.ButtonEvent`,
    `mouse.WheelEvent` or `mouse.MoveEvent`.
    
    Returns the given callback for easier development.
    """
    _listener.add_handler(callback)
    return callback

def unhook(callback):
    """
    Removes a previously installed hook.
    """
    _listener.remove_handler(callback)

def unhook_all():
    """
    Removes all hooks registered by this application. Note this may include
    hooks installed by high level functions, such as `record`.
    """
    _listener.handlers.clear()

def record(button=MIDDLE):
    """
    Records all mouse events until the user presses the given button.
    Then returns the list of events recorded. Pairs well with `play(events)`.

    Note: this is a blocking function.
    Note: for more details on the mouse hook and events see `hook`.
    """
    recorded = []
    hook(recorded.append)
    wait(button)
    unhook(recorded.append)
    return recorded

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is <= 0 then the actions are replayed as fast
    as the OS allows. Pairs well with `record()`.
    """
    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            _time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        if isinstance(event, ButtonEvent):
            if event.event_type == UP:
                _os_mouse.release(event.button)
            else:
                _os_mouse.press(event.button)
        elif isinstance(event, MoveEvent):
            _os_mouse.move_to(event.x, event.y)
        elif isinstance(event, WheelEvent):
            _os_mouse.wheel(event.delta)

if __name__ == '__main__':
    print('Recording... Press middle button to stop and replay.')
    print(play(record()))
