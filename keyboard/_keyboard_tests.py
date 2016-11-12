# -*- coding: utf-8 -*-
import time
import unittest
import string

import keyboard

from ._keyboard_event import KeyboardEvent, canonical_names, KEY_DOWN, KEY_UP

# Fake events with fake scan codes for a totally deterministic test.
all_names = set(canonical_names.values()) | set(string.ascii_lowercase) | set(string.ascii_uppercase) | {'shift'}
scan_codes_by_name = {name: i for i, name in enumerate(sorted(all_names))}
scan_codes_by_name.update({key: scan_codes_by_name[value]
    for key, value in canonical_names.items()})

scan_codes_by_name['shift2'] = scan_codes_by_name['shift']

class FakeEvent(KeyboardEvent):
    def __init__(self, event_type, name, scan_code=None):
        KeyboardEvent.__init__(self, event_type, scan_code or scan_codes_by_name[name], name)

class FakeOsKeyboard(object):
    def __init__(self):
        self.listening = False
        self.append = None
        self.queue = None

    def listen(self, queue):
        self.listening = True
        self.queue = queue

    def get_key_name(self, scan_code):
        return next(name for name, i in scan_codes_by_name.items() if i == scan_code and name not in canonical_names)

    def press(self, key):
        if not isinstance(key, str):
            key = self.get_key_name(key)
        self.append((KEY_DOWN, key))

    def release(self, key):
        if not isinstance(key, str):
            key = self.get_key_name(key)
        self.append((KEY_UP, key))

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

    @staticmethod
    def setUpClass():
        keyboard._os_keyboard = FakeOsKeyboard()
        keyboard._listener.start_if_necessary()
        assert keyboard._os_keyboard.listening
        assert keyboard._listener.listening

    def setUp(self):
        self.events = []
        keyboard._pressed_events.clear()
        keyboard._os_keyboard.append = self.events.append

    def tearDown(self):
        keyboard.unhook_all()
        # Make sure there's no spill over between tests.
        self.wait_for_events_queue()

    def press(self, name, scan_code=None):
        keyboard._os_keyboard.queue.put(FakeEvent(KEY_DOWN, name, scan_code))
        self.wait_for_events_queue()

    def release(self, name, scan_code=None):
        keyboard._os_keyboard.queue.put(FakeEvent(KEY_UP, name, scan_code))
        self.wait_for_events_queue()

    def click(self, name, scan_code=None):
        self.press(name, scan_code)
        self.release(name, scan_code)

    def flush_events(self):
        self.wait_for_events_queue()
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def wait_for_events_queue(self):
        keyboard._listener.queue.join()

    def test_matches(self):
        self.assertTrue(keyboard.matches(FakeEvent(KEY_DOWN, 'shift'), scan_codes_by_name['shift']))
        self.assertTrue(keyboard.matches(FakeEvent(KEY_DOWN, 'shift'), 'shift'))
        self.assertTrue(keyboard.matches(FakeEvent(KEY_DOWN, 'shift'), 'shift2'))
        self.assertTrue(keyboard.matches(FakeEvent(KEY_DOWN, 'shift2'), 'shift'))

    def test_listener(self):
        empty_event = FakeEvent(KEY_DOWN, 'space')
        empty_event.scan_code = None
        keyboard._os_keyboard.queue.put(empty_event)
        self.assertEqual(self.flush_events(), [])

    def test_canonicalize(self):
        space_scan_code = [[scan_codes_by_name['space']]]
        space_name = [['space']]
        self.assertEqual(keyboard.canonicalize(space_scan_code), space_scan_code)
        self.assertEqual(keyboard.canonicalize(space_name), space_name)
        self.assertEqual(keyboard.canonicalize(scan_codes_by_name['space']), space_scan_code)
        self.assertEqual(keyboard.canonicalize('space'), space_name)
        self.assertEqual(keyboard.canonicalize(' '), space_name)
        self.assertEqual(keyboard.canonicalize('spacebar'), space_name)
        self.assertEqual(keyboard.canonicalize('Space'), space_name)
        self.assertEqual(keyboard.canonicalize('SPACE'), space_name)
        
        with self.assertRaises(ValueError):
            keyboard.canonicalize(['space'])
        with self.assertRaises(ValueError):
            keyboard.canonicalize(keyboard)

        self.assertEqual(keyboard.canonicalize('_'), [['_']])
        self.assertEqual(keyboard.canonicalize('space_bar'), space_name)

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

        with self.assertRaises(ValueError):
            self.assertFalse(keyboard.is_pressed('invalid key'))

        with self.assertRaises(ValueError):
            keyboard.is_pressed('space, space')

    def test_is_pressed_duplicated_key(self):
        self.assertFalse(keyboard.is_pressed(100))
        self.assertFalse(keyboard.is_pressed(101))
        self.assertFalse(keyboard.is_pressed('ctrl'))

        self.press('ctrl', 100)
        self.assertTrue(keyboard.is_pressed(100))
        self.assertFalse(keyboard.is_pressed(101))
        self.assertTrue(keyboard.is_pressed('ctrl'))
        self.release('ctrl', 100)

        self.press('ctrl', 101)
        self.assertFalse(keyboard.is_pressed(100))
        self.assertTrue(keyboard.is_pressed(101))
        self.assertTrue(keyboard.is_pressed('ctrl'))
        self.release('ctrl', 101)

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

        self.wait_for_events_queue()

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

        keyboard.write('\n')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'enter'), (KEY_UP, 'enter')])

    def test_send(self):
        keyboard.send('shift', True, False)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift')])

        keyboard.send('a')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a')])

        keyboard.send('a, b')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

        keyboard.send('shift+a, b')
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift'), (KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_UP, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b')])

        self.press('a')
        keyboard.write('a', restore_state_after=False, delay=0.001)
        # TODO: two KEY_UP 'a' because the tests are not clearing the pressed
        # keys correctly, it's not a bug in the keyboard module itself.
        self.assertEqual(self.flush_events(), [(KEY_UP, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'a'), (KEY_UP, 'a')])

        shift_scan_code = scan_codes_by_name['shift']

        keyboard.send(shift_scan_code, True, False)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift')])
        keyboard.send([[shift_scan_code]], True, False)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift')])
        keyboard.send([['shift']], True, False)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'shift')])

    def test_type_unicode(self):
        keyboard.write(u'û')
        events = self.flush_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'unicode')
        self.assertEqual(events[0].name, u'û')

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
            lock.release()
        Thread(target=t).start()
        self.click('a')
        self.press('shift')
        self.press('b')
        self.release('b')
        self.release('shift')
        self.press('esc')
        lock.acquire()
        expected = [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')]
        for event_recorded, expected_pair in zip(self.recorded, expected):
            expected_type, expected_name = expected_pair
            self.assertEqual(event_recorded.event_type, expected_type)
            self.assertEqual(event_recorded.name, expected_name)

        keyboard._pressed_events.clear()

        keyboard.play(self.recorded, speed_factor=0)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')])

        keyboard.play(self.recorded, speed_factor=100)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')])

        # Should be ignored and not throw an error.
        keyboard.play([FakeEvent('fake type', 'a')])

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
        self.assertFalse(self.triggered)
        self.press('shift')
        self.click('b')
        self.release('shift')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('space')
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
        # We overwrote the triggers to remove space. Should not trigger.
        self.assertFalse(self.triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('enter')
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
        # Should have timed out.
        self.assertFalse(self.triggered)
        keyboard.remove_word_listener('bird')

    def test_abbreviation(self):
        keyboard.add_abbreviation('tm', 'a')
        self.press('shift')
        self.click('t')
        self.release('shift')
        self.click('space')
        self.assertEqual(self.flush_events(), []) # abbreviations should be case sensitive
        self.click('t')
        self.click('m')
        self.click('space')
        self.assertEqual(self.flush_events(), [
            (KEY_UP, 'space'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'a'),
            (KEY_UP, 'a')])

        keyboard.add_abbreviation('TM', 'A')
        self.press('shift')
        self.click('t')
        self.release('shift')
        self.click('m')
        self.click('space')
        self.assertEqual(self.flush_events(), [])
        self.press('shift')
        self.click('t')
        self.click('m')
        self.release('shift')
        self.click('space')
        self.assertEqual(self.flush_events(), [
            (KEY_UP, 'space'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'shift'),
            (KEY_DOWN, 'a'),
            (KEY_UP, 'a'),
            (KEY_UP, 'shift'),])

    def test_stash_restore_state(self):
        self.press('a')
        self.press('b')
        state = keyboard.stash_state()
        self.assertEqual(sorted(self.flush_events()), [(KEY_UP, 'a'), (KEY_UP, 'b')])
        keyboard._pressed_events.clear()
        assert len(state) == 2
        self.press('c')
        keyboard.restore_state(state)
        self.assertEqual(sorted(self.flush_events()), [(KEY_DOWN, 'a'), (KEY_DOWN, 'b'), (KEY_UP, 'c')])

    def test_get_typed_strings(self):
        keyboard.hook(self.events.append)
        self.click('b')
        self.click('i')
        self.press('shift')
        self.click('r')
        self.click('caps lock')
        self.click('d')
        self.click('caps lock')
        self.release('shift')
        self.click(' ')
        self.click('backspace')
        self.click('.')
        self.click('enter')
        self.click('n')
        self.click('e')
        self.click('w')
        self.assertEqual(keyboard.get_typed_strings(self.events), ['biRd.', 'new'])

    def test_on_press(self):
        keyboard.on_press(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.release('a')
        self.press('a')

    def test_on_release(self):
        keyboard.on_release(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.press('a')
        self.release('a')

    def test_call_later(self):
        self.triggered = False
        def trigger(): self.triggered = True
        keyboard.call_later(trigger, delay=0.1)
        self.assertFalse(self.triggered)
        time.sleep(0.2)
        self.assertTrue(self.triggered)


if __name__ == '__main__':
    unittest.main()
