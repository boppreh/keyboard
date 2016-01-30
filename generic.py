from threading import Thread
import traceback

_handlers = []

def _callback(event):
    for handler in _handlers:
        try:
            if handler(event):
                # Stop processing this hotkey.
                return 1
        except Exception as e:
            traceback.print_exc()

def start_listening(listen):
	_listening_thread = Thread(target=listen, args=(_callback,))
	_listening_thread.daemon=True
	_listening_thread.start()

def add_handler(handler):
    """ Adds a function to receive each keyboard event captured. """
    _handlers.append(handler)

def remove_handler(handler):
    """ Removes a previously added keyboard event handler. """
    _handlers.remove(handler)