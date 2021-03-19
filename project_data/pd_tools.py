#! /usr/bin/env python
from datetime import datetime as dt
from dateutil import relativedelta


def recurring_monthly(start_date, stop_date, base_string):
    dtime_list = generate_recurring(start_date, stop_date, show_print=False, months=1)
    time_list = []
    desc_list = []
    for dtentry in dtime_list:
        time_list.append(dt.strftime(dtentry, '%y/%m/%d'))
        desc_list.append(f"{base_string} {dt.strftime(dtentry, '%y-%b')}")
    return time_list, desc_list


def generate_recurring(start_date, stop_date, show_print=True, **kwargs):
    """
    start_date/stop_date: mm/dd/yy
    kwargs is any interval=value acceptable to dateutil.relativedelta
    """
    if not len(kwargs):
        kwargs['months'] = 3
    this_date = dt.strptime(start_date, '%m/%d/%y')
    ending = dt.strptime(stop_date, '%m/%d/%y')
    ctr = 0
    data = [this_date]
    while this_date <= ending:
        this_date = this_date + relativedelta.relativedelta(**kwargs)
        data.append(this_date)
        if show_print:
            ctr += 1
            print(f"{ctr:02d}:  {dt.strftime(this_date, '%Y-%m-%d')}")
    return data
