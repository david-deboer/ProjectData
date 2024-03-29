from project_data import pd_utils

find_allowed = ['dtype', 'status', 'owner', 'other', 'id']


def agrees(supval, chkval, method='equals', retain_case=True):
    """
    Check if the supval/chkval "agree".

    Parameter
    ---------
    supval : str
        value 1
    chkval : str
        value 2
    method : str
        One of "equals", "in", "start"
    retain_case : bool
        Retain the case of the strings or not.
    """
    if chkval is not None:
        if isinstance(supval, str):
            if not retain_case:
                supval = supval.lower()
                chkval = chkval.lower()
            if method == 'in':
                if supval in chkval:
                    return True
            elif method == 'start':
                if chkval.startswith(supval):
                    return True
            else:
                if supval == chkval:
                    return True
        else:
            if supval == chkval:
                return True
    elif supval is None:
        return True
    return False


class Filter:
    def __init__(self):
        self.find_allowed = find_allowed
        self.pass_thru = ['any', 'all', 'n/a', '-1', -1]  # do all if one of these

    def set_find_default(self):
        for allowed in find_allowed:
            setattr(self, allowed, ['all'])
        self.id = [-1]

    def _filter_field(self, finding, val):
        """
        Checks if 'val' is in finding.

        Parameters
        ----------
        finding : list
            finding ...
        val : list
            val ...
        """
        f_val = [str(x).strip().lower() for x in val]
        for ifind in finding:
            sfnd = str(ifind).strip().lower()
            if (sfnd in self.pass_thru) or (sfnd in f_val):
                return True
        return False

    def on_fields(self, rec, status):
        """
        Steps through the self.find_allowed as filter.
        Parameters:
        -----------
        Finding_class:  is a class Records_fields that has the search terms (as initially set in
                        self.set_find_defaults and modified by set_state or find call)
        rec:  is one record
        status:  is the status as returned by Data_class.check_ganttable_status
        """
        for field in self.find_allowed:
            finding = getattr(self, field)
            rec_val = getattr(rec, field)
            if field == 'status':
                val = [status[0].lower()]
            elif rec_val is None:
                val = ['None']
            else:
                val = [str(x).lower() for x in pd_utils.listify(rec_val)]
            if not self._filter_field(finding, val):
                return False
        return True

    def on_time(self, vtime, v1time, v2time, match, rec):
        """
        Filter on time.
        """
        if 'upda' in match.lower() or 'init' in match.lower():
            event, timing = match.split()
            print("In don't think this works.")
            if not rec[event]:
                return False
            if timing.lower() == 'before':
                return rec[event] <= v2time
            if timing.lower() == 'after':
                return rec[event] >= v2time
            if timing.lower() == 'between':
                return rec[event] >= v1time and rec[event] <= v2time
        else:
            if vtime >= v1time and vtime <= v2time:
                return True

        return False
