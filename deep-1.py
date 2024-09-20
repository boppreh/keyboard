from pynput import keyboard
import threading
import time

# Dictionary to map keys
key_mapping = {
    keyboard.Key.ctrl_l: keyboard.Key.alt_l,
    keyboard.Key.alt_l: keyboard.Key.ctrl_l,
    keyboard.KeyCode.from_char('a'): keyboard.KeyCode.from_char('b'),
    keyboard.KeyCode.from_char('b'): keyboard.KeyCode.from_char('a'),
}

# Hold-tap settings
hold_tap_keys = {
    # Hold space for 0.2 seconds to trigger shift
    keyboard.Key.space: (keyboard.Key.shift, 0.2),
}

# Global variables to track key states
pressed_keys = set()
hold_tap_timers = {}


def on_press(key):
    global pressed_keys

    # Remap keys
    if key in key_mapping:
        key = key_mapping[key]

    # Handle hold-tap feature
    if key in hold_tap_keys:
        hold_key, hold_time = hold_tap_keys[key]
        hold_tap_timers[key] = threading.Timer(hold_time, lambda: on_hold(key, hold_key))
        hold_tap_timers[key].start()

    # Simulate key press
    pressed_keys.add(key)
    with keyboard.Controller() as controller:
        for k in pressed_keys:
            controller.press(k)


def on_release(key):
    global pressed_keys

    # Cancel hold-tap timer if key is released
    if key in hold_tap_timers:
        hold_tap_timers[key].cancel()
        del hold_tap_timers[key]

    # Simulate key release
    pressed_keys.discard(key)
    with keyboard.Controller() as controller:
        for k in pressed_keys:
            controller.release(k)


def on_hold(key, hold_key):
    global pressed_keys

    # Simulate hold key press
    with keyboard.Controller() as controller:
        controller.press(hold_key)
        pressed_keys.add(hold_key)


# Start listening to keyboard events
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
