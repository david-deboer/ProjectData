"""ProjectData."""
import os
from argparse import Namespace
from project_data import pd_gantt
from project_data import pd_utils
from project_data import filters as FF
import datetime
from pysqlite_simple import tables
from ddb_util import state_variable
from tabulate import tabulate
from matplotlib import MatplotlibDeprecationWarning
import matplotlib.dates
import matplotlib.pyplot as plt
import warnings
import copy

warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


class Data(state_variable.StateVar):
    """
    Overall data class.

    This class has the functions to read in the data file [milestones/reqspecs/interfaces/risks.db]
        dbtype is the type of database [milestones, reqspecs, interfaces, risks]
        self.data is the "internal" database
        sqlmap are the fields in the sqlite3 database (read from the .db file, but should
        correspond to entryMap strings) each db file has the following tables (dbtype, trace,
        type, updated)
    """

    def __init__(self, dbtype, projectStart='14/09/01', db_file='databases.json', **kwargs):
        """Initialize."""
        super().__init__([])
        self.sv_load(load_from=db_file, keys_to_use='state_variables', use_to_init=db_file)
        self.state(**kwargs)
        self.displayMethods = {'show': self.show, 'listing': self.listing, 'gantt': self.gantt,
                               'noshow': self.noshow, 'file': self.fileout}
        self.projectStart = projectStart
        self.dbtype = dbtype
        self.db_list, self.ganttable_status = pd_utils.get_db_json(db_file)
        self.dirName = self.db_list[dbtype]['subdirectory']
        self.inFile = os.path.join(self.dirName, self.db_list[dbtype]['dbfilename'])
        self.db = tables.DB(self.inFile)
        self.make_new_entry = False
        self.gantt_return_info = None

    def read_data(self, since=None):
        """
        Parameters
        ----------
        since : str/None
            If set, will only load from the updated table after since.
            Running mi.find('since') will show just these.

        OTHER RANDOM SQLITE3 NOTES:
           for command line sqlite3, select etc (non .commands)  end with ;
           sqlite3 database.db .dump > database.txt          produces a text version
           sqlite3 database.db < database.txt                is the inverse
        """

        self.db.read_table('records', order_by='id')
        self.num_records = len(self.db.records.refname)
        if since is not None:
            print("Type mi.find('since') to see records.")
            self.db.read_table('updated', order_by='updated', updated='>{}'.format(since))
        else:
            self.db.read_table('updated', order_by='updated')
        self.db.read_table('types')
        self.db.read_table('trace')

        # collate updated and trace for refname
        self.updated_collate = {}
        for i, refname in enumerate(self.db.updated.refname):
            self.updated_collate.setdefault(refname, [])
            self.updated_collate[refname].append(i)
        self.trace_collate = {}
        for i, refname in enumerate(self.db.trace.refname):
            self.trace_collate.setdefault(refname, [])
            self.trace_collate[refname].append(i)

    def dtype_info(self, dtype='nsfB', just_dates=False, plot_stats='complete,cdf'):
        """
        Print out a short timeline of dtype.
        """
        if dtype not in self.db.types.name:
            print("{} not found".format(dtype))
            return None
        i = self.db.types.name.index(dtype)
        rec = self.db.mk_entry_ns('types', i)
        print("Information for {}: {}".format(rec.name, rec.description))
        quarters = {'stats': [], 'stat_mid': [], 'complete_color': []}
        if rec.start is not None:
            rec.start = pd_utils.get_time(rec.start)
            quarters['start'] = rec.start
            print("  {}  ".format(datetime.datetime.strftime(rec.start, '%y/%m/%d')), end='')
        if rec.duration_months is not None:
            duration_qtr = int(rec.duration_months / 3.0)
            quarters['duration'] = duration_qtr
            print("  {}  months, {} quarters".format(rec.duration_months, duration_qtr))
        if (rec.start is not None) and (rec.duration_months is not None):
            tdelt = datetime.timedelta(1.0)
            y_old = rec.start.year
            end = pd_utils.get_qtr_date(duration_qtr, rec.start) - tdelt
            print('{}  -  {}'.format(datetime.datetime.strftime(rec.start, '%Y/%m/%d'),
                                     datetime.datetime.strftime(end, '%Y/%m/%d')))
            pd10 = 10 * '-'
            proj_year = 0
            for q in range(duration_qtr):
                if not q % 4:
                    proj_year += 1
                py_sym = pd_utils.quarter_symbol(q, proj_year)
                qtr = pd_utils.get_qtr_date(q, rec.start)
                quarters[q] = [qtr]
                qstr = datetime.datetime.strftime(qtr, '%Y/%m/%d')
                pspace = proj_year * ' '
                if qtr.year > y_old:
                    y_old = qtr.year
                    print("\t         {}     {}  {}{}".format(pd10, pd10, pspace, str(proj_year)))
                print("\tQtr {:2d}:  {}".format(q + 1, qstr), end='')
                qtr = pd_utils.get_qtr_date(q + 1, rec.start) - tdelt
                quarters[q].append(qtr)
                if not just_dates:
                    self.find(quarters[q][0], quarters[q][1], dtype=dtype, display='noshow')
                quarters['stats'].append(copy.copy(self.find_stats))
                quarters['complete_color'].append(pd_gantt.lag2rgb(self.find_stats['complete']['ave']))  # noqa
                mid_pt = (quarters[q][1] - quarters[q][0]).days / 2.0
                quarters['stat_mid'].append(quarters[q][0] + datetime.timedelta(days=mid_pt))
                print("  -  {}  {}".format(datetime.datetime.strftime(qtr, '%Y/%m/%d'), py_sym))
                if not just_dates and plot_stats:
                    gs, pn = plot_stats.split(',')
                    self.plot_find_stats(gstatus=gs, figure=pn)
        self.quarters = quarters

    def make_find_stats(self, foundrec):
        self.find_stats = {}
        if not len(foundrec):
            return
        for gs in self.ganttable_status.keys():
            self.find_stats[gs.lower()] = {"cnt": 0, "net": 0, "ave": 0.0}
        self.find_stats["_time1"] = None
        self.find_stats["_time2"] = None
        now = datetime.datetime.now()
        need_to_set_time = True
        for i in foundrec:
            this_status = self.db.records.status[i]
            this_date = pd_utils.get_time(self.db.records.value[i])
            if this_date is None:
                continue
            if need_to_set_time:
                need_to_set_time = False
                self.find_stats['_time1'] = this_date
                self.find_stats['_time2'] = this_date
            else:
                if this_date < self.find_stats['_time1']:
                    self.find_stats['_time1'] = this_date
                if this_date > self.find_stats['_time2']:
                    self.find_stats['_time2'] = this_date
            if this_status is None:
                if this_date is None:
                    lag = 0
                else:
                    lag = (now - this_date).days
                if lag <= 0:
                    sdict = {'_type': 'none', 'net': 1, 'cnt': 1, 'ave': 1}
                else:
                    sdict = {'_type': 'late', 'net': 1, 'cnt': 1, 'ave': lag}
            else:
                this_status_type = None
                for stat_type in self.find_stats.keys():
                    if stat_type in this_status.lower():
                        this_status_type = stat_type
                        break
                if this_status_type is None:
                    print("Status type {} uncounted".format(this_status))
                    continue
                sdict = {'_type': this_status_type.lower(), 'net': 0, 'cnt': 1, 'ave': 0}
                try:
                    val = float(this_status.split()[1])
                    sdict['net'] = 1
                    sdict['ave'] = val
                except (ValueError, IndexError):
                    pass
            this = sdict['_type'].lower()
            for k, v in sdict.items():
                if k.startswith('_'):
                    continue
                self.find_stats[this][k] += v
        for stat_type, val in self.find_stats.items():
            if stat_type.startswith('_'):
                continue
            if val['net']:
                x = val['ave'] / val['net']
                self.find_stats[stat_type]['ave'] = x

    def show_find_stats(self):
        headers = ['Type', 'Count', 'Net', 'Average']
        table_data = []
        print("\nPeriod: {}  -  {}"
              .format(str(self.find_stats['_time1']), str(self.find_stats['_time2'])))
        for k in sorted(list(self.find_stats.keys())):
            if k.startswith('_'):
                continue
            ave = "{:.1f}".format(self.find_stats[k]['ave'])
            row = [k, self.find_stats[k]['cnt'], self.find_stats[k]['net'], ave]
            table_data.append(row)
        print(tabulate(table_data, headers=headers, tablefmt='orgtbl'))

    def plot_find_stats(self, gstatus='complete', figure='cdf'):
        max_marker_size = 60.0
        normalize_marker_to = 10.0
        fig = plt.figure("Plot_Stats")
        dt = (self.find_stats['_time2'] - self.find_stats['_time1']) / 2
        x = self.find_stats['_time1'] + dt
        x_num = matplotlib.dates.date2num(x)
        clr = self.find_stats[gstatus]['ave']
        sze = self.find_stats[gstatus]['net']
        if figure == 'cdf' and self.gantt_return_info is not None:
            y = None
            for i, date_num in enumerate(self.gantt_return_info['cdf_x']):
                if date_num > x_num:
                    y = self.gantt_return_info['cdf_y'][i] / self.gantt_return_info['cdf_tot']
                    break
            if y is None:
                y = 0.5
        else:
            y = self.find_stats[gstatus]['ave']
        clr = pd_gantt.lag2rgb(clr)
        sze = int((sze / normalize_marker_to) * max_marker_size)
        plt.plot(x, y, 's', color=clr, markersize=sze)
        ycdf = self.gantt_return_info['cdf_y'] / self.gantt_return_info['cdf_tot']
        plt.plot(self.gantt_return_info['cdf_x'], ycdf, 'k')
        fig.autofmt_xdate()

