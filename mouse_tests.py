import unittest
from mouse_event import MouseEvent, MOVE, WHEEL, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, HORIZONTAL, DOUBLE
import mouse

class FakeOsMouse(object):
    def __init__(self, append):
        self.append = append
        self.position = (0, 0)

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
    def setUp(self):
        # We will use our own events, thank you very much.
        mouse.listener.listening = True
        self.events = []
        mouse.os_mouse = FakeOsMouse(self.events.append)
        for button in (LEFT, RIGHT, MIDDLE, X, X2):
            self.release(button)

    def flush_events(self):
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def press(self, button=LEFT):
        mouse.listener.callback(MouseEvent(DOWN, button))

    def release(self, button=LEFT):
        mouse.listener.callback(MouseEvent(UP, button))

    def double_click(self, button=LEFT):
        mouse.listener.callback(MouseEvent(DOUBLE, button))

    def click(self, button=LEFT):
        self.press(button)
        self.release(button)

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
        self.assertEqual(mouse.get_position(), mouse.os_mouse.get_position())

    def test_move(self):
        mouse.move(0, 0)
        self.assertEqual(mouse.os_mouse.get_position(), (0, 0))
        mouse.move(100, 500)
        self.assertEqual(mouse.os_mouse.get_position(), (100, 500))
        mouse.move(1, 2, False)
        self.assertEqual(mouse.os_mouse.get_position(), (101, 502))

        mouse.move(0, 0)
        mouse.move(100, 499, True, duration=0.01)
        self.assertEqual(mouse.os_mouse.get_position(), (100, 499))
        mouse.move(100, 1, False, duration=0.01)
        self.assertEqual(mouse.os_mouse.get_position(), (200, 500))
        mouse.move(0, 0, False, duration=0.01)
        self.assertEqual(mouse.os_mouse.get_position(), (200, 500))

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

        mouse.listener.remove_handler(handler)
        return self.triggered

    def test_on_button(self):
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, LEFT)]))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, RIGHT)]))
        self.assertTrue(self.triggers(mouse.on_button, [(DOWN, X)]))

        self.assertFalse(self.triggers(mouse.on_button, [(WHEEL, '')]))

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