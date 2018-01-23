#! usr/bin/env python
from __future__ import absolute_import, print_function
import os
from operator import itemgetter
import subprocess
import math
import sqlite3
import datetime
import datetime as dt
import time
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from matplotlib.dates import MONTHLY, DateFormatter, rrulewrapper, RRuleLocator


def get_time(timestr):
    try:
        timeval = time.strptime(timestr, '%y/%m/%d')
    except ValueError:
        try:
            timeval = time.strptime(timestr, '%Y/%m/%d')
        except ValueError:
            print('Incorrect time:  ', timestr)
            timeval = None
    return timeval


def searchfield(value, infield, match):
    foundMatch = False
    if type(infield) == list:
        foundMatch = searchlist(value, infield, match)
    elif type(infield) == str or type(infield) == unicode and type(value) == str:
        value = value.strip()
        infield = infield.strip()
        if match == 'weak':
            foundMatch = value.lower() in infield.lower()
        elif match == 'moderate':
            foundMatch = value in infield
        elif match == 'strong':
            foundMatch = value.lower() == infield.lower()
        elif match == 'verystrong':
            foundMatch = value == infield
        else:  # default is weak
            foundMatch = value.lower() in infield.lower()
    else:
        foundMatch = value == infield
    return foundMatch


def searchlist(value, inlist, match):
    foundMatch = False
    for v in inlist:
        if type(v) == list:
            foundMatch = searchlist(value, v, match)
        else:
            foundMatch = searchfield(value, v, match)
    return foundMatch


def check_handle(handle):
    badHandle = not handle.isalpha()
    if badHandle:
        print("Note that tex can't have any digits or non-alpha characters")
        useHandle = raw_input('Please try a new handle:  ')
        checkHandle(useHandle)
    else:
        useHandle = handle
    return useHandle


def make_handle(refname):
    if refname.isalpha():
        return refname
    r = {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six',
         '7': 'seven', '8': 'eight', '9': 'nine', '0': 'zero',
         '-': 'dash', ':': '', '.': 'dot', ',': 'comma', '_': 'underscore'}
    handle = ''
    for c in refname:
        if c in r.keys():
            handle += r[c]
        elif not c.isalpha():
            handle += 'X'
        else:
            handle += c
    handle = check_handle(handle)
    return handle


def make_refname(description, length=30):
    ref = description.replace(' ', '').replace('\"', '').lower()[:length]
    return ref


def money(v, a=2, d='$'):
    """I thought about using e.g. pyMoney etc, but overkill and others
       would have to download the package...
          v is the amount
          a is the accuracy (but only no decimal and two-decimal options for display)
          d is the currency sign"""

    r = round(v, a)

    if a > 0:
        g = str("{:s}{:,.2f}".format(d, r))
    else:
        g = str("{:s}{:,.0f}".format(d, r))
    return g


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


