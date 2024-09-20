import keyboard
from keyboard._keyboard_event import KeyboardEvent
from threading import Timer

# Dictionary to map keys
mapping_keys = {
    # lt
    61: 'q',
    21: 'w',
    65: 'f',
    20: 'p',
    58: 'b',
    # lm
    32: 'a',
    36: 'r',
    38: 's',
    33: 't',
    31: 'g',
    # lb
    18: 'z',
    22: 'x',
    24: 'c',
    19: 'd',
    17: 'v',
    # RT
    5: 'j',
    10: 'l',
    9: 'u',
    8: 'y',
    4: ';',
    # RM
    34: 'm',
    # 57: 'n',
    64: 'e',
    35: 'i',
    62: 'o',
    # RB
    48: 'k',
    93: 'h',
    115: ',',
    49: '.',
    80: '/',

}

# Hold-tap settings
hold_tap_keys = {
    # Hold space for 0.2 seconds to trigger shift
    37: ('space', 'tab', 0.2),
    57: ('n', 'shift', 0.2),
}

# Layer-tap settings
layer_tap_keys = {
    # Hold 'f' key for 0.2 seconds to activate layer 1
    # 33: (1, 'f', 0.2),
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
layer_activated = False


def on_press(key_code: int):
    global layer_activated
    if key_code in pressed_keys:
        return

    pressed_keys.add(key_code)

    if key_code in layers[current_layer]:
        keyboard.press(layers[current_layer][key_code])

    if key_code in hold_tap_keys:
        _, hold_key, hold_time = hold_tap_keys[key_code]
        hold_tap_timers[key_code] = Timer(
            hold_time, lambda: on_hold(key_code, hold_key))
        hold_tap_timers[key_code].start()

    if key_code in layer_tap_keys:
        layer, _, hold_time = layer_tap_keys[key_code]
        layer_tap_timers[key_code] = Timer(
            hold_time, lambda: activate_layer(key_code, layer))
        layer_tap_timers[key_code].start()


def on_release(key_code: int):
    global current_layer, layer_activated

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
            if not layer_activated:
                keyboard.press_and_release(tap_key)
        else:
            current_layer = 0  # Reset to base layer
            layer_activated = False

    pressed_keys.discard(key_code)


def on_hold(key_code: int, hold_key):
    keyboard.press(hold_key)
    del hold_tap_timers[key_code]


def activate_layer(key_code: int, layer: int):
    global current_layer, layer_activated
    current_layer = layer
    layer_activated = True
    del layer_tap_timers[key_code]


def callback(event: KeyboardEvent):
    # print(f"code {event.scan_code}")
    # # return
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
