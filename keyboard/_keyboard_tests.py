# -*- coding: utf-8 -*-
from __future__ import print_function

import unittest

import keyboard
from keyboard import KEY_UP, KEY_DOWN, KeyboardEvent, SUPPRESS, ALLOW
import itertools
import time

itercounter = itertools.count(1, step=0.0002)
make_event = lambda event_type, scan_code, time=None: KeyboardEvent(event_type=event_type, scan_code=scan_code, time=next(itercounter) if time is None else time)
PRESS = lambda scan_code, time=None: [make_event(KEY_DOWN, scan_code, time)]
RELEASE = lambda scan_code, time=None: [make_event(KEY_UP, scan_code, time)]
def TRIGGER(n=1000):
    keyboard._listener.is_replaying = True
    keyboard.release(n)
    keyboard._listener.is_replaying = False
TRIGGERED = lambda n=1000: [make_event(KEY_UP, n)]
NAME_MAP = {'-2': [(-2, False)], '-1': [(-1, False)], '0': [(0, False)], '1': [(1, False)], '2': [(2, False)], '10': [(10, True)]}

keyboard.stop()

def format_event(event):
    if event.scan_code == 1000:
        return 'TRIGGERED()'
    elif event.scan_code >= 100:
        return 'TRIGGERED({})'.format(event.scan_code)
    elif event.event_type == KEY_DOWN:
        return 'PRESS({})'.format(event.scan_code)
    elif event.event_type == KEY_UP:
        return 'RELEASE({})'.format(event.scan_code)

