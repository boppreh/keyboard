import time
import unittest
import keyboard
from keyboard_event import KeyboardEvent, canonical_names, KEY_DOWN, KEY_UP

# Fake events with fake scan codes for a totally deterministic test.
scan_codes_by_name = {name: i for i, name in enumerate(canonical_names.values())}
class FakeEvent(KeyboardEvent):
	def __init__(self, event_type, name):
		self.event_type = event_type
		self.names = [name]
		self.scan_code = scan_codes_by_name[name]
		self.time = time.time()

class TestKeyboard(unittest.TestCase):
	def setUp(self):
		# We will use our own events, thank you very much.
		keyboard.listener.listening = True

	def press(self, name):
		keyboard.listener.callback(FakeEvent(KEY_DOWN, name))

	def release(self, name):
		keyboard.listener.callback(FakeEvent(KEY_UP, name))

	def click(self, name):
		self.press(name)
		self.release(name)

	def test_is_pressed(self):
		self.assertFalse(keyboard.is_pressed('enter'))
		self.assertFalse(keyboard.is_pressed(scan_codes_by_name['enter']))
		self.press('enter')
		self.assertTrue(keyboard.is_pressed('enter'))
		self.assertTrue(keyboard.is_pressed(scan_codes_by_name['enter']))
		self.release('enter')
		self.assertFalse(keyboard.is_pressed('enter'))
		self.click('enter')
		self.assertFalse(keyboard.is_pressed('enter'))

		self.press('enter')
		self.assertFalse(keyboard.is_pressed('ctrl+enter'))
		self.press('ctrl')
		self.assertTrue(keyboard.is_pressed('ctrl+enter'))

	def triggers(self, combination, keys):
		self.triggered = False
		def on_triggered():
			self.triggered = True
		keyboard.add_hotkey(combination, on_triggered)
		for group in keys:
			for key in group:
				self.assertFalse(self.triggered)
				self.press(key)
			for key in reversed(group):
				self.release(key)
		keyboard.remove_hotkey(combination)
		return self.triggered

	def test_register_hotkey(self):
		self.assertFalse(self.triggers('space', [['enter']]))
		self.assertTrue(self.triggers('space', [['space']]))
		self.assertTrue(self.triggers('space, enter', [['space'], ['enter']]))
		self.assertFalse(self.triggers('enter, space', [['space'], ['enter']]))
		self.assertTrue(self.triggers('ctrl+space, enter', [['ctrl', 'space'], ['enter']]))
		self.assertFalse(self.triggers('ctrl+space, enter', [['ctrl'], ['space'], ['enter']]))
		self.assertTrue(self.triggers('ctrl+space, enter', [['space', 'ctrl'], ['enter']]))
		self.assertTrue(self.triggers('ctrl+space, enter, space', [['ctrl', 'space'], ['enter'], ['ctrl', 'space'], ['enter'], ['space']]))
		


if __name__ == '__main__':
	unittest.main()