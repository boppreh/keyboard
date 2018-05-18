# 0.13.2

- [Mac] Fixed "map_name" error (i.e. implement new backend API).
- [Win] Improve detection of "right alt" key.
- [All] Misc fixes for edge cases.


# 0.13.1

- [Windows/Linux] Fixed installation.


# 0.13.0

- [All] New `remap_` and `block_` functions.
- [All] New high-level functions for parsing and converting hotkey names.
- [All] Added `.modifiers` and `.is_keymap` attribute to events.
- [All] Event name now matches character typed (e.g. now event from key `1` reports as `!` if shift is pressed). This gives `get_typed_strings` more precision.
- [Windows] New key suppression system should fix most bugs with `suppress=True`.
- [Linux] Added `.device` attribute to events.
- [All] Many, many bugfixes.


# 0.11.0

- [Windows] Used explicit WinDLL to fix "expected CFunctionType instance instead of CFunctionType".
- [Windows] Added more Windows virtual key codes for key name mapping (should fix .e.g "?").
- [All] Fixed canonicalization removing too much space (thanks @iliazeus).
- [All] Added `start_recording` and `stop_recording` for more flexible macros (thanks @softuser25 for the suggestion).
- [All] Added `read_shortcut` function.
- [All] Added `get_shortcut_name` function.
- [All] Cleaned up `examples` folder and added more examples.


# 0.10.4

- [Mac] Added aliases for modifiers (control->ctrl, option->alt, command->windows).
- [All] Add reference to mouse project.
- [All] Use WinDLL for mouse part instead of raw ctypes.windll.user32.


# 0.10.3

- [All] Fix PyPI readme (https://github.com/pypa/setuptools/issues/1126).
- [All] Remove bdist from release (PEP 527).


# 0.10.2

- [All] Removed ctypes type-hints to avoid runtime errors in unusual systems.
- [All] Add mention of new `mouse` project.
- [All] Add mention of experimental OS X support.
- [All] Fixes to release process.


# 0.10.0

- [OS X] Added experimental OS X support (thanks @glitchassassin!).
- [Windows] Fixed error on fractional `mouse.wheel()` (thanks @bobonthenet!).
- [Windows] Fixed name for arrow keys` virtual key codes.
- [Windows] Make backend easier to use in other projects (e.g. `_winkeyboard.prepare_intercept`).
- [Linux] Fixed mouse support in Mint VirtualBox guest (thanks @foodforarabbit!).
- [All] Added mouse alias `hold = press` (thanks @DanMossa!).
- [All] Added `mouse.drag`.
- [All] Added examples on how to use the library.
- [All] Update docs to mention how to differentiate key presses and releases (thanks @TrakJohnson!).
- [All] Change the default value of `add_abbreviation(..., match_suffix)`.


# 0.9.13

- [Windows] Fix bug when listening to alt-gr.
- [All] Add `trigger_on_release` parameter to `add_hotkey`.
- [All] Make `wait` and `read_key` interruptible by ctrl+c.
- [All] Small fixes on code/name mapping.

Thanks glitchassassin and BladeMight for the pull requests.


# 0.9.12

- [Windows] Fixed some incorrect key names (e.g. enter as '\r', and left keys reported as 'right ...')
- [Python2] `long` scan codes no longer crash the `matches` function.
- [All] add `read_key` function, which blocks and returns the next event.
- [All] Added makefile.


# 0.9.11

- [All] Fixed Python2 compatbility.
- [All] Updated release process to always run both Python2 and Python3 tests before publishing.


# 0.9.10

- [Windows] Add `suppress` parameter to hotkeys to block the combination from being sent to other programs.
- [Windows] Better key mapping for common keys (now using Virtual Key Codes when possible).
- [Windows] Normalize numpad and key code names.
- [Linux] Errors about requiring sudo are now thrown in the main thread, making them catchable.
- [All] `wheel` method in mouse module.


# 0.9.9

- [Windows] Include scan codes in generated events, instead of only Virtual Key Codes. This allows software like Citrix to receive the events correctly.
- [Windows] Fix bugs that prevented keys without associated Virtual Key Codes from beign processed.


# 0.9.8

- Allow sending of keypad events on both Windows and Linux.
- Fixed bug where key sending was failing on Linux notebooks.


# 0.9.7

- [Windows] Fixed a bug where the `windows` key name failed to map to a scan code.


# 0.9.6

- [Windows] Modifier keys now report 'left' or 'right' on their names.
- [Windows] Keypad attribute should be much more accurate even with NumLock.
- [Windows] Media keys are now fully supported for both report and playback.


# 0.9.5

- [Windows] Add aliases to correct page down/page up names.
- [Windows] Fixed a bug where left and right key events were being created without names.
- [Windows] Prefer to report home/page up/page down/end keys as such instead of their keypad names.


# 0.9.4

- Distinguish events from numeric pad keys (`event.is_keypad`).
- [Linux] Annotate event with device id (`event.device`).


# 0.9.3

- [Linux] Create fake keyboard with uinput if none is available.
- [Linux] Avoid errors when an unknown key is pressed.


# 0.9.2

- Streamline release process


# 0.9.1

- Add `add_abbreviation` and `register_word_listener` functions.
- Add functions for low level hooks (`hook`, `hook_key`).
- Add `on_press` and `on_release` functions.
- Add alternative names (aliases) for many functions.
- Add large number of alternative key names, especially for accents.
- Make module produce and consume JSON if ran as script (`python -m keyboard`).
- 100% test coverage.

- [Linux] Add support for writing arbitrary Unicode.
- [Linux] Look for Linux keyboard devices in /proc/bus/input/devices.
- [Linux] Aggregate as many devices as possibles (e.g. USB keyboard on notebook).
- [Linux] Improved support for internationalized keys.

- [Windows] Process keys asynchronously to reduce key delay.

- [All] Too many bugfixes to count.
- [All] Major backend refactor.

# 0.7.1

- Alpha version.
