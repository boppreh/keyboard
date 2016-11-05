# -*- coding: utf-8 -*-
"""
keyboard
========

Take full control of your keyboard with this small Python library. Hook global events, register hotkeys, simulate key presses and much more.

- Global event hook on all keyboards (captures keys regardless of focus).
- **Listen** and **sends** keyboard events.
- Works with **Windows** and **Linux** (requires sudo).
- **Pure Python**, no C modules to be compiled.
- **Zero dependencies**. Trivial to install and deploy, just copy the files.
- **Python 2 and 3**.
- Complex hotkey support (e.g. `Ctrl+Shift+M, Ctrl+Space`) with controllable timeout.
- Includes **high level API** (e.g. [`record`](#keyboard.record) and [`play`](#keyboard.play), [`add_abbreviation`](#keyboard.add_abbreviation).
- Maps keys as they actually are in your layout, with **full internationalization support** (e.g. `Ctrl+ç`).
- Events automatically captured in separate thread, doesn't block main program.
- Tested and documented.
- Doesn't break accented dead keys (I'm looking at you, pyHook).
- Mouse support coming soon.

Example:

```
import keyboard

# Press PAGE UP then PAGE DOWN to type "foobar".
keyboard.add_hotkey('page up, page down', lambda: keyboard.write('foobar'))

keyboard.press_and_release('shift+s, space')

# Blocks until you press esc.
keyboard.wait('esc')
```

This program makes no attempt to hide itself, so don't use it for keyloggers.
"""

import time as _time
from threading import Lock as _Lock
from threading import Thread as _Thread
from ._keyboard_event import KeyboardEvent

try:
    basestring
except NameError:
    basestring = str

# Just a dynamic object to store attributes for the closures.
class _State(object): pass

import platform as _platform
if _platform.system() == 'Windows':
    from. import _winkeyboard as _os_keyboard
else:
    from. import _nixkeyboard as _os_keyboard

from ._keyboard_event import KEY_DOWN, KEY_UP
from ._keyboard_event import normalize_name as _normalize_name
from ._generic import GenericListener as _GenericListener

all_modifiers = ('alt', 'alt gr', 'ctrl', 'shift', 'win')

_pressed_events = {}
class _KeyboardListener(_GenericListener):
    def pre_process_event(self, event):
        if not event.scan_code:
            return False

        if event.event_type == KEY_UP:
            if event.scan_code in _pressed_events:
                del _pressed_events[event.scan_code]
        else:
            _pressed_events[event.scan_code] = event

        return True

    def listen(self):
        _os_keyboard.listen(self.queue)
_listener = _KeyboardListener()

def matches(event, name):
    """
    Returns True if the given event represents the same key as the one given in
    `name`.
    """
    if isinstance(name, int):
        return event.scan_code == int
    elif _os_keyboard.map_char(name) == event.scan_code:
        return True
    else:
        normalized = _normalize_name(name)
        return (
            normalized == event.name
            or 'left ' + normalized == event.name
            or 'right ' + normalized == event.name
        )

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
    elif len(key) > 1 and ('+' in key or ',' in key):
        parts = canonicalize(key)
        if len(parts) > 1:
            raise ValueError('Cannot check status of multi-step combination ({}).'.format(key))
        return all(is_pressed(part) for part in parts[0])
    else:
        for event in _pressed_events.values():
            if matches(event, key):
                return True
        return False

def canonicalize(hotkey):
    """
    Splits a user provided hotkey into a list of steps, each one made of a list
    of scan codes or names. Used to normalize input at the API boundary. When a
    combo is given (e.g. 'ctrl + a, b') spaces are ignored.

        canonicalize(57) -> [[57]]
        canonicalize([[57]]) -> [[57]]
        canonicalize('space') -> [['space']]
        canonicalize('ctrl+space') -> [['ctrl', 'space']]
        canonicalize('ctrl+space, space') -> [['ctrl', 'space'], ['space']]

    Note we must not convert names into scan codes because a name may represent
    more than one physical key (e.g. two 'ctrl' keys).
    """
    if isinstance(hotkey, list) and all(isinstance(step, list) for step in hotkey):
        # Already canonicalized, nothing to do.
        return hotkey
    elif isinstance(hotkey, int):
        return [[hotkey]]

    if not isinstance(hotkey, basestring):
        raise ValueError('Unexpected hotkey: {}. Expected int scan code, str key combination or normalized hotkey.'.format(hotkey))

    if len(hotkey) == 1 or ('+' not in hotkey and ',' not in hotkey):
        return [[_normalize_name(hotkey)]]
    else:
        steps = []
        for str_step in hotkey.replace(' ', '').split(','):
            steps.append([])
            for part in str_step.split('+'):
                steps[-1].append(_normalize_name(part))
        return steps

