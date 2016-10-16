keyboard
========

Take full control of your keyboard with this small Python library. Hook global events, register hotkeys, simulate key presses and much more.

- Global event hook on all keyboards (captures keys regardless of focus).
- **Receive** and **send** keyboard events.
- Works with **Windows** and **Linux** (requires sudo).
- **Pure Python**, no C modules to be compiled.
- **Zero dependencies**. Trivial to install and deploy, just copy the files.
- **Python 2 and 3**.
- Complex hotkey support (e.g. `Ctrl+Shift+M, Ctrl+Space`) with controllable timeout.
- Includes **high level API** (e.g. `record` and `play`, `add_abbreviation`).
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


# API
## keyboard.**KEY\_DOWN**
    = 'down'

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**KEY\_UP**
    = 'up'

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**all\_modifiers**
    = ('alt', 'alt gr', 'ctrl', 'shift', 'win')

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**os\_keyboard**
    = <module 'keyboard._nixkeyboard' from './keyboard/_nixkeyboard.py'>

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**platform**
    = <module 'platform' from '/usr/lib/python3.4/platform.py'>

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**time**
    = <module 'time' (built-in)>

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.


## keyboard.**is\_pressed**(key)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L34)


Returns True if the key is pressed.

    is_pressed(57) -> True
    is_pressed('space') -> True
    is_pressed('ctrl+space') -> True



## keyboard.**canonicalize**(hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L56)


Splits a user provided hotkey into a list of steps, each one made of a list
of scan codes. Used to normalize input at the API boundary. When a combo is
given (e.g. 'ctrl + a, b') spaces are ignored.

    canonicalize(57) -> [[57]]
    canonicalize('space') -> [[57]]
    canonicalize('ctrl+space') -> [[97, 57]]
    canonicalize('ctrl+space, space') -> [[97, 57], [57]]



## keyboard.**call\_later**(fn, args=(), delay=0.001)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L85)


Calls the provided function in a new thread after waiting some time.
Useful for giving the system some time to process an event, without blocking
the current execution flow.



## keyboard.**clear\_all\_hotkeys**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L94)


Removes all hotkey handlers. Note some functions such as 'wait' and 'record'
internally use hotkeys and will be affected by this call.

Abbreviations and word listeners are not hotkeys and therefore not affected.  
To remove all hooks use `unhook_all()`.



## keyboard.**add\_hotkey**(hotkey, callback, args=(), blocking=True, timeout=1)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L107)


Invokes a callback every time a key combination is pressed. The hotkey must
be in the format "ctrl+shift+a, s". This would trigger when the user holds
ctrl, shift and "a" at once, releases, and then presses "s". To represent
literal commas, pluses and spaces use their names ('comma', 'plus',
'space').

- `args` is an optional list of arguments to passed to the callback during
each invocation.
- `blocking` defines if the system should block processing other hotkeys
after a match is found. In Windows also tries to block other processes
from processing the key.
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



## keyboard.**register\_hotkey**

Alias for `add\_hotkey`.


## keyboard.**hook**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L174)


Installs a global listener on all available keyboards, invoking `callback`
each time a key is pressed or released.

The event passed to the callback is of type `keyboard_event.KeyboardEvent`,
with the following attributes:

- `name`: an Unicode representation of the character (e.g. "&") or
description (e.g.  "space"). The name is always lower-case.
- `scan_code`: number representing the physical key, e.g. 55.
- `time`: timestamp of the time the event occurred, with as much precision
as given by the OS.

Returns the given callback for easier development.



## keyboard.**unhook**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L193)

Removes a previously hooked callback. 


## keyboard.**unhook\_all**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L197)


Removes all keyboard hooks in use, including hotkeys, abbreviations, word
listeners, `record`ers and `wait`s.



## keyboard.**hook\_key**(key, keydown\_callback=&lt;function &lt;lambda&gt; at 0x76940d68&gt;, keyup\_callback=&lt;function &lt;lambda&gt; at 0x76940db0&gt;)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L206)


Hooks key up and key down events for a single key. Returns the event handler
created. To remove a hooked key use `unhook_key(key)` or
`unhook_key(handler)`.

Note: this function shares state with hotkeys, so `clear_all_hotkeys`
affects it aswell.



## keyboard.**remove\_hotkey**(hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L227)


Removes a previously registered hotkey. Accepts either the hotkey used
during registration (exact string) or the event handler returned by the
`add_hotkey` or `hook_key` functions.



## keyboard.**unhook\_key**

Alias for `remove\_hotkey`.


## keyboard.**add\_word\_listener**(word, callback, triggers=[&#x27;space&#x27;], match\_suffix=False, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L243)


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



## keyboard.**register\_word\_listener**

Alias for `add\_word\_listener`.


## keyboard.**remove\_word\_listener**(word)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L295)


Removes a previously registered word listener. Accepts either the word used
during registration (exact string) or the event handler returned by the
`add_word_listener` or `add_abbreviation` functions.



## keyboard.**remove\_abbreviation**

Alias for `remove\_word\_listener`.


## keyboard.**add\_abbreviation**(source\_text, replacement\_text, match\_suffix=True, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L307)


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



## keyboard.**register\_abbreviation**

Alias for `add\_abbreviation`.


## keyboard.**stash\_state**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L333)


Builds a list of all currently pressed scan codes, releases them and returns
the list. Pairs well with `restore_state`.



## keyboard.**restore\_state**(scan\_codes)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L343)


Given a list of scan_codes ensures these keys, and only these keys, are
pressed. Pairs well with `stash_state`.



## keyboard.**write**(text, delay=0, restore\_state\_after=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L355)


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



## keyboard.**send**(combination, do\_press=True, do\_release=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L398)


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



## keyboard.**press**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L423)

Presses and holds down a key combination (see `send`). 


## keyboard.**release**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L427)

Releases a key combination (see `send`). 


## keyboard.**press\_and\_release**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L431)

Presses and releases the key combination (see `send`). 


## keyboard.**wait**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L435)


Blocks the program execution until the given key combination is pressed.



## keyboard.**record**(until=&#x27;escape&#x27;)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L445)


Records all keyboard events from all keyboards until the user presses the
given key combination. Then returns the list of events recorded, of type
`keyboard_event.KeyboardEvent`. Pairs well with
`play(events)`.

Note: this is a blocking function.
Note: for more details on the keyboard hook and events see `hook`.



## keyboard.**play**(events, speed\_factor=1.0)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L461)


Plays a sequence of recorded events, maintaining the relative time
intervals. If speed_factor is <= 0 then the actions are replayed as fast
as the OS allows. Pairs well with `record()`.

Note: the current keyboard state is cleared at the beginning and restored at
the end of the function.



## keyboard.**get\_typed\_strings**(events, allow\_backspace=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L485)


Given a sequence of events, tries to deduce what strings were typed.
Strings are separated when a non-textual key is pressed (such as tab or
enter). Characters are converted to uppercase according to shift and
capslock status. If `allow_backspace` is True, backspaces remove the last
character typed.

    get_type_strings(record()) -> ['', 'This is what', 'I recorded', '']



## keyboard.**normalize\_name**(name)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/_keyboard_event.py#L170)




