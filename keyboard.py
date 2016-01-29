#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from threading import Thread
from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
try:
    from winkeyboard import listen, press, release, map_char
except:
    from nixkeyboard import listen, press, release, map_char

_pressed_events = {}
def _update_state(event):
    if event.event_type == KEY_UP:
        if event.scan_code in _pressed_events:
            del _pressed_events[event.scan_code]
    else:
        _pressed_events[event.scan_code] = event

handlers = [_update_state]

listening_thread = Thread(target=listen, args=(handlers,))
listening_thread.daemon=True
listening_thread.start()

def add_handler(handler):
    """ Adds a function to receive each keyboard event captured. """
    handlers.append(handler)

def remove_handler(handler):
    """ Removes a previously added keyboard event handler. """
    handlers.remove(handler)

def is_pressed(key):
    """ Returns True if the key (by name or code) is pressed. """
    if isinstance(key, int):
        return key in _pressed_events
    else:
        for event in _pressed_events.values():
            if event.matches(key):
                return True
        return False

def _split_combination(hotkey):
    if isinstance(hotkey, int) or len(hotkey) == 1:
        return [[hotkey]]
    else:
        return [step.split('+') for step in hotkey.split(', ')]

hotkeys = {}
def register_hotkey(hotkey, callback, args=(), blocking=True, timeout=1):
    """
    Adds a hotkey handler that invokes callback each time the hotkey is
    detected. Returns a handler that can be used to unregister it later. The
    hotkey must be in the format "ctrl+shift+a, s". This would trigger when the
    user presses "ctrl+shift+a", releases, and then presses "s".

    `blocking` defines if the system should continue processing other hotkeys
    after a match is found.

    `timeout` is the amount of time allowed to pass between key strokes before
    the combination state is reset.
    """
    steps = _split_combination(hotkey)

    state = lambda: None
    state.step = 0
    state.time = time.time()

    def handler(event):
        if event.event_type == KEY_UP:
            return

        timed_out = state.step > 0 and event.time - state.time > timeout
        unexpected = not any(event.matches(part) for part in steps[state.step])
        if unexpected or timed_out:
            if state.step > 0:
                state.step = 0
                handler(event)
            else:
                state.step = 0
        else:
            state.time = event.time
            if all(is_pressed(part) for part in steps[state.step]):
                state.step += 1
                if state.step == len(steps):
                    state.step = 0
                    callback(*args)
                    return blocking

    hotkeys[hotkey] = handler
    add_handler(handler)
    return handler

def unregister_hotkey(hotkey):
    """ Removes a previously registered hotkey. """
    remove_handler(hotkeys[hotkey])

def write(text, delay=0):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Composite characters such as à are not available. Raises ValueError
    for unavailable characters.
    """
    for letter in text:
        if letter.isupper():
            send('shift', True, False)
        send(letter)
        if letter.isupper():
            send('shift', False, True)
        if delay:
            time.sleep(delay)

def send(combination, press=True, release=True):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4, enter", "shift+s"
    """
    for step in _split_combination(combination):
        scan_codes = [map_name_to_scancode(normalize_name(part)) for part in step]

        if press:
            for scan_code in scan_codes:
                press(scan_code)

        if release:
            for scan_code in scan_codes:
                release(scan_code)

def wait(combination):
    """
    Blocks the program execution until a key combination is activated.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    hotkey_handler = register_hotkey(combination, lock.release)
    lock.acquire()
    remove_handler(hotkey_handler)

def record(until='escape', exclude=[]):
    """
    Records and returns all keyboard events until the user presses the given
    key combination.
    """
    from threading import Lock

    recorded = []
    lock = Lock()
    lock.acquire()

    def handler(event):
        recorded.append(event)

    def stop():
        remove_handler(stop_handler)
        remove_handler(handler)
        lock.release()
    stop_handler = register_hotkey(until, stop)

    add_handler(handler)
    lock.acquire()
    return recorded

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is invalid (<= 0) the actions are replayed
    instantly.
    """
    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        if event.event_type == KEY_DOWN:
            press(event.scan_code)
        else:
            release(event.scan_code)

if __name__ == '__main__':
    #print('Press esc twice to replay keyboard actions.')
    #play(record('esc, esc'), 3)
    print(record('esc'))