def call_later(fn, args=(), delay=0.001):
    """
    Calls the provided function in a new thread after waiting some time.
    Useful for giving the system some time to process an event, without blocking
    the current execution flow.
    """
    _Thread(target=lambda: _time.sleep(delay) or fn(*args)).start()

_hotkeys = {}
def clear_all_hotkeys():
    """
    Removes all hotkey handlers. Note some functions such as 'wait' and 'record'
    internally use hotkeys and will be affected by this call.

    Abbreviations and word listeners are not hotkeys and therefore not affected.  
    To remove all hooks use `unhook_all()`.
    """
    for handler in _hotkeys.values():
        unhook(handler)
    _hotkeys.clear()

# Alias.
remove_all_hotkeys = clear_all_hotkeys

def add_hotkey(hotkey, callback, args=(), blocking=True, timeout=1):
    """
    Invokes a callback every time a key combination is pressed. The hotkey must
    be in the format "ctrl+shift+a, s". This would trigger when the user holds
    ctrl, shift and "a" at once, releases, and then presses "s". To represent
    literal commas, pluses and spaces use their names ('comma', 'plus',
    'space').

    - `args` is an optional list of arguments to passed to the callback during
    each invocation.
    - `blocking` defines if the it should block processing other hotkeys after
    a match is found.
    - `timeout` is the amount of seconds allowed to pass between key presses

    The event handler function is returned. To remove a hotkey call
    `remove_hotkey(hotkey)` or `remove_hotkey(handler)`.
    before the combination state is reset.

    Note: hotkeys are activated when the last key is *pressed*, not released.
    Note: the callback is executed in a separate thread, asynchronously. For an
    example of how to use a callback synchronously, see `wait`.

        add_hotkey(57, print, args=['space was pressed'])
        add_hotkey(' ', print, args=['space was pressed'])
        add_hotkey('space', print, args=['space was pressed'])
        add_hotkey('Space', print, args=['space was pressed'])

        add_hotkey('ctrl+q', quit)
        add_hotkey('ctrl+alt+enter, space', some_callback)
    """
    steps = canonicalize(hotkey)

    state = _State()
    state.step = 0
    state.time = _time.time()

    def handler(event):
        if event.event_type == KEY_UP:
            return

        timed_out = state.step > 0 and timeout and event.time - state.time > timeout
        unexpected = not any(matches(event, part) for part in steps[state.step])

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

    _hotkeys[hotkey] = handler
    return hook(handler)

# Alias.
register_hotkey = add_hotkey

def hook(callback):
    """
    Installs a global listener on all available keyboards, invoking `callback`
    each time a key is pressed or released.
    
    The event passed to the callback is of type `keyboard.KeyboardEvent`,
    with the following attributes:

    - `name`: an Unicode representation of the character (e.g. "&") or
    description (e.g.  "space"). The name is always lower-case.
    - `scan_code`: number representing the physical key, e.g. 55.
    - `time`: timestamp of the time the event occurred, with as much precision
    as given by the OS.

    Returns the given callback for easier development.
    """
    _listener.add_handler(callback)
    return callback

def unhook(callback):
    """ Removes a previously hooked callback. """
    _listener.remove_handler(callback)

def unhook_all():
    """
    Removes all keyboard hooks in use, including hotkeys, abbreviations, word
    listeners, `record`ers and `wait`s.
    """
    _hotkeys.clear()
    _word_listeners.clear()
    del _listener.handlers[:]

def hook_key(key, keydown_callback=lambda: None, keyup_callback=lambda: None):
    """
    Hooks key up and key down events for a single key. Returns the event handler
    created. To remove a hooked key use `unhook_key(key)` or
    `unhook_key(handler)`.

    Note: this function shares state with hotkeys, so `clear_all_hotkeys`
    affects it aswell.
    """
    def handler(event):
        if not matches(event, key):
            return

        if event.event_type == KEY_DOWN:
            keydown_callback()
        if event.event_type == KEY_UP:
            keyup_callback()

    _hotkeys[key] = handler
    return hook(handler)

def on_press(callback):
    """
    Invokes `callback` for every KEY_DOWN event. For details see `hook`.
    """
    return hook(lambda e: e.event_type == KEY_DOWN and callback(e))

