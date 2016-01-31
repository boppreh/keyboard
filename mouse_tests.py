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

    def flush_events(self):
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def press(self, button=LEFT):
        mouse.listener.callback(MouseEvent(DOWN, button))

    def release(self, button=LEFT):
        mouse.listener.callback(MouseEvent(UP, button))

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


if __name__ == '__main__':
    unittest.main()