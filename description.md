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
