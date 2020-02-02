"""
Creates a simple Gantt chart
Adapted from https://bitbucket.org/DBrent/phd/src/1d1c5444d2ba2ee3918e0dfd5e886eaeeee49eec/visualisation/plot_gantt.py  # noqa
BHC 2014

Adapted by ddeboer 6/Feb/2015
"""
from __future__ import absolute_import, print_function
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import MONTHLY, DateFormatter, rrulewrapper, RRuleLocator
import numpy as np


def check_gantt_labels(label, labels):
    if label in labels:
        label += '&'
        label = check_gantt_labels(label, labels)
    if label not in labels:
        return label


def __create_date(yymmdd, return_triplet=False):
    """Creates the date from yy/mm/dd"""
    dlist = yymmdd.split('/')
    if len(dlist) < 3:
        print('error  ', dlist)
    if int(dlist[0]) < 1000:
        yr = 2000 + int(dlist[0])
    else:
        yr = int(dlist[0])
    mn = int(dlist[1])
    dy = int(dlist[2])
    date = dt.datetime(yr, mn, dy)
    mdate = matplotlib.dates.date2num(date)
    if return_triplet:
        return yr, mn, dy
    else:
        return mdate


def get_index(k, lbls):
    for i, l in enumerate(lbls):
        if k in l:
            return i
    return None


def get_key(p, task_dates):
    for k in task_dates.keys():
        if p in k:
            return k
    return None


