from threading import Thread
import traceback
import functools
from .keyboard_event import normalize_name

class GenericListener(object):
    def __init__(self):
        self.handlers = []
        self.listening = False

    def invoke_handlers(self, event):
        for handler in self.handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                traceback.print_exc()

    def wrap(self, func):
        """
        Wraps a function ensuring the listener thread is active.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwds):
            if not self.listening:
                self.listening = True
                self.listening_thread = Thread(target=self.listen)
                self.listening_thread.daemon=True
                self.listening_thread.start()
            return func(*args, **kwds)
        return wrapper

    def add_handler(self, handler):
        """ Adds a function to receive each event captured. """
        self.handlers.append(handler)

    def remove_handler(self, handler):
        """ Removes a previously added event handler. """
        self.handlers.remove(handler)
