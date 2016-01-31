keyboard
========

*keyboard* is a small Python library to capture keyboard events in Windows and
Linux. It is meant as a replacement for the keyboard functions of [pyHook](http://sourceforge.net/apps/mediawiki/pyhook/index.php?title=Main_Page),
but simpler, 100% Python and without the dead-keys bug.

It is in process of expansion, but the keyboard hook part is in working order.

The listening loop is kept in a separate thread, started only when the first
handler is added and closes gracefully with the interpreter.

This program makes no attempt to hide itself, so don't use it for keyloggers.
