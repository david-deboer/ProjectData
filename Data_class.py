import os
from argparse import Namespace
import pd_gantt
import pd_utils
import filter_fields as FF
import datetime
from pysqlite_simple import tables
from ddb_util import state_variable


class Data(state_variable.StateVar):
    """
    This class has the functions to read in the data file [milestones/reqspecs/interfaces/risks.db]
        dbtype is the type of database [milestones, reqspecs, interfaces, risks]
        self.data is the "internal" database
        sqlmap are the fields in the sqlite3 database (read from the .db file, but should
        correspond to entryMap strings) each db file has the following tables (dbtype, trace,
        type, updated)
    """

    def __init__(self, dbtype, projectStart='14/09/01', db_json_file='databases.json', **kwargs):
        super().__init__([])
        self.sv_json(json_file=db_json_file, keys_to_use='state_variables', use_to_initialize=True)
        self.state(**kwargs)
        self.displayMethods = {'show': self.show, 'listing': self.listing, 'gantt': self.gantt,
                               'noshow': self.noshow, 'file': self.fileout}
        self.projectStart = projectStart
        self.dbtype = dbtype
        self.db_list, self.ganttable_status = pd_utils.get_db_json(db_json_file)
        self.dirName = self.db_list[dbtype]['subdirectory']
        self.inFile = os.path.join(self.dirName, self.db_list[dbtype]['dbfilename'])
        self.db = tables.DB(self.inFile)
        self.enable_new_entry = False

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

        self.db.read('records', order_by='id')
        self.num_records = len(self.db.records.refname)
        if since is not None:
            print("Type mi.find('since') to see records.")
            self.db.read('updated', order_by='updated', updated='>{}'.format(since))
        else:
            self.db.read('updated', order_by='updated')
        self.db.read('types')
        self.db.read('trace')

        # collate updated and trace for refname
        self.updated_collate = {}
        for i, refname in enumerate(self.db.updated.refname):
            self.updated_collate.setdefault(refname, [])
            self.updated_collate[refname].append(i)
        self.trace_collate = {}
        for i, refname in enumerate(self.db.trace.refname):
            self.trace_collate.setdefault(refname, [])
            self.trace_collate[refname].append(i)

    def dtype_info(self, dtype='nsfB'):
        """
        Print out a short timeline of dtype.
        """
        if dtype not in self.db.types.name:
            print("{} not found".format(dtype))
            return None
        i = self.db.types.name.index(dtype)
        rec = self.db.mk_entry_ns('types', i)
        print("Information for {}: {}".format(rec.name, rec.description))
        if rec.start is not None:
            rec.start = pd_utils.get_time(rec.start)
            print("  {}  ".format(datetime.datetime.strftime(rec.start, '%y/%m/%d')), end='')
        if rec.duration_months is not None:
            duration_qtr = int(rec.duration_months / 3.0)
            print("  {}  months, {} quarters".format(rec.duration_months, duration_qtr))
        if (rec.start is not None) and (rec.duration_months is not None):
            tdelt = datetime.timedelta(1.0)
            y_old = rec.start.year
            end = pd_utils.get_qtr_date(duration_qtr, rec.start) - tdelt
            print('{}  -  {}'.format(datetime.datetime.strftime(rec.start, '%Y/%m/%d'),
                                     datetime.datetime.strftime(end, '%Y/%m/%d')))
            pdash = 10 * '-'
            proj_year = 0
            for q in range(duration_qtr):
                if not q % 4:
                    proj_year += 1
                py_sym = pd_utils.quarter_symbol(q, proj_year)
                qtr = pd_utils.get_qtr_date(q, rec.start)
                qstr = datetime.datetime.strftime(qtr, '%Y/%m/%d')
                pspace = proj_year * ' '
                if qtr.year > y_old:
                    y_old = qtr.year
                    print("\t         {}     {}  {}{}".format(pdash, pdash, pspace, str(proj_year)))
                print("\tQtr {:2d}:  {}".format(q + 1, qstr), end='')
                qtr = pd_utils.get_qtr_date(q + 1, rec.start) - tdelt
                print("  -  {}  {}".format(datetime.datetime.strftime(qtr, '%Y/%m/%d'), py_sym))

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
            if not isinstance(value1time, datetime.datetime) or\
               not isinstance(value2time, datetime.datetime):
                return 0
            for i, rdata in enumerate(getattr(self.db.records, field)):  # Loop over all records
                if rdata is None:
                    continue
                if '-' in rdata:  # A date range is given - use first
                    val2check = rdata.split('-')[0].strip()
                else:
                    val2check = str(rdata)
                timevalue = pd_utils.get_time(val2check)
                if not isinstance(timevalue, datetime.datetime):
                    continue
                status = self.check_ganttable_status(self.db.records.status[i], timevalue)
                recns = self.db.mk_entry_ns('records', i)
                if self.filter.on_fields(recns, status) and\
                   self.filter.on_time(timevalue, value1time, value2time, match, recns):
                    foundrec.append(i)
        else:
            print("This code for non-gantt stuff doesn't work")
            for dat in self.data.keys():
                for fff in self.data[dat].keys():
                    if pd_utils.searchfield(value, self.data[dat][fff], match):
                        foundrec.append(dat)
        if len(foundrec):
            foundrec = self.getview(foundrec, self.display_howsort)
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
        sval : appropriate database field
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
            if dbdesc is not None:
                if isinstance(sval, str):
                    if not retain_case:
                        sval = sval.lower()
                        dbdesc = dbdesc.lower()
                    if method == 'in':
                        if sval in dbdesc:
                            fndi.append(i)
                    elif method == 'start':
                        if dbdesc.startswith(sval):
                            fndi.append(i)
                    else:
                        if sval == dbdesc:
                            fndi.append(i)
                else:
                    if sval == dbdesc:
                        fndi.append(i)
        if len(fndi) == 1:
            if verbose:
                self.show(fndi)
            return fndi[0]
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
        self.enable_new_entry = True
        if 'description' not in kwargs.keys():
            print("New entries must include a description.\nNot adding record.")
            return
        if 'value' not in kwargs.keys():
            print("New entries must include a value.\nNot adding record.")
            return
        refname_maxlen = len(pd_utils.make_refname(kwargs['description'], 1000))
        if 'refname' in kwargs.keys():
            refname = kwargs['refname']
            refname_len = len(refname)
            del kwargs['refname']
        else:
            refname_len = 100
            refname = pd_utils.make_refname(kwargs['description'], refname_len)
        while refname in self.db.records.refname:
            refname_len += 2
            if refname_len > refname_maxlen:
                print("Not unique description:  {}\nNot adding record."
                      .format(kwargs['description']))
                return
            refname = pd_utils.make_refname(kwargs['description'], refname_len)
        self.update(refname, dt, updater, upnote, **kwargs)
        self.enable_new_entry = False
        return

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

        update_entry = Namespace()
        new_entry = False
        changed = False
        if changing is None:
            if self.enable_new_entry:
                update_entry.refname = refname
                if 'id' not in kwargs.keys():
                    id = max(self.db.records.id) + 1
                else:
                    id = kwargs['id']
                update_entry.id = id
                if upnote is None:
                    upnote = 'Initial'
                self.db.add('records', table_entries=update_entry)
                changed = True
                new_entry = True
            else:
                print("No update: {} not present to update.".format(refname))
                return False
        else:
            if self.enable_new_entry:
                print("No update:  {} already exists, can't add it as new.".format(refname))
                return False

        # Process it
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
                self.db.add('trace', table_entries=trace_entries)
                changed = True
            elif fld == 'refname':  # Do last
                continue
            elif fld not in self.db['tables'].records.cols:
                print('{} is not a database field - skipping'.format(fld))
                continue
            else:
                new_data = {fld: new_value}
                self.db.update('records', changing, **new_data)
                changed = True
        if 'refname' in kwargs.keys():  # Do last
            print('\tChanging name {} to {}'.format(refname, kwargs['refname']))
            print("==> I'm not entirely sure this is comprehensive yet or not")
            if self.change_refName(refname, kwargs['refname']):
                changed = True

        if changed:  # Need to update 'updated' database
            self.read_data()
            qdb_exec = "SELECT * FROM updated where refname='{}' COLLATE NOCASE ORDER BY level".format(refname)  # noqa
            try:
                new_update = upd[-1][-1] + 1
            except IndexError:
                new_update = 0
            qdb_exec = "INSERT INTO updated VALUES (?,?,?,?,?)"
            if dt is None:
                bbb = datetime.datetime.now()
                dt = "{:02d}/{:02d}/{:02d}".format(bbb.year - 2000, bbb.month, bbb.day)
            if updater is None:
                updater = input("Who is updating:  ")
            if upnote is None:
                upnote = input("Update note to append previous record notes:  ")
            if new_entry:
                full_upnote = upnote
            else:
                oldnote = changing[0][self.sqlmap['records']['notes'][0]]
                if oldnote is None:
                    oldnote = ''
                full_upnote = upnote + ' :: <Previous note: ' + oldnote + '>'
            qv = (refname, dt, updater, full_upnote, new_update)
            self.checkTrace(refname)
        return changed

    def change_refName(self, old_name=None, new_name=None):
        """Need to update all dbs when the refname is changed"""
        print("This will change the refname '{}' to '{}' in all databases"
              .format(old_name, new_name))
        print("\tFirst in " + self.inFile)
        print("WARNING:  dbEM and pbwd not defined!!!!")
        dbEM = None
        pbwd = None
        changing = 1  # qdb.fetchall()
        qdb_exec = "SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(old_name)
        if len(changing) == 1:
            qdb_exec = "UPDATE records SET refname='{}' WHERE refname='{}'".format(new_name, old_name)  # noqa
            qdb_exec = "UPDATE trace SET refname='{}' WHERE refname='{}'".format(new_name, old_name)  # noqa
            qdb_exec = "UPDATE updated SET refname='{}' WHERE refname='{}'".format(new_name, old_name)  # noqa
        elif len(changing) > 1:
            print('Ambiguous entry:  {} has {} entries'.format(old_name, len(changing)))
            return False
        else:
            print('\tNone to change')
            return False
        for tr in self.db_list['traceable']:
            dirName = self.db_list[tr][dbEM['dirName']]
            path = os.path.join(pbwd, dirName)
            inFile = os.path.join(path, self.db_list[tr][dbEM['inFile']])
            print('\tChecking ' + inFile)
            qdb_exec = ("SELECT * FROM trace WHERE tracename='{}' AND "
                        "tracetype='{}'".format(old_name, self.dbtype))
            if len(changing) > 0:
                plural = 's'
                if len(changing) == 1:
                    plural = ''
                print('\t\t{} record{}'.format(len(changing), plural))
                qdb_exec = ("UPDATE trace SET tracename='{}' WHERE tracename='{}' AND "
                            "tracetype='{}'".format(new_name, old_name, self.dbtype))
            else:
                print('\t\tNone to change')
        self.readData()
        return True

    def checkTrace(self, checkrec='all'):
        print("WARNING:  dbEM and pbwd not defined!!!!")
        dbEM = None
        pbwd = None
        return
        if checkrec == 'all':
            checkrec = self.data.keys()
        elif type(checkrec) is not list:
            checkrec = [checkrec]
        for tr in self.db_list['traceable']:
            dirName = self.db_list[tr][dbEM['dirName']]
            path = os.path.join(pbwd, dirName)
            inFile = os.path.join(path, self.db_list[tr][dbEM['inFile']])
            print('Checking {} {}Trace in {} against {}'.format(self.dbtype, tr, checkrec, inFile))
            for rec in checkrec:
                for rs in self.data[rec][tr + 'Trace']:
                    if len(rs) > 0:
                        qdb_exec = "SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(rs)  # noqa
                        if len(checking) == 0:
                            print(rs + ' not found in entry ' + self.dbtype + ':' + rec)

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
        """This just returns the keys to view but doesn't display anything"""
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
            # ---1---# implement this later for all tracetypes
