keyboard
========

Take full control of your keyboard with this small Python library. Hook global events, register hotkeys, simulate key presses and much more.

- Global event hook (captures keys regardless of focus).
- Simulates key presses.
- Complex hotkey support (e.g. `Ctrl+Shift+A` followed by `Alt+Space`) with controllable timeout.
- Maps keys as they actually are, with full internationalization support ('Ctrl+ç').
- Events automatically captured in separate thread, doesn't block main program.
- Pure Python, no C modules to be compiled.
- Zero dependencies.
- Works with Windows and Linux (if you have a Mac, pull requests are welcome).
- Python 2 and Python 3.
- Mouse support coming soon.
- Tested and documented.

Example:

```
import keyboard

# Press PAGE UP then PAGE DOWN to type "foobar".
keyboard.add_hotkey('page up, page down', lambda: keyboard.write('foobar'))

# Blocks until you press esc.
wait('esc')
```

This program makes no attempt to hide itself, so don't use it for keyloggers.