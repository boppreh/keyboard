# -*- coding: utf-8 -*-
"""
keyboard
========

Take full control of your keyboard with this small Python library. Hook global events, register hotkeys, simulate key presses and much more.

## Features

- **Global event hook** on all keyboards (captures keys regardless of focus).
- **Listen** and **send** keyboard events.
- Works with **Windows** and **Linux** (requires sudo), with experimental **OS X** support (thanks @glitchassassin!).
- **Pure Python**, no C modules to be compiled.
- **Zero dependencies**. Trivial to install and deploy, just copy the files.
- **Python 2 and 3**.
- Complex hotkey support (e.g. `Ctrl+Shift+M, Ctrl+Space`) with controllable timeout.
- Includes **high level API** (e.g. [record](#keyboard.record) and [play](#keyboard.play), [add_abbreviation](#keyboard.add_abbreviation)).
- Maps keys as they actually are in your layout, with **full internationalization support** (e.g. `Ctrl+ç`).
- Events automatically captured in separate thread, doesn't block main program.
- Tested and documented.
- Doesn't break accented dead keys (I'm looking at you, pyHook).
- Mouse support available via project [mouse](https://github.com/boppreh/mouse) (`pip install mouse`).

## Usage

Install the [PyPI package](https://pypi.python.org/pypi/keyboard/):

    $ sudo pip install keyboard

or clone the repository (no installation required, source files are sufficient):

    $ git clone https://github.com/boppreh/keyboard

Then check the [API docs](https://github.com/boppreh/keyboard#api) to see what features are available.


## Example


```
import keyboard

keyboard.press_and_release('shift+s, space')

keyboard.write('The quick brown fox jumps over the lazy dog.')

# Press PAGE UP then PAGE DOWN to type "foobar".
keyboard.add_hotkey('page up, page down', lambda: keyboard.write('foobar'))

# Blocks until you press esc.
keyboard.wait('esc')

# Record events until 'esc' is pressed.
recorded = keyboard.record(until='esc')
# Then replay back at three times the speed.
keyboard.play(recorded, speed_factor=3)

# Type @@ then press space to replace with abbreviation.
keyboard.add_abbreviation('@@', 'my.long.email@example.com')
# Block forever.
keyboard.wait()
```

## Known limitations:

- Events generated under Windows don't report device id (`event.device == None`). [#21](https://github.com/boppreh/keyboard/issues/21)
- Media keys on Linux may appear nameless (scan-code only) or not at all. [#20](https://github.com/boppreh/keyboard/issues/20)
- Key suppression/blocking only available on Windows. [#22](https://github.com/boppreh/keyboard/issues/22)
- To avoid depending on X, the Linux parts reads raw device files (`/dev/input/input*`)
but this requries root.
- Other applications, such as some games, may register hooks that swallow all 
key events. In this case `keyboard` will be unable to report events.
- This program makes no attempt to hide itself, so don't use it for keyloggers or online gaming bots. Be responsible.
"""

import itertools
import time as _time
from collections import Counter
from threading import Thread as _Thread
from ._keyboard_event import KeyboardEvent

try:
    # Python2
    long, basestring
    _is_str = lambda x: isinstance(x, basestring)
    _is_number = lambda x: isinstance(x, (int, long))
    import Queue as _queue
except NameError:
    # Python3
    _is_str = lambda x: isinstance(x, str)
    _is_number = lambda x: isinstance(x, int)
    import queue as _queue
_is_list = lambda x: isinstance(x, (list, tuple))

# Just a dynamic object to store attributes for the closures.
class _State(object): pass

import platform as _platform
if _platform.system() == 'Windows':
    from. import _winkeyboard as _os_keyboard
elif _platform.system() == 'Linux':
    from. import _nixkeyboard as _os_keyboard
elif _platform.system() == 'Darwin':
    from. import _darwinkeyboard as _os_keyboard
else:
    raise OSError("Unsupported platform '{}'".format(_platform.system()))

