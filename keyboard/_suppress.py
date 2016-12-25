from threading import Lock


class SuppressionTable(object):
    _keys = {}
    _lock = Lock()  # Required to edit keys
    _table = {}
    _table_lock = Lock()  # Required to edit table

    def is_allowed(self, key, advance=True):
        """
        The goal of this function is to be very fast. This is accomplished
        through the table structure, which ensures that we only need to
        check whether `key is in self._table` and change what variable
        is referenced by `self._table`.
        """
        suppress = key in self._table or key in self._keys
        if advance:
            self._table_lock.acquire()
            if key in self._table and self._table[key]:
                self._table = self._table[key]
            else:
                self._table = self._keys
            self._table_lock.release()

        return not suppress

    def _refresh(self):
        self._table_lock.acquire()
        self._table = self._keys
        self._table_lock.release()

    def _acquire_table(self, sequence, table):
        """
        Returns a flat (single level) dictionary
        :param sequence:
        :param table:
        :return:
        """
        el = sequence.pop(0)
        if el not in table:
            table[el] = {}

        if sequence:
            return self._acquire_table(sequence, table[el])
        else:
            return table

    def suppress_sequence(self, sequence):
        """
        Adds keys to the suppress_keys table
        :param sequence: List of scan codes
        """

        # the suppress_keys table is organized
        # as a dict of dicts so that the critical
        # path is only checking whether the
        # scan code is 'in current_dict'
        self._lock.acquire()
        self._acquire_table(sequence, self._keys)
        self._refresh()
        self._lock.release()

    def suppress_none(self):
        """
        Clears the suppress_keys table and disables
        key suppression
        :return:
        """
        self._lock.acquire()
        self._keys = {}
        self._refresh()
        self._lock.release()
