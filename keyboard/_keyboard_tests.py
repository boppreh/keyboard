# -*- coding: utf-8 -*-
"""
Side effects are avoided using two techniques:

- Low level OS requests (keyboard._os_keyboard) are mocked out by rewriting
the functions at that namespace. This includes a list of dummy keys.
- Events are pumped manually by the main test class, and accepted events
are tested against expected values.

Fake user events are appended to `input_events`, passed through
keyboard,_listener.direct_callback, then, if accepted, appended to
`output_events`. Fake OS events (keyboard.press) are processed
and added to `output_events` immediately, mimicking real functionality.
"""
from __future__ import print_function

import unittest
import time

import keyboard
from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

dummy_keys = {
    'space': [(0, [])],

    'a': [(1, [])],
    'b': [(2, [])],
    'c': [(3, [])],
    'A': [(1, ['shift']), (-1, [])],
    'B': [(2, ['shift']), (-2, [])],
    'C': [(3, ['shift']), (-3, [])],

    'alt': [(4, [])],
    'left alt': [(4, [])],

    'left shift': [(5, [])],
    'right shift': [(6, [])],

    'left ctrl': [(7, [])],

    'backspace': [(8, [])],
    'caps lock': [(9, [])],

    '+': [(10, [])],
    ',': [(11, [])],
    '_': [(12, [])],

    'none': [],
    'duplicated': [(20, []), (20, [])],
}

def make_event(event_type, name, scan_code=None, time=0):
    return KeyboardEvent(event_type=event_type, scan_code=scan_code or dummy_keys[name][0][0], name=name, time=time)

# Used when manually pumping events.
input_events = []
output_events = []

def send_instant_event(event):
    if keyboard._listener.direct_callback(event):
        output_events.append(event)

# Mock out side effects.
keyboard._os_keyboard.init = lambda: None
keyboard._os_keyboard.listen = lambda callback: None
keyboard._os_keyboard.map_name = dummy_keys.__getitem__
keyboard._os_keyboard.press = lambda scan_code: send_instant_event(make_event(KEY_DOWN, None, scan_code))
keyboard._os_keyboard.release = lambda scan_code: send_instant_event(make_event(KEY_UP, None, scan_code))
keyboard._os_keyboard.type_unicode = lambda char: output_events.append(KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name=char))

# Shortcuts for defining test inputs and expected outputs.
# Usage: d_shift + d_a + u_a + u_shift
d_a = [make_event(KEY_DOWN, 'a')]
u_a = [make_event(KEY_UP, 'a')]
du_a = d_a+u_a
d_b = [make_event(KEY_DOWN, 'b')]
u_b = [make_event(KEY_UP, 'b')]
du_b = d_b+u_b
d_c = [make_event(KEY_DOWN, 'c')]
u_c = [make_event(KEY_UP, 'c')]
du_c = d_c+u_c
d_ctrl = [make_event(KEY_DOWN, 'left ctrl')]
u_ctrl = [make_event(KEY_UP, 'left ctrl')]
du_ctrl = d_ctrl+u_ctrl
d_shift = [make_event(KEY_DOWN, 'left shift')]
u_shift = [make_event(KEY_UP, 'left shift')]
du_shift = d_shift+u_shift
d_alt = [make_event(KEY_DOWN, 'alt')]
u_alt = [make_event(KEY_UP, 'alt')]
du_alt = d_alt+u_alt
du_backspace = [make_event(KEY_DOWN, 'backspace'), make_event(KEY_UP, 'backspace')]
du_capslock = [make_event(KEY_DOWN, 'caps lock'), make_event(KEY_UP, 'caps lock')]
d_space = [make_event(KEY_DOWN, 'space')]
u_space = [make_event(KEY_UP, 'space')]
du_space = [make_event(KEY_DOWN, 'space'), make_event(KEY_UP, 'space')]

trigger = lambda e=None: keyboard.press(999)
triggered_event = [KeyboardEvent(KEY_DOWN, scan_code=999)]

