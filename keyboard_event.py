from time import time as now

class KeyboardEvent(object):
    def __init__(self, event_type, scan_code, char=None, name=None, time=None):
        self.event_type = event_type
        self.scan_code = scan_code
        self.time = now() if time is None else time
        self.char = char
        self.name = name

    def __str__(self):
        return 'KeyboardEvent({} {})'.format(self.name,
                                             'up' if self.event_type
                                             == KEY_UP else 'down')

KEY_DOWN = 'key down'
KEY_UP = 'key up'