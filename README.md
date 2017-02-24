
keyboard
========

Take full control of your keyboard with this small Python library. Hook global events, register hotkeys, simulate key presses and much more.

## Features

- Global event hook on all keyboards (captures keys regardless of focus).
- **Listen** and **sends** keyboard events.
- Works with **Windows** and **Linux** (requires sudo).
- **Pure Python**, no C modules to be compiled.
- **Zero dependencies**. Trivial to install and deploy, just copy the files.
- **Python 2 and 3**.
- Complex hotkey support (e.g. `Ctrl+Shift+M, Ctrl+Space`) with controllable timeout.
- Includes **high level API** (e.g. [record](#keyboard.record) and [play](#keyboard.play), [add_abbreviation](#keyboard.add_abbreviation)).
- Maps keys as they actually are in your layout, with **full internationalization support** (e.g. `Ctrl+ç`).
- Events automatically captured in separate thread, doesn't block main program.
- Tested and documented.
- Doesn't break accented dead keys (I'm looking at you, pyHook).
- Mouse support coming soon.

This program makes no attempt to hide itself, so don't use it for keyloggers.

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
- Linux doesn't seem to report media keys. [#20](https://github.com/boppreh/keyboard/issues/20)
- Currently no way to suppress keys ('catch' events and block them). [#22](https://github.com/boppreh/keyboard/issues/22)
- To avoid depending on X the Linux parts reads raw device files (`/dev/input/input*`)
but this requries root.
- Other applications, such as some games, may register hooks that swallow all 
key events. In this case `keyboard` will be unable to report events.



# API
#### Table of Contents

- [keyboard.**KEY\_DOWN**](#keyboard.KEY_DOWN)
- [keyboard.**KEY\_UP**](#keyboard.KEY_UP)
- [keyboard.**KeyboardEvent**](#keyboard.KeyboardEvent)
- [keyboard.**all\_modifiers**](#keyboard.all_modifiers)
- [keyboard.**is\_str**](#keyboard.is_str)
- [keyboard.**is\_number**](#keyboard.is_number)
- [keyboard.**matches**](#keyboard.matches)
- [keyboard.**is\_pressed**](#keyboard.is_pressed)
- [keyboard.**canonicalize**](#keyboard.canonicalize)
- [keyboard.**call\_later**](#keyboard.call_later)
- [keyboard.**clear\_all\_hotkeys**](#keyboard.clear_all_hotkeys)
- [keyboard.**remove\_all\_hotkeys**](#keyboard.remove_all_hotkeys) *(alias)*
- [keyboard.**add\_hotkey**](#keyboard.add_hotkey)
- [keyboard.**register\_hotkey**](#keyboard.register_hotkey) *(alias)*
- [keyboard.**hook**](#keyboard.hook)
- [keyboard.**unhook**](#keyboard.unhook)
- [keyboard.**unhook\_all**](#keyboard.unhook_all)
- [keyboard.**hook\_key**](#keyboard.hook_key)
- [keyboard.**on\_press**](#keyboard.on_press)
- [keyboard.**on\_release**](#keyboard.on_release)
- [keyboard.**remove\_hotkey**](#keyboard.remove_hotkey)
- [keyboard.**unhook\_key**](#keyboard.unhook_key) *(alias)*
- [keyboard.**add\_word\_listener**](#keyboard.add_word_listener)
- [keyboard.**register\_word\_listener**](#keyboard.register_word_listener) *(alias)*
- [keyboard.**remove\_word\_listener**](#keyboard.remove_word_listener)
- [keyboard.**remove\_abbreviation**](#keyboard.remove_abbreviation) *(alias)*
- [keyboard.**add\_abbreviation**](#keyboard.add_abbreviation)
- [keyboard.**register\_abbreviation**](#keyboard.register_abbreviation) *(alias)*
- [keyboard.**stash\_state**](#keyboard.stash_state)
- [keyboard.**restore\_state**](#keyboard.restore_state)
- [keyboard.**write**](#keyboard.write)
- [keyboard.**to\_scan\_code**](#keyboard.to_scan_code)
- [keyboard.**send**](#keyboard.send)
- [keyboard.**press**](#keyboard.press)
- [keyboard.**release**](#keyboard.release)
- [keyboard.**press\_and\_release**](#keyboard.press_and_release)
- [keyboard.**wait**](#keyboard.wait)
- [keyboard.**read\_key**](#keyboard.read_key)
- [keyboard.**record**](#keyboard.record)
- [keyboard.**play**](#keyboard.play)
- [keyboard.**replay**](#keyboard.replay) *(alias)*
- [keyboard.**get\_typed\_strings**](#keyboard.get_typed_strings)


<a name="keyboard.KEY_DOWN"/>
## keyboard.**KEY\_DOWN**
    = 'down'


<a name="keyboard.KEY_UP"/>
## keyboard.**KEY\_UP**
    = 'up'


<a name="keyboard.KeyboardEvent"/>
## class keyboard.**KeyboardEvent**




<a name="KeyboardEvent.event_type"/>
### KeyboardEvent.**event\_type**


<a name="KeyboardEvent.name"/>
### KeyboardEvent.**name**


<a name="KeyboardEvent.scan_code"/>
### KeyboardEvent.**scan\_code**


<a name="KeyboardEvent.time"/>
### KeyboardEvent.**time**




<a name="keyboard.all_modifiers"/>
## keyboard.**all\_modifiers**
    = ('alt', 'alt gr', 'ctrl', 'shift', 'win')


<a name="keyboard.is_str"/>
## keyboard.**is\_str**(x)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L88)




<a name="keyboard.is_number"/>
## keyboard.**is\_number**(x)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L89)




<a name="keyboard.matches"/>
## keyboard.**matches**(event, name)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L134)


Returns True if the given event represents the same key as the one given in
`name`.



<a name="keyboard.is_pressed"/>
## keyboard.**is\_pressed**(key)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L151)


Returns True if the key is pressed.

    is_pressed(57) -> True
    is_pressed('space') -> True
    is_pressed('ctrl+space') -> True



<a name="keyboard.canonicalize"/>
## keyboard.**canonicalize**(hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L173)


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



<a name="keyboard.call_later"/>
## keyboard.**call\_later**(fn, args=(), delay=0.001)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L207)


Calls the provided function in a new thread after waiting some time.
Useful for giving the system some time to process an event, without blocking
the current execution flow.



<a name="keyboard.clear_all_hotkeys"/>
## keyboard.**clear\_all\_hotkeys**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L225)


Removes all hotkey handlers. Note some functions such as 'wait' and 'record'
internally use hotkeys and will be affected by this call.

Abbreviations and word listeners are not hotkeys and therefore not affected.  
To remove all hooks use [`unhook_all()`](#keyboard.unhook_all).



<a name="keyboard.remove_all_hotkeys"/>
## keyboard.**remove\_all\_hotkeys**

Alias for [`clear_all_hotkeys`](#keyboard.clear_all_hotkeys).


<a name="keyboard.add_hotkey"/>
## keyboard.**add\_hotkey**(hotkey, callback, args=(), suppress=False, timeout=1)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L242)


Invokes a callback every time a key combination is pressed. The hotkey must
be in the format "ctrl+shift+a, s". This would trigger when the user holds
ctrl, shift and "a" at once, releases, and then presses "s". To represent
literal commas, pluses and spaces use their names ('comma', 'plus',
'space').

- `args` is an optional list of arguments to passed to the callback during
each invocation.
- `suppress` defines if the it should block processing other hotkeys after
a match is found. Currently Windows-only.
- `timeout` is the amount of seconds allowed to pass between key presses

The event handler function is returned. To remove a hotkey call
[`remove_hotkey(hotkey)`](#keyboard.remove_hotkey) or [`remove_hotkey(handler)`](#keyboard.remove_hotkey).
before the combination state is reset.

Note: hotkeys are activated when the last key is *pressed*, not released.
Note: the callback is executed in a separate thread, asynchronously. For an
example of how to use a callback synchronously, see [`wait`](#keyboard.wait).

    add_hotkey(57, print, args=['space was pressed'])
    add_hotkey(' ', print, args=['space was pressed'])
    add_hotkey('space', print, args=['space was pressed'])
    add_hotkey('Space', print, args=['space was pressed'])

    add_hotkey('ctrl+q', quit)
    add_hotkey('ctrl+alt+enter, space', some_callback)



<a name="keyboard.register_hotkey"/>
## keyboard.**register\_hotkey**

Alias for [`add_hotkey`](#keyboard.add_hotkey).


<a name="keyboard.hook"/>
## keyboard.**hook**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L311)


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



<a name="keyboard.unhook"/>
## keyboard.**unhook**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L330)

Removes a previously hooked callback. 


<a name="keyboard.unhook_all"/>
## keyboard.**unhook\_all**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L334)


Removes all keyboard hooks in use, including hotkeys, abbreviations, word
listeners, [`record`](#keyboard.record)ers and [`wait`](#keyboard.wait)s.



<a name="keyboard.hook_key"/>
## keyboard.**hook\_key**(key, keydown\_callback=&lt;lambda&gt;, keyup\_callback=&lt;lambda&gt;)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L343)


Hooks key up and key down events for a single key. Returns the event handler
created. To remove a hooked key use [`unhook_key(key)`](#keyboard.unhook_key) or
[`unhook_key(handler)`](#keyboard.unhook_key).

Note: this function shares state with hotkeys, so [`clear_all_hotkeys`](#keyboard.clear_all_hotkeys)
affects it aswell.



<a name="keyboard.on_press"/>
## keyboard.**on\_press**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L364)


Invokes `callback` for every KEY_DOWN event. For details see [`hook`](#keyboard.hook).



<a name="keyboard.on_release"/>
## keyboard.**on\_release**(callback)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L370)


Invokes `callback` for every KEY_UP event. For details see [`hook`](#keyboard.hook).



<a name="keyboard.remove_hotkey"/>
## keyboard.**remove\_hotkey**(hotkey\_or\_handler)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L399)


Removes a previously registered hotkey. Accepts either the hotkey used
during registration (exact string) or the event handler returned by the
[`add_hotkey`](#keyboard.add_hotkey) or [`hook_key`](#keyboard.hook_key) functions.



<a name="keyboard.unhook_key"/>
## keyboard.**unhook\_key**

Alias for [`remove_hotkey`](#keyboard.remove_hotkey).


<a name="keyboard.add_word_listener"/>
## keyboard.**add\_word\_listener**(word, callback, triggers=[&#x27;space&#x27;], match\_suffix=False, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L418)


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
[`remove_word_listener(word)`](#keyboard.remove_word_listener) or [`remove_word_listener(handler)`](#keyboard.remove_word_listener).

Note: all actions are performed on key down. Key up events are ignored.
Note: word mathes are **case sensitive**.



<a name="keyboard.register_word_listener"/>
## keyboard.**register\_word\_listener**

Alias for [`add_word_listener`](#keyboard.add_word_listener).


<a name="keyboard.remove_word_listener"/>
## keyboard.**remove\_word\_listener**(word\_or\_handler)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L469)


Removes a previously registered word listener. Accepts either the word used
during registration (exact string) or the event handler returned by the
[`add_word_listener`](#keyboard.add_word_listener) or [`add_abbreviation`](#keyboard.add_abbreviation) functions.



<a name="keyboard.remove_abbreviation"/>
## keyboard.**remove\_abbreviation**

Alias for [`remove_word_listener`](#keyboard.remove_word_listener).


<a name="keyboard.add_abbreviation"/>
## keyboard.**add\_abbreviation**(source\_text, replacement\_text, match\_suffix=True, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L477)


Registers a hotkey that replaces one typed text with another. For example

    add_abbreviation('tm', u'™')

Replaces every "tm" followed by a space with a ™ symbol (and no space). The
replacement is done by sending backspace events.

- `match_suffix` defines if endings of words should also be checked instead
of only whole words. E.g. if true, typing 'carpet'+space will trigger the
listener for 'pet'. Defaults to false, only whole words are checked.
- `timeout` is the maximum number of seconds between typed characters before
the current word is discarded. Defaults to 2 seconds.

For more details see [`add_word_listener`](#keyboard.add_word_listener).



<a name="keyboard.register_abbreviation"/>
## keyboard.**register\_abbreviation**

Alias for [`add_abbreviation`](#keyboard.add_abbreviation).


<a name="keyboard.stash_state"/>
## keyboard.**stash\_state**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L503)


Builds a list of all currently pressed scan codes, releases them and returns
the list. Pairs well with [`restore_state`](#keyboard.restore_state).



<a name="keyboard.restore_state"/>
## keyboard.**restore\_state**(scan\_codes)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L513)


Given a list of scan_codes ensures these keys, and only these keys, are
pressed. Pairs well with [`stash_state`](#keyboard.stash_state).



<a name="keyboard.write"/>
## keyboard.**write**(text, delay=0, restore\_state\_after=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L525)


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



<a name="keyboard.to_scan_code"/>
## keyboard.**to\_scan\_code**(key)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L568)


Returns the scan code for a given key name (or scan code, i.e. do nothing).
Note that a name may belong to more than one physical key, in which case
one of the scan codes will be chosen.



<a name="keyboard.send"/>
## keyboard.**send**(combination, do\_press=True, do\_release=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L580)


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



<a name="keyboard.press"/>
## keyboard.**press**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L605)

Presses and holds down a key combination (see [`send`](#keyboard.send)). 


<a name="keyboard.release"/>
## keyboard.**release**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L609)

Releases a key combination (see [`send`](#keyboard.send)). 


<a name="keyboard.press_and_release"/>
## keyboard.**press\_and\_release**(combination)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L613)

Presses and releases the key combination (see [`send`](#keyboard.send)). 


<a name="keyboard.wait"/>
## keyboard.**wait**(combination=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L617)


Blocks the program execution until the given key combination is pressed or,
if given no parameters, blocks forever.



<a name="keyboard.read_key"/>
## keyboard.**read\_key**(filter=&lt;lambda&gt;)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L629)


Blocks until a keyboard event happens, then returns that event.



<a name="keyboard.record"/>
## keyboard.**record**(until=&#x27;escape&#x27;)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L645)


Records all keyboard events from all keyboards until the user presses the
given key combination. Then returns the list of events recorded, of type
`keyboard.KeyboardEvent`. Pairs well with
[`play(events)`](#keyboard.play).

Note: this is a blocking function.
Note: for more details on the keyboard hook and events see [`hook`](#keyboard.hook).



<a name="keyboard.play"/>
## keyboard.**play**(events, speed\_factor=1.0)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L661)


Plays a sequence of recorded events, maintaining the relative time
intervals. If speed_factor is <= 0 then the actions are replayed as fast
as the OS allows. Pairs well with [`record()`](#keyboard.record).

Note: the current keyboard state is cleared at the beginning and restored at
the end of the function.



<a name="keyboard.replay"/>
## keyboard.**replay**

Alias for [`play`](#keyboard.play).


<a name="keyboard.get_typed_strings"/>
## keyboard.**get\_typed\_strings**(events, allow\_backspace=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L689)


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