def plotGantt(ylabels, dates, predecessors=None, percent_complete=None, show_cdf=True, other_labels=None):
    """This will plot a gantt chart of items (ylabels) and dates.
       If included, it will plot percent_complete for tasks and color code for milestones
       (note, if included, it must have a percent_complete entry for every label)
       If included, it will connect predecessors (note, if included, it also must have an entry for every ylabel)
       other_labels prints another label by the entry (to right on plot), it also must have an entry for every ylabel"""
    # Check data
    if len(ylabels) != len(dates) or percent_complete is not None and len(percent_complete) != len(ylabels):
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
    fig = plt.figure(figsize=(9, 8), tight_layout=True)
    plt.axis(xmin=date_min, xmax=date_max)
    ax = fig.add_subplot(111)
    step = 0.5
    ymin = step
    ymax = len(ylabels) * step

    # Plot the data
    for i in range(0, len(ylabels)):
        start_date, end_date = task_dates[ylabels[i]]
        if start_date == end_date:  # Milestone
            clr = percent_complete[i]
            mkr = 'D'
            plt.plot(end_date, i * step + ymin, mkr, color=clr, markersize=8)
        else:
            plt.barh(i * step + ymin, end_date - start_date, left=start_date, height=0.3, align='center', color='blue', alpha=0.75)
            # if percent_complete is not None and percent_complete[i]>0.0:
            #     plt.barh(i*step+ymin, (end_date - start_date)*percent_complete[i], left=start_date, height=0.15, align='center', color='red', alpha = 0.75)
            # ax.barh((i*0.5)+0.5+0.05, (end_date - start_date)*studentEffort, left=start_date, height=0.1, align='center', color='yellow', alpha = 0.75)
            # ax.barh((i*0.5)+1.0, end_date - mid_date, left=mid_date, height=0.3, align='center',label=labels[1], color='yellow')

    # Format the y-axis
    pos = np.arange(ymin, ymax + step / 2.0, step)  # add the step/2.0 to get that last value
    locsy, labelsy = plt.yticks(pos, ylabels)
    plt.setp(labelsy, fontsize=14)
    plt.grid(color='g', linestyle=':')

    # Plot current time
    now = dt.datetime.now()
    mdate = matplotlib.dates.date2num(now)
    plt.plot([mdate, mdate], [ymin - step, ymax + step], 'k--')

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
                    j = ylabels.index(p)
                    yp = j * step + ymin
                    xp = task_dates[p][1]
                    ykp = [yk, yk, yp]
                    xkp = [xk, xp, xp]
                    plt.plot(xkp, ykp, color='k')

    ax.xaxis_date()  # Tell matplotlib that these are dates...
    rule = rrulewrapper(MONTHLY, interval=1)
    loc = RRuleLocator(rule)
    formatter = DateFormatter("%b '%y")
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(formatter)
    labelsx = ax.get_xticklabels()
    plt.setp(labelsx, rotation=30, fontsize=12)

    # Finish up
    ax.invert_yaxis()
    plt.axis(ymin=ymax + (step - 0.01), ymax=ymin - (step - 0.01))
    fig.autofmt_xdate()
    plt.tight_layout()

    # ##---If plotting cdf---###
    if show_cdf:  # First get total completed and check if milestones
        cdf_tot = 0.0
        for i in range(0, len(ylabels)):
            start_date, end_date = task_dates[ylabels[i]]
            if start_date == end_date:  # Milestone
                if percent_complete[i] != 'w':
                    cdf_tot += 1.0
            else:
                print('NOT MILESTONE')
                show_cdf = False
                break
    if show_cdf:
        cx_dat = np.arange(date_min, mdate, 1.0)
        cy_dat = []
        # DO IN DUMBEST BRUTE FORCE WAY IMAGINABLE
        for xd in cx_dat:
            ctr = 0.0
            for i in range(0, len(ylabels)):
                start_date, end_date = task_dates[ylabels[i]]
                if xd > start_date and type(percent_complete[i]) is tuple:
                    ctr += 1.0
            cy_dat.append(ctr)  # /len(ylabels))
        cy_dat = np.array(cy_dat)
        fig = plt.figure('cdf')
        plt.axis(xmin=date_min, xmax=date_max, ymin=0.0, ymax=1.0)
        ax = fig.add_subplot(111)
        plt.plot(cx_dat, cy_dat / cdf_tot)
        plt.ylabel('Fraction Completed')
        plt.grid()
        ax.xaxis_date()  # Tell matplotlib that these are dates...
        rule = rrulewrapper(MONTHLY, interval=1)
        loc = RRuleLocator(rule)
        formatter = DateFormatter("%b '%y")
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(formatter)
        labelsx = ax.get_xticklabels()
        plt.setp(labelsx, rotation=30, fontsize=12)


def sortByValue(inDict):
    ind = {}
    for i, v in enumerate(inDict):
        nk = inDict[v]
        if nk in ind.keys():
            print('sortByValue key [ ' + str(nk) + ' ] already exists, overwriting...')
        ind[nk] = v
    sind = ind.keys()
    sind.sort()
    sk = []
    for s in sind:
        sk.append(ind[s])
    return sk


def listify(X):
    if X is None:
        return None
    if isinstance(X, (str, unicode)) and ',' in X:
        return X.split(',')
    if isinstance(X, list):
        return X
    return [X]


