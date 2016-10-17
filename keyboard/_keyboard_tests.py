# -*- coding: utf-8 -*-
import time
import unittest
import string

import keyboard

from ._keyboard_event import KeyboardEvent, canonical_names, KEY_DOWN, KEY_UP

# Fake events with fake scan codes for a totally deterministic test.
all_names = set(canonical_names.values()) | set(string.ascii_lowercase) | {'shift'}
scan_codes_by_name = {name: i for i, name in enumerate(sorted(all_names))}
scan_codes_by_name.update({key: scan_codes_by_name[value]
    for key, value in canonical_names.items()})

class FakeEvent(KeyboardEvent):
    def __init__(self, event_type, name):
        self.event_type = event_type
        self.name = name
        self.scan_code = scan_codes_by_name[name]
        self.time = time.time()

class FakeOsKeyboard(object):
    def __init__(self, append):
        self.append = append

    def press(self, scan_code):
        self.append((KEY_DOWN, next(name for name, i in scan_codes_by_name.items() if i == scan_code and name not in canonical_names)))

    def release(self, scan_code):
        self.append((KEY_UP, next(name for name, i in scan_codes_by_name.items() if i == scan_code and name not in canonical_names)))

    def map_char(self, char):
        try:
            return scan_codes_by_name[char.lower()], ('shift',) if char.isupper() else ()
        except KeyError as e:
            raise ValueError(e)

    def type_unicode(self, letter):
        event = FakeEvent('unicode', 'a')
        event.name = letter
        self.append(event)