from ._keyboard_event import KEY_DOWN, KEY_UP
from ._keyboard_event import normalize_name as _normalize_name
from ._generic import GenericListener as _GenericListener

all_modifiers = {'alt', 'alt gr', 'ctrl', 'shift', 'windows'}
for key in list(all_modifiers):
    all_modifiers.add('left ' + key)
    all_modifiers.add('right ' + key)
sided_keys = {'ctrl', 'alt', 'shift', 'windows'}

_pressed_events = {}
_blocking_hook = None
class _KeyboardListener(_GenericListener):
    active_modifiers = set()
    blocking_hotkeys = {}
    blocking_keys = {}
    filtered_modifiers = Counter()
    is_replaying = False

    # Supporting hotkey suppression is harder than it looks. See
    # https://github.com/boppreh/keyboard/issues/22
    modifier_states = {} # "alt" -> "allowed"
    transition_table = {
        #Current state of the modifier, per `modifier_states`.
        #|
        #|             Type of event that triggered this modifier update.
        #|             |
        #|             |         Type of key that triggered this modiier update.
        #|             |         |
        #|             |         |            Should we send a fake key press?
        #|             |         |            |
        #|             |         |     =>     |       Accept the event?
        #|             |         |            |       |
        #|             |         |            |       |      Next state.
        #v             v         v            v       v      v
        ('free',       KEY_UP,   'modifier'): (False, True, 'free'),
        ('free',       KEY_DOWN, 'modifier'): (False, False, 'pending'),
        ('pending',    KEY_UP,   'modifier'): (True,  True, 'free'),
        ('pending',    KEY_DOWN, 'modifier'): (False, True, 'allowed'),
        ('suppressed', KEY_UP,   'modifier'): (False, False, 'free'),
        ('suppressed', KEY_DOWN, 'modifier'): (False, False, 'suppressed'),
        ('allowed',    KEY_UP,   'modifier'): (False, True, 'free'),
        ('allowed',    KEY_DOWN, 'modifier'): (False, True, 'allowed'),

        ('free',       KEY_UP,   'hotkey'):   (False, None, 'free'),
        ('free',       KEY_DOWN, 'hotkey'):   (False, None, 'free'),
        ('pending',    KEY_UP,   'hotkey'):   (False, None, 'suppressed'),
        ('pending',    KEY_DOWN, 'hotkey'):   (False, None, 'suppressed'),
        ('suppressed', KEY_UP,   'hotkey'):   (False, None, 'suppressed'),
        ('suppressed', KEY_DOWN, 'hotkey'):   (False, None, 'suppressed'),
        ('allowed',    KEY_UP,   'hotkey'):   (False, None, 'allowed'),
        ('allowed',    KEY_DOWN, 'hotkey'):   (False, None, 'allowed'),

        ('free',       KEY_UP,   'other'):    (False, True, 'free'),
        ('free',       KEY_DOWN, 'other'):    (False, True, 'free'),
        ('pending',    KEY_UP,   'other'):    (True,  True, 'allowed'),
        ('pending',    KEY_DOWN, 'other'):    (True,  True, 'allowed'),
        ('suppressed', KEY_UP,   'other'):    (True,  True, 'allowed'),
        ('suppressed', KEY_DOWN, 'other'):    (True,  True, 'allowed'),
        ('allowed',    KEY_UP,   'other'):    (False, True, 'allowed'),
        ('allowed',    KEY_DOWN, 'other'):    (False, True, 'allowed'),
    }

    def init(self):
        _os_keyboard.init()
        
    def pre_process_event(self, event):
        return event.scan_code or (event.name and event.name != 'unknown')

    def direct_callback(self, event):
        """
        This function is called for every OS keyboard event and decides if the
        event should be blocked or not, and passes a copy of the event to
        other, non-blocking, listeners.

        There are two ways to block events: remapped keys, which translate
        events by suppressing and re-emitting; and blocked hotkeys, which
        suppress specific key combinations.
        """

        # Pass through all fake key events, don't even report to other handlers.
        if self.is_replaying:
            return True

        # Useful for media keys, which are reported with scan_code = 0, or
        # artificial events.
        if not event.scan_code:
            event.scan_code = to_scan_code(event.name)

        if _blocking_hook and not _blocking_hook(event):
            return False

        event_type = event.event_type

        # Mappings based on individual keys instead of hotkeys.
        if event.name in self.blocking_keys and not self.blocking_keys[event.name](event):
            return False

        # Update tables of currently pressed keys and modifiers.
        if event_type == KEY_DOWN:
            if event.name in all_modifiers: self.active_modifiers.add(event.name)
            _pressed_events[event.scan_code] = event

        # Default accept.
        accept = True

        if self.blocking_hotkeys:
            if self.filtered_modifiers[event.name]:
                origin = 'modifier'
                modifiers_to_update = [event.name]
            else:
                modifiers_to_update = self.active_modifiers
                hotkey_pair = (tuple(sorted(self.active_modifiers)), event.name)
                if hotkey_pair in self.blocking_hotkeys:
                    accept = self.blocking_hotkeys[hotkey_pair](event)
                    origin = 'hotkey'
                else:
                    origin = 'other'

            for key in modifiers_to_update:
                transition_tuple = (self.modifier_states.get(key, 'free'), event_type, origin)
                should_press, new_accept, new_state = self.transition_table[transition_tuple]
                if should_press: press(key)
                if new_accept is not None: accept = new_accept
                self.modifier_states[key] = new_state

        # Update tables of currently pressed keys and modifiers.
        if event_type == KEY_UP:
            if event.name in all_modifiers: self.active_modifiers.discard(event.name)
            if event.scan_code in _pressed_events: del _pressed_events[event.scan_code]

        # Queue for handlers that won't block the event.
        self.queue.put(event)

        return accept

    def listen(self):
        _os_keyboard.listen(self.direct_callback)

