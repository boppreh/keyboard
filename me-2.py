import threading
import keyboard
from keyboard._keyboard_event import KeyboardEvent
from threading import Timer

# Dictionary to map keys
key_mapping = {
    'a': 'b',
    'b': 'a',
}

# Hold-tap settings
hold_tap_keys = {
    # Hold space for 0.2 seconds to trigger shift
    'c': ('d', 0.2),
}

# Global variables to track key states
pressed_keys = set()
hold_tap_timers = {}

def on_press(event: KeyboardEvent):
    key = event.name

    # ignore repeating keys
    if key in pressed_keys:
        return

    # Remap keys
    if key in key_mapping:
        print(f"Pressed: {key}")
        pressed_keys.add(key)
        keyboard.press(key_mapping[key])

    # Handle hold-tap feature
    if key in hold_tap_keys:
        hold_key, hold_time = hold_tap_keys[key]
        hold_tap_timers[key] = Timer(hold_time, lambda: on_hold(key, hold_key))
        hold_tap_timers[key].start()

def on_release(event: KeyboardEvent):
    key = event.name

    # Cancel hold-tap timer if key is released
    if key in hold_tap_timers:
        hold_tap_timers[key].cancel()
        del hold_tap_timers[key]

    if key in pressed_keys:
      pressed_keys.discard(key)
      if key in key_mapping:
          pressed_keys.discard(key)
          keyboard.release(key_mapping[key])
          return
      keyboard.release(key)

def on_hold(key, hold_key):
    pressed_keys.discard(key)
    pressed_keys.add(hold_key)
    keyboard.press(hold_key)
    del hold_tap_timers[key]
    # if key in pressed_keys and key not in hold_tap_timers:
    #   hold_tap_timers[key] = keyboard.start_recording()
    # elif key not in pressed_keys and key in hold_tap_timers:
    #   elapsed_time = keyboard.stop_recording()
    #   if elapsed_time >= hold_time:
    #       # keyboard.press_and_release(hold_key)
    #       keyboard.press(hold_key)
    #   del hold_tap_timers[key]

def callback(event: KeyboardEvent):
    print(f"event.name: {event.name}")
    if event.event_type == keyboard.KEY_DOWN:
        on_press(event)
    elif event.event_type == keyboard.KEY_UP:
        on_release(event)


keyboard.hook(callback, True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print("Exiting...")
finally:
    keyboard.unhook_all()
