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
        suppress = key in self._table
        if advance:
            self._table_lock.acquire()
            if suppress and type(self._table[key]) is dict:
                self._table = self._table[key]
            else:
                self._table = self._keys
            self._table_lock.release()

        return suppress

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
        if el not in table or (len(sequence) > 1 and type(table[el]) is not dict):
            if len(sequence) > 1:
                table[el] = {}
            else:
                table[el] = True

        if type(table[el]) is dict:
            return self._acquire_table(sequence, table[el])
        else:
            return table

    def _clean_table(self, table):
        """
        Removes all nested dictionaries which contain no true values
        :param table:
        :return:
        """
        return dict((self._clean_table(k), self._clean_table(v)) for k, v in table.items() if k and v)

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
        table = self._acquire_table(sequence, self._keys)
        table[sequence[0]] = True
        self._refresh()
        self._lock.release()


    def unsuppress_sequence(self, sequence):
        """
        Removes keys from the suppress_keys table;
        this does not track high level callbacks,
        check whether another hook  with the same keys
        has been added before calling this function
        :param sequence: List of scan codes
        :return:
        """
        self._lock.acquire()
        table = self._acquire_table(sequence, self._keys)
        table[sequence[0]] = False
        self._keys = self._clean_table(self._keys)
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