# ###############################################FIND###################################################
    def find(self, value, value2=None, field='value', match='weak', display='gantt', **kwargs):
        """
        This will find records matching value, except for milestones which looks between
            value,value2 dates (time format is yy/mm/dd)
            value: value for which to search
            value2: second value if used e.g. for bounding dates [None]
            field:  field in which to search (or 'any'/'all')  [value]
            match:  strength of match (weak, moderate, strong, verystrong) or timing of updates
                    'updated before'      <value>
                    'updated after'       <value>
                    'updated between'     <value> - <value2>
                    'initialized before'  <value>
                    'initialized after'   <value>
                    'initialized between' <value> - <value2>
            display:  how to return data ('show'/'listing'/'gantt'/'file'/'noshow')
                      If noshow returns the list of indices
            kwargs:  one of the following records table fields upon which to filter
                     - dtype, status, owner, other, id
        """

        # Set defaults and run through kwarg filters
        self.filter = FF.Filter()
        self.filter.set_find_default()
        self.filter.dtype = self.find_dtype
        self.find_stats = {}
        for k, v in kwargs.items():
            if k in self.filter.find_allowed:
                vl = pd_utils.listify(v)
                setattr(self.filter, k, vl)
            else:
                print('keyword {} not allowed'.format(k))
                continue

        foundrec = []
        if value == 'since':  # assumes read_data(since='') has been executed
            for k in self.updated_collate:
                foundrec.append(self.db.records.refname.index(k))
        elif self.dbtype in self.db_list['ganttable'] and field.lower() == 'value':
            # ...value is a date, so checking dtype and date(s)
            if value2 is None:
                value2 = value
                value = self.projectStart
            value1time = pd_utils.get_time(value)
            value2time = pd_utils.get_time(value2)
            if not isinstance(value1time, datetime.datetime) or not isinstance(value2time, datetime.datetime):  # noqa
                return 0
            for i, rdata in enumerate(getattr(self.db.records, field)):  # Loop over all records
                if rdata is None:
                    continue
                if '-' in rdata:  # A date range is given - use first
                    val2check = pd_utils.get_time(rdata.split('-')[0].strip())
                else:
                    val2check = pd_utils.get_time(str(rdata).strip())
                if not isinstance(val2check, datetime.datetime):
                    continue
                status = self.check_ganttable_status(self.db.records.status[i], val2check)
                recns = self.db.mk_entry_ns('records', i)
                if self.filter.on_fields(recns, status) and\
                   self.filter.on_time(val2check, value1time, value2time, match, recns):
                    foundrec.append(i)
        else:
            for i, rdata in enumerate(getattr(self.db.records, field)):
                if pd_utils.searchfield(value, rdata, match):
                    foundrec.append(i)
        if len(foundrec):
            foundrec = self.getview(foundrec, self.display_howsort)
            self.make_find_stats(foundrec)
            self.show_find_stats()
            if display not in self.displayMethods.keys():
                display = 'listing'
            return self.displayMethods[display](foundrec)
        else:
            print('No records found.')

    def unique(self, field, filter_on=None, returnList=False):
        """
        Searches the given field in self.db.records and comes up with a list of
        unique values within that field.
        """
        unique_values = []
        if filter_on:
            fld, val = filter_on.split('=')
        for idat, chk in enumerate(getattr(self.db.records, field)):
            if filter_on:
                if getattr(self.db.records, fld)[idat].lower() != val.strip().lower():
                    continue
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

    def getref(self, sval, search='description', method='start', verbose=True, retain_case=False):
        """
        Find a record searching various fields.

        Parameters
        ----------
        sval :  value for which to search
            value to look for
        search : str
            database field to look within
        method : str
            method for strings, either 'in', 'start' or 'equal'
        verbose : bool
            if found just one, this will diplsay or not
        retain_case : bool
            if not retain_case, it will check all lower

        Returns
        -------
        None or str
            Returns refname if one and only one is found, else None
        """
        fndi = []
        for i, dbdesc in enumerate(getattr(self.db.records, search)):
            if FF.agrees(sval, dbdesc, method=method, retain_case=retain_case):
                fndi.append(i)
        if len(fndi) == 1:
            if verbose:
                self.show(fndi)
            return self.db.records.refname[fndi[0]]
        print("{} found".format(len(fndi)))
        self.listing(fndi)
        return None

    def find_matching_refname(self, refname):
        """
        This takes a refname of unknown capitalization and finds the correct refname.
        If a string is returned, it is an exact match.
        If a list if returned, it is a lower()ed match to that/those.
        """
        if refname in self.db.records.refname:
            return refname
        ret_refn = []
        for db_refname in self.db.records.refname:
            if refname.lower() == db_refname.lower():
                ret_refn.append(db_refname)
        return ret_refn