# #            if self.dbtype!='reqspec':
# #                dirName = self.db_list['reqspec'][dbEM['dirName']]
# #                path = os.path.join(pbwd,dirName)
# #                inFile = os.path.join(path,self.db_list['reqspec'][dbEM['inFile']])
# #                rsdata = self.readData(inFile)
# #            else:
# #                rsdata = self.data
            if self.show_trace:
                trace_s = ''
                for tracetype in self.db_list['traceable']:
                    fieldName = tracetype + 'Trace'
                    trace_s += '\t' + tracetype + ' trace\n'
                    xxxTrace = '0'#self.data[name][fieldName]
                    if len(xxxTrace) == 0 or len(xxxTrace[0]) == 0:
                        trace_s = ''
                    else:
                        for xxx in xxxTrace:
                            if len(xxx) > 0:
                                trace_s += '\t\t{}\n:  '.format(xxx)
                                # ---1---#
# #                                try:
# #                                    s+=(rsdata[rrr][self.entryMap['value']]+'\n')
# #                                except:
# #                                    s+='not found in database\n'
                if not len(trace_s):
                    trace_s = '\tNo trace info found.\n'
                s += trace_s
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
        labels = []
        dates = []
        tstats = []
        preds = []
        annots = []
        for v in view:
            field_rec = self.db.mk_entry_ns('records', v)
            label = [getattr(field_rec, gl) for gl in self.gantt_label]
            label = pd_gantt.check_gantt_labels(': '.join(label), labels)[:self.gantt_label_length]
            value = str(getattr(field_rec, 'value'))
            status = str(getattr(field_rec, 'status')).lower().strip()
            annot = []
            for ga in self.gantt_annot:
                if isinstance(getattr(field_rec, ga), list):
                    grp = [str(x) for x in getattr(field_rec, ga)]
                    annot.append(','.join(grp))
                elif getattr(field_rec, ga) is None:
                    annot = []
                else:
                    annot = [str(getattr(field_rec, ga))]
            annot = '; '.join(annot)
            predv = []
            # if 'milestoneTrace' in field_rec.keys():
            #     milepred = getattr(field_rec, 'milestoneTrace')
            #     if self.dbtype == 'milestone' or self.dbtype == 'wbs':
            #         for x in milepred:
            #             if x in view:
            #                 predv.append(getattr(field_rec, 'description')[0:self.gantt_label_length])  # noqa
            # if 'taskTrace' in field_rec.keys():
            #     taskpred = getattr(field_rec, 'taskTrace')
            #     if self.dbtype == 'task' or self.dbtype == 'wbs':
            #         for x in taskpred:
            #             if x in view:
            #                 predv.append(getattr(field_rec, 'description')[0:self.gantt_label_length])  # noqa
            labels.append(label)
            preds.append(predv)
            dates.append(value)
            annots.append(annot)
            status_return = self.check_ganttable_status(status, value)
            tstats.append(status_return)
        if not self.plot_predecessors:
            preds = None
        other_labels = None
        if len(self.gantt_annot):
            other_labels = annots
        show_cdf = self.show_cdf and self.filter.status[0].lower() != 'late'
        pd_gantt.plotGantt(labels, dates, preds, tstats,
                           show_cdf=show_cdf, other_labels=other_labels)
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
