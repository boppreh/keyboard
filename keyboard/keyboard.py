# -*- coding: utf-8 -*-
import time

import platform
if platform.system() == 'Windows':
    from. import winkeyboard as os_keyboard
else:
    from. import nixkeyboard as os_keyboard

from .keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name    
from .generic import GenericListener

_pressed_events = {}
class KeyboardListener(GenericListener):
    def callback(self, event):
        if not event.scan_code:
            return

        if event.event_type == KEY_UP:
            if event.scan_code in _pressed_events:
                del _pressed_events[event.scan_code]
        else:
            _pressed_events[event.scan_code] = event
        return self.invoke_handlers(event)

    def listen(self):
        os_keyboard.listen(self.callback)

listener = KeyboardListener()

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

    `blocking` defines if the system should block processing other hotkeys
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

        timed_out = state.step > 0 and timeout and event.time - state.time > timeout
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

def add_abbreviation(src, dst):
    """
    Registers a hotkey that replaces one typed text with another. For example

        add_abbreviation('tm', '™')

    Replaces every "tm" followed by a space with a ™ symbol.
    """
    return add_hotkey(', '.join(src + ' '), lambda: write('\b'*(len(src)+1) + dst), timeout=0)

remove_abbreviation = remove_hotkey

@listener.wrap
def write(text, delay=0):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Characters not available on the keyboard are typed as explicit unicode
    characters using OS-specific functionality, such as alt+codepoint.

    Delay is a number of seconds to wait between keypresses.
    """
    for letter in text:
        try:
            if letter in '\n\b\t ':
                letter = normalize_name(letter)
            scan_code, shifted = os_keyboard.map_char(letter)

            if shifted:
                send('shift', True, False)

            os_keyboard.press(scan_code)
            os_keyboard.release(scan_code)

            if shifted:
                send('shift', False, True)
        except ValueError:
            os_keyboard.type_unicode(letter)

        if delay:
            time.sleep(delay)

@listener.wrap
def send(combination, do_press=True, do_release=True):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4, enter", "shift+s"
    """
    for step in _split_combination(combination):
        scan_codes = [os_keyboard.map_char(normalize_name(part))[0] for part in step]

        if do_press:
            for scan_code in scan_codes:
                os_keyboard.press(scan_code)

        if do_release:
            for scan_code in reversed(scan_codes):
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
def record(until='escape'):
    """
    Records and returns all keyboard events until the user presses the given
    key combination.
    """
    recorded = []
    listener.add_handler(recorded.append)
    wait(until)
    listener.remove_handler(recorded.append)
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

def get_typed_strings(events, allow_backspace=True):
    """
    Given a sequence of events, tries to deduce what strings were typed.
    Strings are separated when an unencodable key is pressed (such as tab
    or enter). Characters are converted to uppercase according to shift
    and capslock status. If `allow_backspace` is True, backspaces remove the
    last character typed.

    get_type_strings(record()) -> ['', 'This is what', 'I recorded', '']
    """
    shift_pressed = False
    capslock_pressed = False
    strings = ['']
    for event in events:
        if event.matches('shift'):
            shift_pressed = event.event_type == 'down'
        elif event.matches('caps lock') and event.event_type == 'down':
            capslock_pressed = not capslock_pressed
        elif event.matches('backspace') and event.event_type == 'down':
            strings[-1] = strings[-1][:-1]
        elif event.event_type == 'down':
            if len(event.name) == 1:
                single_char = event.name
                if shift_pressed ^ capslock_pressed:
                    single_char = single_char.upper()
                strings[-1] = strings[-1] + single_char
            else:
                strings.append('')
    return strings


if __name__ == '__main__':
	add_abbreviation('tm', '™')
	input()
    #print('Press esc twice to replay keyboard actions.')
    #play(record('esc, esc'), 3)
