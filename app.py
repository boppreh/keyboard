import keyboard
import time
import json


class KeyboardInterceptor:
    def __init__(self, config_file):
        self.keymap = {}
        self.hold_tap_config = {}
        self.pressed_keys = {}
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            self.keymap = config.get('keymap', {})
            self.hold_tap_config = config.get('hold_tap', {})

    def on_key_event(self, event):
        if event.event_type == keyboard.KEY_DOWN:
            self.handle_key_down(event.name)
        elif event.event_type == keyboard.KEY_UP:
            self.handle_key_up(event.name)

    def handle_key_down(self, key):
        remapped_key = self.keymap.get(key, key)

        if remapped_key in self.hold_tap_config:
            self.pressed_keys[remapped_key] = time.time()
            hold_time_ms = self.hold_tap_config[remapped_key]['hold_time_ms']

            # Schedule the hold behavior
            keyboard.on_press_key(remapped_key, lambda _: self.execute_hold_behavior(
                remapped_key), suppress=True)

            # Schedule the tap behavior
            keyboard.call_later(self.execute_tap_behavior, args=(
                remapped_key,), delay=hold_time_ms/1000)
        else:
            keyboard.press(remapped_key)

    def handle_key_up(self, key):
        remapped_key = self.keymap.get(key, key)

        if remapped_key in self.hold_tap_config:
            press_time = self.pressed_keys.pop(remapped_key, None)
            if press_time:
                elapsed_time = (time.time() - press_time) * 1000
                hold_time_ms = self.hold_tap_config[remapped_key]['hold_time_ms']

                if elapsed_time < hold_time_ms:
                    # Cancel the scheduled hold behavior
                    keyboard.unhook_key(remapped_key)
        else:
            keyboard.release(remapped_key)

    def execute_hold_behavior(self, key):
        hold_action = self.hold_tap_config[key]['hold_action']
        keyboard.press(hold_action)

    def execute_tap_behavior(self, key):
        if key in self.pressed_keys:
            tap_action = self.hold_tap_config[key]['tap_action']
            keyboard.press(tap_action)
            keyboard.release(tap_action)
            self.pressed_keys.pop(key, None)

    def start(self):
        keyboard.hook(self.on_key_event)
        keyboard.wait()


if __name__ == "__main__":
    print('Starting....')
    interceptor = KeyboardInterceptor("config.json")
    interceptor.start()