def plotGantt(ylabels, dates, predecessors=None, status_codes=None, show_cdf=True, other_labels=None):  # noqa
    """
    This will plot a gantt chart of items (ylabels) and dates.  If included, it will plot percent
    complete for tasks and color code for milestones (note, if included, it must have a status_codes
    entry for every label)  If included, it will connect predecessors (note, if included, it also
    must have an entry for every ylabel) other_labels prints another label by the entry (to right on
    plot), it also must have an entry for every ylabel
    """
    # Check data
    if len(ylabels) != len(dates) or status_codes is not None and len(status_codes) != len(ylabels):
        print('Data not in correct format.')
        return 0
    # Get dates in right format and find extrema
    task_dates = {}
    date_min = 10000000
    date_max = -10000000
    for i, task in enumerate(ylabels):
        if type(dates[i]) == str and '-' in dates[i]:
            dates[i] = dates[i].split('-')
        if type(dates[i]) == str:
            dates[i] = [dates[i]]
        if len(dates[i]) == 1:
            dates[i].append(dates[i][0])
        cdl = []
        for ddd in dates[i]:
            mdate = __create_date(ddd)
            cdl.append(mdate)
            if mdate < date_min:
                date_min = mdate
                yrmin, mnmin, dymin = __create_date(ddd, return_triplet=True)
            if mdate > date_max:
                date_max = mdate
                yrmax, mnmax, dymax = __create_date(ddd, return_triplet=True)
        task_dates[task] = cdl
    date_min = matplotlib.dates.date2num(dt.datetime(yrmin, mnmin, 1))
    if mnmax == 12:
        mnmax = 1
        yrmax += 1
    else:
        mnmax += 1
    date_max = matplotlib.dates.date2num(dt.datetime(yrmax, mnmax, 1))
    if (date_max - date_min) / 30.0 > 5:  # give a wider plot buffer
        date_max = matplotlib.dates.date2num(dt.datetime(yrmax, mnmax, 28))

    # Initialise plot
    fig1 = plt.figure(figsize=(9, 8), tight_layout=True)
    ax1 = fig1.add_subplot(111)
    ax1.axis(xmin=date_min, xmax=date_max)
    step = 0.5
    ymin = step
    ymax = len(ylabels) * step

    # Plot the data
    for i in range(0, len(ylabels)):
        start_date, end_date = task_dates[ylabels[i]]
        if start_date == end_date:  # Milestone
            clr = status_codes[i][1]
            mkr = 'D'
            plt.plot(end_date, i * step + ymin, mkr, color=clr, markersize=8)
        else:
            print("Should use the percent complete status_codes for color etc.")
            plt.barh(i * step + ymin, end_date - start_date, left=start_date, height=0.3,
                     align='center', color='blue', alpha=0.75)

    # Format the y-axis
    pos = np.arange(ymin, ymax + step / 2.0, step)  # add the step/2.0 to get that last value
    locsy, labelsy = plt.yticks(pos, ylabels)
    plt.setp(labelsy, fontsize=14)
    plt.grid(color='g', linestyle=':')

    # Plot current time
    now = dt.datetime.now()
    now_date = matplotlib.dates.date2num(now)
    plt.plot([now_date, now_date], [ymin - step, ymax + step], 'k--')

    # Plot other_labels if present
    if other_labels is not None:
        for i in range(0, len(ylabels)):
            start_date, end_date = task_dates[ylabels[i]]
            plt.text(end_date + 5, i * step + ymin, str(other_labels[i]))

    # Plot predecessors
    if predecessors is not None:
        for i, k in enumerate(ylabels):
            yk = i * step + ymin
            xk = task_dates[k][0]
            for p in predecessors[i]:
                if len(p) > 0:
                    j = get_index(p, ylabels)
                    if j is None:
                        continue
                    yp = j * step + ymin
                    k = get_key(p, task_dates)
                    if k is None:
                        continue
                    xp = task_dates[k][1]
                    # xp = task_dates[p][1]
                    ykp = [yk, yk, yp]
                    xkp = [xk, xp, xp]
                    plt.plot(xkp, ykp, color='b', linewidth=3)

    ax1.xaxis_date()  # Tell matplotlib that these are dates...
    rule = rrulewrapper(MONTHLY, interval=1)
    loc = RRuleLocator(rule)
    formatter = DateFormatter("%b '%y")
    ax1.xaxis.set_major_locator(loc)
    ax1.xaxis.set_major_formatter(formatter)
    labelsx = ax1.get_xticklabels()
    plt.setp(labelsx, rotation=30, fontsize=12)

    # Finish up
    ax1.invert_yaxis()
    ax1.axis(ymin=ymax + (step - 0.01), ymax=ymin - (step - 0.01))
    fig1.autofmt_xdate()
    plt.tight_layout()

    # ##---If plotting cdf, check to see if you should---###
    if show_cdf:  # First get total number of milestones
        cdf_tot = 0
        for i in range(0, len(ylabels)):
            start_date, end_date = task_dates[ylabels[i]]
            if start_date == end_date:  # Milestone
                if start_date > now_date:
                    continue
                if status_codes[i][0] != 'removed':
                    cdf_tot += 1
            else:
                print('NOT MILESTONE')
                show_cdf = False
                break
        if not cdf_tot:
            cdf_tot = 1
    if show_cdf:
        cx_dat = np.arange(date_min, now_date, 1.0)
        cy_dat = []
        for xd in cx_dat:
            ctr = 0.0
            for i in range(0, len(ylabels)):
                start_date, end_date = task_dates[ylabels[i]]
                if xd > start_date and status_codes[i][0] == 'complete':
                    ctr += 1.0
            cy_dat.append(ctr)  # /len(ylabels))
        cy_dat = np.array(cy_dat)
        fig2 = plt.figure('cdf')
        ax2 = fig2.add_subplot(111)
        ax2.axis(xmin=date_min, xmax=date_max, ymin=0.0, ymax=1.0)
        plt.plot(cx_dat, cy_dat / cdf_tot)
        plt.ylabel('Fraction Completed')
        plt.grid()
        ax2.xaxis_date()  # Tell matplotlib that these are dates...
        rule = rrulewrapper(MONTHLY, interval=1)
        loc = RRuleLocator(rule)
        formatter = DateFormatter("%b '%y")
        ax2.xaxis.set_major_locator(loc)
        ax2.xaxis.set_major_formatter(formatter)
        labelsx = ax2.get_xticklabels()
        plt.setp(labelsx, rotation=30, fontsize=12)