def on_release(callback):
    """
    Invokes `callback` for every KEY_UP event. For details see `hook`.
    """
    return hook(lambda e: e.event_type == KEY_UP and callback(e))

def _remove_named_hook(name_or_handler, names):
    """
    Removes a hook that was registered with a given name in a dictionary.
    """
    if callable(name_or_handler):
        handler = name_or_handler
        try:
            name = next(n for n, h in names.items() if h == handler)
        except StopIteration:
            raise ValueError('This handler is not associated with any name.')
        unhook(handler)
        del names[name]
    else:
        name = name_or_handler
        try:
            handler = names[name]
        except KeyError as e:
            raise ValueError('No such named listener: ' + repr(name), e)
        unhook(names[name])
        del names[name]

def remove_hotkey(hotkey_or_handler):
    """
    Removes a previously registered hotkey. Accepts either the hotkey used
    during registration (exact string) or the event handler returned by the
    `add_hotkey` or `hook_key` functions.
    """
    _remove_named_hook(hotkey_or_handler, _hotkeys)

# Alias.
unhook_key = remove_hotkey

_word_listeners = {}
def add_word_listener(word, callback, triggers=['space'], match_suffix=False, timeout=2):
    """
    Invokes a callback every time a sequence of characters is typed (e.g. 'pet')
    and followed by a trigger key (e.g. space). Modifiers (e.g. alt, ctrl,
    shift) are ignored.

    - `word` the typed text to be matched. E.g. 'pet'.
    - `callback` is an argument-less function to be invoked each time the word
    is typed.
    - `triggers` is the list of keys that will cause a match to be checked. If
    the user presses some key that is not a character (len>1) and not in
    triggers, the characters so far will be discarded. By default only space
    bar triggers match checks.
    - `match_suffix` defines if endings of words should also be checked instead
    of only whole words. E.g. if true, typing 'carpet'+space will trigger the
    listener for 'pet'. Defaults to false, only whole words are checked.
    - `timeout` is the maximum number of seconds between typed characters before
    the current word is discarded. Defaults to 2 seconds.

    Returns the event handler created. To remove a word listener use
    `remove_word_listener(word)` or `remove_word_listener(handler)`.

    Note: all actions are performed on key down. Key up events are ignored.
    Note: word mathes are **case sensitive**.
    """
    if word in _word_listeners:
        raise ValueError('Already listening for word {}'.format(repr(word)))

    state = _State()
    state.current = ''
    state.time = _time.time()

    def handler(event):
        name = event.name
        if event.event_type == KEY_UP or name in all_modifiers: return

        matched = state.current == word or (match_suffix and state.current.endswith(word))
        if name in triggers and matched:
            callback()
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

def remove_word_listener(word_or_handler):
    """
    Removes a previously registered word listener. Accepts either the word used
    during registration (exact string) or the event handler returned by the
    `add_word_listener` or `add_abbreviation` functions.
    """
    _remove_named_hook(word_or_handler, _word_listeners)

def add_abbreviation(source_text, replacement_text, match_suffix=True, timeout=2):
    """
    Registers a hotkey that replaces one typed text with another. For example

        add_abbreviation('tm', u'™')

    Replaces every "tm" followed by a space with a ™ symbol (and no space). The
    replacement is done by sending backspace events.

    - `match_suffix` defines if endings of words should also be checked instead
    of only whole words. E.g. if true, typing 'carpet'+space will trigger the
    listener for 'pet'. Defaults to false, only whole words are checked.
    - `timeout` is the maximum number of seconds between typed characters before
    the current word is discarded. Defaults to 2 seconds.
    
    For more details see `add_word_listener`.
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
        _os_keyboard.release(scan_code)
    return state

def restore_state(scan_codes):
    """
    Given a list of scan_codes ensures these keys, and only these keys, are
    pressed. Pairs well with `stash_state`.
    """
    current = set(_pressed_events)
    target = set(scan_codes)
    for scan_code in current - target:
        _os_keyboard.release(scan_code)
    for scan_code in target - current:
        _os_keyboard.press(scan_code)

def write(text, delay=0, restore_state_after=True):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Characters not available on the keyboard are typed as explicit unicode
    characters using OS-specific functionality, such as alt+codepoint.

    To ensure text integrity all currently pressed keys are released before
    the text is typed.

    - `delay` is the number of seconds to wait between keypresses, defaults to
    no delay.
    - `restore_state_after` can be used to restore the state of pressed keys
    after the text is typed, i.e. presses the keys that were released at the
    beginning. Defaults to True.
    """
    state = stash_state()

    for letter in text:
        try:
            if letter in '\n\b\t ':
                letter = _normalize_name(letter)
            scan_code, modifiers = _os_keyboard.map_char(letter)

            if is_pressed(scan_code):
                release(scan_code)

            for modifier in modifiers:
                press(modifier)

            _os_keyboard.press(scan_code)
            _os_keyboard.release(scan_code)

            for modifier in modifiers:
                release(modifier)
        except ValueError:
            _os_keyboard.type_unicode(letter)

        if delay:
            _time.sleep(delay)

    if restore_state_after:
        restore_state(state)

