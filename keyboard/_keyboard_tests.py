# -*- coding: utf-8 -*-
import time
import unittest
import string
from threading import Event

import keyboard

from ._keyboard_event import KeyboardEvent, canonical_names, KEY_DOWN, KEY_UP

by_names = {
    'a': [(1, [])],
    'b': [(2, [])],
    'c': [(3, [])],
    'A': [(1, ['shift']), (-1, [])],
    'B': [(2, ['shift']), (-1, [])],
    'C': [(3, ['shift']), (-1, [])],

    'alt': [(4, [])],
    'left alt': [(4, [])],

    'left shift': [(5, [])],
    'shift': [(5, []), (6, [])],
    'right shift': [(6, [])],

    'left ctrl': [(7, [])],
    'ctrl': [(8, []), (7, [])],
}

def event_for(event_type, name, scan_code=None):
    return KeyboardEvent(event_type=event_type, scan_code=scan_code or by_names[name][0][0], name=name)

input_events = []
output_events = []

keyboard._os_keyboard.init = lambda: None
keyboard._os_keyboard.listen = lambda callback: None
keyboard._os_keyboard.map_name = by_names.__getitem__
def fake_event(event_type, scan_code):
    event = KeyboardEvent(event_type=event_type, scan_code=scan_code)
    if keyboard._listener.direct_callback(event):
        output_events.append(event)
keyboard._os_keyboard.press = lambda scan_code: fake_event(KEY_DOWN, scan_code)
keyboard._os_keyboard.release = lambda scan_code: fake_event(KEY_UP, scan_code)

d_a = [event_for(KEY_DOWN, 'a')]
u_a = [event_for(KEY_UP, 'a')]
d_b = [event_for(KEY_DOWN, 'b')]
u_b = [event_for(KEY_UP, 'b')]
d_c = [event_for(KEY_DOWN, 'c')]
u_c = [event_for(KEY_UP, 'c')]
d_ctrl = [event_for(KEY_DOWN, 'ctrl')]
u_ctrl = [event_for(KEY_UP, 'ctrl')]
d_shift = [event_for(KEY_DOWN, 'left shift')]
u_shift = [event_for(KEY_UP, 'left shift')]
d_alt = [event_for(KEY_DOWN, 'alt')]
u_alt = [event_for(KEY_UP, 'alt')]