# ################################################UPDATE################################################
    def add(self, dt=None, updater=None, upnote=None, **kwargs):
        """
        Adds a new record (essentially a wrapper for update which
        generates a refname and enables new)
        """
        self.make_new_entry = True
        if 'description' not in kwargs.keys():
            print("New entries must include a description.\nNot adding record.")
            return
        if 'value' not in kwargs.keys():
            print("New entries must include a value.\nNot adding record.")
            return
        refname_maxlen = len(pd_utils.make_refname(kwargs['description'], 200))
        if 'refname' in kwargs.keys():
            if kwargs['refname'] in self.db.records.refname:
                refname = None
            else:
                refname = kwargs['refname']
                refname_len = len(refname)
                del kwargs['refname']
        else:
            refname_len = 80
            refname = pd_utils.make_refname(kwargs['description'], refname_len)
            while refname in self.db.records.refname:
                refname_len += 2
                if refname_len > refname_maxlen:
                    refname = None
                    break
                refname = pd_utils.make_refname(kwargs['description'], refname_len)
        if refname is None:
            print("Not unique refname for {}\nNot adding record.".format(kwargs['description']))
        else:
            self.update(refname, dt, updater, upnote, **kwargs)
        self.make_new_entry = False

    def update(self, refname, dt=None, updater=None, upnote=None, **kwargs):
        """
        Updates a record field as well as the updated db, adds if not present
            name is the refname of the record, if not present a new entry is made
            dt is the YY/MM/DD of updated time (default is now)
            updater is the name of the updater (default is to query)
            upnote is the note to be included in updated record (default is to query
            or 'initial' on creation)
            kwargs should be valid key=value pairs
        """
        try:
            i_chng = self.db.records.refname.index(refname)
            changing = self.db.mk_entry_ns('records', i_chng)
        except ValueError:
            changing = None
        if changing is None and not self.make_new_entry:
            print("No update: {} not present to update.".format(refname))
            return False
        elif changing is not None and self.make_new_entry:
            print("No update:  {} already exists, can't add it as new.".format(refname))
            return False

        update_entry = Namespace()
        changed = False
        if changing is None:
            update_entry.refname = refname
            if 'id' not in kwargs.keys():
                id = max(self.db.records.id) + 1
            else:
                id = kwargs['id']
            update_entry.id = id
            if upnote is None:
                upnote = 'Initial'
            self.db.add_entry('records', entries_to_add=update_entry)
            changed = True
        # Process it
        new_data = {}
        old_data = {}
        for fld, new_value in kwargs.items():
            if 'trace' in fld.lower():
                ttype = fld[0:-5]
                trlist = new_value.split(',')
                trace_entries = Namespace(refname=[], tracename=[], tracetype=[])
                for tr in trlist:
                    trace_entries.refname.append(refname)
                    trace_entries.tracename.append(tr)
                    trace_entries.tracetype.append(ttype)
                    print('\tAdding trace {}.{} to {}'.format(ttype, tr, refname))
                self.db.add_entry('trace', entries_to_add=trace_entries)
                changed = True
            elif fld == 'refname':
                print("Don't do that.")
                continue
            elif fld not in self.db.tables['records'].cols:
                print('{} is not a database field - skipping'.format(fld))
                continue
            else:
                old_data[fld] = getattr(self.db.records, fld)
                new_data[fld] = new_value
                changed = True
        if len(list(new_data.keys())):
            self.db.update_entry('records', changing, **new_data)

        if changed:  # Need to update 'updated' database table
            self.db.read_table('records')
            old_vals = ''
            for k, v in old_data.items():
                old_vals += '[{}: {}]'.format(k, v)

            nupd = Namespace(refname=refname, previous=old_vals)
            if dt is None:
                bbb = datetime.datetime.now()
                nupd.updated = "{:02d}/{:02d}/{:02d}".format(bbb.year - 2000, bbb.month, bbb.day)
            else:
                nupd.updated = dt
            if updater is None:
                nupd.by = input("Who is updating:  ")
            else:
                nupd.by = updater
            if upnote is None:
                nupd.note = input("Update note to append previous record notes:  ")
            else:
                nupd.note = upnote

            self.db.add_entry('updated', nupd)
        return changed

