#! /usr/bin/env python

from __future__ import absolute_import, division, print_function
from datetime import datetime as dt


def recurring_monthly(start_date, stop_date, base_string):
    starting = dt.strptime(start_date, '%m/%d/%y')
    dom = "{:02d}".format(int(start_date.split('/')[1]))
    ending = dt.strptime(stop_date, '%m/%d/%y')
    desc_list = [base_string + ' ' + dt.strptime('%2.2d-%2.2d' % (y, m), '%Y-%m').strftime('%b-%y')
                 for y in xrange(starting.year, ending.year + 1)
                 for m in xrange(starting.month if y == starting.year else 1, ending.month + 1 if y == ending.year else 13)]
    time_list = [dt.strptime('%2.2d-%2.2d' % (y, m), '%Y-%m').strftime('%y/%m/?')
                 for y in xrange(starting.year, ending.year + 1)
                 for m in xrange(starting.month if y == starting.year else 1, ending.month + 1 if y == ending.year else 13)]
    time_list = [x.replace('?', dom) for x in time_list]
    return time_list, desc_list
