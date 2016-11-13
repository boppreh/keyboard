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