class TestNewCore(unittest.TestCase):
    def setUp(self):
        self.output_events = []
        keyboard._listener = keyboard._KeyboardListener()
        keyboard._modifier_scan_codes = {-1, -2, -3}
        def send_fake_event(event_type, scan_code):
            event = make_event(event_type, scan_code)
            keyboard._listener.process_sync_event(event)
            self.output_events.append(event)
        keyboard._os_keyboard.press = lambda key: send_fake_event(KEY_DOWN, key)
        keyboard._os_keyboard.release = lambda key: send_fake_event(KEY_UP, key)
        keyboard._os_keyboard.map_name = lambda name: NAME_MAP[name]

    def sim(self, input_events, expected=None):
        if expected is None:
            expected = input_events

        for event in input_events:
            if keyboard._listener.process_sync_event(event):
                self.output_events.append(event)

        to_names = lambda es: '+'.join(map(format_event, es))
        self.assertEqual(to_names(self.output_events), to_names(expected))
        del self.output_events[:]

        for hook_obj in keyboard._listener.suppressing_hooks:
            if isinstance(hook_obj, keyboard._HotkeyHook):
                self.assertEqual(hook_obj.state, 0)
                self.assertTrue(all(decision is not keyboard.SUSPEND for event, decision in hook_obj.decisions.items()))

    ####
    # Test core functions to hotkey handling.
    ####

    def test_allowing_hook(self):
        keyboard.hook(lambda event: ALLOW)
        self.sim(PRESS(0)+RELEASE(0), PRESS(0)+RELEASE(0))
    def test_suppressing_hook(self):
        keyboard.hook(lambda event: keyboard.SUPPRESS, suppress=True)
        self.sim(PRESS(0)+RELEASE(0), [])

    def test_suppressing_key_hook(self):
        keyboard.hook_key(0, lambda e: TRIGGER(), suppress=True)
        self.sim(PRESS(1)+PRESS(0), PRESS(1)+TRIGGERED())
    def test_allowing_key_hook(self):
        keyboard.hook_key(0, lambda e: TRIGGER() or ALLOW, suppress=True)
        self.sim(PRESS(1)+PRESS(0), PRESS(1)+TRIGGERED()+PRESS(0))

    def test_single_key_blocking_hotkey(self):
        keyboard.add_hotkey(0, TRIGGER)
        self.sim(PRESS(1)+RELEASE(1))
        self.sim(PRESS(0)+RELEASE(0), TRIGGERED())
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+PRESS(0)+RELEASE(0), TRIGGERED()+PRESS(1)+RELEASE(1)+TRIGGERED())
        self.sim(PRESS(1)+PRESS(0)+RELEASE(1)+RELEASE(0), PRESS(1)+TRIGGERED()+RELEASE(1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(0))
        self.sim(PRESS(0)+PRESS(0)+RELEASE(0), TRIGGERED()+TRIGGERED())

    def test_single_key_allowing_hotkey(self):
        keyboard.add_hotkey(0, lambda: TRIGGER() or ALLOW)
        self.sim(PRESS(1)+RELEASE(1))
        self.sim(PRESS(0)+RELEASE(0), TRIGGERED()+PRESS(0)+RELEASE(0))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+PRESS(0)+RELEASE(0), TRIGGERED()+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+TRIGGERED()+PRESS(0)+RELEASE(0))
        self.sim(PRESS(1)+PRESS(0)+RELEASE(1)+RELEASE(0), PRESS(1)+TRIGGERED()+PRESS(0) +RELEASE(1)+RELEASE(0))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(0))
        self.sim(PRESS(0)+PRESS(0)+RELEASE(0), TRIGGERED()+PRESS(0)+TRIGGERED()+PRESS(0)+RELEASE(0))

    def test_single_key_with_modifier_blocking_hotkey(self):
        keyboard.add_hotkey((-1, 0), TRIGGER)
        self.sim(PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+RELEASE(-1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(0)+RELEASE(-1), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(0), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(0)+PRESS(-1)+RELEASE(-1)+RELEASE(0))
        self.sim(PRESS(-1)+PRESS(1)+PRESS(0)+RELEASE(1)+RELEASE(-1)+RELEASE(0), PRESS(-1)+PRESS(1)+TRIGGERED()+RELEASE(1)+RELEASE(-1))

    def test_single_key_with_modifier_on_release_blocking_hotkey(self):
        keyboard.add_hotkey((-1, 0), TRIGGER, trigger_on_release=True)
        self.sim(PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+RELEASE(-1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(0)+RELEASE(-1), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(0), PRESS(-1)+RELEASE(-1)+TRIGGERED())
        self.sim(PRESS(0)+PRESS(-1)+RELEASE(-1)+RELEASE(0))
        self.sim(PRESS(-1)+PRESS(1)+PRESS(0)+RELEASE(1)+RELEASE(-1)+RELEASE(0), PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1)+TRIGGERED())

    def test_single_key_with_many_modifiers_blocking_hotkey(self):
        keyboard.add_hotkey((-2, -1, 0), TRIGGER)
        self.sim(PRESS(-2)+PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+RELEASE(-1)+RELEASE(-2))
        self.sim(PRESS(-2)+PRESS(-1)+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2), PRESS(-2)+PRESS(-1)+TRIGGERED()+RELEASE(-1)+RELEASE(-2))
        self.sim(PRESS(-1)+PRESS(-2)+PRESS(0)+RELEASE(0)+RELEASE(-2)+RELEASE(-1), PRESS(-1)+PRESS(-2)+TRIGGERED()+RELEASE(-2)+RELEASE(-1))
        self.sim(PRESS(-2)+PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(-2)+RELEASE(0), PRESS(-2)+PRESS(-1)+TRIGGERED()+RELEASE(-1)+RELEASE(-2))
        self.sim(PRESS(-3)+PRESS(-2)+PRESS(-1)+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2)+RELEASE(-3))

    def test_single_keys_multistep_blocking_hotkey(self):
        keyboard.add_hotkey((((0,),), ((1,),)), TRIGGER)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1), PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(2)+RELEASE(2)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), PRESS(0)+RELEASE(0)+PRESS(2)+RELEASE(2)+TRIGGERED())
        self.sim(PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), PRESS(0)+RELEASE(0)+TRIGGERED())
        self.sim(PRESS(0)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), PRESS(0)+TRIGGERED()+RELEASE(0))
        self.sim(PRESS(0)+PRESS(0)+RELEASE(0)+PRESS(2)+RELEASE(2), PRESS(0)+PRESS(0)+RELEASE(0)+PRESS(2)+RELEASE(2))

    def test_keys_with_modifiers_multistep_blocking_hotkey(self):
        keyboard.add_hotkey((((0,),), ((-1,), (1,),)), TRIGGER)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+RELEASE(-1))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(2)+RELEASE(2)+RELEASE(-1), PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(2)+RELEASE(2)+RELEASE(-1))

    def test_single_key_on_release_blocking_hotkey(self):
        keyboard.add_hotkey(0, TRIGGER, trigger_on_release=True)
        self.sim(PRESS(1)+RELEASE(1))
        self.sim(PRESS(0)+RELEASE(0), TRIGGERED())
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+PRESS(0)+RELEASE(0), TRIGGERED()+PRESS(1)+RELEASE(1)+TRIGGERED())
        self.sim(PRESS(1)+PRESS(0)+RELEASE(1)+RELEASE(0), PRESS(1)+RELEASE(1)+TRIGGERED())
        keyboard.release(0)
        del self.output_events[:]
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(-1)+RELEASE(0))
        self.sim(PRESS(0)+PRESS(0)+RELEASE(0), PRESS(0)+TRIGGERED()+RELEASE(0))

    def test_keys_with_modifiers_multistep_on_release_blocking_hotkey(self):
        keyboard.add_hotkey((((0,),), ((-1,), (1,),)), TRIGGER, trigger_on_release=True)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1))
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1)+RELEASE(-1))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(2)+RELEASE(2)+RELEASE(-1), PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(2)+RELEASE(2)+RELEASE(-1))

    def test_hotkey_trigger_order(self):
        keyboard.add_hotkey(0, lambda: TRIGGER(1000), trigger_on_release=False)
        keyboard.add_hotkey(0, lambda: TRIGGER(2000), trigger_on_release=True)
        keyboard.add_hotkey(0, lambda: TRIGGER(3000), trigger_on_release=False)
        self.sim(PRESS(0)+RELEASE(0), TRIGGERED(1000)+TRIGGERED(3000)+TRIGGERED(2000))

    def test_many_steps_hotkey(self):
        keyboard.add_hotkey((((0,),), ((0,),), ((0,),), ((1,),)), TRIGGER)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+PRESS(0)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+PRESS(0)+PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+PRESS(0)+PRESS(0)+PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), PRESS(0)+TRIGGERED()+RELEASE(0))
        self.sim(PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1), PRESS(0)+RELEASE(0)+TRIGGERED())

    def test_hotkey_timeout(self):
        keyboard.add_hotkey((((0,),), ((-1,), (1,),)), TRIGGER, timeout=1)
        self.sim(PRESS(0, time=0.1)+RELEASE(0, time=0.2)+PRESS(-1, time=0.5)+PRESS(1, time=0.7)+RELEASE(1, time=0.8)+RELEASE(-1, time=0.9), PRESS(-1)+TRIGGERED()+RELEASE(-1))
        self.sim(PRESS(0, time=1)+RELEASE(0, time=1.1)+PRESS(-1, time=2.5)+PRESS(1, time=2.6)+RELEASE(1)+RELEASE(-1), PRESS(-1)+RELEASE(-1)+PRESS(0)+RELEASE(0)+PRESS(-1)+PRESS(1)+RELEASE(1)+RELEASE(-1))

    def test_combo_hotkey(self):
        keyboard.add_hotkey((0, 1), TRIGGER)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1)+RELEASE(1))
        self.sim(PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(1)+PRESS(0)+RELEASE(0)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(2)+PRESS(1)+PRESS(0)+RELEASE(0)+RELEASE(1)+RELEASE(2))
        self.sim(PRESS(-2)+PRESS(1)+PRESS(0)+RELEASE(0)+RELEASE(1)+RELEASE(-2))

    def test_multistep_combo_hotkey(self):
        keyboard.add_hotkey((((0,),), ((0,), (1,),)), TRIGGER)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), TRIGGERED())
        self.sim(PRESS(0)+PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), TRIGGERED())
        # TODO: when a multi-step combo contains the same key multiple times in a row,
        # all events related to that key are captured, regardless of count.
        #self.sim(PRESS(0)+RELEASE(0)+PRESS(0)+RELEASE(0)+PRESS(0)+PRESS(1)+RELEASE(0)+RELEASE(1), PRESS(0)+RELEASE(0)+TRIGGERED())

    def test_multistep_combo_hotkey_alt(self):
        keyboard.add_hotkey((((0,),(1,)), ((0,),)), TRIGGER)
        self.sim(PRESS(0)+PRESS(0)+PRESS(1)+PRESS(0)+RELEASE(0)+RELEASE(1), TRIGGERED())

    def test_all_modifiers_combo_hotkey(self):
        keyboard.add_hotkey((-1, -2), TRIGGER)
        self.sim(PRESS(-1)+PRESS(-2)+RELEASE(-1)+RELEASE(-2), TRIGGERED())
        self.sim(PRESS(-1)+RELEASE(-1)+PRESS(-2)+RELEASE(-2))

        # This test is debatable. Since the modifiers were suppressed, should
        # the following key be allowed without restoring the modifier state?
        # Should the modifier release by suppressed too, even though it's
        # risky that a logic error may cause stuck keys?
        #self.sim(PRESS(-1)+PRESS(-2)+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2), TRIGGERED()+PRESS(-1)+PRESS(-2)+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2))
        self.sim(PRESS(-1)+PRESS(-2)+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2), TRIGGERED()+PRESS(0)+RELEASE(0)+RELEASE(-1)+RELEASE(-2))

    def test_pending_modifiers(self):
        keyboard.add_hotkey((-1, 1), TRIGGER)
        self.sim(PRESS(-1)+PRESS(0)+RELEASE(0)+RELEASE(-1))

    ###
    # Test higher level functions.
    ###

    def test_hotkey_with_args(self):
        keyboard.add_hotkey((0, 1), TRIGGER, args=(1005,))
        self.sim(PRESS(0)+PRESS(1), TRIGGERED(1005))

    def test_unhook_fn(self):
        result = []
        fn = lambda e: result.append(True) or keyboard.ALLOW
        keyboard.hook(fn, suppress=True)
        self.sim(PRESS(0))
        self.assertEqual(result, [True])

        result = []
        keyboard.unhook(fn)
        keyboard.unhook(fn)
        self.sim(PRESS(0))
        self.assertEqual(result, [])

    def test_hook_disable(self):
        result = []
        fn = lambda e: result.append(True) or keyboard.ALLOW
        hook = keyboard.hook(fn, suppress=True)
        self.sim(PRESS(0))
        self.assertEqual(result, [True])

        result = []
        hook.disable()
        hook.disable()
        self.sim(PRESS(0))
        self.assertEqual(result, [])

    def test_hook_context(self):
        result = []
        with keyboard.hook(lambda e: result.append(True) or keyboard.ALLOW, suppress=True):
            self.sim(PRESS(0))
        self.assertEqual(result, [True])

        del result[:]
        self.sim(PRESS(0))
        self.assertEqual(result, [])

    def test_key_to_scan_code(self):
        self.assertEqual(keyboard.key_to_scan_codes(5), (5,))
        self.assertEqual(keyboard.key_to_scan_codes((1, 2,)), (1, 2,))
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes('missing')
        self.assertEqual(keyboard.key_to_scan_codes('missing', 'replacement'), 'replacement')

    def test_parse_hotkey(self):
        self.assertEqual(keyboard.parse_hotkey(0), keyboard.Hotkey([keyboard.Step([keyboard.Key(0, (0,))])]))
        self.assertEqual(keyboard.parse_hotkey((0, 1)), keyboard.Hotkey([keyboard.Step([keyboard.Key(0, (0,)), keyboard.Key(1, (1,))])]))
        self.assertEqual(keyboard.parse_hotkey((((0,),(1,)), ((0,),))), keyboard.Hotkey([keyboard.Step([keyboard.Key(0, (0,)), keyboard.Key(1, (1,))]), keyboard.Step([keyboard.Key(0, (0,))])]))
        self.assertEqual(keyboard.parse_hotkey(keyboard.parse_hotkey(0)), keyboard.parse_hotkey(0))
        self.assertEqual(keyboard.parse_hotkey('0'), keyboard.parse_hotkey(0))
        self.assertEqual(keyboard.parse_hotkey('0+1'), keyboard.parse_hotkey((0, 1)))
        self.assertEqual(keyboard.parse_hotkey('0+1, 0'), keyboard.parse_hotkey((((0,),(1,)), ((0,),))))
        with self.assertRaises(TypeError):
            keyboard.parse_hotkey(1.5)

    def test_send(self):
        keyboard.send(0)
        self.sim([], PRESS(0)+RELEASE(0))

        keyboard.send(0, do_press=False, do_release=True)
        self.sim([], RELEASE(0))

        keyboard.send(0, do_press=True, do_release=False)
        self.sim([], PRESS(0))

        hook = keyboard.add_hotkey(0, TRIGGER)
        keyboard.send(0)
        self.sim([], PRESS(0)+RELEASE(0))
        keyboard.send(0, process_events=True)
        # TODO: PRESS and RELEASE are actually suppressed, but the way the testing framework is organized they still appear in the output events.
        self.sim([], TRIGGERED()+PRESS(0)+RELEASE(0))
        hook.disable()

    def test_is_pressed(self):
        self.assertFalse(keyboard.is_pressed(0))
        self.sim(PRESS(0))
        self.assertTrue(keyboard.is_pressed(0))
        self.sim(RELEASE(0))
        self.assertFalse(keyboard.is_pressed(0))

        self.sim(PRESS(0))
        self.assertFalse(keyboard.is_pressed((0, 1)))
        self.sim(PRESS(1))
        self.assertTrue(keyboard.is_pressed((0, 1)))

        with self.assertRaises(ValueError):
            keyboard.is_pressed('0, 1')

    def test_call_later(self):
        triggered = []
        def fn(arg1, arg2):
            assert arg1 == 1 and arg2 == 2
            triggered.append(True)
        keyboard.call_later(fn, (1, 2), 0.01)
        self.assertFalse(triggered)
        time.sleep(0.05)
        self.assertTrue(triggered)

    def test_on_press_on_release(self):
        keyboard.on_press(lambda e: TRIGGER(1000), suppress=True)
        keyboard.on_release(lambda e: TRIGGER(2000), suppress=True)
        keyboard.on_press_key(2, lambda e: TRIGGER(3000), suppress=True)
        keyboard.on_release_key(2, lambda e: TRIGGER(4000), suppress=True)
        self.sim(PRESS(1)+RELEASE(1), TRIGGERED(1000)+TRIGGERED(2000))
        self.sim(PRESS(2)+RELEASE(2), TRIGGERED(1000)+TRIGGERED(3000)+TRIGGERED(2000)+TRIGGERED(4000))

    def test_block_key(self):
        keyboard.block_key(0)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1), PRESS(1))

    def test_remap_key(self):
        keyboard.remap_key(0, 2)
        self.sim(PRESS(0)+RELEASE(0)+PRESS(1), PRESS(2)+RELEASE(2)+PRESS(1))

    def test_remap_hotkey(self):
        with keyboard.remap_hotkey(0, 2):
            self.sim(PRESS(0)+RELEASE(0)+PRESS(1), PRESS(2)+RELEASE(2)+PRESS(1))

        with keyboard.remap_hotkey("-1+1", "-2+2"):
            # TODO: this is a really ugly substitution, with extra modifier events and an unmatched release, can we do better?
            self.sim(PRESS(-1)+PRESS(1)+RELEASE(-1)+RELEASE(1), PRESS(-1)+RELEASE(-1)+PRESS(-2)+PRESS(2)+RELEASE(2)+RELEASE(-2)+PRESS(-1)+RELEASE(-1)+RELEASE(1))

    def test_ensure_state(self):
        self.sim(PRESS(-1))
        with keyboard.ensure_state():
            pass
        self.sim([], RELEASE(-1)+PRESS(-1))

        self.sim(PRESS(-1))
        with keyboard.ensure_state(-2, 1):
            self.sim([], RELEASE(-1)+PRESS(-2)+PRESS(1))
        self.sim([], RELEASE(1)+RELEASE(-2)+PRESS(-1))

    def test_stash_state(self):
        keyboard.stash_state()
        self.sim([])

        self.sim(PRESS(-1)+PRESS(0))
        stashed_state = keyboard.stash_state()
        self.sim([], RELEASE(-1)+RELEASE(0))

        self.sim(PRESS(-2))
        keyboard.restore_state(stashed_state)
        self.sim([], RELEASE(-2)+PRESS(-1)+PRESS(0))

        self.sim(PRESS(-2))
        keyboard.restore_modifiers(stashed_state)
        self.sim([], RELEASE(-2)+PRESS(-1))

if __name__ == '__main__':
    unittest.main()