class TestKeyboard(unittest.TestCase):
    def tearDown(self):
        del input_events[:]
        del output_events[:]
        del keyboard._listener.handlers[:]
        del keyboard._listener.blocking_hooks[:]
        keyboard._pressed_events.clear()
        keyboard._hooks.clear()
        keyboard._listener.active_modifiers.clear()
        keyboard._listener.blocking_hotkeys.clear()
        keyboard._listener.blocking_keys.clear()
        keyboard._listener.filtered_modifiers.clear()
        keyboard._listener.modifier_states.clear()
        keyboard._listener.is_replaying = False

    def do(self, manual_events, expected=None):
        input_events.extend(manual_events)
        while input_events:
            event = input_events.pop(0)
            if keyboard._listener.direct_callback(event):
                output_events.append(event)
        if expected:
            self.assertEqual(output_events, expected)
        del output_events[:]

        keyboard._listener.queue.join()

    def test_is_pressed_none(self):
        self.assertFalse(keyboard.is_pressed('a'))
    def test_is_pressed_true(self):
        self.do(d_a)
        self.assertTrue(keyboard.is_pressed('a'))
    def test_is_pressed_true_scan_code_true(self):
        self.do(d_a)
        self.assertTrue(keyboard.is_pressed(1))
    def test_is_pressed_true_scan_code_false(self):
        self.do(d_a)
        self.assertFalse(keyboard.is_pressed(2))
    def test_is_pressed_true_scan_code_invalid(self):
        self.do(d_a)
        self.assertFalse(keyboard.is_pressed(-1))
    def test_is_pressed_false(self):
        self.do(d_a+u_a+d_b)
        self.assertFalse(keyboard.is_pressed('a'))
        self.assertTrue(keyboard.is_pressed('b'))
    def test_is_pressed_hotkey_true(self):
        self.do(d_shift+d_a)
        self.assertTrue(keyboard.is_pressed('shift+a'))
    def test_is_pressed_hotkey_false(self):
        self.do(d_shift+d_a+u_a)
        self.assertFalse(keyboard.is_pressed('shift+a'))
    def test_is_pressed_multi_step_fail(self):
        self.do(u_a+d_a)
        with self.assertRaises(ValueError):
            keyboard.is_pressed('a, b')

    def test_send_single_press_release(self):
        keyboard.send('a', do_press=True, do_release=True)
        self.do([], d_a+u_a)
    def test_send_single_press(self):
        keyboard.send('a', do_press=True, do_release=False)
        self.do([], d_a)
    def test_send_single_release(self):
        keyboard.send('a', do_press=False, do_release=True)
        self.do([], u_a)
    def test_send_single_none(self):
        keyboard.send('a', do_press=False, do_release=False)
        self.do([], [])
    def test_press(self):
        keyboard.press('a')
        self.do([], d_a)
    def test_release(self):
        keyboard.release('a')
        self.do([], u_a)

    def test_send_modifier_press_release(self):
        keyboard.send('ctrl+a', do_press=True, do_release=True)
        self.do([], d_ctrl+d_a+u_a+u_ctrl)
    def test_send_modifiers_release(self):
        keyboard.send('ctrl+shift+a', do_press=False, do_release=True)
        self.do([], u_a+u_shift+u_ctrl)

    def test_call_later(self):
        triggered = []
        def trigger(arg1, arg2):
            assert arg1 == 1 and arg2 == 2
            triggered.append(True)
        keyboard.call_later(trigger, (1, 2), 0.01)
        self.assertFalse(triggered)
        time.sleep(0.02)
        self.assertTrue(triggered)

    def test_hook_nonblocking(self):
        self.i = 0
        def count(e):
            self.assertEqual(e.name, 'a')
            self.i += 1
        keyboard.hook(count, suppress=False)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 2)
        keyboard.unhook(count)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 2)
        keyboard.hook(count, suppress=False)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 4)
        keyboard.unhook_all()
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 4)
    def test_hook_blocking(self):
        self.i = 0
        def count(e):
            self.assertIn(e.name, ['a', 'b'])
            self.i += 1
            return e.name == 'b'
        keyboard.hook(count, suppress=True)
        self.do(d_a+d_b, d_b)
        self.assertEqual(self.i, 2)
        keyboard.unhook(count)
        self.do(d_a+d_b, d_a+d_b)
        self.assertEqual(self.i, 2)
        keyboard.hook(count, suppress=True)
        self.do(d_a+d_b, d_b)
        self.assertEqual(self.i, 4)
        keyboard.unhook_all()
        self.do(d_a+d_b, d_a+d_b)
        self.assertEqual(self.i, 4)
    def test_on_press_nonblocking(self):
        keyboard.on_press(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.do(d_a+u_a)
    def test_on_press_blocking(self):
        keyboard.on_press(lambda e: e.scan_code == 1, suppress=True)
        self.do([event_for(KEY_DOWN, 'A', -1)] + d_a, d_a)
    def test_on_release(self):
        keyboard.on_release(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.do(d_a+u_a)

    def test_hook_key_invalid(self):
        with self.assertRaises(ValueError):
            keyboard.hook_key('invalid', lambda e: None)
    def test_hook_key_nonblocking(self):
        self.i = 0
        def count(event):
            self.i += 1
        keyboard.hook_key('A', count)
        self.do(d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([event_for(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key('A')
        self.do(d_a)
        self.assertEqual(self.i, 3)
    def test_hook_key_blocking(self):
        self.i = 0
        def count(event):
            self.i += 1
            return event.scan_code == 1
        keyboard.hook_key('A', count, suppress=True)
        self.do(d_a, d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b, u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([event_for(KEY_DOWN, 'A', -1)], [])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key('A')
        self.do([event_for(KEY_DOWN, 'A', -1)], [event_for(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
    def test_on_press_key_nonblocking(self):
        keyboard.on_press_key('A', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.do(d_a+u_a+d_b+u_b)
    def test_on_press_key_blocking(self):
        keyboard.on_press_key('A', lambda e: e.scan_code == 1, suppress=True)
        self.do([event_for(KEY_DOWN, 'A', -1)] + d_a, d_a)
    def test_on_release_key(self):
        keyboard.on_release_key('a', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.do(d_a+u_a)



if __name__ == '__main__':
    unittest.main()

exit()

class OldTests(object):
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
        self.assertEqual(list(keyboard.get_typed_strings(self.events)), ['biRd.', 'new'])

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

    def test_suppression(self):
        def dummy():
            pass

        keyboard.add_hotkey('z', dummy, suppress=True)
        keyboard.add_hotkey('a+b+c', dummy, suppress=True)
        keyboard.add_hotkey('a+g+h', dummy, suppress=True, timeout=0.01)

        for key in ['a', 'b', 'c']:
            self.assertFalse(self.press(key))
        for key in ['a', 'b', 'c']:
            self.assertFalse(self.release(key))

        self.assertTrue(self.click('d'))

        for key in ['a', 'b']:
            self.assertFalse(self.press(key))
        for key in ['a', 'b']:
            self.assertFalse(self.release(key))

        self.assertTrue(self.click('c'))

        for key in ['a', 'g']:
            self.assertFalse(self.press(key))
        for key in ['a', 'g']:
            self.assertFalse(self.release(key))

        time.sleep(0.03)
        self.assertTrue(self.click('h'))

        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.release('a'))

        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.release('z'))

        keyboard.remove_hotkey('a+g+h')
        keyboard.remove_hotkey('a+b+c')

        self.assertTrue(self.click('a'))

if __name__ == '__main__':
    unittest.main()