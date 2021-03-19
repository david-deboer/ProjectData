#! /usr/bin/env python
from datetime import datetime as dt
from dateutil import relativedelta


def recurring_monthly(start_date, stop_date, base_string, tstr=None):
    dtime_list = generate_recurring(start_date, stop_date, show_print=False,
                                    tstr_to_try=tstr, months=1)
    time_list = []
    desc_list = []
    for dtentry in dtime_list:
        time_list.append(dt.strftime(dtentry, '%y/%m/%d'))
        desc_list.append(f"{base_string} {dt.strftime(dtentry, '%y-%b')}")
    return time_list, desc_list


def _a_time_conversion(this_date, tstr_list_to_try=None):
    default_tstr_list_to_try = ['%m/%d/%y', '%m/%d/%Y', '%Y/%m/%d', '%y/%m/%d']
    if tstr_list_to_try is None:
        tstr_list_to_try = default_tstr_list_to_try
    elif isinstance(tstr_list_to_try, str):
        tstr_list_to_try = [tstr_list_to_try]
    for this_tstr in tstr_list_to_try:
        this_tstr = this_tstr.replace('-', '/')
        try:
            return dt.strptime(this_date, this_tstr)
        except ValueError:
            continue
    else:
        raise ValueError('No valid conversion string.')


def generate_recurring(start_date, stop_date, show_print=True,
                       tstr_to_try=None, **kwargs):
    """
    start_date/stop_date in one of formats in tstr_to_try
    kwargs is any interval=value acceptable to dateutil.relativedelta
    """
    if not len(kwargs):
        kwargs['months'] = 3
    this_date = _a_time_conversion(start_date, tstr_to_try)
    ending = _a_time_conversion(stop_date, tstr_to_try)
    ctr = 0
    data = [this_date]
    while this_date <= ending:
        this_date = this_date + relativedelta.relativedelta(**kwargs)
        data.append(this_date)
        if show_print:
            ctr += 1
            print(f"{ctr:02d}:  {dt.strftime(this_date, '%Y-%m-%d')}")
    return data