def to_scan_code(key):
    """
    Returns the scan code for a given key name (or scan code, i.e. do nothing).
    Note that a name may belong to more than one physical key, in which case
    one of the scan codes will be chosen.
    """
    if isinstance(key, int):
        return key
    else:
        scan_code, modifiers = _os_keyboard.map_char(_normalize_name(key))
        return scan_code

def send(combination, do_press=True, do_release=True):
    """
    Sends OS events that perform the given hotkey combination.

    - `combination` can be either a scan code (e.g. 57 for space), single key
    (e.g. 'space') or multi-key, multi-step combination (e.g. 'alt+F4, enter').
    - `do_press` if true then press events are sent. Defaults to True.
    - `do_release` if true then release events are sent. Defaults to True.

        send(57)
        send('ctrl+alt+del')
        send('alt+F4, enter')
        send('shift+s')

    Note: keys are released in the opposite order they were pressed.
    """
    for keys in canonicalize(combination):
        if do_press:
            for key in keys:
                _os_keyboard.press(to_scan_code(key))

        if do_release:
            for key in reversed(keys):
                _os_keyboard.release(to_scan_code(key))

def press(combination):
    """ Presses and holds down a key combination (see `send`). """
    send(combination, True, False)

def release(combination):
    """ Releases a key combination (see `send`). """
    send(combination, False, True)

def press_and_release(combination):
    """ Presses and releases the key combination (see `send`). """
    send(combination, True, True)

def wait(combination):
    """
    Blocks the program execution until the given key combination is pressed.
    """
    lock = _Lock()
    lock.acquire()
    hotkey_handler = add_hotkey(combination, lock.release)
    lock.acquire()
    remove_hotkey(hotkey_handler)

def record(until='escape'):
    """
    Records all keyboard events from all keyboards until the user presses the
    given key combination. Then returns the list of events recorded, of type
    `keyboard.KeyboardEvent`. Pairs well with
    `play(events)`.

    Note: this is a blocking function.
    Note: for more details on the keyboard hook and events see `hook`.
    """
    recorded = []
    hook(recorded.append)
    wait(until)
    unhook(recorded.append)
    return recorded

def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is <= 0 then the actions are replayed as fast
    as the OS allows. Pairs well with `record()`.

    Note: the current keyboard state is cleared at the beginning and restored at
    the end of the function.
    """
    state = stash_state()

    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            _time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        key = event.scan_code or event.name
        if event.event_type == KEY_DOWN:
            press(key)
        elif event.event_type == KEY_UP:
            release(key)
        # Ignore other types of events.

    restore_state(state)

replay = play

def get_typed_strings(events, allow_backspace=True):
    """
    Given a sequence of events, tries to deduce what strings were typed.
    Strings are separated when a non-textual key is pressed (such as tab or
    enter). Characters are converted to uppercase according to shift and
    capslock status. If `allow_backspace` is True, backspaces remove the last
    character typed.

        get_type_strings(record()) -> ['This is what', 'I recorded', '']
    """
    shift_pressed = False
    capslock_pressed = False
    strings = ['']
    for event in events:
        name = event.name
        if name == 'space':
            # Space is the only key that we canonicalize to the spelled out name
            # because of legibility.
            name = ' '

        if name == 'shift':
            shift_pressed = event.event_type == 'down'
        elif name == 'caps lock' and event.event_type == 'down':
            capslock_pressed = not capslock_pressed
        elif allow_backspace and name == 'backspace' and event.event_type == 'down':
            strings[-1] = strings[-1][:-1]
        elif event.event_type == 'down':
            if len(name) == 1:
                if shift_pressed ^ capslock_pressed:
                    name = name.upper()
                strings[-1] = strings[-1] + name
            else:
                strings.append('')
    return strings
