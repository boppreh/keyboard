from threading import Lock, Thread
from timeit import default_timer as timer
from keyboard._keyboard_event import normalize_name
import re


class KeyTable(object):
    _keys = {}
    _write = Lock()  # Required to edit keys
    _table = {}
    _time = -1
    _elapsed = 0  # Maximum time that has elapsed so far in the sequence
    _read = Lock()  # Required to edit table
    _in_sequence = False
    _keys_suppressed = []  # List of keys that have been suppressed so far in the sequence
    _disable = False  # Disables key suppression during replay to avoid infinite loop
    SEQUENCE_END = 2  # Delimeter that signifies the end of the sequence

    def __init__(self, press_key, release_key):
        self.press_key = press_key
        self.release_key = release_key

    def is_allowed(self, key, is_up, advance=True):
        """
        The goal of this function is to be very fast. This is accomplished
        through the table structure, which ensures that we only need to
        check whether `key is in self._table` and change what variable
        is referenced by `self._table`.

        Unfortunately, handling timeouts properly has added significantly to
        the logic required, but the function should still be well within required
        time limits.
        """
        if self._disable:
            return True

        if key != self.SEQUENCE_END:
            key = re.sub('(left|right) ', '', key)

        time = timer()
        if self._time == -1:
            elapsed = 0
        else:
            elapsed = time - self._time
            if self._elapsed > elapsed:
                elapsed = self._elapsed

        if is_up:
            if self._in_sequence:
                if key != self.SEQUENCE_END:
                    self._keys_suppressed.append((key, is_up))
                return False
            else:
                advance = False

        in_sequence = key in self._table and elapsed < self._table[key][0]
        in_keys = key in self._keys
        suppress = in_sequence or in_keys
        if advance:
            self._read.acquire()
            if in_sequence and self._table[key][2]:
                self._keys_suppressed.clear()
            if in_sequence and self._table[key][1]:
                self._table = self._table[key][1]
                if self._time != -1:
                    self._elapsed = elapsed
                self._time = -1
            elif in_keys and self._keys[key][1]:
                self._table = self._keys[key][1]
                if self._time != -1:
                    self._elapsed = elapsed
                self._time = -1
                self._replay_keys()
                self._keys_suppressed.clear()
            else:
                self._table = self._keys
                self._time = -1
                self._elapsed = -1
                self._replay_keys()
                self._keys_suppressed.clear()
            self._in_sequence = in_sequence
            self._read.release()

        if key != self.SEQUENCE_END and suppress:
            self._keys_suppressed.append((key, is_up))

        return not suppress

    def complete_sequence(self):
        if self.SEQUENCE_END in self._table:
            self.is_allowed(self.SEQUENCE_END, False)
            self._read.acquire()
            self._time = timer()
            self._read.release()
        else:
            self._read.acquire()
            self._time = -1
            self._elapsed = 0
            self._table = self._keys
            self._replay_keys()
            self._keys_suppressed.clear()
            self._read.release()

    def _replay_keys(self):
        self._disable = True
        for key, is_up in self._keys_suppressed:
            if is_up:
                self.release_key(key)
            else:
                self.press_key(key)
        self._disable = False

    def _refresh(self):
        self._read.acquire()
        self._disable = False
        self._table = self._keys
        self._read.release()

    def _acquire_table(self, sequence, table, timeout):
        """
        Returns a flat (single level) dictionary
        :param sequence:
        :param table:
        :return:
        """
        el = sequence.pop(0)
        if el not in table:
            table[el] = (timeout, {}, False)
        if table[el][0] < timeout:
            table[el][0] = timeout

        if sequence:
            return self._acquire_table(sequence, table[el][1], timeout)
        else:
            return table

    def suppress_sequence(self, sequence, timeout):
        """
        Adds keys to the suppress_keys table
        :param sequence: List of scan codes
        :param timeout: Time allowed to elapse before resetting
        """

        # the suppress_keys table is organized
        # as a dict of dicts so that the critical
        # path is only checking whether the
        # scan code is 'in current_dict'
        flat = []
        for subsequence in sequence:
            flat.extend(subsequence)
            flat.append(self.SEQUENCE_END)

        last_index = flat[-1]
        self._write.acquire()
        table = self._acquire_table(flat, self._keys, timeout)
        table[last_index] = (table[last_index][0], table[last_index][1], True)
        self._refresh()
        self._write.release()

    def suppress_none(self):
        """
        Clears the suppress_keys table and disables
        key suppression
        :return:
        """
        self._write.acquire()
        self._keys = {}
        self._refresh()
        self._write.release()

        self._read.acquire()
        self._disable = True
        self._read.release()
