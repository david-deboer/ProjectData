import pd_utils


class Records_fields:
    def __init__(self):
        self.required = ['refname', 'value', 'description', 'dtype', 'status', 'owner', 'other', 'notes', 'id', 'commentary']
        self.find_allowed = ['dtype', 'status', 'owner', 'other', 'id']
        self.pass_thru = ['any', 'all', 'n/a', '-1', -1]  # do all if one of these

    def set_find_default(self):
        self.dtype = ['all']
        self.owner = ['all']
        self.other = ['all']
        self.status = ['all']
        self.id = [-1]

    def _filter_field(self, finding, val):
        """
        Checks 'val'
        """
        for ifind in finding:
            sfnd = str(ifind).strip().lower()
            val = str(val).strip().lower()
            if (sfnd in self.pass_thru) or (sfnd == val):
                return True
        return False

    def filter_rec(self, Finding_class, rec, status):
        """
        Steps through the self.find_allowed as filter.
        Parameters:
        -----------
        Finding_class:  is a class Records_fields that has the search terms (as initially set in
                        self.set_find_defaults and modified by set_state or find call)
        rec:  is one record of Data_class
        status:  is the status as returned by Data_class.check_ganttable_status
        """
        for field in self.find_allowed:
            finding = getattr(Finding_class, field)
            if field == 'status':
                val = status[0].lower()
            else:
                val = str(rec[field]).lower()
            if not self._filter_field(finding, val):
                return False
        return True

    def filter_on_updates(self, match, v1time, v2time, rec):
        """
        Filter on the updated table.
        """
        event, timing = match.split()
        if not rec[event]:
            return False
        if timing.lower() == 'before':
            return rec[event] <= v2time
        if timing.lower() == 'after':
            return rec[event] >= v2time
        if timing.lower() == 'between':
            return rec[event] >= v1time and rec[event] <= v2time
        return False