class TestKeyboard(unittest.TestCase):
    # Without this attribute Python2 tests fail for some unknown reason.
    __name__ = 'what'

    def setUp(self):
        # We will use our own events, thank you very much.
        keyboard._listener.listening = True
        self.events = []
        keyboard._pressed_events.clear()
        keyboard._os_keyboard = FakeOsKeyboard(self.events.append)

    def tearDown(self):
        keyboard.unhook_all()

    def press(self, name):
        keyboard._listener.callback(FakeEvent(KEY_DOWN, name))

    def release(self, name):
        keyboard._listener.callback(FakeEvent(KEY_UP, name))

    def click(self, name):
        self.press(name)
        self.release(name)

    def flush_events(self):
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def test_listener(self):
        empty_event = FakeEvent(KEY_DOWN, 'space')
        empty_event.scan_code = None
        keyboard._listener.callback(empty_event)
        self.assertEqual(self.flush_events(), [])

    def test_canonicalize(self):
        space = [[scan_codes_by_name['space']]]
        self.assertEqual(keyboard.canonicalize(space), space)
        self.assertEqual(keyboard.canonicalize(space[0][0]), space)
        self.assertEqual(keyboard.canonicalize('space'), space)
        self.assertEqual(keyboard.canonicalize(' '), space)
        self.assertEqual(keyboard.canonicalize('spacebar'), space)
        self.assertEqual(keyboard.canonicalize('Space'), space)
        self.assertEqual(keyboard.canonicalize('SPACE'), space)
        with self.assertRaises(ValueError):
            keyboard.canonicalize('invalid')
        with self.assertRaises(ValueError):
            keyboard.canonicalize(['space'])
        with self.assertRaises(ValueError):
            keyboard.canonicalize([['space']])
        with self.assertRaises(ValueError):
            keyboard.canonicalize(keyboard)

    def test_is_pressed(self):
        self.assertFalse(keyboard.is_pressed('enter'))
        self.assertFalse(keyboard.is_pressed(scan_codes_by_name['enter']))
        self.press('enter')
        self.assertTrue(keyboard.is_pressed('enter'))
        self.assertTrue(keyboard.is_pressed(scan_codes_by_name['enter']))
        self.release('enter')
        self.release('enter')
        self.assertFalse(keyboard.is_pressed('enter'))
        self.click('enter')
        self.assertFalse(keyboard.is_pressed('enter'))

        self.press('enter')
        self.assertFalse(keyboard.is_pressed('ctrl+enter'))
        self.press('ctrl')
        self.assertTrue(keyboard.is_pressed('ctrl+enter'))

        self.press('space')
        self.assertTrue(keyboard.is_pressed('space'))
        self.assertFalse(keyboard.is_pressed('invalid key'))

        with self.assertRaises(ValueError):
            keyboard.is_pressed('space, space')

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

        # This line is required because hotkey processing wait a moment
        # before invoking the function. This is required in Windows systems
        # or else the rest of the system would process the key *after* the
        # callback executed.
        time.sleep(0.01)

        return self.triggered

    def test_hook(self):
        self.i = 0
        def count(e):
            self.assertEqual(e.name, 'a')
            self.i += 1
        keyboard.hook(count)
        self.click('a')
        self.assertEqual(self.i, 2)
        keyboard.hook(count)
        self.click('a')
        self.assertEqual(self.i, 6)
        keyboard.unhook(count)
        self.click('a')
        self.assertEqual(self.i, 8)
        keyboard.unhook(count)
        self.click('a')
        self.assertEqual(self.i, 8)

    def test_hook_key(self):
        self.i = 0
        def count():
            self.i += 1
        keyboard.hook_key('a', keyup_callback=count)
        self.press('a')
        self.assertEqual(self.i, 0)
        self.release('a')
        self.click('b')
        self.assertEqual(self.i, 1)
        keyboard.hook_key('b', keydown_callback=count)
        self.press('b')
        self.assertEqual(self.i, 2)
        keyboard.unhook_key('a')
        keyboard.unhook_key('b')
        self.click('a')
        self.assertEqual(self.i, 2)

    def test_register_hotkey(self):
        self.assertFalse(self.triggers('a', [['b']]))
        self.assertTrue(self.triggers('a', [['a']]))
        self.assertTrue(self.triggers('a, b', [['a'], ['b']]))
        self.assertFalse(self.triggers('b, a', [['a'], ['b']]))
        self.assertTrue(self.triggers('a+b', [['a', 'b']]))
        self.assertTrue(self.triggers('ctrl+a, b', [['ctrl', 'a'], ['b']]))
        self.assertFalse(self.triggers('ctrl+a, b', [['ctrl'], ['a'], ['b']]))
        self.assertTrue(self.triggers('ctrl+a, b', [['a', 'ctrl'], ['b']]))
        self.assertTrue(self.triggers('ctrl+a, b, a', [['ctrl', 'a'], ['b'], ['ctrl', 'a'], ['b'], ['a']]))

    def test_remove_hotkey(self):
        keyboard.press('a')
        keyboard.add_hotkey('a', self.fail)
        keyboard.clear_all_hotkeys()
        keyboard.press('a')
        keyboard.add_hotkey('a', self.fail)
        keyboard.clear_all_hotkeys()
        keyboard.press('a')

        keyboard.clear_all_hotkeys()

        keyboard.add_hotkey('a', self.fail)
        with self.assertRaises(ValueError):
            keyboard.remove_hotkey('b')
        keyboard.remove_hotkey('a')

    def test_write(self):
        keyboard.write('a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a')])

        keyboard.write('ab')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

        keyboard.write('Ab')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift'), (KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_UP, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

    def test_send(self):
        keyboard.send('shift', True, False)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift')])

        keyboard.send('a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a')])

        keyboard.send('a, b')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

        keyboard.send('shift+a, b')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift'), (KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_UP, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

        with self.assertRaises(ValueError):
            keyboard.send('foo', True, False)

        self.press('a')
        keyboard.write('a', restore_state_after=False, delay=0.001)
        # TODO: two KEY_UP 'a' because the tests are not clearing the pressed
        # keys correctly, it's not a bug in the keyboard module itself.
        self.assertEqual(self.flush_events(), [(KEY_UP, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'a'), (KEY_UP, 'a')])

    def test_type_unicode(self):
        keyboard.write('û')
        events = self.flush_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'unicode')
        self.assertEqual(events[0].name, 'û')

    def test_press_release(self):
        keyboard.press('a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a')])
        keyboard.release('a')
        self.assertEqual(self.flush_events(), [(KEY_UP, 'a')])

        keyboard.press('shift+a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift'), (KEY_DOWN, 'a')])
        keyboard.release('shift+a')
        self.assertEqual(self.flush_events(), [(KEY_UP, 'a'), (KEY_UP, 'shift')])

        keyboard.press_and_release('a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a')])

    def test_wait(self):
        # If this fails it blocks. Unfortunately, but I see no other way of testing.
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        def t():
            keyboard.wait('a')
            lock.release()
        Thread(target=t).start()
        self.click('a')
        lock.acquire()

    def test_record_play(self):
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        self.recorded = None
        def t():
            self.recorded = keyboard.record('esc')
            keyboard.play(self.recorded, speed_factor=0)
            lock.release()
        Thread(target=t).start()
        self.click('a')
        self.press('shift')
        self.press('b')
        self.release('b')
        self.release('shift')
        self.click('esc')
        lock.acquire()
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc'), (KEY_UP, 'esc')])

        keyboard.play(self.recorded, speed_factor=100)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc'), (KEY_UP, 'esc')])

    def test_word_listener_normal(self):
        keyboard.add_word_listener('bird', self.fail)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('s')
        self.click('space')
        with self.assertRaises(ValueError):
            keyboard.add_word_listener('bird', self.fail)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        def on_triggered():
            self.triggered = True
        keyboard.add_word_listener('bird', on_triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        # Callback is called after a moment to let the OS process the last key.
        time.sleep(0.01)
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        def on_triggered():
            self.triggered = True
        # Word listener should be case sensitive.
        keyboard.add_word_listener('Bird', on_triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        time.sleep(0.01)
        self.assertFalse(self.triggered)
        self.press('shift')
        self.click('b')
        self.release('shift')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('space')
        time.sleep(0.01)
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('Bird')

    def test_word_listener_edge_cases(self):
        self.triggered = False
        def on_triggered():
            self.triggered = True
        handler = keyboard.add_word_listener('bird', on_triggered, triggers=['enter'])
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('space')
        time.sleep(0.01)
        # We overwrote the triggers to remove space. Should not trigger.
        self.assertFalse(self.triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('enter')
        time.sleep(0.01)
        self.assertTrue(self.triggered)
        with self.assertRaises(ValueError):
            # Must pass handler returned by function, not passed callback.
            keyboard.remove_word_listener(on_triggered)
        with self.assertRaises(ValueError):
            keyboard.remove_word_listener('birb')
        keyboard.remove_word_listener(handler)

        self.triggered = False
        # Timeout of 0 should mean "no timeout".
        keyboard.add_word_listener('bird', on_triggered, timeout=0)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        time.sleep(0.01)
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        keyboard.add_word_listener('bird', on_triggered, timeout=0.01)
        self.click('b')
        self.click('i')
        self.click('r')
        time.sleep(0.03)
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        time.sleep(0.01)
        # Should have timed out.
        self.assertFalse(self.triggered)
        keyboard.remove_word_listener('bird')

    def test_abbreviation(self):
        keyboard.add_abbreviation('tm', 'a')
        self.click('t')
        self.click('m')
        self.click('space')
        time.sleep(0.01)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'a'),
            (KEY_UP, 'a')])

    def test_stash_restore_state(self):
        self.press('a')
        self.press('b')
        state = keyboard.stash_state()
        self.assertEqual(self.flush_events(), [(KEY_UP, 'a'), (KEY_UP, 'b')])
        keyboard._pressed_events.clear()
        assert len(state) == 2
        self.press('c')
        keyboard.restore_state(state)
        self.assertEqual(self.flush_events(), [(KEY_UP, 'c'), (KEY_DOWN, 'b'), (KEY_DOWN, 'a')])


if __name__ == '__main__':
    unittest.main()
