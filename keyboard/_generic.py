# -*- coding: utf-8 -*-
from threading import Thread, Lock
import traceback
import functools

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

class GenericListener(object):
    lock = Lock()

    def __init__(self):
        self.handlers = []
        self.listening = False
        self.queue = Queue()

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
        self.lock.acquire()
        try:
            if not self.listening:
                self.init()

                self.listening = True
                self.listening_thread = Thread(target=self.listen)
                self.listening_thread.daemon = True
                self.listening_thread.start()

                self.processing_thread = Thread(target=self.process)
                self.processing_thread.daemon = True
                self.processing_thread.start()
        finally:
            self.lock.release()

    def pre_process_event(self, event):
        raise NotImplementedError('This method should be implemented in the child class.')

    def process(self):
        """
        Loops over the underlying queue of events and processes them in order.
        """
        assert self.queue is not None
        while True:
            event = self.queue.get()
            if self.pre_process_event(event):
                self.invoke_handlers(event)
            self.queue.task_done()
            
    def add_handler(self, handler):
        """
        Adds a function to receive each event captured, starting the capturing
        process if necessary.
        """
        self.start_if_necessary()
        self.handlers.append(handler)

    def remove_handler(self, handler):
        """ Removes a previously added event handler. """
        while handler in self.handlers:
            self.handlers.remove(handler)
