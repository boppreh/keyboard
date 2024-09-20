import keyboard
import time
from threading import Timer


class KeyConfig:
    def __init__(self, original, remapped, hold_tap=None, mod_tap=None):
        self.original = original
        self.remapped = remapped
        self.hold_tap = hold_tap
        self.mod_tap = mod_tap


class KeyboardManager:
    def __init__(self):
        self.key_configs = []
        self.hold_time = 0.2  # seconds
        self.pressed_keys = set()
        self.timers = {}

    def add_key_config(self, config):
        self.key_configs.append(config)

    def setup_keyboard_listeners(self):
        keyboard.on_press(self.on_key_press)
        keyboard.on_release(self.on_key_release)

    def on_key_press(self, event):
        if event.name in self.pressed_keys:
            return

        self.pressed_keys.add(event.name)
        config = self.get_key_config(event.name)

        if config:
            if config.mod_tap:
                self.handle_mod_tap(config)
            elif config.hold_tap:
                self.handle_hold_tap(config)
            else:
                self.trigger_key_press(config.remapped)
        else:
            self.trigger_key_press(event.name)

    def on_key_release(self, event):
        self.pressed_keys.discard(event.name)
        if event.name in self.timers:
            self.timers[event.name].cancel()
            del self.timers[event.name]

        config = self.get_key_config(event.name)
        if config and config.mod_tap and not self.pressed_keys:
            self.trigger_key_press(config.mod_tap['tap'])

    def handle_hold_tap(self, config):
        def on_hold():
            self.trigger_key_press(config.hold_tap['hold'])

        self.timers[config.original] = Timer(self.hold_time, on_hold)
        self.timers[config.original].start()

    def handle_mod_tap(self, config):
        def on_hold():
            self.trigger_key_press(config.mod_tap['mod'])

        self.timers[config.original] = Timer(self.hold_time, on_hold)
        self.timers[config.original].start()

    def get_key_config(self, key):
        return next((config for config in self.key_configs if config.original == key), None)

    def trigger_key_press(self, key):
        print(f"Key pressed: {key}")
        # In a real implementation, you'd interface with the OS or use keyboard.press() and keyboard.release()

    def run(self):
        self.setup_keyboard_listeners()
        print("Keyboard manager initialized. Try pressing keys!")
        keyboard.wait()


# Usage example
if __name__ == "__main__":
    keyboard_manager = KeyboardManager()

    keyboard_manager.add_key_config(KeyConfig("a", "b"))
    keyboard_manager.add_key_config(
        KeyConfig("c", "c", hold_tap={"hold": "ctrl", "tap": "c"}))
    keyboard_manager.add_key_config(
        KeyConfig("d", "d", mod_tap={"mod": "shift", "tap": "d"}))

    keyboard_manager.run()
