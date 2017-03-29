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