_listener = _KeyboardListener()

def matches(event, name):
    """
    Returns True if the given event represents the same key as the one given in
    `name`.
    """
    if _is_number(name):
        return event.scan_code == name

    normalized = _normalize_name(name)
    matched_name = (
        normalized == event.name
        or 'left ' + normalized == event.name
        or 'right ' + normalized == event.name
    )

    return matched_name or _os_keyboard.map_char(normalized)[0] == event.scan_code

def is_pressed(key):
    """
    Returns True if the key is pressed.

        is_pressed(57) -> True
        is_pressed('space') -> True
        is_pressed('ctrl+space') -> True
    """
    _listener.start_if_necessary()
    if _is_number(key):
        # Optimization.
        return key in _pressed_events
    parts = _parse_hotkey(key)
    if len(parts) > 1:
        raise ValueError('Cannot check status of multi-step combination ({}).'.format(key))
    for key in parts[0]:
        for event in _pressed_events.values():
            if not matches(event, key):
                return False
    return True

def _parse_hotkey(hotkey):
    """
    Splits a user provided hotkey into a list of steps, each one made of a list
    of scan codes or names. Used to normalize input at the API boundary. When a
    combo is given (e.g. 'ctrl + a, b') spaces are ignored.

        _parse_hotkey(57) -> [[57]]
        _parse_hotkey([[57]]) -> [[57]]
        _parse_hotkey('space') -> [['space']]
        _parse_hotkey('ctrl+space') -> [['ctrl', 'space']]
        _parse_hotkey('ctrl+space, space') -> [['ctrl', 'space'], ['space']]

    Note we must not convert names into scan codes because a name may represent
    more than one physical key (e.g. two 'ctrl' keys).
    """
    if _is_list(hotkey) and all(_is_list(step) for step in hotkey):
        # Already _parse_hotkeyd, nothing to do.
        return hotkey
    elif _is_list(hotkey) and all(not _is_list(key) for key in hotkey):
        # Make list of names or scan codes into list of steps.
        return _parse_hotkey([hotkey])
    elif _is_number(hotkey):
        return [[hotkey]]

    if not _is_str(hotkey):
        raise ValueError('Unexpected hotkey: {}. Expected int scan code, str key combination or normalized hotkey.'.format(hotkey))

    if len(hotkey) == 1 or ('+' not in hotkey and ',' not in hotkey):
        return [[_normalize_name(hotkey)]]
    else:
        steps = []
        for str_step in hotkey.split(','):
            steps.append([])
            for part in str_step.split('+'):
                steps[-1].append(_normalize_name(part.strip()))
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
    internally use hotkeys and will be affected by this call. Also unblocks all
    keys.

    Abbreviations and word listeners are not hotkeys and therefore not affected.  
    To remove all hooks use `unhook_all()`.
    """
    for handler in _hotkeys.values():
        unhook(handler)
    _hotkeys.clear()
    clear_all_blocks()

# Alias.
remove_all_hotkeys = clear_all_hotkeys

def add_hotkey(hotkey, callback, args=(), suppress=False, timeout=1, trigger_on_release=False):
    """
    Invokes a callback every time a key combination is pressed. The hotkey must
    be in the format "ctrl+shift+a, s". This would trigger when the user holds
    ctrl, shift and "a" at once, releases, and then presses "s". To represent
    literal commas, pluses and spaces use their names ('comma', 'plus',
    'space').

    - `args` is an optional list of arguments to passed to the callback during
    each invocation.
    - `suppress` defines if the it should block processing other hotkeys after
    a match is found. Currently Windows-only.
    - `timeout` is the amount of seconds allowed to pass between key presses.
    - `trigger_on_release` if true, the callback is invoked on key release instead
    of key press.

    The event handler function is returned. To remove a hotkey call
    `remove_hotkey(hotkey)` or `remove_hotkey(handler)`.
    before the combination state is reset.

    Note: hotkeys are activated when the last key is *pressed*, not released.
    Note: the callback is executed in a separate thread, asynchronously. For an
    example of how to use a callback synchronously, see `wait`.

    Examples:

        # Different but equivalent ways to listen for a spacebar key press.
        add_hotkey(' ', print, args=['space was pressed'])
        add_hotkey('space', print, args=['space was pressed'])
        add_hotkey('Space', print, args=['space was pressed'])
        # Here 57 represents the keyboard code for spacebar; so you will be
        # pressing 'spacebar', not '57' to activate the print function.
        add_hotkey(57, print, args=['space was pressed'])

        add_hotkey('ctrl+q', quit)
        add_hotkey('ctrl+alt+enter, space', some_callback)
    """
    if suppress:
        # TODO: removal
        return hook_blocking_hotkey(hotkey, lambda e: (callback(args), False)[1])

    steps = _parse_hotkey(hotkey)

    state = _State()
    state.step = 0
    state.time = _time.time()

    def handler(event):
        if event.event_type == KEY_UP:
            if trigger_on_release and state.step == len(steps):
                state.step = 0
                callback(*args)
                return suppress
            return

        # Just waiting for the user to release a key.
        if trigger_on_release and state.step >= len(steps):
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
            if all(is_pressed(part) or matches(event, part) for part in steps[state.step]):
                state.step += 1
                if not trigger_on_release and state.step == len(steps):
                    state.step = 0
                    callback(*args)
                    return suppress

    _hotkeys[hotkey] = handler
    return hook(handler)

# Alias.
register_hotkey = add_hotkey

removal_callbacks = {}
def hook(callback, on_remove=lambda: None):
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
    removal_callbacks[callback] = on_remove
    return callback

def unhook(callback):
    """ Removes a previously hooked callback. """
    _listener.remove_handler(callback)
    removal_callbacks[callback]()

def unhook_all():
    """
    Removes all keyboard hooks in use, including hotkeys, abbreviations, word
    listeners, `record`ers and `wait`s.
    """
    _hotkeys.clear()
    _word_listeners.clear()
    for callback in removal_callbacks.values():
        callback()
    removal_callbacks.clear()
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

    return name

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

def add_abbreviation(source_text, replacement_text, match_suffix=False, timeout=2):
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
    # TODO: stash caps lock state.
    state = sorted(_pressed_events)
    for scan_code in state:
        _os_keyboard.release(scan_code)
    return state

def restore_state(scan_codes):
    """
    Given a list of scan_codes ensures these keys, and only these keys, are
    pressed. Pairs well with `stash_state`.
    """
    _listener.is_replaying = True

    current = set(_pressed_events)
    target = set(scan_codes)
    for scan_code in current - target:
        _os_keyboard.release(scan_code)
    for scan_code in target - current:
        _os_keyboard.press(scan_code)

    _listener.is_replaying = False

def write(text, delay=0, restore_state_after=True, exact=None):
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
    - `exact` forces typing all characters as explicit unicode (e.g.
    alt+codepoint or special events). If None, uses platform-specific suggested
    value.
    """
    state = stash_state()
    
    # Window's typing of unicode characters is quite efficient and should be preferred.
    if exact or (exact is None and _platform.system() == 'Windows'):
        for letter in text:
            _os_keyboard.type_unicode(letter)
            if delay: _time.sleep(delay)

    else:
        for letter in text:
            if letter in '\n\b\t ':
                letter = _normalize_name(letter)
                
            try:
                scan_code, modifiers = _os_keyboard.map_char(letter)
            except ValueError:
                _os_keyboard.type_unicode(letter)
                continue

            if is_pressed(scan_code):
                release(scan_code)

            for modifier in modifiers:
                press(modifier)

            _os_keyboard.press(scan_code)
            _os_keyboard.release(scan_code)

            for modifier in modifiers:
                release(modifier)

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
    if _is_number(key):
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
    _listener.is_replaying = True

    for keys in _parse_hotkey(combination):
        if do_press:
            for key in keys:
                _os_keyboard.press(to_scan_code(key))

        if do_release:
            for key in reversed(keys):
                _os_keyboard.release(to_scan_code(key))

    _listener.is_replaying = False