def stringify(X):
    if X is None:
        return None
    if isinstance(X, str):
        return X
    if isinstance(X, list):
        return ','.join(X)
    return str(X)


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

    def filter_field(self, finding, val):
        for ifind in finding:
            sfnd = str(ifind).lower()
            if (sfnd in self.pass_thru) or (sfnd in val):
                return True
        return False

    def filter_rec(self, Finding, rec, status):
        """
        Steps through the self.find_allowed as filter.
        Parameters:
        -----------
        Finding:  is a class Records_fields that has the search terms (as initially set in self.set_find_defaults)
        rec:  is one record of Data_class
        status:  is the status as returned by Data_class.check_ganttable_status
        """
        for field in self.find_allowed:
            finding = getattr(Finding, field)
            if field == 'status':
                val = status[0].lower()
            else:
                val = str(rec[field]).lower()
            if not self.filter_field(finding, val):
                return False
        return True


class Data:
    Records = Records_fields()

    def __init__(self, dbtype, projectStart='14/09/01', verbose=True):
        """This class has the functions to read in the data file [milestones/reqspecs/interfaces/risks.db] and write out
           a number of tex files.  See README and Architecture.dat
               dbtype is the type of database [milestones, reqspecs, interfaces, risks]
               self.data is the "internal" database and self.db is the read-in sqlite3 database
               sql_map are the fields in the sqlite3 database (read from the .db file, but should correspond to entryMap strings)
               each db file has the following tables (dbtype, trace, type, updated)"""
        self.displayTypes = {'show': self.show, 'listing': self.listing, 'gantt': self.gantt,
                             'noshow': self.noshow, 'file': self.fileout}
        self.ganttable_status = {'removed': 'w',  # see check_ganttable_status
                                 'late': 'red',  # 'darkorange'
                                 'moved': 'y',
                                 'notyet': 'k',
                                 'none': 'k',
                                 'complete': 'b'}
        self.projectStart = projectStart
        self.dbtype = dbtype
        self.dbTypes = {'milestone': {'subdirectory': '.', 'dbfilename': 'milestones.db', 'caption': 'Milestones',
                        'ganttable': 'True', 'traceable': 'True'}}
        self.dirName = self.dbTypes[dbtype]['subdirectory']
        self.inFile = os.path.join(self.dirName, self.dbTypes[dbtype]['dbfilename'])
        self.ganttables = []
        if self.dbTypes[dbtype]['ganttable'] == 'True':
            self.ganttables.append(dbtype)
        self.traceables = []
        if self.dbTypes[dbtype]['traceable'] == 'True':
            self.traceables.append(dbtype)
        self.caption = self.dbTypes[dbtype]['caption']
        self.init_state_variables()
        if verbose:
            self.show_state_var()
        self.cache_lower_data_keys = []
        self.__enable_new_entry = False

    def init_state_variables(self):
        self.state_vars = ['show_cdf', 'description_length', 'gantt_label_to_use', 'other_gantt_label',
                           'display_howsort', 'plot_predecessors', 'show_dtype', 'show_trace', 'show_color_bar',
                           'output_filename', 'gantt_label_prefix', 'default_find_dtype']
        self.show_cdf = True
        self.show_color_bar = True
        self.description_length = 50
        self.gantt_label_to_use = 'description'
        self.other_gantt_label = 'owner'
        self.display_howsort = 'value'
        self.plot_predecessors = True
        self.show_dtype = 'all'
        self.default_find_dtype = ['nsfB']
        self.show_trace = True
        self.output_filename = 'fileout.csv'
        self.gantt_label_prefix = None

    def set_state(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k in self.state_vars:
                setattr(self, k, v)
                print('Setting {} to {}'.format(k, v))
            else:
                print('state_var [{}] not found.'.format(k))

    def show_state_var(self):
        print("State variables")
        for k in self.state_vars:
            print('\t{}:  {}'.format(k, getattr(self, k)))

    def readData(self, inFile=None):
        """This reads in the sqlite3 database and puts it into db and data arrays.
           If inFile==None:
                it reads self.inFile and makes the data, db and sql_map arrays 'self':  this is the 'normal' way,
           if inFile is a valid db file:
                then it returns that data, not changing self (to handle pulling trace values etc out)
           OTHER RANDOM SQLITE3 NOTES:
           for command line sqlite3, select etc (non .commands)  end with ;
           sqlite3 database.db .dump > database.txt          produces a text version
           sqlite3 database.db < database.txt                is the inverse"""

        if inFile is None:
            selfVersion = True
            inFile = self.inFile
        else:
            selfVersion = False

        try:
            sm = self.get_sql_map(inFile)
        except IOError:
            if '+' in inFile:
                print(inFile + ' is a concatenated database -- read in and concatDat')
            else:
                print('Sorry, ' + inFile + ' is not a valid database')
            return None
        for r in self.Records.required:
            if r not in sm.keys():
                raise ValueError("{} column not found in {}.".format(r, inFile))

        self.sql_map = sm
        dbconnect = sqlite3.connect(inFile)
        qdb = dbconnect.cursor()

        # get allowed types
        qdb_exec = "SELECT * FROM types"
        qdb.execute(qdb_exec)
        db = qdb.fetchall()
        allowedTypes = []
        for t in db:
            allowedTypes.append(str(t[0]).lower())
        self.allowedTypes = allowedTypes

        # get all records in dbtype database table
        qdb_exec = "SELECT * FROM records ORDER BY id"
        qdb.execute(qdb_exec)
        db = qdb.fetchall()

        # put database records into data dictionary (records/trace tables)
        data = {}
        self.cache_lower_data_keys = []
        for rec in db:
            refname = rec[sm['refname'][0]]
            # ...get a single entry
            entry = {}
            for v in sm.keys():
                entry[v] = rec[sm[v][0]]  # This makes the entry dictionary
            if entry['status'] is None:
                entry['status'] = 'No status'
            if entry['owner'] is not None:
                entry['owner'] = entry['owner'].split(',')  # make csv list a python list
            # ...get trace information
            for tracetype in self.traceables:
                fieldName = tracetype + 'Trace'
                qdb_exec = "SELECT * FROM trace WHERE refname='{}' COLLATE NOCASE and tracetype='{}' ORDER BY tracename".format(refname, tracetype)
                qdb.execute(qdb_exec)
                trace = qdb.fetchall()
                entry[fieldName] = []
                for v in trace:
                    entry[fieldName].append(v[1])
            # ...read in updated table
            qdb_exec = "SELECT * FROM updated WHERE refname='{}' COLLATE NOCASE ORDER BY level".format(refname)
            qdb.execute(qdb_exec)
            updates = qdb.fetchall()
            entry['updated'] = []
            for v in updates:
                entry['updated'].append([v[1], v[2], v[3]])
            # ...put in data dictionary if not a duplicate
            if refname.lower() in self.cache_lower_data_keys:
                refname = self.find_matching_refname(refname)
                existingEntry = data[refname]
                print('name collision:  ' + refname)
                print('--> not adding to data')
                print('[\n', existingEntry)
                print('\n]\n[\n', entry)
                print('\n]')
            else:
                data[refname] = entry
                self.cache_lower_data_keys.append(refname.lower())
            # ...give warning if not in 'allowedTypes' (but keep anyway)
            if entry['dtype'] is not None and entry['dtype'].lower() not in allowedTypes:
                print('Warning type not in allowed list for {}: {}'.format(refname, entry['dtype']))
                print('Allowed types are:')
                print(allowedTypes)

        # check Trace table to ensure that all refnames are valid
        for tracetype in self.traceables:
            fieldName = tracetype + 'Trace'
            qdb_exec = "SELECT * FROM trace where tracetype='{}' COLLATE NOCASE".format(tracetype)
            qdb.execute(qdb_exec)
            trace = qdb.fetchall()
            for t in trace:
                t_refname = t[0]
                if t_refname.lower() not in self.cache_lower_data_keys:
                    print('{} not in data records:  {}'.format(fieldName, t[0]))
        # check Updated table to ensure that all refnames are valid
        qdb_exec = "SELECT * FROM updated"
        qdb.execute(qdb_exec)
        updates = qdb.fetchall()
        already_found = []
        for u in updates:
            u_refname = u[0]
            if u_refname.lower() not in self.cache_lower_data_keys and u_refname not in already_found:
                already_found.append(u_refname)
                print('updated not in data records:  ', u[0])
        dbconnect.close()
        if 'projectstart' in data.keys():
            self.projectStart = data['projectstart']['value']
            print('Setting project start to ' + self.projectStart)
        if selfVersion:
            self.data = data
            self.db = db
            self.sql_map = sm
        return data

    def get_sql_map(self, inFile=None, tables=['records'], show_detail=False):
        if inFile is None:
            inFile = self.inFile
        if os.path.exists(inFile):
            dbconnect = sqlite3.connect(inFile)
        else:
            print(inFile + ' not found')
            return 0
        qdb = dbconnect.cursor()
        sql_map = {}
        self.rec_fields = []
        for tbl in tables:
            qdb.execute("PRAGMA table_info({})".format(tbl))
            if show_detail:
                print("Table name: {}".format(tbl))
            for t in qdb.fetchall():
                if show_detail:
                    print('\t', t)
                if tbl == 'records':
                    sql_map[str(t[1])] = (t[0], t[2])
                    self.rec_fields.append(t[1])
        dbconnect.close()
        return sql_map

# ##################################################################FIND##################################################################
    def find(self, value, value2=None, field='value', match='weak', display='gantt', return_list=False, **kwargs):
        """This will find records matching value1, except for milestones which looks between value1,value2 dates (time format is yy/m/d)
            value: value for which to search
            value2: second value if used e.g. for bounding dates [None]
            field:  field in which to search (or 'any'/'all')  [value]
            match:  strength of match (weak, moderate, strong, verystrong) [weak]
            display:  how to return data ('show'/'listing'/'gantt'/'file')  [gantt]
            return_list: if True, will return the list [False]
            kwargs:  one of the following records table fields upon which to filter - dtype, status, owner, other, id"""

        # Set defaults and run through kwarg filters
        self.Records.set_find_default()
        if self.default_find_dtype:  # Change dtype filter if state variable set
            self.Records.dtype = self.default_find_dtype
        for k in kwargs.keys():
            if k in self.Records.find_allowed:
                if isinstance(kwargs[k], str) or isinstance(kwargs[k], int):
                    setattr(self.Records, k, [kwargs[k]])
                else:  # Assume it's a list
                    setattr(self.Records, k, kwargs[k])
            else:
                print('keyword {} not allowed'.format(k))
                continue

        rec = Records_fields()
        foundrec = []
        if self.dbtype in self.ganttables and field.lower() == 'value':
            # ...value is a date, so checking dtype and date(s)
            if value2 is None:
                value2 = value
                value = self.projectStart
            value1time = get_time(value)
            value2time = get_time(value2)
            if not isinstance(value1time, time.struct_time) or not isinstance(value2time, time.struct_time):
                return 0
            for dat in self.data.keys():  # Loop over all records
                if self.data[dat][field] is None:
                    continue
                if '-' in self.data[dat][field]:  # A date range is given - use first
                    val2check = self.data[dat][field].split('-')[0].strip()
                else:
                    val2check = str(self.data[dat][field])
                timevalue = get_time(val2check)
                if not isinstance(timevalue, time.struct_time):
                    continue
                status = self.check_ganttable_status(self.data[dat]['status'], timevalue)
                if rec.filter_rec(self.Records, self.data[dat], status):
                    if timevalue >= value1time and timevalue <= value2time:
                        foundrec.append(dat)
        else:
            for dat in self.data.keys():
                foundType = False
                if dtype.lower() in pthru and self.data[dat]['dtype'].lower() != 'na':
                    foundType = True
                elif dtype.lower() in self.data[dat]['dtype'].lower():
                    foundType = True
                if foundType:
                    foundMatch = False
                    if field.lower() in pthru:
                        for fff in self.data[dat].keys():
                            foundMatch = searchfield(value, self.data[dat][fff], match)
                            if foundMatch:
                                break
                    elif field in self.data[dat].keys():
                        foundMatch = searchfield(value, self.data[dat][field], match)
                    else:
                        print('Invalid field for search')
                        return
                    if foundMatch:
                        foundrec.append(dat)
        if len(foundrec):
            foundrec = self._getview(foundrec, self.display_howsort)
            if display not in self.displayTypes.keys():
                display = 'listing'
            self.displayTypes[display](foundrec)
        else:
            print('No records found.')
        if return_list:
            return foundrec

    def list_unique(self, field, filter_on=[], returnList=False):
        unique_values = []
        for dat in self.data.keys():
            if filter_on:
                if self.data[dat][filter_on[0]].lower() != filter_on[1].lower():
                    continue
            chk = self.data[dat][field]
            if chk is None:
                continue
            if type(chk) == list:
                for checking in chk:
                    if checking not in unique_values:
                        unique_values.append(checking)
            else:
                if chk not in unique_values:
                    unique_values.append(chk)
        print("Unique values for ", field)
        for q in unique_values:
            if q is not None:
                print('\t', q)
        if returnList:
            return unique_values

    def getref(self, d, search='description', verbose=True):
        fndk = []
        for dat in self.data.keys():
            dbdesc = self.data[dat][search]
            if dbdesc is not None:
                if isinstance(d, str):
                    if d.lower() in dbdesc.lower():
                        fndk.append(dat)
                else:
                    if d == dbdesc:
                        fndk.append(dat)
        if len(fndk) == 1:
            if verbose:
                self.show(fndk[0])
            return fndk[0]
        else:
            print("{} found".format(len(fndk)))
            for f in fndk:
                refname = self.data[f]['refname']
                dbdesc = self.data[f]['description']
                value = self.data[f]['value']
                status = self.data[f]['status']
                notes = self.data[f]['notes']
                print(refname, ':  ', dbdesc, ' [', value, ']')
                print('\t', status, ':  ', notes)
        return None

# ##################################################################VIEW##################################################################
    def show_schema(self):
        sm = self.get_sql_map(self.inFile)
        for v in sorted(sm.values()):
            for k in sm.keys():
                if sm[k] == v:
                    print(k, '  ', end='')
        print

    def _getview(self, view, howsort):
        if howsort not in self.Records.required:
            print("{} sort option not valid.")
        if view == 'all':
            view = self.data.keys()
        if type(view) is not list:
            view = [view]
        if howsort is None:
            thesekeys = view
        else:
            self.sortedKeys = self.sortby(howsort)
            thesekeys = []
            for key in self.sortedKeys:
                if key in view:
                    thesekeys.append(key)
        return thesekeys

    def noshow(self, view='all'):
        """This just returns the keys to view but doesn't display anything"""
        view = self._getview(view, self.display_howsort)
        return view

    def show(self, view='all', output='stdout'):
        view = self._getview(view, self.display_howsort)
        if output is not 'stdout':
            save2file = True
            fp = open(output, 'w')
        else:
            save2file = False
        for name in view:
            handle = make_handle(name)
            value = self.data[name]['value']
            description = self.data[name]['description']
            dtype = self.data[name]['dtype']
            if self.show_dtype.lower() == 'all' or self.show_dtype.lower() == dtype.lower():
                pass
            else:
                continue
            owner = self.data[name]['owner']
            other = self.data[name]['other']
            updated = self.data[name]['updated']
            notes = self.data[name]['notes']
            idno = self.data[name]['id']
            status = self.data[name]['status']
            commentary = self.data[name]['commentary']
            s = '({}) {}     (\\def\\{})\n'.format(idno, name, handle)
            s += '\tvalue:       {}\n'.format(value)
            s += '\tdescription: {}\n'.format(description)
            s += '\tdtype:        {}\n'.format(dtype)
            s += '\tstatus:      {}\n'.format(status)
            s += '\tnotes:       {}\n'.format(notes)
            s += '\towner:       '
            if owner:
                for o in owner:
                    s += (o + ', ')
                s = s.strip().strip(',')
            s += '\n'
            if other:
                s += '\tother:       {}\n'.format(other)
            if commentary:
                s += '\tcommentary:  {}\n'.format(commentary)
            if len(self.traceables) and self.show_trace:
                for tracetype in self.traceables:
                    fieldName = tracetype + 'Trace'
                    s += '\t' + tracetype + ' trace\n'
                    xxxTrace = self.data[name][fieldName]
                    if len(xxxTrace) == 0 or len(xxxTrace[0]) == 0:
                        s += '\t\tNone\n'
                    else:
                        for xxx in xxxTrace:
                            if len(xxx) > 0:
                                s += '\t\t{}:  '.format(xxx)
            s += '\tUpdated\n'
            if updated:
                for uuu in updated:
                    s += '\t\t{},  {},  {}\n'.format(uuu[0].strip(), uuu[1].strip(), uuu[2].strip())
            print(s)
            if save2file:
                fp.write(s + '\n')
        if save2file:
            print('Writing data to ' + output)
            fp.close()

    def fileout(self, view='all'):
        tag = self.output_filename.split('.')[1]
        if tag == 'csv':
            import csv
        view = self._getview(view, self.display_howsort)
        with open(self.output_filename, 'wb') as output_file:
            if tag == 'csv':
                s = ['value', 'description', 'owner', 'status', 'other', 'notes', 'commentary']
                csvw = csv.writer(output_file)
                csvw.writerow(s)
            for key in view:
                description = self.data[key]['description']
                val = self.data[key]['value']
                status = self.data[key]['status']
                owner = stringify(self.data[key]['owner'])
                other = stringify(self.data[key]['other'])
                notes = stringify(self.data[key]['notes'])
                commentary = stringify(self.data[key]['commentary'])
                if tag == 'csv':
                    s = [val, description, owner, status, other, notes, commentary]
                    csvw.writerow(s)
                else:
                    s = '{} ({:8s}) {}:  {}   ({})\n'.format(val, owner, description, status, key)
                    output_file.write(s)
        print('Writing file to ', self.output_filename)

    def listing(self, view='all'):
        """
        Provides a short listing of the given records (default is all) in fixed widths.
        You can set the description_length via set_description_length(X)
        """
        desc_len = str(self.description_length) + '.' + str(self.description_length)
        view = self._getview(view, self.display_howsort)
        for key in view:
            desc = self.data[key]['description']
            val = self.data[key]['value']
            stat = self.data[key]['status']
            owner = stringify(self.data[key]['owner'])
            print('{:10.10} {:12.12} \t {:{d_l}} ({})'.format(val, owner, desc, key, d_l=desc_len))

    def gantt(self, view='all'):
        view = self._getview(view, self.display_howsort)
        if self.dbtype not in self.ganttables:
            print('You can only gantt:  ', self.ganttables)
        if type(view) != list:
            view = [view]
        if self.gantt_label_to_use not in self.Records.required:
            print("{} label not found to use.".format(self.gantt_label_to_use))
            return
        if self.other_gantt_label and self.other_gantt_label not in self.Records.required:
            print("{} other label not found to use.".format(self.other_gantt_label))
            return
        if self.gantt_label_prefix and self.gantt_label_prefix not in self.Records.required:
            print("{} prefix label not found to use.".format(self.gantt_label_prefix))
            return
        label_prec = 's'
        if self.gantt_label_to_use == 'description':
            label_prec = '.' + str(self.description_length)
        labels = []
        dates = []
        tstat = []
        pred = []
        other = []
        for v in view:
            label = ''
            if self.gantt_label_prefix:
                label = '{}: '.format(self.data[v][self.gantt_label_prefix])
            label += '{:{prec}}'.format(str(self.data[v][self.gantt_label_to_use]), prec=label_prec)
            label = check_gantt_labels(label, labels)
            labels.append(label)
            value = str(self.data[v]['value'])
            status = str(self.data[v]['status']).lower().strip()
            othlab = self.data[v][self.other_gantt_label]
            if othlab is None:
                othlab = ' '
            else:
                othlab = stringify(othlab)
            predss = []
            if 'milestoneTrace' in self.data[v].keys():
                milepred = self.data[v]['milestoneTrace']
                if self.dbtype == 'milestone' or self.dbtype == 'wbs':
                    for x in milepred:
                        if x in view:
                            predss.append(str(self.data[x]['description'])[0:self.description_length])
            if 'taskTrace' in self.data[v].keys():
                taskpred = self.data[v]['taskTrace']
                if self.dbtype == 'task' or self.dbtype == 'wbs':
                    for x in taskpred:
                        if x in view:
                            predss.append(str(self.data[x]['description'])[0:labelLength])
            pred.append(predss)
            dates.append(value)
            other.append(othlab)
            status_return = self.check_ganttable_status(status, value)
            tstat.append(status_return[1])
        if not self.plot_predecessors:
            pred = None
        other_labels = None
        if self.other_gantt_label:
            other_labels = other
        show_cdf = self.show_cdf and self.Records.status[0].lower() != 'late'
        plotGantt(labels, dates, pred, tstat, show_cdf=show_cdf, other_labels=other_labels)
        if self.show_color_bar and self.Records.status[0].lower() != 'late':
            colorBar()

    def check_ganttable_status(self, status, valuetime):
        if status is None or status.lower() == 'no status' or not len(status):
            status = 'none'
        status = status.lower().split()
        status_code = status[0]
        tcode = self.ganttable_status['none']
        if status_code in self.ganttable_status.keys():
            tcode = self.ganttable_status[status_code]
        if status_code == 'removed':
            return (status_code, tcode)

        if isinstance(valuetime, str):
            if '-' in valuetime:
                valuetime = valuetime.split('-')[-1]
            valuetime = get_time(valuetime)
        elif not isinstance(valuetime, time.struct_time):
            print("Invalid time:  ", valuetime, type(valuetime))
        now = time.localtime()

        lag = 0.0
        if len(status) == 2:
            try:
                lag = float(status[1])
            except ValueError:
                statustime = get_time(status[1])
                if isinstance(statustime, time.struct_time):
                    lag = (statustime - valuetime) / 3600.0 / 24.0
                else:
                    tcode = status[1]

        if now > valuetime and status_code != 'complete':
            status_code = 'late'
            tcode = self.ganttable_status[status_code]
        elif status_code == 'complete':
            tcode = lag2rgb(lag)
        return (status_code, tcode)

    def sortby(self, sb):
        sortdict = {}
        for k in self.data:
            sdt = self.data[k][sb]
            if type(sdt) == list:
                sdt = sdt[0]
            sortdict[k] = sdt
        sk = sorted(sortdict.items(), key=itemgetter(1, 0))
        sl = []
        for k in sk:
            sl.append(k[0])
        return sl


# ########################################################################################################################################
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


def colorCurve():
    plt.figure('ColorCurve')
    plt.xlabel('Days')
    for j in range(180):
        i = j - 90.0
        c = lag2rgb(i)
        plt.plot(i, c[0], 'r.')
        plt.plot(i, c[1], 'g.')
        plt.plot(i, c[2], 'b.')


def lag2rgb(lag):
    if lag < -90.0:
        c = (0.0, 1.0, 0.0)
    elif lag > 90.0:
        c = (0.0, 0.0, 1.0)
    else:
        r = 0.0
        if lag > -85.0:
            a = 2.0 * (90.0)**2
            b = math.exp(-(lag - 90.0)**2 / a)
            r = 0.5 * math.exp(-(lag - 90.0)**2 / a)
        else:
            b = 0.0
        if lag < 85.0:
            a = 2.0 * (90.0)**2
            g = math.exp(-(lag + 90.0)**2 / a)
        else:
            g = 0.0
        c = (r, g, b)
    return c


mi = Data('milestone')
dbmi = mi.readData()
print("HERA Milestone viewer")
print("Type mi.find(['start_date_YY/MM/DD'], 'stop_date_YY/MM/DD', [owner='X'], [status='late'])")