def colorBar():
    fff = plt.figure('ColorBar')
    ax = fff.add_subplot(111)
    ax.set_yticklabels([])
    plt.xlabel('Days')
    for j in range(180):
        i = j - 90.0
        c = lag2rgb(i)
        plt.plot([i], [1.0], 's', markersize=20, color=c, markeredgewidth=0.0, fillstyle='full')
    ar = plt.axis()
    boxx = [ar[0], ar[1], ar[1], ar[0], ar[0]]
    boxy = [-5.0, -5.0, 6.0, 6.0, -5.0]
    plt.plot(boxx, boxy, 'k')
    plt.axis('image')


def lag2rgb(lag):
    s = 255.0
    bs = [[85.0, (255.0 / s, 190.0 / s, 50.0 / s)],
          [50.0, (220.0 / s, 110.0 / s, 110.0 / s)],
          [25.0, (125.0 / s, 110.0 / s, 150.0 / s)],
          [5.0, (55.0 / s, 0.0 / s, 250.0 / s)],
          [-5.0, (55.0 / s, 0.0 / s, 250.0 / s)],
          [-25.0, (0.0 / s, 200.0 / s, 0.0 / s)],
          [-85.0, (0.0 / s, 255.0 / s, 0.0 / s)],
          [-999.0, (0.0 / s, 255.0 / s, 0.0 / s)]]
    for j in range(len(bs)):
        if bs[j][0] < lag:
            break
    else:
        j = 0
    if j == 0 or j == len(bs) - 1:
        return bs[j][1]
    else:
        c = []
        dx = bs[j - 1][0] - bs[j][0]
        for i, y2 in enumerate(bs[j - 1][1]):
            y1 = bs[j][1][i]
            m = (y2 - y1) / dx
            c.append(m * (lag - bs[j][0]) + y1)
        return c


def colorCurve():
    plt.figure('ColorCurve')
    plt.xlabel('Days')
    s = 255.0
    rv = np.arange(-100, 100, 1)
    for j in rv:
        c = lag2rgb(j)
        plt.plot(j, s * c[0], 'r.')
        plt.plot(j, s * c[1], 'g.')
        plt.plot(j, s * c[2], 'b.')
        plt.plot(j, s * 0.5, color=c, marker='o')
        plt.plot(j, s * 0.505, color=c, marker='o')
        plt.plot(j, s * 0.51, color=c, marker='o')


just_testing = False
if just_testing:
    # Data
    ylabels = []
    ylabels.append('Hardware Design & Review')
    ylabels.append('Hardware Construction')
    ylabels.append('Integrate and Test Laser Source')
    ylabels.append('Objective #1')
    ylabels.append('Objective #2')
    ylabels.append('Present at ASMS')
    ylabels.append('Present Data at Gordon Conference')
    ylabels.append('Manuscripts and Final Report')

    effort = []
    effort.append(0.2)
    effort.append(0.2)
    effort.append(0.2)
    effort.append(0.3)
    effort.append(0.25)
    effort.append(0.3)
    effort.append(0.5)
    effort.append(0.7)

    customDates = []
    customDates.append(['2014/6/1', '2014/12/5'])
    customDates.append(['2014/6/1', '2014/8/7'])
    customDates.append(['2014/7/6', '2014/7/6'])
    customDates.append(['2014/10/12', '2015/3/5'])
    customDates.append(['2015/2/8', '2015/6/4'])
    customDates.append(['2015/5/21', '2015/6/3'])
    customDates.append(['2015/7/2', '2015/7/2'])
    customDates.append(['2015/4/23', '2015/8/1'])
    plotGantt(ylabels, customDates)
