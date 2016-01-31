#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name
import platform
if platform.system() == 'Windows':
    import winkeyboard as os_keyboard
else:
    import nixkeyboard as os_keyboard
    
from generic import GenericListener

_pressed_events = {}
class KeyboardListener(GenericListener):
    def callback(self, event):
        if event.event_type == KEY_UP:
            if event.scan_code in _pressed_events:
                del _pressed_events[event.scan_code]
        else:
            _pressed_events[event.scan_code] = event
        return self.invoke_handlers(event)

    def listen(self):
        os_keyboard.listen(self.callback)

listener = KeyboardListener()

def map_name_to_scancode(target_name):
    for scan_code, pairs in os_keyboard.scan_code_table.items():
        for name, is_shift in pairs:
            if name == target_name:
                return scan_code
    raise ValueError('Unknown name {}'.format(target_name))

@listener.wrap
def is_pressed(key):
    """ Returns True if the key (by name or code) is pressed. """
    if isinstance(key, int):
        return key in _pressed_events
    elif len(key) and '+' in key:
        return all(is_pressed(part) for part in key.split('+'))
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
@listener.wrap
def add_hotkey(hotkey, callback, args=(), blocking=True, timeout=1):
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

    # Just a dynamic object to store attributes for the `handler` closure.
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
                # Could be start of hotkey again.
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
    listener.add_handler(handler)
    return handler

@listener.wrap
def remove_hotkey(hotkey):
    """ Removes a previously registered hotkey. """
    listener.remove_handler(hotkeys[hotkey])

@listener.wrap
def write(text, delay=0):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Composite characters such as à are not available. Raises ValueError
    for unavailable characters.
    """
    for letter in text:
        scan_code, shift = os_keyboard.map_char(letter)
        if shift:
            send('shift', True, False)
        os_keyboard.press(scan_code)
        os_keyboard.release(scan_code)
        if shift:
            send('shift', False, True)
        if delay:
            time.sleep(delay)

@listener.wrap
def send(combination, do_press=True, do_release=True):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4, enter", "shift+s"
    """
    for step in _split_combination(combination):
        scan_codes = [map_name_to_scancode(normalize_name(part)) for part in step]

        if do_press:
            for scan_code in scan_codes:
                os_keyboard.press(scan_code)

        if do_release:
            for scan_code in scan_codes:
                os_keyboard.release(scan_code)

@listener.wrap
def press(combination):
    send(combination, True, False)

@listener.wrap
def release(combination):
    send(combination, False, True)

@listener.wrap
def wait(combination):
    """
    Blocks the program execution until a key combination is activated.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    hotkey_handler = add_hotkey(combination, lock.release)
    lock.acquire()
    listener.remove_handler(hotkey_handler)

@listener.wrap
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
        listener.remove_handler(stop_handler)
        listener.remove_handler(handler)
        lock.release()
    stop_handler = add_hotkey(until, stop)

    listener.add_handler(handler)
    lock.acquire()
    return recorded

@listener.wrap
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
            os_keyboard.press(event.scan_code)
        else:
            os_keyboard.release(event.scan_code)

if __name__ == '__main__':
    print('Press esc twice to replay keyboard actions.')
    play(record('esc, esc'), 3)
