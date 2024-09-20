from pynput.keyboard import Key, Controller, KeyCode, Listener
import time

# Dictionary to map keys
key_mapping = {
    # keyboard.Key.ctrl_l: keyboard.Key.alt_l,
    # keyboard.Key.alt_l: keyboard.Key.ctrl_l,
    KeyCode.from_char('a'): KeyCode.from_char('b'),
    KeyCode.from_char('b'): KeyCode.from_char('a'),
}

# Hold-tap settings
hold_tap_keys = {
    # Hold space for 0.2 seconds to trigger shift
    Key.space: (Key.shift, 0.2),
}

# Global variables to track key states
keyboard = Controller()
pressed_keys = set()
hold_tap_timers = {}


def on_press(pressed_key):
    # Remap keys
    if pressed_key in key_mapping:
        pressed_key = key_mapping[pressed_key]
        pressed_keys.add(pressed_key)
        keyboard.press(pressed_key)


def on_release(pressed_key):
    if pressed_key in pressed_keys:
        pressed_keys.discard(pressed_key)
        # Release the remapped key
        keyboard.release(pressed_key)


# Collect events until released
with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
