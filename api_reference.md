None


# API
#### Table of Contents
<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**ALLOW**](#keyboard.ALLOW)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**Hotkey**](#keyboard.Hotkey)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**KEY\_DOWN**](#keyboard.KEY_DOWN)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**KEY\_UP**](#keyboard.KEY_UP)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**Key**](#keyboard.Key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**KeyboardEvent**](#keyboard.KeyboardEvent)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**SUPPRESS**](#keyboard.SUPPRESS)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**SUSPEND**](#keyboard.SUSPEND)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**Step**](#keyboard.Step)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**all\_modifiers**](#keyboard.all_modifiers)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**sided\_modifiers**](#keyboard.sided_modifiers)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**version**](#keyboard.version)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**ensure\_state**](#keyboard.ensure_state)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**is\_modifier**](#keyboard.is_modifier)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**start**](#keyboard.start)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**stop**](#keyboard.stop)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**reload**](#keyboard.reload)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**hook**](#keyboard.hook) *(aliases: `add_hook`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**hook\_key**](#keyboard.hook_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**add\_hotkey**](#keyboard.add_hotkey)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**key\_to\_scan\_codes**](#keyboard.key_to_scan_codes)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**parse\_hotkey**](#keyboard.parse_hotkey)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**send**](#keyboard.send) *(aliases: `press_and_release`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**press**](#keyboard.press)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**release**](#keyboard.release)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**is\_pressed**](#keyboard.is_pressed)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**call\_later**](#keyboard.call_later)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**on\_press**](#keyboard.on_press)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**on\_release**](#keyboard.on_release)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**on\_press\_key**](#keyboard.on_press_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**on\_release\_key**](#keyboard.on_release_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**block\_key**](#keyboard.block_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**unhook**](#keyboard.unhook) *(aliases: `clear_hotkey`, `remove_abbreviation`, `remove_hotkey`, `remove_word_listener`, `unblock_key`, `unhook_key`, `unregister_hotkey`, `unremap_hotkey`, `unremap_key`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**unhook\_all**](#keyboard.unhook_all) *(aliases: `clear_all_hotkeys`, `remove_all_hotkeys`, `unhook_all_hotkeys`, `unregister_all_hotkeys`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**remap\_key**](#keyboard.remap_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**remap\_hotkey**](#keyboard.remap_hotkey)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**stash\_state**](#keyboard.stash_state)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**restore\_state**](#keyboard.restore_state)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**restore\_modifiers**](#keyboard.restore_modifiers)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**write**](#keyboard.write)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**wait**](#keyboard.wait)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**get\_hotkey\_name**](#keyboard.get_hotkey_name)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**read\_event**](#keyboard.read_event)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**read\_key**](#keyboard.read_key)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**read\_hotkey**](#keyboard.read_hotkey)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**get\_typed\_strings**](#keyboard.get_typed_strings)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**start\_recording**](#keyboard.start_recording)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**stop\_recording**](#keyboard.stop_recording)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**record**](#keyboard.record)<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**play**](#keyboard.play) *(aliases: `replay`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**add\_word\_listener**](#keyboard.add_word_listener) *(aliases: `register_word_listener`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**add\_abbreviation**](#keyboard.add_abbreviation) *(aliases: `register_abbreviation`)*<!-- This documentation was automatically generated. Please edit the source code files, and not this document directly. -->

- [keyboard.**normalize\_name**](#keyboard.normalize_name)


<a name="keyboard.ALLOW"/>

## keyboard.**ALLOW**




<a name="keyboard.Hotkey"/>

## class keyboard.**Hotkey**






<a name="keyboard.KEY_DOWN"/>

## keyboard.**KEY\_DOWN**
```py
= 'down'
```

<a name="keyboard.KEY_UP"/>

## keyboard.**KEY\_UP**
```py
= 'up'
```

<a name="keyboard.Key"/>

## class keyboard.**Key**






<a name="keyboard.KeyboardEvent"/>

## class keyboard.**KeyboardEvent**




<a name="KeyboardEvent.device"/>

### KeyboardEvent.**device**


<a name="KeyboardEvent.event_type"/>

### KeyboardEvent.**event\_type**


<a name="KeyboardEvent.is_keypad"/>

### KeyboardEvent.**is\_keypad**


<a name="KeyboardEvent.modifiers"/>

### KeyboardEvent.**modifiers**


<a name="KeyboardEvent.name"/>

### KeyboardEvent.**name**


<a name="KeyboardEvent.scan_code"/>

### KeyboardEvent.**scan\_code**


<a name="KeyboardEvent.time"/>

### KeyboardEvent.**time**


<a name="KeyboardEvent.to_json"/>

### KeyboardEvent.**to\_json**(self, ensure\_ascii=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/_keyboard_event.py#L43)






<a name="keyboard.SUPPRESS"/>

## keyboard.**SUPPRESS**




<a name="keyboard.SUSPEND"/>

## keyboard.**SUSPEND**




<a name="keyboard.Step"/>

## class keyboard.**Step**






<a name="keyboard.all_modifiers"/>

## keyboard.**all\_modifiers**
```py
= {'alt', 'alt gr', 'ctrl', 'left alt', 'left ctrl', 'left shift', 'left windows', 'right alt', 'right ctrl', 'right shift', 'right windows', 'shift', 'windows'}
```

<a name="keyboard.sided_modifiers"/>

## keyboard.**sided\_modifiers**
```py
= {'alt', 'ctrl', 'shift', 'windows'}
```

<a name="keyboard.version"/>

## keyboard.**version**
```py
= '0.13.5'
```

<a name="keyboard.ensure_state"/>

<a name="keyboard.is_modifier"/>

## keyboard.**is\_modifier**(key)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L60)


Returns True if `key` is a scan code or name of a modifier key.



<a name="keyboard.start"/>

## keyboard.**start**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L355)


Starts the global keyboard listener, including background threads, to process
OS events.



<a name="keyboard.stop"/>

## keyboard.**stop**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L363)


Stops the global keyboard listener, and signals the background threads to exit.



<a name="keyboard.reload"/>

## keyboard.**reload**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L370)


Restarts the global keyboard listener, including background threads, and reloads
the mapping of scan codes to key names.



<a name="keyboard.hook"/>

## keyboard.**hook**(callback, suppress=False, extra\_ids=())

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L413)


Installs a global listener on all available keyboards, invoking `callback`
each time a key is pressed or released.

If `suppress` is True, then the callback is invoked before the event is
received by other programs, and the event is suppressed unless the callback
returns `keyboard.ALLOW`.

The event passed to the callback is of type `keyboard.KeyboardEvent`,
with the following attributes:

- `name`: an Unicode representation of the character (e.g. "&") or
description (e.g.  "space"). The name is always lower-case.
- `scan_code`: number representing the physical key, e.g. 55.
- `time`: timestamp of the time the event occurred, with as much precision
as given by the OS.

Returns a Hook object with `.enable()` and `.disable()` methods.

Example:

```py
hook(lambda event: print('Got event:', event))
```



<a name="keyboard.hook_key"/>

## keyboard.**hook\_key**(key, callback, suppress=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L461)


Hooks key up and key down events for a single key. Returns the event handler
created.

If `suppress` is True, then the callback is invoked before the event is
received by other programs, and the event is suppressed unless the callback
returns `keyboard.ALLOW`.

Returns a Hook object with `.enable()` and `.disable()` methods.



<a name="keyboard.add_hotkey"/>

## keyboard.**add\_hotkey**(hotkey, callback, args=(), suppress=True, timeout=1, trigger\_on\_release=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L672)


Invokes a callback every time a hotkey is pressed. The hotkey must
be in the format `ctrl+shift+a, s`. This would trigger when the user holds
ctrl, shift and "a" at once, releases, and then presses "s". To represent
literal commas, pluses, and spaces, use their names ('comma', 'plus',
'space').

- `args` is an optional list of arguments to passed to the callback during
each invocation.
- `suppress` defines if successful triggers should block the keys from being
sent to other programs.
- `timeout` is the amount of seconds allowed to pass between key presses.
- `trigger_on_release` if true, the callback is invoked on key release instead
of key press.

Returns a Hook object with `.enable()` and `.disable()` methods.

Note: hotkeys are activated when the last key is *pressed*, not released.
Note: the callback is executed in a separate thread, asynchronously. For an
example of how to use a callback synchronously, see [`wait`](#keyboard.wait).

Examples:

```py

# Different but equivalent ways to listen for a spacebar key press.
add_hotkey(' ', print, args=['space was pressed'])
add_hotkey('space', print, args=['space was pressed'])
add_hotkey('Space', print, args=['space was pressed'])
# Here 57 represents the keyboard code for spacebar; so you will be
# pressing 'spacebar', not '57' to activate the print function.
add_hotkey(57, print, args=['space was pressed'])

add_hotkey('ctrl+q', quit)
add_hotkey('ctrl+alt+enter, space', some_callback)
```



<a name="keyboard.key_to_scan_codes"/>

## keyboard.**key\_to\_scan\_codes**(key, default=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L722)


Returns a list of scan codes associated with this key (name or scan code).



<a name="keyboard.parse_hotkey"/>

## keyboard.**parse\_hotkey**(hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L810)


Parses a user-provided hotkey into nested tuples representing the
parsed structure, with the bottom values being lists of scan codes.
Also accepts raw scan codes, which are then wrapped in the required
number of nestings.

Example:

```py

parse_hotkey("alt+shift+a, alt+b, c")
#    Keys:    ^~^ ^~~~^ ^  ^~^ ^  ^
#    Steps:   ^~~~~~~~~~^  ^~~~^  ^

# ((alt_codes, shift_codes, a_codes), (alt_codes, b_codes), (c_codes,))
```



<a name="keyboard.send"/>

## keyboard.**send**(hotkey, do\_press=True, do\_release=True, process\_events=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L855)


Sends OS events that perform the given *hotkey* hotkey.

- `hotkey` can be either a scan code (e.g. 57 for space), single key
(e.g. 'space') or multi-key, multi-step hotkey (e.g. 'alt+F4, enter').
- `do_press` if true then press events are sent. Defaults to True.
- `do_release` if true then release events are sent. Defaults to True.

```py

send(57)
send('ctrl+alt+del')
send('alt+F4, enter')
send('shift+s')
```

Note: keys are released in the opposite order they were pressed.



<a name="keyboard.press"/>

## keyboard.**press**(hotkey, process\_events=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L892)

Presses and holds down a hotkey (see [`send`](#keyboard.send)).


<a name="keyboard.release"/>

## keyboard.**release**(hotkey, process\_events=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L897)

Releases a hotkey (see [`send`](#keyboard.send)).


<a name="keyboard.is_pressed"/>

## keyboard.**is\_pressed**(hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L902)


Returns True if the key is pressed.

```py

is_pressed(57) #-> True
is_pressed('space') #-> True
is_pressed('ctrl+space') #-> True
```



<a name="keyboard.call_later"/>

## keyboard.**call\_later**(fn, args=(), delay=0.001)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L929)


Calls the provided function in a new thread after waiting some time.
Useful for giving the system some time to process an event, without suppressing
the current execution flow.



<a name="keyboard.on_press"/>

## keyboard.**on\_press**(callback, suppress=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L939)


Invokes `callback` for every KEY_DOWN event. For details see [`hook`](#keyboard.hook).



<a name="keyboard.on_release"/>

## keyboard.**on\_release**(callback, suppress=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L946)


Invokes `callback` for every KEY_UP event. For details see [`hook`](#keyboard.hook).



<a name="keyboard.on_press_key"/>

## keyboard.**on\_press\_key**(key, callback, suppress=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L953)


Invokes `callback` for KEY_DOWN event related to the given key. For details see [`hook`](#keyboard.hook).



<a name="keyboard.on_release_key"/>

## keyboard.**on\_release\_key**(key, callback, suppress=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L962)


Invokes `callback` for KEY_UP event related to the given key. For details see [`hook`](#keyboard.hook).



<a name="keyboard.block_key"/>

## keyboard.**block\_key**(key)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L971)


Suppresses all key events of the given key, regardless of modifiers.



<a name="keyboard.unhook"/>

## keyboard.**unhook**(callback\_or\_hook\_or\_hotkey)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L978)


Removes a previously added hook, either by callback or by the return value
of [`hook`](#keyboard.hook).



<a name="keyboard.unhook_all"/>

## keyboard.**unhook\_all**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L997)


Removes all keyboard hooks in use, including hotkeys, abbreviations, word
listeners, blocked keys, [`record`](#keyboard.record)ers and [`wait`](#keyboard.wait)s.



<a name="keyboard.remap_key"/>

## keyboard.**remap\_key**(src, dst)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1011)


Whenever the key `src` is pressed or released, regardless of modifiers,
press or release the hotkey `dst` instead.



<a name="keyboard.remap_hotkey"/>

## keyboard.**remap\_hotkey**(src, dst, suppress=True, trigger\_on\_release=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1026)


Whenever the hotkey `src` is pressed, suppress it and send
`dst` instead.

Example:

```py

remap('alt+w', 'ctrl+up')
```



<a name="keyboard.stash_state"/>

## keyboard.**stash\_state**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1074)


Builds a list of all currently pressed scan codes, releases them and returns
the list. Pairs well with [`restore_state`](#keyboard.restore_state) and [`restore_modifiers`](#keyboard.restore_modifiers).



<a name="keyboard.restore_state"/>

## keyboard.**restore\_state**(scan\_codes)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1087)


Given a list of scan_codes ensures these keys, and only these keys, are
pressed. Pairs well with [`stash_state`](#keyboard.stash_state), alternative to [`restore_modifiers`](#keyboard.restore_modifiers).



<a name="keyboard.restore_modifiers"/>

## keyboard.**restore\_modifiers**(scan\_codes)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1105)


Like [`restore_state`](#keyboard.restore_state), but only restores modifier keys.



<a name="keyboard.write"/>

## keyboard.**write**(text, delay=0, restore\_state\_after=True, exact=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1112)


Sends artificial keyboard events to the OS, simulating the typing of a given
text. Characters not available on the keyboard are typed as explicit unicode
characters using OS-specific functionality, such as alt+codepoint.

To ensure text integrity, all currently pressed keys are released before
the text is typed, and modifiers are restored afterwards.

- `delay` is the number of seconds to wait between keypresses, defaults to
no delay.
- `restore_state_after` can be used to restore the state of pressed keys
after the text is typed, i.e. presses the keys that were released at the
beginning. Defaults to True.
- `exact` forces typing all characters as explicit unicode (e.g.
alt+codepoint or special events). If None, uses platform-specific suggested
value.



<a name="keyboard.wait"/>

## keyboard.**wait**(hotkey=None, suppress=False, trigger\_on\_release=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1169)


Blocks the program execution until the given hotkey is pressed or,
if given no parameters, blocks forever.



<a name="keyboard.get_hotkey_name"/>

## keyboard.**get\_hotkey\_name**(names=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1188)


Returns a string representation of hotkey from the given key names, or
the currently pressed keys if not given.  This function:

- normalizes names;
- removes "left" and "right" prefixes;
- replaces the "+" key name with "plus" to avoid ambiguity;
- puts modifier keys first, in a standardized order;
- sort remaining keys;
- finally, joins everything with "+".

Example:

```py

get_hotkey_name(['+', 'left ctrl', 'shift'])
# "ctrl+shift+plus"
```



<a name="keyboard.read_event"/>

## keyboard.**read\_event**(suppress=False, timeout=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1223)


Blocks until a keyboard event happens, then returns that event.

If `timeout` is not None, waits at most `timeout` seconds else raise a
queue.Empty exception.



<a name="keyboard.read_key"/>

## keyboard.**read\_key**(suppress=False, timeout=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1235)


Blocks until a keyboard event happens, then returns that event's name or,
if missing, its scan code.

If `timeout` is not None, waits at most `timeout` seconds else raise a
queue.Empty exception.



<a name="keyboard.read_hotkey"/>

## keyboard.**read\_hotkey**(suppress=True, timeout=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1251)


Similar to [`read_key()`](#keyboard.read_key), but blocks until the user presses and releases a
hotkey (or single key), then returns a string representing the hotkey
pressed.

If `timeout` is not None, waits at most `timeout` seconds else raise a
queue.Empty exception.

Example:

```py

read_hotkey()
# "ctrl+shift+p"
```



<a name="keyboard.get_typed_strings"/>

## keyboard.**get\_typed\_strings**(events, allow\_backspace=True)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1277)


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

```py

get_type_strings(record()) #-> ['This is what', 'I recorded', '']
```



<a name="keyboard.start_recording"/>

## keyboard.**start\_recording**(recorded\_events\_queue=None)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1331)


Starts recording all keyboard events into a global variable, or the given
queue if any. Returns the queue of events and the hooked function.

Use [`stop_recording()`](#keyboard.stop_recording) or [`unhook(hooked_function)`](#keyboard.unhook) to stop.



<a name="keyboard.stop_recording"/>

## keyboard.**stop\_recording**()

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1344)


Stops the global recording of events and returns a list of the events
captured.



<a name="keyboard.record"/>

## keyboard.**record**(until=&#x27;escape&#x27;, suppress=False, trigger\_on\_release=False)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1358)


Records all keyboard events from all keyboards until the user presses the
given hotkey. Then returns the list of events recorded, of type
`keyboard.KeyboardEvent`. Pairs well with
[`play(events)`](#keyboard.play).

Note: this is a suppressing function.
Note: for more details on the keyboard hook and events see [`hook`](#keyboard.hook).



<a name="keyboard.play"/>

## keyboard.**play**(events, speed\_factor=1.0)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1373)


Plays a sequence of recorded events, maintaining the relative time
intervals. If speed_factor is <= 0 then the actions are replayed as fast
as the OS allows. Pairs well with [`record()`](#keyboard.record).

Note: the current keyboard state is cleared at the beginning and restored at
the end of the function.



<a name="keyboard.add_word_listener"/>

## keyboard.**add\_word\_listener**(word, callback, triggers=[&#x27;space&#x27;], match\_suffix=False, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1399)


Invokes a callback every time a sequence of characters is typed (e.g. 'pet')
and followed by a trigger key (e.g. space). Modifiers (e.g. alt, ctrl,
shift) are ignored.

- `word` the typed text to be matched. E.g. 'pet'.
- `callback` is an argument-less function to be invoked each time the word
is typed.
- `triggers` is the list of keys that will cause a match to be checked. If
the user presses some key that is not a character (len>1) and not in
triggers, the characters so far will be discarded. By default the trigger
is only `space`.
- `match_suffix` defines if endings of words should also be checked instead
of only whole words. E.g. if true, typing 'carpet'+space will trigger the
listener for 'pet'. Defaults to false, only whole words are checked.
- `timeout` is the maximum number of seconds between typed characters before
the current word is discarded. Defaults to 2 seconds.

Returns the event handler created. To remove a word listener use
[`remove_word_listener(word)`](#keyboard.remove_word_listener), [`remove_word_listener(handler)`](#keyboard.remove_word_listener), or
`returned.disable()`.

Note: all actions are performed on key down. Key up events are ignored.
Note: word matches are **case sensitive**.



<a name="keyboard.add_abbreviation"/>

## keyboard.**add\_abbreviation**(source\_text, replacement\_text, match\_suffix=False, timeout=2)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/__init__.py#L1454)


Registers a hotkey that replaces one typed text with another. For example

```py

add_abbreviation('tm', u'™')
```

Replaces every "tm" followed by a space with a ™ symbol (and no space). The
replacement is done by sending backspace events.

- `match_suffix` defines if endings of words should also be checked instead
of only whole words. E.g. if true, typing 'carpet'+space will trigger the
listener for 'pet'. Defaults to false, only whole words are checked.
- `timeout` is the maximum number of seconds between typed characters before
the current word is discarded. Defaults to 2 seconds.

For more details see [`add_word_listener`](#keyboard.add_word_listener).



<a name="keyboard.normalize_name"/>

## keyboard.**normalize\_name**(name)

[\[source\]](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py#L1232)


Given a key name (e.g. "LEFT CONTROL"), clean up the string and convert to
the canonical representation (e.g. "left ctrl") if one is known.



