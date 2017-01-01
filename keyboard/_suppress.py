from threading import Lock
from timeit import default_timer as timer
from keyboard._keyboard_event import normalize_name

class KeyTable(object):
    _keys = {}
    _write = Lock()  # Required to edit keys
    _table = {}
    _time = -1
    _elapsed = 0  # Maximum time that has elapsed so far in the sequence
    _read = Lock()  # Required to edit table
    _in_sequence = False
    SEQUENCE_END = 2  # Delimeter that signifies the end of the sequence

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
        if key != self.SEQUENCE_END:
            key = normalize_name(key.split(' ')[-1])
        time = timer()
        if -1 in (self._time, self._elapsed):
            elapsed = 0
        else:
            elapsed = time - self._time
            if self._elapsed > elapsed:
                elapsed = self._elapsed

        if is_up:
            if self._in_sequence:
                return False
            else:
                advance = False

        in_sequence = key in self._table and elapsed < self._table[key][0]
        suppress = in_sequence or key in self._keys
        if advance:
            self._read.acquire()
            if suppress and not in_sequence:  # Currently not the most optimized piece of code
                self._table = self._keys
                in_sequence = True
            if in_sequence and self._table[key][1]:
                self._table = self._table[key][1]
                if self._time != -1:
                    self._time = time
                    self._elapsed = elapsed
            else:
                self._table = self._keys
                self._time = -1
                self._elapsed = -1
            self._in_sequence = in_sequence
            self._read.release()

        return not suppress

    def complete_sequence(self):
        if self.SEQUENCE_END in self._table:
            self._read.acquire()
            self._time = timer()
            self._read.release()
            self.is_allowed(self.SEQUENCE_END, False)
        else:
            self._read.acquire()
            self._time = -1
            self._table = self._keys
            self._read.release()

    def _refresh(self):
        self._read.acquire()
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
            table[el] = (timeout, {})
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

        print(flat)

        self._write.acquire()
        self._acquire_table(flat, self._keys, timeout)
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