class TestKeyboard(unittest.TestCase):
    def tearDown(self):
        keyboard.unhook_all()
        #self.assertEquals(keyboard._hooks, {})
        #self.assertEquals(keyboard._hotkeys, {})

    def setUp(self):
        #keyboard._hooks.clear()
        #keyboard._hotkeys.clear()
        del input_events[:]
        del output_events[:]
        keyboard._recording = None
        keyboard._pressed_events.clear()
        keyboard._physically_pressed_keys.clear()
        keyboard._logically_pressed_keys.clear()
        keyboard._hotkeys.clear()
        keyboard._listener.init()
        keyboard._word_listeners = {} 

    def do(self, manual_events, expected=None):
        input_events.extend(manual_events)
        while input_events:
            event = input_events.pop(0)
            if keyboard._listener.direct_callback(event):
                output_events.append(event)
        if expected is not None:
            to_names = lambda es: '+'.join(('d' if e.event_type == KEY_DOWN else 'u') + '_' + str(e.scan_code) for e in es)
            self.assertEqual(to_names(output_events), to_names(expected))
        del output_events[:]

        keyboard._listener.queue.join()

    def test_event_json(self):
        event = make_event(KEY_DOWN, u'á \'"', 999)
        import json
        self.assertEqual(event, KeyboardEvent(**json.loads(event.to_json())))

    def test_is_modifier_name(self):
        for name in keyboard.all_modifiers:
            self.assertTrue(keyboard.is_modifier(name))
    def test_is_modifier_scan_code(self):
        for i in range(10):
            self.assertEqual(keyboard.is_modifier(i), i in [4, 5, 6, 7])

    def test_key_to_scan_codes_brute(self):
        for name, entries in dummy_keys.items():
            if name in ['none', 'duplicated']: continue
            expected = tuple(scan_code for scan_code, modifiers in entries)
            self.assertEqual(keyboard.key_to_scan_codes(name), expected)
    def test_key_to_scan_code_from_scan_code(self):
        for i in range(10):
            self.assertEqual(keyboard.key_to_scan_codes(i), (i,))
    def test_key_to_scan_code_from_letter(self):
        self.assertEqual(keyboard.key_to_scan_codes('a'), (1,))
        self.assertEqual(keyboard.key_to_scan_codes('A'), (1,-1))
    def test_key_to_scan_code_from_normalized(self):
        self.assertEqual(keyboard.key_to_scan_codes('shift'), (5,6))
        self.assertEqual(keyboard.key_to_scan_codes('SHIFT'), (5,6))
        self.assertEqual(keyboard.key_to_scan_codes('ctrl'), keyboard.key_to_scan_codes('CONTROL'))
    def test_key_to_scan_code_from_sided_modifier(self):
        self.assertEqual(keyboard.key_to_scan_codes('left shift'), (5,))
        self.assertEqual(keyboard.key_to_scan_codes('right shift'), (6,))
    def test_key_to_scan_code_underscores(self):
        self.assertEqual(keyboard.key_to_scan_codes('_'), (12,))
        self.assertEqual(keyboard.key_to_scan_codes('right_shift'), (6,))
    def test_key_to_scan_code_error_none(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes(None)
    def test_key_to_scan_code_error_empty(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes('')
    def test_key_to_scan_code_error_other(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes({})
    def test_key_to_scan_code_list(self):
        self.assertEqual(keyboard.key_to_scan_codes([10, 5, 'a']), (10, 5, 1))
    def test_key_to_scan_code_empty(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes('none')
    def test_key_to_scan_code_duplicated(self):
        self.assertEqual(keyboard.key_to_scan_codes('duplicated'), (20,))

    def test_parse_hotkey_simple(self):
        self.assertEqual(keyboard.parse_hotkey('a'), (((1,),),))
        self.assertEqual(keyboard.parse_hotkey('A'), (((1,-1),),))
    def test_parse_hotkey_separators(self):
        self.assertEqual(keyboard.parse_hotkey('+'), keyboard.parse_hotkey('plus'))
        self.assertEqual(keyboard.parse_hotkey(','), keyboard.parse_hotkey('comma'))
    def test_parse_hotkey_keys(self):
        self.assertEqual(keyboard.parse_hotkey('left shift + a'), (((5,), (1,),),))
        self.assertEqual(keyboard.parse_hotkey('left shift+a'), (((5,), (1,),),))
    def test_parse_hotkey_simple_steps(self):
        self.assertEqual(keyboard.parse_hotkey('a,b'), (((1,),),((2,),)))
        self.assertEqual(keyboard.parse_hotkey('a, b'), (((1,),),((2,),)))
    def test_parse_hotkey_steps(self):
        self.assertEqual(keyboard.parse_hotkey('a+b, b+c'), (((1,),(2,)),((2,),(3,))))
    def test_parse_hotkey_example(self):
        alt_codes = keyboard.key_to_scan_codes('alt')
        shift_codes = keyboard.key_to_scan_codes('shift')
        a_codes = keyboard.key_to_scan_codes('a')
        b_codes = keyboard.key_to_scan_codes('b')
        c_codes = keyboard.key_to_scan_codes('c')
        self.assertEqual(keyboard.parse_hotkey("alt+shift+a, alt+b, c"), ((alt_codes, shift_codes, a_codes), (alt_codes, b_codes), (c_codes,)))
    def test_parse_hotkey_list_scan_codes(self):
        self.assertEqual(keyboard.parse_hotkey([1, 2, 3]), (((1,), (2,), (3,)),))
    def test_parse_hotkey_deep_list_scan_codes(self):
        result = keyboard.parse_hotkey('a')
        self.assertEqual(keyboard.parse_hotkey(result), (((1,),),))
    def test_parse_hotkey_list_names(self):
        self.assertEqual(keyboard.parse_hotkey(['a', 'b', 'c']), (((1,), (2,), (3,)),))

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
    def test_press_and_release(self):
        keyboard.press_and_release('a')
        self.do([], d_a+u_a)

    def test_send_modifier_press_release(self):
        keyboard.send('ctrl+a', do_press=True, do_release=True)
        self.do([], d_ctrl+d_a+u_a+u_ctrl)
    def test_send_modifiers_release(self):
        keyboard.send('ctrl+shift+a', do_press=False, do_release=True)
        self.do([], u_a+u_shift+u_ctrl)

    def test_call_later(self):
        triggered = []
        def fn(arg1, arg2):
            assert arg1 == 1 and arg2 == 2
            triggered.append(True)
        keyboard.call_later(fn, (1, 2), 0.01)
        self.assertFalse(triggered)
        time.sleep(0.05)
        self.assertTrue(triggered)

    def test_hook_nonblocking(self):
        self.i = 0
        def count(e):
            self.assertEqual(e.name, 'a')
            self.i += 1
        hook = keyboard.hook(count, suppress=False)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 2)
        keyboard.unhook(hook)
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
        hook = keyboard.hook(count, suppress=True)
        self.do(d_a+d_b, d_b)
        self.assertEqual(self.i, 2)
        keyboard.unhook(hook)
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
        self.do([make_event(KEY_DOWN, 'A', -1)] + d_a, d_a)
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
        hook = keyboard.hook_key('A', count)
        self.do(d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([make_event(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key(hook)
        self.do(d_a)
        self.assertEqual(self.i, 3)
    def test_hook_key_blocking(self):
        self.i = 0
        def count(event):
            self.i += 1
            return event.scan_code == 1
        hook = keyboard.hook_key('A', count, suppress=True)
        self.do(d_a, d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b, u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([make_event(KEY_DOWN, 'A', -1)], [])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key(hook)
        self.do([make_event(KEY_DOWN, 'A', -1)], [make_event(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
    def test_on_press_key_nonblocking(self):
        keyboard.on_press_key('A', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.do(d_a+u_a+d_b+u_b)
    def test_on_press_key_blocking(self):
        keyboard.on_press_key('A', lambda e: e.scan_code == 1, suppress=True)
        self.do([make_event(KEY_DOWN, 'A', -1)] + d_a, d_a)
    def test_on_release_key(self):
        keyboard.on_release_key('a', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.do(d_a+u_a)

    def test_block_key(self):
        blocked = keyboard.block_key('a')
        self.do(d_a+d_b, d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], [make_event(KEY_DOWN, 'A', -1)])
        keyboard.unblock_key(blocked)
        self.do(d_a+d_b, d_a+d_b)
    def test_block_key_ambiguous(self):
        keyboard.block_key('A')
        self.do(d_a+d_b, d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], [])

    def test_remap_key_simple(self):
        mapped = keyboard.remap_key('a', 'b')
        self.do(d_a+d_c+u_a, d_b+d_c+u_b)
        keyboard.unremap_key(mapped)
        self.do(d_a+d_c+u_a, d_a+d_c+u_a)
    def test_remap_key_ambiguous(self):
        keyboard.remap_key('A', 'b')
        self.do(d_a+d_b, d_b+d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], d_b)
    def test_remap_key_multiple(self):
        mapped = keyboard.remap_key('a', 'shift+b')
        self.do(d_a+d_c+u_a, d_shift+d_b+d_c+u_b+u_shift)
        keyboard.unremap_key(mapped)
        self.do(d_a+d_c+u_a, d_a+d_c+u_a)

    def test_stash_state(self):
        self.do(d_a+d_shift)
        self.assertEqual(sorted(keyboard.stash_state()), [1, 5])
        self.do([], u_a+u_shift)
    def test_restore_state(self):
        self.do(d_b)
        keyboard.restore_state([1, 5])
        self.do([], u_b+d_a+d_shift)
    def test_restore_modifieres(self):
        self.do(d_b)
        keyboard.restore_modifiers([1, 5])
        self.do([], u_b+d_shift)

    def test_write_simple(self):
        keyboard.write('a', exact=False)
        self.do([], d_a+u_a)
    def test_write_multiple(self):
        keyboard.write('ab', exact=False)
        self.do([], d_a+u_a+d_b+u_b)
    def test_write_modifiers(self):
        keyboard.write('Ab', exact=False)
        self.do([], d_shift+d_a+u_a+u_shift+d_b+u_b)
    # restore_state_after has been removed after the introduction of `restore_modifiers`.
    #def test_write_stash_not_restore(self):
    #    self.do(d_shift)
    #    keyboard.write('a', restore_state_after=False, exact=False)
    #    self.do([], u_shift+d_a+u_a)
    def test_write_stash_restore(self):
        self.do(d_shift)
        keyboard.write('a', exact=False)
        self.do([], u_shift+d_a+u_a+d_shift)
    def test_write_multiple(self):
        last_time = time.time()
        keyboard.write('ab', delay=0.01, exact=False)
        self.do([], d_a+u_a+d_b+u_b)
        self.assertGreater(time.time() - last_time, 0.015)
    def test_write_unicode_explicit(self):
        keyboard.write('ab', exact=True)
        self.do([], [KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name='a'), KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name='b')])
    def test_write_unicode_fallback(self):
        keyboard.write(u'áb', exact=False)
        self.do([], [KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name=u'á')]+d_b+u_b)

    def test_start_stop_recording(self):
        keyboard.start_recording()
        self.do(d_a+u_a)
        self.assertEqual(keyboard.stop_recording(), d_a+u_a)
    def test_stop_recording_error(self):
        with self.assertRaises(ValueError):
            keyboard.stop_recording()

    def test_record(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.record('space', suppress=True))
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True
        t.start()
        # 0.01s sleep failed once already. Better solutions?
        time.sleep(0.01)
        self.do(du_a+du_b+du_space, du_a+du_b)
        self.assertEqual(queue.get(timeout=0.5), du_a+du_b+du_space)

    def test_play_nodelay(self):
        keyboard.play(d_a+u_a, 0)
        self.do([], d_a+u_a)
    def test_play_stash(self):
        self.do(d_ctrl)
        keyboard.play(d_a+u_a, 0)
        self.do([], u_ctrl+d_a+u_a+d_ctrl)
    def test_play_delay(self):
        last_time = time.time()
        events = [make_event(KEY_DOWN, 'a', 1, 100), make_event(KEY_UP, 'a', 1, 100.01)]
        keyboard.play(events, 1)
        self.do([], d_a+u_a)
        self.assertGreater(time.time() - last_time, 0.005)

    def test_get_typed_strings_simple(self):
        events = du_a+du_b+du_backspace+d_shift+du_a+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['aA ', 'a'])
    def test_get_typed_strings_backspace(self):
        events = du_a+du_b+du_backspace
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['a'])
        events = du_backspace+du_a+du_b
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['ab'])
    def test_get_typed_strings_shift(self):
        events = d_shift+du_a+du_b+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['AB ', 'a'])
    def test_get_typed_strings_all(self):
        events = du_a+du_b+du_backspace+d_shift+du_a+du_capslock+du_b+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['aAb ', 'A'])

    def test_get_hotkey_name_simple(self):
        self.assertEqual(keyboard.get_hotkey_name(['a']), 'a')
    def test_get_hotkey_name_modifiers(self):
        self.assertEqual(keyboard.get_hotkey_name(['a', 'shift', 'ctrl']), 'ctrl+shift+a')
    def test_get_hotkey_name_normalize(self):
        self.assertEqual(keyboard.get_hotkey_name(['SHIFT', 'left ctrl']), 'ctrl+shift')
    def test_get_hotkey_name_plus(self):
        self.assertEqual(keyboard.get_hotkey_name(['+']), 'plus')
    def test_get_hotkey_name_duplicated(self):
        self.assertEqual(keyboard.get_hotkey_name(['+', 'plus']), 'plus')
    def test_get_hotkey_name_full(self):
        self.assertEqual(keyboard.get_hotkey_name(['+', 'left ctrl', 'shift', 'WIN', 'right alt']), 'ctrl+alt+shift+windows+plus')
    def test_get_hotkey_name_multiple(self):
        self.assertEqual(keyboard.get_hotkey_name(['ctrl', 'b', '!', 'a']), 'ctrl+!+a+b')
    def test_get_hotkey_name_from_pressed(self):
        self.do(du_c+d_ctrl+d_a+d_b)
        self.assertEqual(keyboard.get_hotkey_name(), 'ctrl+a+b')

    def test_read_hotkey(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.read_hotkey())
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True
        t.start()
        time.sleep(0.01)
        self.do(d_ctrl+d_a+d_b+u_ctrl)
        self.assertEqual(queue.get(timeout=0.5), 'ctrl+a+b')

    def test_read_event(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.read_event(suppress=True))
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True
        t.start()
        time.sleep(0.01)
        self.do(d_a, [])
        self.assertEqual(queue.get(timeout=0.5), d_a[0])

    def test_read_key(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.read_key(suppress=True))
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True
        t.start()
        time.sleep(0.01)
        self.do(d_a, [])
        self.assertEqual(queue.get(timeout=0.5), 'a')

    def test_wait_infinite(self):
        self.triggered = False
        def process():
            keyboard.wait()
            self.triggered = True
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True # Yep, we are letting this thread loose.
        t.start()
        time.sleep(0.01)
        self.assertFalse(self.triggered)

    def test_wait_until_success(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.wait(queue.get(timeout=0.5), suppress=True) or True)
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True
        t.start()
        queue.put('a')
        time.sleep(0.01)
        self.do(d_a, [])
        self.assertTrue(queue.get(timeout=0.5))
    def test_wait_until_fail(self):
        def process():
            keyboard.wait('a', suppress=True)
            self.fail()
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True # Yep, we are letting this thread loose.
        t.start()
        time.sleep(0.01)
        self.do(d_b)

    def test_add_hotkey_single_step_suppress_allow(self):
        keyboard.add_hotkey('a', lambda: trigger() or True, suppress=True)
        self.do(d_a, triggered_event+d_a)
    def test_add_hotkey_single_step_suppress_args_allow(self):
        arg = object()
        keyboard.add_hotkey('a', lambda a: self.assertIs(a, arg) or trigger() or True, args=(arg,), suppress=True)
        self.do(d_a, triggered_event+d_a)
    def test_add_hotkey_single_step_suppress_single(self):
        keyboard.add_hotkey('a', trigger, suppress=True)
        self.do(d_a, triggered_event)
    def test_add_hotkey_single_step_suppress_removed(self):
        keyboard.remove_hotkey(keyboard.add_hotkey('a', trigger, suppress=True))
        self.do(d_a, d_a)
    def test_add_hotkey_single_step_suppress_removed(self):
        keyboard.remove_hotkey(keyboard.add_hotkey('ctrl+a', trigger, suppress=True))
        self.do(d_ctrl+d_a, d_ctrl+d_a)
        self.assertEqual(keyboard._listener.filtered_modifiers[dummy_keys['left ctrl'][0][0]], 0)
    def test_remove_hotkey_internal(self):
        remove = keyboard.add_hotkey('shift+a', trigger, suppress=True)
        self.assertTrue(all(keyboard._listener.blocking_hotkeys.values()))
        self.assertTrue(all(keyboard._listener.filtered_modifiers.values()))
        self.assertNotEqual(keyboard._hotkeys, {})
        remove()
        self.assertTrue(not any(keyboard._listener.filtered_modifiers.values()))
        self.assertTrue(not any(keyboard._listener.blocking_hotkeys.values()))
        self.assertEqual(keyboard._hotkeys, {})
    def test_remove_hotkey_internal_multistep_start(self):
        remove = keyboard.add_hotkey('shift+a, b', trigger, suppress=True)
        self.assertTrue(all(keyboard._listener.blocking_hotkeys.values()))
        self.assertTrue(all(keyboard._listener.filtered_modifiers.values()))
        self.assertNotEqual(keyboard._hotkeys, {})
        remove()
        self.assertTrue(not any(keyboard._listener.filtered_modifiers.values()))
        self.assertTrue(not any(keyboard._listener.blocking_hotkeys.values()))
        self.assertEqual(keyboard._hotkeys, {})
    def test_remove_hotkey_internal_multistep_end(self):
        remove = keyboard.add_hotkey('shift+a, b', trigger, suppress=True)
        self.do(d_shift+du_a+u_shift)
        self.assertTrue(any(keyboard._listener.blocking_hotkeys.values()))
        self.assertTrue(not any(keyboard._listener.filtered_modifiers.values()))
        self.assertNotEqual(keyboard._hotkeys, {})
        remove()
        self.assertTrue(not any(keyboard._listener.filtered_modifiers.values()))
        self.assertTrue(not any(keyboard._listener.blocking_hotkeys.values()))
        self.assertEqual(keyboard._hotkeys, {})
    def test_add_hotkey_single_step_suppress_with_modifiers(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+d_a, triggered_event)
    def test_add_hotkey_single_step_suppress_with_modifiers_fail_unrelated_modifier(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+u_shift+d_a, d_shift+u_shift+d_ctrl+d_a)
    def test_add_hotkey_single_step_suppress_with_modifiers_fail_unrelated_key(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+du_b, d_shift+d_ctrl+du_b)
    def test_add_hotkey_single_step_suppress_with_modifiers_unrelated_key(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+du_b+d_a, d_shift+d_ctrl+du_b+triggered_event)
    def test_add_hotkey_single_step_suppress_with_modifiers_release(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+du_b+d_a+u_ctrl+u_shift, d_shift+d_ctrl+du_b+triggered_event+u_ctrl+u_shift)
    def test_add_hotkey_single_step_suppress_with_modifiers_out_of_order(self):
        keyboard.add_hotkey('ctrl+shift+a', trigger, suppress=True)
        self.do(d_shift+d_ctrl+d_a, triggered_event)
    def test_add_hotkey_single_step_suppress_with_modifiers_repeated(self):
        keyboard.add_hotkey('ctrl+a', trigger, suppress=True)
        self.do(d_ctrl+du_a+du_b+du_a, triggered_event+d_ctrl+du_b+triggered_event)
    def test_add_hotkey_single_step_suppress_with_modifiers_release(self):
        keyboard.add_hotkey('ctrl+a', trigger, suppress=True, trigger_on_release=True)
        self.do(d_ctrl+du_a+du_b+du_a, triggered_event+d_ctrl+du_b+triggered_event)
    def test_add_hotkey_single_step_suppress_with_modifier_superset_release(self):
        keyboard.add_hotkey('ctrl+a', trigger, suppress=True, trigger_on_release=True)
        self.do(d_ctrl+d_shift+du_a+u_shift+u_ctrl, d_ctrl+d_shift+du_a+u_shift+u_ctrl)
    def test_add_hotkey_single_step_suppress_with_modifier_superset(self):
        keyboard.add_hotkey('ctrl+a', trigger, suppress=True)
        self.do(d_ctrl+d_shift+du_a+u_shift+u_ctrl, d_ctrl+d_shift+du_a+u_shift+u_ctrl)
    def test_add_hotkey_single_step_timeout(self):
        keyboard.add_hotkey('a', trigger, timeout=1, suppress=True)
        self.do(du_a, triggered_event)
    def test_add_hotkey_multi_step_first_timeout(self):
        keyboard.add_hotkey('a, b', trigger, timeout=0.01, suppress=True)
        time.sleep(0.03)
        self.do(du_a+du_b, triggered_event)
    def test_add_hotkey_multi_step_last_timeout(self):
        keyboard.add_hotkey('a, b', trigger, timeout=0.01, suppress=True)
        self.do(du_a, [])
        time.sleep(0.05)
        self.do(du_b, du_a+du_b)
    def test_add_hotkey_multi_step_success_timeout(self):
        keyboard.add_hotkey('a, b', trigger, timeout=0.05, suppress=True)
        self.do(du_a, [])
        time.sleep(0.01)
        self.do(du_b, triggered_event)
    def test_add_hotkey_multi_step_suffix_timeout(self):
        keyboard.add_hotkey('a, b, a', trigger, timeout=0.01, suppress=True)
        self.do(du_a+du_b, [])
        time.sleep(0.05)
        self.do(du_a, du_a+du_b)
        self.do(du_b+du_a, triggered_event)
    def test_add_hotkey_multi_step_allow(self):
        keyboard.add_hotkey('a, b', lambda: trigger() or True, suppress=True)
        self.do(du_a+du_b, triggered_event+du_a+du_b)

    def test_add_hotkey_single_step_nonsuppress(self):
        queue = keyboard._queue.Queue()
        keyboard.add_hotkey('ctrl+shift+a+b', lambda: queue.put(True), suppress=False)
        self.do(d_shift+d_ctrl+d_a+d_b)
        self.assertTrue(queue.get(timeout=0.5))
    def test_add_hotkey_single_step_nonsuppress_repeated(self):
        queue = keyboard._queue.Queue()
        keyboard.add_hotkey('ctrl+shift+a+b', lambda: queue.put(True), suppress=False)
        self.do(d_shift+d_ctrl+d_a+d_b)
        self.do(d_shift+d_ctrl+d_a+d_b)
        self.assertTrue(queue.get(timeout=0.5))
        self.assertTrue(queue.get(timeout=0.5))
    def test_add_hotkey_single_step_nosuppress_with_modifiers_out_of_order(self):
        queue = keyboard._queue.Queue()
        keyboard.add_hotkey('ctrl+shift+a', lambda: queue.put(True), suppress=False)
        self.do(d_shift+d_ctrl+d_a)
        self.assertTrue(queue.get(timeout=0.5))
    def test_add_hotkey_single_step_suppress_regression_1(self):
        keyboard.add_hotkey('a', trigger, suppress=True)
        self.do(d_c+d_a+u_c+u_a, d_c+d_a+u_c+u_a)

    def test_remap_hotkey_single(self):
        keyboard.remap_hotkey('a', 'b')
        self.do(d_a+u_a, d_b+u_b)
    def test_remap_hotkey_complex_dst(self):
        keyboard.remap_hotkey('a', 'ctrl+b, c')
        self.do(d_a+u_a, d_ctrl+du_b+u_ctrl+du_c)
    def test_remap_hotkey_modifiers(self):
        keyboard.remap_hotkey('ctrl+shift+a', 'b')
        self.do(d_ctrl+d_shift+d_a+u_a, du_b)
    def test_remap_hotkey_modifiers_repeat(self):
        keyboard.remap_hotkey('ctrl+shift+a', 'b')
        self.do(d_ctrl+d_shift+du_a+du_a, du_b+du_b)
    def test_remap_hotkey_modifiers_state(self):
        keyboard.remap_hotkey('ctrl+shift+a', 'b')
        self.do(d_ctrl+d_shift+du_c+du_a+du_a, d_shift+d_ctrl+du_c+u_shift+u_ctrl+du_b+d_ctrl+d_shift+u_shift+u_ctrl+du_b+d_ctrl+d_shift)
    def test_remap_hotkey_release_incomplete(self):
        keyboard.remap_hotkey('a', 'b', trigger_on_release=True)
        self.do(d_a, [])
    def test_remap_hotkey_release_complete(self):
        keyboard.remap_hotkey('a', 'b', trigger_on_release=True)
        self.do(du_a, du_b)

    def test_parse_hotkey_combinations_scan_code(self):
        self.assertEqual(keyboard.parse_hotkey_combinations(30), (((30,),),))
    def test_parse_hotkey_combinations_single(self):
        self.assertEqual(keyboard.parse_hotkey_combinations('a'), (((1,),),))
    def test_parse_hotkey_combinations_single_modifier(self):
        self.assertEqual(keyboard.parse_hotkey_combinations('shift+a'), (((1, 5), (1, 6)),))
    def test_parse_hotkey_combinations_single_modifiers(self):
        self.assertEqual(keyboard.parse_hotkey_combinations('shift+ctrl+a'), (((1, 5, 7), (1, 6, 7)),))
    def test_parse_hotkey_combinations_multi(self):
        self.assertEqual(keyboard.parse_hotkey_combinations('a, b'), (((1,),), ((2,),)))
    def test_parse_hotkey_combinations_multi_modifier(self):
        self.assertEqual(keyboard.parse_hotkey_combinations('shift+a, b'), (((1, 5), (1, 6)), ((2,),)))
    def test_parse_hotkey_combinations_list_list(self):
        self.assertEqual(keyboard.parse_hotkey_combinations(keyboard.parse_hotkey_combinations('a, b')), keyboard.parse_hotkey_combinations('a, b'))
    def test_parse_hotkey_combinations_fail_empty(self):
        with self.assertRaises(ValueError):
            keyboard.parse_hotkey_combinations('')


    def test_add_hotkey_multistep_suppress_incomplete(self):
        keyboard.add_hotkey('a, b', trigger, suppress=True)
        self.do(du_a, [])
        self.assertEqual(keyboard._listener.blocking_hotkeys[(1,)], [])
        self.assertEqual(len(keyboard._listener.blocking_hotkeys[(2,)]), 1)
    def test_add_hotkey_multistep_suppress_incomplete(self):
        keyboard.add_hotkey('a, b', trigger, suppress=True)
        self.do(du_a+du_b, triggered_event)
    def test_add_hotkey_multistep_suppress_modifier(self):
        keyboard.add_hotkey('shift+a, b', trigger, suppress=True)
        self.do(d_shift+du_a+u_shift+du_b, triggered_event)
    def test_add_hotkey_multistep_suppress_fail(self):
        keyboard.add_hotkey('a, b', trigger, suppress=True)
        self.do(du_a+du_c, du_a+du_c)
    def test_add_hotkey_multistep_suppress_three_steps(self):
        keyboard.add_hotkey('a, b, c', trigger, suppress=True)
        self.do(du_a+du_b+du_c, triggered_event)
    def test_add_hotkey_multistep_suppress_repeated_prefix(self):
        keyboard.add_hotkey('a, a, c', trigger, suppress=True, trigger_on_release=True)
        self.do(du_a+du_a+du_c, triggered_event)
    def test_add_hotkey_multistep_suppress_repeated_key(self):
        keyboard.add_hotkey('a, b', trigger, suppress=True)
        self.do(du_a+du_a+du_b, du_a+triggered_event)
        self.assertEqual(keyboard._listener.blocking_hotkeys[(2,)], [])
        self.assertEqual(len(keyboard._listener.blocking_hotkeys[(1,)]), 1)
    def test_add_hotkey_multi_step_suppress_regression_1(self):
        keyboard.add_hotkey('a, b', trigger, suppress=True)
        self.do(d_c+d_a+u_c+u_a+du_c, d_c+d_a+u_c+u_a+du_c)
    def test_add_hotkey_multi_step_suppress_replays(self):
        keyboard.add_hotkey('a, b, c', trigger, suppress=True)
        self.do(du_a+du_b+du_a+du_b+du_space, du_a+du_b+du_a+du_b+du_space)

    def test_add_word_listener_success(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free)
        self.do(du_a+du_b+du_c+du_space)
        self.assertTrue(queue.get(timeout=0.5))
    def test_add_word_listener_no_trigger_fail(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free)
        self.do(du_a+du_b+du_c)
        with self.assertRaises(keyboard._queue.Empty):
            queue.get(timeout=0.01)
    def test_add_word_listener_timeout_fail(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free, timeout=1)
        self.do(du_a+du_b+du_c+[make_event(KEY_DOWN, name='space', time=2)])
        with self.assertRaises(keyboard._queue.Empty):
            queue.get(timeout=0.01)
    def test_duplicated_word_listener(self):
        keyboard.add_word_listener('abc', trigger)
        keyboard.add_word_listener('abc', trigger)
    def test_add_word_listener_remove(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free)
        keyboard.remove_word_listener('abc')
        self.do(du_a+du_b+du_c+du_space)
        with self.assertRaises(keyboard._queue.Empty):
            queue.get(timeout=0.01)
    def test_add_word_listener_suffix_success(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free, match_suffix=True)
        self.do(du_a+du_a+du_b+du_c+du_space)
        self.assertTrue(queue.get(timeout=0.5))
    def test_add_word_listener_suffix_fail(self):
        queue = keyboard._queue.Queue()
        def free():
            queue.put(1)
        keyboard.add_word_listener('abc', free)
        self.do(du_a+du_a+du_b+du_c)
        with self.assertRaises(keyboard._queue.Empty):
            queue.get(timeout=0.01)

    #def test_add_abbreviation(self):
    #    keyboard.add_abbreviation('abc', 'aaa')
    #    self.do(du_a+du_b+du_c+du_space, [])


if __name__ == '__main__':
    unittest.main()