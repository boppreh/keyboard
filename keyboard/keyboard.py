# -*- coding: utf-8 -*-
import time
from threading import Lock, Thread

import platform
if platform.system() == 'Windows':
    from. import winkeyboard as os_keyboard
else:
    from. import nixkeyboard as os_keyboard

from .keyboard_event import KEY_DOWN, KEY_UP, normalize_name    
from .generic import GenericListener

all_modifiers = ('alt', 'alt gr', 'ctrl', 'shift', 'win')

_pressed_events = {}
class _KeyboardListener(GenericListener):
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
_listener = _KeyboardListener()

def is_pressed(key):
    """
    Returns True if the key is pressed.

        is_pressed(57) -> True
        is_pressed('space') -> True
        is_pressed('ctrl+space') -> True
    """
    _listener.start_if_necessary()
    if isinstance(key, int):
        return key in _pressed_events
    elif len(key) and '+' in key:
        parts = _split_combination(key)
        if len(parts) > 1:
            raise ValueError('Cannot check status of multi-step combination ({}).'.format(key))
        return all(is_pressed(part) for part in parts[0])
    else:
        for event in _pressed_events.values():
            if event.matches(key):
                return True
        return False

def _split_combination(hotkey):
    """
    Splits a user provided hotkey into a list of steps, each one made of a list
    of key descriptions (name or scan code). Used to normalize input at the API
    boundary. When a combo is given (e.g. 'ctrl + a, b') spaces are ignored.

        _split_combination(57) -> [[57]]
        _split_combination('space') -> [[57]]
        _split_combination('ctrl+space') -> [[97, 57]]
        _split_combination('ctrl+space, space') -> [[97, 57], [57]]
    """
    if isinstance(hotkey, int):
        return [[hotkey]]
    else:
        combination = []
        for step in hotkey.replace(' ', '').split(','):
            combination.append([])
            for part in step.split('+'):
                scan_code, modifiers = os_keyboard.map_char(normalize_name(part))
                combination[-1].append(scan_code)
        return combination

def call_later(fn, args=(), delay=0.001):
    """
    Calls the provided function in a new thread after waiting some time.
    Useful for giving the system some time to process an event, without blocking
    the current execution flow.
    """
    Thread(target=lambda: time.sleep(delay) or fn(*args)).start()

_hotkeys = {}
def clear_all_hotkeys():
    """
    Removes all hotkey handlers. Note some functions such as 'wait' and 'record'
    internally use hotkeys and will be affected by this call.

    Abbreviations and word listeners are not hotkeys and therefore not affected.  
    To remove all hooks use `unhook_all()`.
    """
    global _hotkeys
    for handler in _hotkeys.values():
        unhook(handler)
    _hotkeys = {}

