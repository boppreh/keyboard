keyboard
========

*keyboard* is a small Python library to capture keyboard events in Windows. It
is meant as a replacement for the keyboard functions of pyHook, but simpler,
100% Python and without the dead-keys bug.

To use it just call `add_handler(function)` and `remove_handler(function)`.
Whenever a keyboard event is detected (at any application, regardless of focus),
all registered handlers are called, in order, with a `KeyboardEvent` object as
argument.

`KeyboardEvent` contains the event type (`event_type`), virtual key code
(`key_code`), keyboard scan code (`scan_code`) and timestamp in milliseconds
(`time`).

A `is_pressed(key_code)` function is also available.

The listening loop is kept in a separate thread, started only when the first
handler is added and closes gracefully with the interpreter.

This program makes no attempt to hide itself, so don't use it for keyloggers.
