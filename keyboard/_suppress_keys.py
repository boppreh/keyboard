
class SuppressionTable(object):
    _suppress_keys = {}
    _current_table = {}

    def is_allowed(self, key, advance=True):
        suppress = key in self._current_table
        if advance:
            if suppress and type(self._current_table[key]) is dict:
                self._current_table = self._current_table[key]
            else:
                self._current_table = self._suppress_keys

        return suppress

    def _refresh(self):
        self._current_table = self._suppress_keys

    def _acquire_table(self, sequence, table):
        '''
        Returns a flat (single level) dictionary
        :param sequence:
        :param table:
        :return:
        '''
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
        '''
        Removes all nested dictionaries which contain no true values
        :param table:
        :return:
        '''
        return dict((self._clean_table(k), self._clean_table(v)) for k, v in table.items() if k and v)

    def suppress_sequence(self, sequence):
        '''
        Adds keys to the suppress_keys table
        :param sequence: List of scan codes
        '''

        # the suppress_keys table is organized
        # as a dict of dicts so that the critical
        # path is only checking whether the
        # scan code is 'in current_dict'
        table = self._acquire_table(sequence, self._suppress_keys)
        table[sequence[0]] = True
        self._refresh()


    def unsuppress_sequence(self, sequence):
        '''
        Removes keys from the suppress_keys table;
        this does not track high level callbacks,
        check whether another hook  with the same keys
        has been added before calling this function
        :param sequence: List of scan codes
        :return:
        '''
        table = self._acquire_table(sequence, self._suppress_keys)
        table[sequence[0]] = False
        self._suppress_keys = self._clean_table(self._suppress_keys)
        self._refresh()

    def suppress_none(self):
        '''
        Clears the suppress_keys table and disables
        key suppression
        :return:
        '''
        self._suppress_keys = {}
        self._refresh()