def add_hotkey(hotkey, callback, args=(), blocking=True, timeout=1):
    """
    Adds a hotkey handler that invokes callback each time the hotkey is
    detected. Returns a handler that can be used to unregister it later. The
    hotkey must be in the format "ctrl+shift+a, s". This would trigger when the
    user presses "ctrl+shift+a", releases, and then presses "s". To represent
    literal commas, pluses and spaces use their names ('comma', 'plus',
    'space').

    `blocking` defines if the system should block processing other hotkeys
    after a match is found. This feature is Windows-only.

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
                    # Leave some time for Windows to process the last key.
                    call_later(callback, args)
                    return blocking

    _hotkeys[hotkey] = handler
    return hook(handler)

# Alias.
register_hotkey = add_hotkey

def hook(callback):
    """
    Installs a global listener on all available keyboards, invoking `callback`
    each time a key is pressed or released. An event object is supplied, with
    type `keyboard.keyboard_event.KeyboardEvent` and attributes `name`
    (an Unicode representation of the character (e.g. "&") or description (e.g.
    "space")), `scan_code` (number representing the physical key) and `time`
    (Unix timestamp).
    """
    _listener.add_handler(callback)
    return callback

def unhook(callback):
    """ Removes a previously hooked callback. """
    _listener.remove_handler(callback)

def unhook_all():
    """
    Removes all keyboard hooks in use, including hotkeys, abbreviations, word
    listeners, recorders and 'wait's.
    """
    global _hotkeys
    _hotkeys = {}
    global _word_listeners
    _word_listeners = {}
    _listener.handlers.clear()

def hook_key(key, keydown_callback=lambda: None, keyup_callback=lambda: None):
    """
    Hooks key up and down events for a given key, no hotkeys combos.
    """
    def handler(event):
        if not event.matches(key):
            return

        if event.event_type == KEY_DOWN:
            keydown_callback()
        if event.event_type == KEY_UP:
            keyup_callback()

    _hotkeys[key] = handler
    return hook(handler)

def remove_hotkey(hotkey):
    """ Removes a previously registered hotkey. """
    if callable(hotkey):
        unhook(hotkey)
    else:
        unhook(_hotkeys[hotkey])

_word_listeners = {}
def add_word_listener(word, callback, triggers=['space'], match_suffix=False, timeout=2):
    """
    Invokes a callback every time a sequence of characters is typed and followed
    by a trigger key (e.g. space). Modifiers (e.g. alt, ctrl, shift) are
    ignored.

    - `word` the typed text to be matched. E.g. 'pet'.
    - `callback` is an argument-less function to be invoked each time the word
    is typed.
    - `triggers` is the list of keys that will cause a match to be checked. If
    the user presses some key that is not a character (len>1) and not in
    triggers, the match will be discarded. By default only space bar triggers
    match checks.
    - `match_suffix` defines if endings of words should be checked instead of
    only whole words. E.g. if True, typing 'carpet'+space will trigger the
    listener for 'pet'. Defaults False.
    - `timeout` is maximum number of seconds between typed characters before
    the current word is discarded. Defaults to 2 seconds.
    """
    if word in _word_listeners:
        raise ValueError('Already listening for word {}'.format(repr(word)))

    # Just a dynamic object to store attributes for the `handler` closure.
    state = lambda: None
    state.current = ''
    state.time = time.time()

    def handler(event):
        name = event.name
        if event.event_type == KEY_UP or name in all_modifiers: return

        matched = state.current == word or (match_suffix and state.current.endswith(word))
        if name in triggeres and matched:
            call_later(callback)
            state.current = ''
        elif len(name) > 1:
            state.current = ''
        else:
            if timeout and event.time - state.time > timeout:
                state.current = ''
            state.time = event.time
            state.current += name if not is_pressed('shift') else name.upper()

    _word_listeners[word] = hook(handler)
    return handler

def remove_word_listener(word):
    """
    Removes a previously instaled word listener hotkey. Works given both the
    word source text or the handler returned by `add_word_listener`.
    """
    if callable(word):
        unhook(word)
    else:
        unhook(_word_listeners[word])
        del _word_listeners[word]

def add_abbreviation(source_text, replacement_text, match_suffix=True, timeout=2):
    """
    Registers a hotkey that replaces one typed text with another. For example

        add_abbreviation('tm', u'™')

    Replaces every "tm" followed by a space with a ™ symbol. For details see
    `add_word_listener`.
    """
    replacement = '\b'*(len(source_text)+1) + replacement_text
    callback = lambda: write(replacement, restore_state_after=False)
    return add_word_listener(source_text, callback, match_suffix=match_suffix, timeout=timeout)

# Aliases.
register_word_listener = add_word_listener
register_abbreviation = add_abbreviation
remove_abbreviation = remove_word_listener

def stash_state():
    """
    Builds a list of all currently pressed scan codes, releases them and returns
    the list. Pairs well with `restore_state`.
    """
    state = sorted(_pressed_events)
    for scan_code in state:
        os_keyboard.release(scan_code)
    return state

def restore_state(scan_codes):
    """
    Given a list of scan_codes ensures these keys, and only these keys, are
    pressed.
    """
    current = set(_pressed_events)
    target = set(scan_codes)
    for scan_code in current - target:
        os_keyboard.release(scan_code)
    for scan_code in target - current:
        os_keyboard.press(scan_code)

def write(text, delay=0, restore_state_after=True):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Characters not available on the keyboard are typed as explicit unicode
    characters using OS-specific functionality, such as alt+codepoint.

    Delay is a number of seconds to wait between keypresses.
    """
    state = stash_state()

    for letter in text:
        try:
            if letter in '\n\b\t ':
                letter = normalize_name(letter)
            scan_code, modifiers = os_keyboard.map_char(letter)

            if is_pressed(scan_code):
                release(scan_code)

            for modifier in modifiers:
                press(modifier)

            os_keyboard.press(scan_code)
            os_keyboard.release(scan_code)

            for modifier in modifiers:
                release(modifier)
        except ValueError:
            os_keyboard.type_unicode(letter)

        if delay:
            time.sleep(delay)

    if restore_state_after:
        restore_state(state)

def send(combination, do_press=True, do_release=True):
    """
    Performs a given hotkey combination.

    Ex: "ctrl+alt+del", "alt+F4, enter", "shift+s"
    """
    for scan_codes in _split_combination(combination):
        if do_press:
            for scan_code in scan_codes:
                os_keyboard.press(scan_code)

        if do_release:
            for scan_code in reversed(scan_codes):
                os_keyboard.release(scan_code)

def press(combination):
    """ Presses and holds down the key combination. """
    send(combination, True, False)

def release(combination):
    """ Releases the key combination. """
    send(combination, False, True)

def press_and_release(combination):
    """ Presses and releases the key combination. """
    send(combination, True, True)

def wait(combination):
    """
    Blocks the program execution until a key combination is activated.
    """
    lock = Lock()
    lock.acquire()
    hotkey_handler = add_hotkey(combination, lock.release)
    lock.acquire()
    remove_hotkey(hotkey_handler)

def record(until='escape'):
    """
    Records and returns all keyboard events until the user presses the given
    key combination.
    """
    recorded = []
    hook(recorded.append)
    wait(until)
    unhook(recorded.append)

    return recorded

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is not positive (<= 0) the actions are replayed
    instantly.
    """
    state = stash_state()

    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        if event.event_type == KEY_DOWN:
            os_keyboard.press(event.scan_code)
        else:
            os_keyboard.release(event.scan_code)

    restore_state(state)

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
        elif allow_backspace and event.matches('backspace') and event.event_type == 'down':
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
    print('Press esc twice to replay keyboard actions.')
    play(record('esc, esc'), 3)
