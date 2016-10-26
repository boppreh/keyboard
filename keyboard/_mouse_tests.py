# -*- coding: utf-8 -*-
import unittest
import time

from ._mouse_event import MoveEvent, ButtonEvent, WheelEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE
from keyboard import mouse

class FakeOsMouse(object):
    def __init__(self):
        self.append = None
        self.position = (0, 0)
        self.queue = None

    def listen(self, queue):
        self.listening = True
        self.queue = queue

    def press(self, button):
        self.append((DOWN, button))

    def release(self, button):
        self.append((UP, button))

    def get_position(self):
        return self.position

    def move_to(self, x, y):
        self.position = (x, y)

    def move_relative(self, x, y):
        self.position = (self.position[0] + x, self.position[1] + y)

class TestMouse(unittest.TestCase):
    @staticmethod
    def setUpClass():
        mouse._os_mouse= FakeOsMouse()
        mouse._listener.start_if_necessary()
        assert mouse._os_mouse.listening

    def setUp(self):
        self.events = []
        mouse._pressed_events.clear()
        mouse._os_mouse.append = self.events.append

    def tearDown(self):
        mouse.unhook_all()
        # Make sure there's no spill over between tests.
        self.wait_for_events_queue()

    def wait_for_events_queue(self):
        mouse._listener.queue.join()

    def flush_events(self):
        self.wait_for_events_queue()
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def press(self, button=LEFT):
        mouse._os_mouse.queue.put(ButtonEvent(DOWN, button, time.time()))
        self.wait_for_events_queue()

    def release(self, button=LEFT):
        mouse._os_mouse.queue.put(ButtonEvent(UP, button, time.time()))
        self.wait_for_events_queue()

    def double_click(self, button=LEFT):
        mouse._os_mouse.queue.put(ButtonEvent(DOUBLE, button, time.time()))
        self.wait_for_events_queue()

    def click(self, button=LEFT):
        self.press(button)
        self.release(button)

    def wheel(self, delta=1):
        mouse._os_mouse.queue.put(WheelEvent(delta, time.time()))
        self.wait_for_events_queue()

    def test_hook(self):
        events = []
        self.press()
        mouse.hook(events.append)
        self.press()
        mouse.unhook(events.append)
        self.press()
        self.assertEquals(len(events), 1)

    def test_is_pressed(self):
        self.assertFalse(mouse.is_pressed())
        self.press()
        self.assertTrue(mouse.is_pressed())
        self.release()
        self.press(X2)
        self.assertFalse(mouse.is_pressed())

        self.assertTrue(mouse.is_pressed(X2))
        self.press(X2)
        self.assertTrue(mouse.is_pressed(X2))
        self.release(X2)
        self.release(X2)
        self.assertFalse(mouse.is_pressed(X2))

    def test_buttons(self):
        mouse.press()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT)])
        mouse.release()
        self.assertEqual(self.flush_events(), [(UP, LEFT)])
        mouse.click()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT), (UP, LEFT)])
        mouse.double_click()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT), (UP, LEFT), (DOWN, LEFT), (UP, LEFT)])
        mouse.right_click()
        self.assertEqual(self.flush_events(), [(DOWN, RIGHT), (UP, RIGHT)])
        mouse.click(RIGHT)
        self.assertEqual(self.flush_events(), [(DOWN, RIGHT), (UP, RIGHT)])
        mouse.press(X2)
        self.assertEqual(self.flush_events(), [(DOWN, X2)])

    def test_position(self):
        self.assertEqual(mouse.get_position(), mouse._os_mouse.get_position())

    def test_move(self):
        mouse.move(0, 0)
        self.assertEqual(mouse._os_mouse.get_position(), (0, 0))
        mouse.move(100, 500)
        self.assertEqual(mouse._os_mouse.get_position(), (100, 500))
        mouse.move(1, 2, False)
        self.assertEqual(mouse._os_mouse.get_position(), (101, 502))

        mouse.move(0, 0)
        mouse.move(100, 499, True, duration=0.01)
        self.assertEqual(mouse._os_mouse.get_position(), (100, 499))
        mouse.move(100, 1, False, duration=0.01)
        self.assertEqual(mouse._os_mouse.get_position(), (200, 500))
        mouse.move(0, 0, False, duration=0.01)
        self.assertEqual(mouse._os_mouse.get_position(), (200, 500))

    def triggers(self, fn, events, **kwargs):
        self.triggered = False
        def callback():
            self.triggered = True
        handler = fn(callback, **kwargs)

        for event_type, arg in events:
            if event_type == DOWN:
                self.press(arg)
            elif event_type == UP:
                self.release(arg)
            elif event_type == DOUBLE:
                self.double_click(arg)
            elif event_type == 'WHEEL':
                self.wheel()

        mouse._listener.remove_handler(handler)
        return self.triggered

    def test_on_button(self):
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, LEFT)]))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, RIGHT)]))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, X)]))

        self.assertFalse(self.triggers(mouse.on_button, [('WHEEL', '')]))

        self.assertFalse(self.triggers(mouse.on_button, [(DOWN, X)], buttons=MIDDLE))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE))
        self.assertFalse(self.triggers(mouse.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE, types=UP))
        self.assertTrue(self.triggers(mouse.on_button, [(UP, MIDDLE)], buttons=MIDDLE, types=UP))

        self.assertTrue(self.triggers(mouse.on_button, [(UP, MIDDLE)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, LEFT)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))
        self.assertFalse(self.triggers(mouse.on_button, [(UP, X)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))

    def test_ons(self):
        self.assertTrue(self.triggers(mouse.on_click, [(UP, LEFT)]))
        self.assertFalse(self.triggers(mouse.on_click, [(UP, RIGHT)]))
        self.assertFalse(self.triggers(mouse.on_click, [(DOWN, LEFT)]))
        self.assertFalse(self.triggers(mouse.on_click, [(DOWN, RIGHT)]))

        self.assertTrue(self.triggers(mouse.on_double_click, [(DOUBLE, LEFT)]))
        self.assertFalse(self.triggers(mouse.on_double_click, [(DOUBLE, RIGHT)]))
        self.assertFalse(self.triggers(mouse.on_double_click, [(DOWN, RIGHT)]))

        self.assertTrue(self.triggers(mouse.on_right_click, [(UP, RIGHT)]))
        self.assertTrue(self.triggers(mouse.on_middle_click, [(UP, MIDDLE)]))

    def test_wait(self):
        # If this fails it blocks. Unfortunately, but I see no other way of testing.
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        def t():
            mouse.wait()
            lock.release()
        Thread(target=t).start()
        self.press()
        lock.acquire()


if __name__ == '__main__':
    unittest.main()