# Alias.
press_and_release = send

def press(combination):
    """ Presses and holds down a key combination (see `send`). """
    send(combination, True, False)

def release(combination):
    """ Releases a key combination (see `send`). """
    send(combination, False, True)

def _make_wait_and_unlock():
    """
    Method to work around CPython's inability to interrupt Lock.join with
    signals. Without this Ctrl+C doesn't close the program.
    """
    q = _queue.Queue(maxsize=1)
    def wait():
        while True:
            try:
                return q.get(timeout=1)
            except _queue.Empty:
                pass
    return (wait, lambda v=None: q.put(v))

def wait(combination=None):
    """
    Blocks the program execution until the given key combination is pressed or,
    if given no parameters, blocks forever.
    """
    wait, unlock = _make_wait_and_unlock()
    if combination is not None:
        hotkey_handler = add_hotkey(combination, unlock)
    wait()
    remove_hotkey(hotkey_handler)

def read_key(filter=lambda e: True):
    """
    Blocks until a keyboard event happens, then returns that event.
    """
    wait, unlock = _make_wait_and_unlock()
    def test(event):
        if filter(event):
            unhook(test)
            unlock(event)
    hook(test)
    return wait()

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

    This function is a generator, so you can pass an infinite stream of events
    and convert them to strings in real time.

    Note this functions is merely an heuristic. Windows for example keeps per-
    process keyboard state such as keyboard layout, and this information is not
    available for our hooks.

        get_type_strings(record()) -> ['This is what', 'I recorded', '']
    """
    shift_pressed = False
    capslock_pressed = False
    string = ''
    for event in events:
        name = event.name

        # Space is the only key that we _parse_hotkey to the spelled out name
        # because of legibility. Now we have to undo that.
        if matches(event, 'space'):
            name = ' '

        if matches(event, 'shift'):
            shift_pressed = event.event_type == 'down'
        elif matches(event, 'caps lock') and event.event_type == 'down':
            capslock_pressed = not capslock_pressed
        elif allow_backspace and matches(event, 'backspace') and event.event_type == 'down':
            string = string[:-1]
        elif event.event_type == 'down':
            if len(name) == 1:
                if shift_pressed ^ capslock_pressed:
                    name = name.upper()
                string = string + name
            else:
                yield string
                string = ''
    yield string


_recording = None
def start_recording(recorded_events_queue=None):
    """
    Starts recording all keyboard events into a global variable, or the given
    queue if any. Returns the queue of events and the hooked function.

    Use `stop_recording()` or `unhook(hooked_function)` to stop.
    """
    global _recording
    recorded_events_queue = recorded_events_queue or _queue.Queue()
    _recording = recorded_events_queue, hook(recorded_events_queue.put)
    return _recording

def stop_recording():
    """
    Stops the global recording of events and returns a list of the events
    captured.
    """
    global _recording
    if not _recording:
        raise ValueError('Must call "start_recording" before.')
    recorded_events_queue, hooked = _recording
    unhook(hooked)
    _recording = None
    return list(recorded_events_queue.queue)


def get_hotkey_name(names=None):
    """
    Returns a string representation of hotkey from the given key names, or
    the currently pressed keys if not given.  This function:

    - normalizes names;
    - removes "left" and "right" prefixes;
    - replaces the "+" key name with "plus" to avoid ambiguity;
    - puts modifier keys first, in a standardized order;
    - sort remaining keys;
    - finally, joins everything with "+".

    Example:

        get_hotkey_name(['+', 'left ctrl', 'shift'])
        # "ctrl+shift+plus"
    """
    if names is None:
        _listener.start_if_necessary()
        names = [e.name for e in _pressed_events.values()]
    else:
        names = [_normalize_name(name) for name in names]
    clean_names = set(e.replace('left ', '').replace('right ', '').replace('+', 'plus') for e in names)
    # https://developer.apple.com/macos/human-interface-guidelines/input-and-output/keyboard/
    # > List modifier keys in the correct order. If you use more than one modifier key in a
    # > hotkey, always list them in this order: Control, Option, Shift, Command.
    modifiers = ['ctrl', 'alt', 'shift', 'windows']
    sorting_key = lambda k: (modifiers.index(k) if k in modifiers else 5, str(k))
    return '+'.join(sorted(clean_names, key=sorting_key))

def read_hotkey():
    """
    Similar to `read_key()`, but blocks until the user presses and releases a key
    combination (or single key), then returns a string representing the hotkey
    pressed.

    Example:

        read_hotkey()
        # "ctrl+shift+p"
    """
    wait, unlock = _make_wait_and_unlock()
    def test(event):
        if event.event_type == KEY_UP:
            unhook(test)
            names = [e.name for e in _pressed_events.values()] + [event.name]
            unlock(get_hotkey_name(names))
    hook(test)
    return wait()
read_hotkey = read_hotkey


def _get_sided_keys(key):
    """
    Generates key variations with 'left' and 'right' when the key is sided.
    """
    if key in sided_keys:
        yield from (prefix + key for prefix in ['', 'left ', 'right '])
    else:
        yield key

def _parse_blocking_hotkey(hotkey):
    _listener.start_if_necessary()

    steps = _parse_hotkey(hotkey)
    if len(steps) > 1:
        raise NotImplementedError('Cannot hook multi-step blocking hotkey (e.g. "alt+s, t"). Please see https://github.com/boppreh/keyboard/issues/22')
    names = set(steps[0])

    modifiers = names & all_modifiers
    rest = names - modifiers
    if len(rest) != 1:
        raise NotImplementedError('Can only hook combinations of modifiers plus a single key. Please see https://github.com/boppreh/keyboard/issues/22')

    main_key = rest.pop()
    return main_key, itertools.product(*(_get_sided_keys(m) for m in modifiers))

def hook_blocking_hotkey(hotkey, handler):
    """
    Sets an event handler to be called whenever the given hotkey is triggered.
    This event will be blcoking (the OS will wait for this handler to finish),
    and may return True or False if the hotkey should be suppressed or not.
    """
    main_key, combinations = _parse_blocking_hotkey(hotkey)
    for possible_combination in combinations:
        for modifier in possible_combination:
            _listener.filtered_modifiers[modifier] += 1
        pair = (tuple(sorted(possible_combination)), main_key)
        _listener.blocking_hotkeys[pair] = handler

    return hotkey

def unhook_blocking_hotkey(hotkey):
    """
    Removes a hotkey hook added via `hook_blocking_hotkey`.
    """
    main_key, combinations = _parse_blocking_hotkey(hotkey)
    for possible_combination in combinations:
        for modifier in possible_combination:
            _listener.filtered_modifiers[modifier] -= 1
        pair = (tuple(sorted(possible_combination)), main_key)
        del _listener.blocking_hotkeys[pair]


def hook_blocking_key(key, handler):
    """
    Sets an event handler to be called for all events regarding the given key,
    regardless of modifiers.
    This event will be blcoking (the OS will wait for this handler to finish),
    and may return True or False if the hotkey should be suppressed or not.
    """
    _listener.start_if_necessary()
    for sided_key in _get_sided_keys(_normalize_name(key)):
        _listener.blocking_keys[sided_key] = handler
    return key

def unhook_blocking_key(key, handler):
    """
    Removes a hook added via `hook_blocking_key`.
    """
    for sided_key in _get_sided_keys(_normalize_name(key)):
        del _listener.blocking_keys[sided_key]
    return key

def remap_hotkey(src, dst):
    """
    Whenever the hotkey `src` is pressed, suppress it and send
    `dst` instead.

    Example:

        remap('alt+w', 'up')
        remap('capslock', 'esc')
    """
    def handler(event):
        if event.event_type == KEY_UP: return False
        for state, modifier in _listener.modifier_states.items():
            if state == 'allowed':
                release(modifier)
        send(dst)
        for state, modifier in _listener.modifier_states.items():
            if state == 'allowed':
                press(modifier)
        return False
    return hook_blocking_hotkey(src, handler)
unremap_hotkey = unhook_blocking_hotkey

def remap_key(src, dst):
    """
    Whenever the key `src` is pressed or released, regardless of modifiers,
    press or release `dst` instead.
    """
    def handler(event):
        if event.event_type == KEY_DOWN:
            press(dst)
        else:
            release(dst)
        return False
    return hook_blocking_key(src, handler)
unremap_key = unhook_blocking_key

def block_key(key):
    """
    Suppresses all key events of the given key, regardless of modifiers.
    """
    return hook_blocking_key(key, lambda e: False)
unblock_key = unhook_blocking_key


def hook_blocking(handler):
    """
    Sets a global, blocking hook. The given `handler` will be invoked for every
    keyboard event, and if `handler` returns False, the event will be
    suppressed. Because this is a blocking hook, if `handler` takes too long to
    return a noticeable delay will be added to every key event.

    Only one such hook may be active.
    """
    global _blocking_hook
    _blocking_hook = handler
    _listener.start_if_necessary()
    return handler

def unhook_blocking():
    """
    Removes a hook added via `hook_blocking`.
    """
    global _blocking_hook
    _blocking_hook = None

def add_multi_step_blocking_hotkey(hotkey, callback):
    # TODO: timeout
    # TODO: merge hotkeys instead of overwriting
    parts = _parse_hotkey(hotkey)

    state = _State()
    state.index = 0
    def set_index(new_index):
        if len(parts) == 1 and new_index == 1:
            return callback()

        unhook_blocking_hotkey(parts[state.index])
        state.index = new_index
        if state.index == len(parts):
            callback()
            state.index = 0
        hook_blocking_hotkey(parts[state.index], triggered)
        
    def triggered(event):
        if event.event_type == KEY_DOWN:
            set_index(state.index+1)
        return False
    hook_blocking_hotkey(parts[state.index], triggered)

    if len(parts) > 1:
        # TODO: allow "a, a, b" when typing "aaab"
        def catch_misses(event):
            if event.event_type == KEY_DOWN and state.index and event.name not in parts[state.index]:
                for part in parts[:state.index]:
                    send(part)
                set_index(0)
            return True
        hook_blocking(catch_misses)

    # TODO
    return