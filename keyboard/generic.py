# -*- coding: utf-8 -*-
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

    def start_if_necessary(self):
        """
        Starts the listening thread if it wans't already.
        """
        if not self.listening:
            self.listening = True
            self.listening_thread = Thread(target=self.listen)
            self.listening_thread.daemon=True
            self.listening_thread.start()

    def add_handler(self, handler):
        """
        Adds a function to receive each event captured, starting the capturing
        process if necessary.
        """
        self.start_if_necessary()
        self.handlers.append(handler)

    def remove_handler(self, handler):
        """ Removes a previously added event handler. """
        self.handlers.remove(handler)
