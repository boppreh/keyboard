from threading import Thread
import traceback
import functools
from keyboard_event import normalize_name

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

class GenericScanCodeTable(object):
    def __init__(self):
        self.table = None

    def populate(self):
        raise NotImplementedError()

    def get_name_keypad(self, scan_code):
        self.ensure_populated()
        return self.table[scan_code]

    def ensure_populated(self):
        if self.table is None:
            self.table = {}
            self.populate()

    def get_scan_code(self, name):
        self.ensure_populated()
        normalized = normalize_name(name)
        for scan_code, entries in self.table.items():
            for other_name, is_keypad in entries:
                if other_name == normalized:
                    return scan_code
        raise ValueError('Char not not found ' + repr(name))

    def __contains__(self, scan_code):
        self.ensure_populated()
        return scan_code in self.table