# ##################################################################VIEW##################################################################
    def getview(self, view, howsort=None):
        if howsort is None:
            howsort = self.display_howsort
        else:
            howsort = pd_utils.listify(howsort)
        for hs in howsort:
            if hs not in self.db.tables['records'].cols:
                raise ValueError("{} sort option not valid.".format(hs))
        if view == 'all':
            view = range(self.num_records)
        else:
            view = pd_utils.listify(view)
        if howsort is None or not len(howsort):
            these_ind = view
        else:
            self.sorted_ind = self.sortby(howsort)
            these_ind = []
            for i in self.sorted_ind:
                if i in view:
                    these_ind.append(i)
        return these_ind

    def noshow(self, view):
        """This just returns the indices to view but doesn't display anything"""
        return view

    def show(self, view, output='stdout'):
        if output != 'stdout':
            save2file = True
            fp = open(output, 'w')
        else:
            save2file = False
        for i in view:
            rec = self.db.mk_entry_ns('records', i)
            s = '({}) {}\n'.format(rec.id, rec.description)
            s += '\tvalue:        {}\n'.format(rec.value)
            s += '\tdtype:        {}\n'.format(rec.dtype)
            s += '\tstatus:       {}\n'.format(rec.status)
            s += '\tnotes:        {}\n'.format(rec.notes)
            s += '\towner:        {}\n'.format(rec.owner)
            if rec.other:
                s += '\tother:       {}\n'.format(rec.other)
            if rec.commentary:
                s += '\tcommentary:  {}\n'.format(rec.commentary)
            if self.show_trace:
                for tracetype in self.db_list['traceable']:
                    print("Need to implement check {}".format(tracetype))
            for iupd in self.updated_collate[rec.refname]:
                s += '{}: {}\n'.format(self.db.updated.note[iupd], self.db.updated.updated[iupd])
            print(s + '\n')
            if save2file:
                fp.write(s + '\n')
        if save2file:
            print('Writing data to ' + output)
            fp.close()

    def fileout(self, view):
        tag = self.output_filename.split('.')[1]
        if tag == 'csv':
            import csv
        with open(self.output_filename, 'w') as output_file:
            if tag == 'csv':
                s = ['value', 'description', 'owner', 'status', 'other', 'notes', 'commentary']
                csvw = csv.writer(output_file)
                csvw.writerow(s)
            for key in view:
                rec = self.db.mk_entry_ns('records', key)
                if tag == 'csv':
                    s = [rec.value, rec.description, rec.owner, rec.status, rec.other,
                         rec.notes, rec.commentary]
                    csvw.writerow(s)
                else:
                    s = ('{} ({:8s}) {}:  {}   ({})\n'
                         .format(rec.value, rec.owner, rec.description, rec.status, key))
                    output_file.write(s)
        print('Writing file to ', self.output_filename)

    def listing(self, view):
        """
        Provides a short listing of the given records (default is all) in fixed widths.
        """
        for i in view:
            rec = self.db.mk_entry_ns('records', i)
            print('{:10.10} {} ({})'.format(rec.value, rec.description, rec.status))

    def gantt(self, view):
        if self.dbtype not in self.db_list['ganttable']:
            print('{} not ganttable:  ', self.dbtype)
            return
        for gantt_label in self.gantt_label:
            if gantt_label not in self.db.tables['records'].cols:
                print("{} label not found to use.".format(gantt_label))
                return
        for gantt_annot in self.gantt_annot:
            if gantt_annot not in self.db.tables['records'].cols:
                print("{} annot not found to use.".format(gantt_annot))
                return
        gdat = Namespace(labels=[], dates=[], tstats=[], preds=[], annots=[])
        for v in view:
            field_rec = self.db.mk_entry_ns('records', v)
            label = [getattr(field_rec, gl) for gl in self.gantt_label]
            label = pd_gantt.check_gantt_labels(': '.join(label), gdat.labels)[:self.gantt_label_length]  # noqa
            value = str(getattr(field_rec, 'value'))
            status = str(getattr(field_rec, 'status')).lower().strip()
            annot = []
            for ga in self.gantt_annot:
                gafr = getattr(field_rec, ga)
                if isinstance(gafr, list):
                    grp = [str(x) for x in gafr]
                    annot.append(','.join(grp))
                elif gafr is None:
                    pass
                else:
                    annot.append(str(gafr))
            annot = '; '.join(annot)
            predv = []
            if 'milestoneTrace' in dir(field_rec):
                milepred = getattr(field_rec, 'milestoneTrace')
                if self.dbtype == 'milestone' or self.dbtype == 'wbs':
                    for x in milepred:
                        if x in view:
                            predv.append(getattr(field_rec, 'description')[0:self.gantt_label_length])  # noqa
            if 'taskTrace' in dir(field_rec):
                taskpred = getattr(field_rec, 'taskTrace')
                if self.dbtype == 'task' or self.dbtype == 'wbs':
                    for x in taskpred:
                        if x in view:
                            predv.append(getattr(field_rec, 'description')[0:self.gantt_label_length])  # noqa
            gdat.labels.append(label)
            gdat.preds.append(predv)
            gdat.dates.append(value)
            gdat.annots.append(annot)
            status_return = self.check_ganttable_status(status, value)
            gdat.tstats.append(status_return)
        if not self.plot_predecessors:
            gdat.preds = None
        other_labels = None
        if len(self.gantt_annot):
            other_labels = gdat.annots
        show_cdf = self.show_cdf and self.filter.status[0].lower() != 'late'
        g = pd_gantt.plotGantt(gdat.labels, gdat.dates, gdat.preds, gdat.tstats,
                               show_cdf=show_cdf, other_labels=other_labels)
        self.gantt_return_info = g
        if self.show_color_bar and self.filter.status[0].lower() != 'late':
            pd_gantt.colorBar()

    def check_ganttable_status(self, status, valuetime):
        """
                self.ganttable_status = {'removed': 'w',
                                         'late': 'r',
                                         'moved': 'y',
                                         'none': 'k',
                                         'complete': 'b',
                                         'unknown': 'm'}
        """
        # Get status_code
        if status is None or status.lower().startswith('no') or not len(status):
            status_code = 'none'
        else:
            status = status.lower().split()
            status_code = status[0]
        if status_code not in self.ganttable_status.keys():
            status_code = 'unknown'
        tcode = self.ganttable_status[status_code]
        if status_code == 'removed':
            return (status_code, tcode)

        if isinstance(valuetime, str):
            if '-' in valuetime:
                valuetime = valuetime.split('-')[-1]
            valuetime = pd_utils.get_time(valuetime)
        elif not isinstance(valuetime, datetime.datetime):
            print("Invalid time:  ", valuetime, type(valuetime))
        now = datetime.datetime.now()

        lag = 0.0
        if status is not None and len(status) == 2:
            try:
                lag = float(status[1])
            except ValueError:
                statustime = pd_utils.get_time(status[1])
                if isinstance(statustime, datetime.datetime):
                    lag = (statustime - valuetime) / 3600.0 / 24.0
                else:
                    tcode = status[1]

        if now > valuetime and status_code != 'complete':
            status_code = 'late'
            tcode = self.ganttable_status[status_code]
        elif status_code == 'complete':
            tcode = pd_gantt.lag2rgb(lag)
        return (status_code, tcode)

    def sortby(self, sort_it_by):
        sortable_dict = {}
        for i in range(self.num_records):
            this_key = []
            for sb in sort_it_by:
                sdt = getattr(self.db.records, sb)[i]
                if sdt is None:
                    sdt = ' '
                elif isinstance(sdt, list):
                    ','.join(sdt)
                this_key.append(sdt)
            sortable_dict[tuple(this_key)] = i
        sl = []
        for key, val in sorted(sortable_dict.items()):
            sl.append(val)
        return sl
