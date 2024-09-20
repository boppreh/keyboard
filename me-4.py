import keyboard
from keyboard._keyboard_event import KeyboardEvent
from threading import Timer

# Dictionary to map keys
mapping_keys = {
    30: 'b',
    48: 'a',
}

# Hold-tap settings
hold_tap_keys = {
    # Hold space for 0.2 seconds to trigger shift
    46: ('c', 'd', 0.2),
}

# Layer-tap settings
layer_tap_keys = {
    # Hold 'f' key for 0.2 seconds to activate layer 1
    33: (1, 'f', 0.2),
}

# Layer definitions
layers = {
    0: mapping_keys,  # Base layer
    1: {  # Layer 1
        30: 'x',
        48: 'y',
    },
}

# Global variables to track key states
pressed_keys = set()
hold_tap_timers = {}
layer_tap_timers = {}
current_layer = 0

def on_press(key_code: int):
    if key_code in pressed_keys:
        return

    pressed_keys.add(key_code)

    if key_code in layers[current_layer]:
        keyboard.press(layers[current_layer][key_code])

    if key_code in hold_tap_keys:
        _, hold_key, hold_time = hold_tap_keys[key_code]
        hold_tap_timers[key_code] = Timer(hold_time, lambda: on_hold(key_code, hold_key))
        hold_tap_timers[key_code].start()

    if key_code in layer_tap_keys:
        layer, _, hold_time = layer_tap_keys[key_code]
        layer_tap_timers[key_code] = Timer(hold_time, lambda: activate_layer(layer))
        layer_tap_timers[key_code].start()

def on_release(key_code: int):
    global current_layer

    if key_code in layers[current_layer]:
        keyboard.release(layers[current_layer][key_code])

    if key_code in hold_tap_keys:
        tap_key, hold_key, _ = hold_tap_keys[key_code]
        if key_code in hold_tap_timers:
            hold_tap_timers[key_code].cancel()
            del hold_tap_timers[key_code]
            keyboard.press_and_release(tap_key)
        else:
            keyboard.release(hold_key)

    if key_code in layer_tap_keys:
        _, tap_key, _ = layer_tap_keys[key_code]
        if key_code in layer_tap_timers:
            layer_tap_timers[key_code].cancel()
            del layer_tap_timers[key_code]
            keyboard.press_and_release(tap_key)
        else:
            current_layer = 0  # Reset to base layer

    pressed_keys.discard(key_code)

def on_hold(key_code: int, hold_key):
    keyboard.press(hold_key)
    del hold_tap_timers[key_code]

def activate_layer(layer):
    global current_layer
    current_layer = layer

def callback(event: KeyboardEvent):
    if not isinstance(event.scan_code, int):
        return
    if event.event_type == keyboard.KEY_DOWN:
        on_press(event.scan_code)
    elif event.event_type == keyboard.KEY_UP:
        on_release(event.scan_code)

keyboard.hook(callback, True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print("Exiting...")
finally:
    keyboard.unhook_all()