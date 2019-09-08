#! usr/bin/env python
import os
from operator import itemgetter
import sqlite3
import datetime
import time
from argparse import Namespace
import matplotlib.pyplot as plt
#  Project specific modules
import pd_gantt
import pd_utils
import fields_class as FC


class Data:
    db_json_file = 'databases.json'

    def __init__(self, dbtype, projectStart='14/09/01', verbose=True):
        """This class has the functions to read in the data file [milestones/reqspecs/interfaces/risks.db] and write out
           a number of tex files.  See README and Architecture.dat
               dbtype is the type of database [milestones, reqspecs, interfaces, risks]
               self.data is the "internal" database
               sql_map are the fields in the sqlite3 database (read from the .db file, but should correspond to entryMap strings)
               each db file has the following tables (dbtype, trace, type, updated)"""
        self.displayMethods = {'show': self.show, 'listing': self.listing, 'gantt': self.gantt,
                               'noshow': self.noshow, 'file': self.fileout}
        self.ganttable_status = {'removed': 'w',  # see check_ganttable_status
                                 'late': 'r',
                                 'moved': 'y',
                                 'none': 'k',
                                 'complete': 'b',
                                 'unknown': 'm'}
        self.Records = FC.Records_fields()
        self.projectStart = projectStart
        self.dbtype = dbtype
        # Get db type data from json
        self.dbTypes = pd_utils.get_db_json(self.db_json_file)
        self.dirName = self.dbTypes[dbtype]['subdirectory']
        self.inFile = os.path.join(self.dirName, self.dbTypes[dbtype]['dbfilename'])
        self.ganttables = []
        if self.dbTypes[dbtype]['ganttable'] == 'True':
            self.ganttables.append(dbtype)
        self.traceables = []
        if self.dbTypes[dbtype]['traceable'] == 'True':
            self.traceables.append(dbtype)
        self.caption = self.dbTypes[dbtype]['caption']
        self._enable_new_entry = False
        self.state_var_defaults = {'gantt_label_length': 50,
                                   'gantt_label': ['description'],
                                   'gantt_annot': ['owner'],
                                   'display_howsort': ['value'],
                                   'find_dtype': [],
                                   'output_filename': 'fileout.csv',
                                   'plot_predecessors': True,
                                   'show_trace': True,
                                   'show_color_bar': True,
                                   'show_cdf': True,
                                   'quiet_update': False}
        self.state_vars = list(self.state_var_defaults.keys())
        self.state_initialized = False
        self.set_state(**self.state_var_defaults)
        if verbose:
            self.show_state()

    def set_state(self, **kwargs):
        for k, v in kwargs.items():
            if k in self.state_vars:
                valid_set = True
                def_var = self.state_var_defaults[k]
                if isinstance(v, type(def_var)):
                    setattr(self, k, v)
                elif isinstance(v, str) and ',' in v:
                    v = [x.strip() for x in v.split(',')]
                elif isinstance(v, str) and isinstance(def_var, list):
                    v = [v.strip()]
                else:
                    valid_set = False
                if self.state_initialized:
                    if valid_set:
                        print('Setting {} to {}'.format(k, v))
                    else:
                        print("{}: {} invalid format".format(k, v))
            else:
                print('state_var [{}] not found.'.format(k))
        self.state_initialized = True

    def show_state(self):
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

        dbconnect = sqlite3.connect(inFile)
        qdb = dbconnect.cursor()

        # get allowed types
        qdb_exec = "SELECT * FROM types"
        qdb.execute(qdb_exec)
        allowedTypes = {}
        for t in qdb.fetchall():
            allowedTypes[str(t[0]).lower()] = t

        # put database records into data dictionary (records/trace tables)
        qdb_exec = "SELECT * FROM records ORDER BY id"
        qdb.execute(qdb_exec)
        data = {}
        self.cache_lower_data_keys = set()
        for rec in qdb.fetchall():
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
                entry[fieldName] = []
                for v in qdb.fetchall():
                    entry[fieldName].append(v[1])
            # ...read in updated table
            qdb_exec = "SELECT * FROM updated WHERE refname='{}' COLLATE NOCASE ORDER BY level".format(refname)
            qdb.execute(qdb_exec)
            entry['updates'] = []
            latest = pd_utils.get_time(self.projectStart)
            entry['initialized'] = None
            updtime = None
            for v in qdb.fetchall():
                entry['updates'].append([v[1], v[2], v[3]])
                updtime = pd_utils.get_time(v[1])
                if 'init' in v[3].lower():
                    entry['initialized'] = updtime
                if updtime > latest:
                    latest = updtime
            entry['updated'] = updtime
            # ...put in data dictionary if not a duplicate
            if refname.lower() in self.cache_lower_data_keys:
                refname = self.find_matching_refname(refname)
                existingEntry = data[refname]
                print('name collision:  {} --> not adding to data'.format(refname))
                print('[\n', existingEntry)
                print('\n]\n[\n', entry)
                print('\n]')
            else:
                data[refname] = entry
                self.cache_lower_data_keys.add(refname.lower())
            # ...give warning if not in 'allowedTypes' (but keep anyway)
            if entry['dtype'] is not None and entry['dtype'].lower() not in allowedTypes.keys():
                print('Warning type not in allowed list for {}: {}'.format(refname, entry['dtype']))
                print('Allowed types are:')
                print(allowedTypes.keys())

        # check Trace table to ensure that all refnames are valid
        for tracetype in self.traceables:
            fieldName = tracetype + 'Trace'
            qdb_exec = "SELECT * FROM trace where tracetype='{}' COLLATE NOCASE".format(tracetype)
            qdb.execute(qdb_exec)
            for t in qdb.fetchall():
                t_refname = t[0]
                if t_refname.lower() not in self.cache_lower_data_keys:
                    print('{} not in data records:  {}'.format(fieldName, t[0]))
        # check Updated table to ensure that all refnames are valid
        qdb_exec = "SELECT * FROM updated"
        qdb.execute(qdb_exec)
        for u in qdb.fetchall():
            u_refname = u[0]
            if u_refname.lower() not in self.cache_lower_data_keys:
                print('updated not in data records:  ', u[0])
        dbconnect.close()
        if 'projectstart' in data.keys():
            self.projectStart = data['projectstart']['value']
            print('Setting project start to ' + self.projectStart)
        if selfVersion:
            self.allowedTypes = allowedTypes
            self.data = data
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

    def concatDat(self, dblist):
        """This will concatentate the database list into a single database, which is used to make WBS=TASK+MILESTONE"""
        self.data = {}
        fullcount = 0
        overcount = 0
        for db in dblist:
            dbcount = 0
            for entry in db.data.keys():
                fullcount += 1
                dbcount += 1
                if entry in self.data.keys():
                    print(entry + ' already present - overwriting')
                    overcount += 1
                self.data[entry] = db.data[entry]
        fullcount -= overcount

    def dtype_info(self, dtype='nsfB'):
        dkey = dtype.lower()
        if dkey not in self.allowedTypes.keys():
            print("{} not found".format(dtype))
            return None
        name = self.allowedTypes[dkey][0]
        description = self.allowedTypes[dkey][1]
        dtdate = self.allowedTypes[dkey][2]
        dtdur = self.allowedTypes[dkey][3]
        print("Information for {}: {}".format(name, description))
        if dtdate is not None:
            print("\t{}  ".format(dtdate), end='')
        if dtdur is not None:
            dur_in_qtr = int(dtdur / 3.0)
            print("{}  months, {} quarters".format(dtdur, dur_in_qtr))
        else:
            print()
        if (dtdate is not None) and (dtdur is not None):
            sta = datetime.datetime.strptime(dtdate, '%y/%m/%d')
            y_old = sta.year
            end = pd_utils.get_dmy(dur_in_qtr, sta.day, sta.month, sta.year) - datetime.timedelta(1.0)
            print('{}  -  {}'.format(datetime.datetime.strftime(sta, '%Y/%m/%d'), datetime.datetime.strftime(end, '%Y/%m/%d')))
            proj_year = 0
            for q in range(dur_in_qtr):
                if not q % 4:
                    proj_year += 1
                py_sym = pd_utils.quarter_symbol(q, proj_year)
                qtr = pd_utils.get_dmy(q, sta.day, sta.month, sta.year)
                if qtr.year > y_old:
                    y_old = qtr.year
                    print("\t         ----------     ----------    " + ((proj_year + 1) % 2) * ' ' + str(proj_year))
                print("\tQtr {:2d}:  {}".format(q + 1, datetime.datetime.strftime(qtr, '%Y/%m/%d')), end='')
                qtr = pd_utils.get_dmy(q + 1, sta.day, sta.month, sta.year) - datetime.timedelta(1.0)
                print("  -  {}  {}".format(datetime.datetime.strftime(qtr, '%Y/%m/%d'), py_sym))

# ##################################################################FIND##################################################################
    def find(self, value, value2=None, field='value', match='weak', display='gantt', **kwargs):
        """This will find records matching value, except for milestones which looks between value,value2 dates (time format is yy/m/d)
            value: value for which to search
            value2: second value if used e.g. for bounding dates [None]
            field:  field in which to search (or 'any'/'all')  [value]
            match:  strength of match (weak, moderate, strong, verystrong) [weak] or timing of updates
                    'updated before'      <value>
                    'updated after'       <value>
                    'updated between'     <value> - <value2>
                    'initialized before'  <value>
                    'initialized after'   <value>
                    'initialized between' <value> - <value2>
            display:  how to return data ('show'/'listing'/'gantt'/'file'/'noshow') If noshow returns the list of keys
            kwargs:  one of the following records table fields upon which to filter - dtype, status, owner, other, id"""

        # Set defaults and run through kwarg filters
        self.Records.set_find_default()
        self.Records.dtype = self.find_dtype
        for k, v in kwargs.items():
            if k in self.Records.find_allowed:
                if isinstance(v, str) or isinstance(v, int):
                    setattr(self.Records, k, [v])
                else:  # Assume it's a list
                    setattr(self.Records, k, v)
            else:
                print('keyword {} not allowed'.format(k))
                continue

        rec = FC.Records_fields()
        foundrec = []
        if self.dbtype in self.ganttables and field.lower() == 'value':
            # ...value is a date, so checking dtype and date(s)
            if value2 is None:
                value2 = value
                value = self.projectStart
            value1time = pd_utils.get_time(value)
            value2time = pd_utils.get_time(value2)
            if not isinstance(value1time, time.struct_time) or not isinstance(value2time, time.struct_time):
                return 0
            for dat in self.data.keys():  # Loop over all records
                if self.data[dat][field] is None:
                    continue
                if '-' in self.data[dat][field]:  # A date range is given - use first
                    val2check = self.data[dat][field].split('-')[0].strip()
                else:
                    val2check = str(self.data[dat][field])
                timevalue = pd_utils.get_time(val2check)
                if not isinstance(timevalue, time.struct_time):
                    continue
                status = self.check_ganttable_status(self.data[dat]['status'], timevalue)
                if rec.filter_rec(self.Records, self.data[dat], status):
                    print(status)
                    if 'upda' in match.lower() or 'init' in match.lower():
                        if rec.filter_on_updates(match, value1time, value2time, self.data[dat]):
                            foundrec.append(dat)
                    else:
                        if timevalue >= value1time and timevalue <= value2time:
                            foundrec.append(dat)
        else:
            print("This code isn't really checked out out for non-gantt stuff...")
            for dat in self.data.keys():
                for fff in self.data[dat].keys():
                    if pd_utils.searchfield(value, self.data[dat][fff], match):
                        foundrec.append(dat)
                # foundType = False
                # if dtype.lower() in pthru and self.data[dat]['dtype'].lower() != 'na':
                #     foundType = True
                # elif dtype.lower() in self.data[dat]['dtype'].lower():
                #     foundType = True
                # if foundType:
                #     foundMatch = False
                #     if field.lower() in pthru:
                #         for fff in self.data[dat].keys():
                #             foundMatch = pd_utils.searchfield(value, self.data[dat][fff], match)
                #             if foundMatch:
                #                 break
                #     elif field in self.data[dat].keys():
                #         foundMatch = pd_utils.searchfield(value, self.data[dat][field], match)
                #     else:
                #         print('Invalid field for search')
                #         return
                #     if foundMatch:
                #         foundrec.append(dat)
        if len(foundrec):
            foundrec = self.getview(foundrec, self.display_howsort)
            if display not in self.displayMethods.keys():
                display = 'listing'
            return self.displayMethods[display](foundrec)
        else:
            print('No records found.')

    def unique(self, field, filter_on=None, returnList=False):
        unique_values = []
        for dat in self.data.keys():
            if filter_on:
                fld, val = filter_on.split('=')
                if self.data[dat][fld.strip().lower()].lower() != val.strip().lower():
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

    def getref(self, sval, search='description', finding='start', verbose=True):
        """
        Find a record searching various fields.

        Parameters
        ----------
        sval : appropriate database field
            value to look for
        search : str
            database field to look within
        finding : str
            method for strings, either 'in' or 'start'
        verbose : bool
            if found just one, this will diplsay or not

        Returns
        -------
        None or str
            Returns refname if one and only one is found, else None
        """
        fndk = []
        for dat in self.data.keys():
            dbdesc = self.data[dat][search]
            if dbdesc is not None:
                if isinstance(sval, str):
                    if finding == 'in':
                        if sval.lower() in dbdesc.lower():
                            fndk.append(dat)
                    elif finding == 'start':
                        if dbdesc.lower().startswith(sval.lower()):
                            fndk.append(dat)
                else:
                    if sval == dbdesc:
                        fndk.append(dat)
        if len(fndk) == 1:
            if verbose:
                self.show(fndk)
            return fndk[0]
        print("{} found".format(len(fndk)))
        self.listing(fndk)
        return None

    def since(self, dstr):
        dbconnect = sqlite3.connect(self.inFile)
        qdb = dbconnect.cursor()
        qdb_exec = "SELECT refname FROM updated WHERE updated>'{}'".format(dstr)
        qdb.execute(qdb_exec)
        updates = qdb.fetchall()
        refnames = []
        for u in updates:
            print(u)
            refnames.append(u[0].lower())
        self.show(refnames, showTrace=False)

    def find_matching_refname(self, refname):
        """
        This takes a refname of unknown capitalization and finds the correct refname.
        Returns None if none are found.
        """
        if refname in self.data.keys():
            return refname
        if refname.lower() in self.cache_lower_data_keys:
            for rn in self.data.keys():
                if refname.lower() == rn.lower():
                    return rn
        return None

# ##################################################################UPDATE##################################################################
    def add(self, dt=None, updater=None, upnote=None, **kwargs):
        """Adds a new record (essentially a wrapper for update which generates a refname and enables new)
        """
        self._enable_new_entry = True
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
        while refname in self.data.keys():
            refname_len += 2
            if refname_len > refname_maxlen:
                print("Not unique description:  {}\nNot adding record.".format(kwargs['description']))
                return
            refname = pd_utils.make_refname(kwargs['description'], refname_len)
        self.update(refname, dt, updater, upnote, **kwargs)
        self._enable_new_entry = False
        return

    def update(self, refname, dt=None, updater=None, upnote=None, **kwargs):
        """Updates a record field as well as the updated db, adds if not present
            name is the refname of the record, if not present a new entry is made
            dt is the YY/MM/DD of updated time (default is now)
            updater is the name of the updater (default is to query)
            upnote is the note to be included in updated record (default is to query or 'initial' on creation)
            kwargs should be valid key=value pairs"""
        self.readData()
        db = sqlite3.connect(self.inFile)
        qdb = db.cursor()
        qdb.execute("SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(refname))
        changing = qdb.fetchall()

        # Checking new versus existing
        new_entry = False
        changed = False
        if len(changing) > 1:
            print('No update: duplicated refname in ' + self.inFile + ' (' + refname + ')')
            db.close()
            return False
        elif len(changing) == 1:
            if self._enable_new_entry:
                print("No update:  {} already exists, can't add it as new.".format(refname))
                db.close()
                return False
            else:
                refname = changing[0][self.sql_map['refname'][0]]
        elif len(changing) == 0:
            if self._enable_new_entry:
                if not self.quiet_update:
                    print('Adding new entry {}'.format(kwargs['description'][:30]))
                new_id = qdb.execute("SELECT MAX(id) as id FROM records").fetchone()[0] + 1
                qdb.execute("INSERT INTO records(refname, id) VALUES (?,?)", (refname, new_id))
                if upnote is None:
                    upnote = 'Initial'
                db.commit()
                changed = True
                new_entry = True
            else:
                print("No update: {} not present to update.".format(refname))
                db.close()
                return False

        # Process it
        for fld, new_value in kwargs.items():
            if 'trace' in fld.lower():
                ttype = fld[0:-5]
                if ',' in new_value:
                    trlist = new_value.split(',')
                else:
                    trlist = [new_value]
                for tr in trlist:
                    print('\tAdding trace ' + ttype + '.' + tr + ' to ' + refname)
                    qf = (refname, tr, ttype, '')
                    qdb.execute("INSERT INTO trace(refname,tracename,tracetype,comment) VALUES (?,?,?,?)", qf)
                changed = True
            elif fld.lower() == 'refname':  # Do last
                continue
            elif fld not in self.sql_map.keys():
                print('{} is not a database field - skipping'.format(fld))
                continue
            else:
                if new_entry:
                    desc = kwargs['description']
                else:
                    desc = self.data[refname]['description']
                ell = '(...)'
                if len(desc) < 20:
                    ell = ''
                if not self.quiet_update:
                    print('\tChanging {}{}.{} to "{}"'.format(desc[:20], ell, fld, new_value))
                qdb_exec = "UPDATE records SET {}='{}' WHERE refname='{}'".format(fld, new_value, refname)
                qdb.execute(qdb_exec)
                changed = True
        if 'refname' in kwargs.keys():  # Do last
            print('\tChanging name {} to {}'.format(refname, kwargs['refname']))
            print("==> I'm not entirely sure this is comprehensive yet or not")
            if self.change_refName(refname, kwargs['refname']):
                changed = True

        if changed:  # Need to update 'updated' database
            db.commit()
            db.close()
            self.readData()
            db = sqlite3.connect(self.inFile)
            qdb = db.cursor()
            qdb_exec = "SELECT * FROM updated where refname='{}' COLLATE NOCASE ORDER BY level".format(refname)
            qdb.execute(qdb_exec)
            upd = qdb.fetchall()
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
                oldnote = changing[0][self.sql_map['notes'][0]]
                if oldnote is None:
                    oldnote = ''
                full_upnote = upnote + ' :: <Previous note: ' + oldnote + '>'
            qv = (refname, dt, updater, full_upnote, new_update)
            qdb.execute(qdb_exec, qv)
            db.commit()
            self.checkTrace(refname)
        db.close()
        return changed

    def change_refName(self, old_name=None, new_name=None):
        """Need to update all dbs when the refname is changed"""
        print("This will change the refname '{}' to '{}' in all databases".format(old_name, new_name))
        print("\tFirst in " + self.inFile)
        db = sqlite3.connect(self.inFile)
        qdb = db.cursor()
        qdb_exec = "SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(old_name)
        qdb.execute(qdb_exec)
        changing = qdb.fetchall()
        if len(changing) == 1:
            qdb_exec = "UPDATE records SET refname='{}' WHERE refname='{}'".format(new_name, old_name)
            qdb.execute(qdb_exec)
            qdb_exec = "UPDATE trace SET refname='{}' WHERE refname='{}'".format(new_name, old_name)
            qdb.execute(qdb_exec)
            qdb_exec = "UPDATE updated SET refname='{}' WHERE refname='{}'".format(new_name, old_name)
            qdb.execute(qdb_exec)
            db.commit()
            db.close()
        elif len(changing) > 1:
            print('Ambiguous entry:  {} has {} entries'.format(old_name, len(changing)))
            db.close()
            return False
        else:
            print('\tNone to change')
            db.close()
            return False
        if self.dbtype in self.traceables:
            for tr in self.traceables:
                dirName = dbTypes[tr][dbEM['dirName']]
                path = os.path.join(pbwd, dirName)
                inFile = os.path.join(path, dbTypes[tr][dbEM['inFile']])
                print('\tChecking ' + inFile)
                db = sqlite3.connect(inFile)
                qdb = db.cursor()
                qdb_exec = "SELECT * FROM trace WHERE tracename='{}' and tracetype='{}'".format(old_name, self.dbtype)
                qdb.execute(qdb_exec)
                changing = qdb.fetchall()
                if len(changing) > 0:
                    plural = 's'
                    if len(changing) == 1:
                        plural = ''
                    print('\t\t{} record{}'.format(len(changing), plural))
                    qdb_exec = "UPDATE trace SET tracename='{}' WHERE tracename='{}' and tracetype='{}'".format(new_name, old_name, self.dbtype)
                    qdb.execute(qdb_exec)
                    db.commit()
                else:
                    print('\t\tNone to change')
                db.close()
        self.readData()
        return True

    def checkTrace(self, checkrec='all'):
        if not self.quiet_update:
            print('checkTrace not implemented...')
        return
        if checkrec == 'all':
            checkrec = self.data.keys()
        elif type(checkrec) is not list:
            checkrec = [checkrec]
        for tr in self.traceables:
            dirName = dbTypes[tr][dbEM['dirName']]
            path = os.path.join(pbwd, dirName)
            inFile = os.path.join(path, dbTypes[tr][dbEM['inFile']])
            print('Checking {} {}Trace in {} against {}'.format(self.dbtype, tr, checkrec, inFile))
            db = sqlite3.connect(inFile)
            qdb = db.cursor()
            for rec in checkrec:
                for rs in self.data[rec][tr + 'Trace']:
                    if len(rs) > 0:
                        qdb_exec = "SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(rs)
                        qdb.execute(qdb_exec)
                        checking = qdb.fetchall()
                        if len(checking) == 0:
                            print(rs + ' not found in entry ' + self.dbtype + ':' + rec)

# ##################################################################VIEW##################################################################
    def show_schema(self):
        sm = self.get_sql_map(self.inFile)
        for v in sorted(sm.values()):
            for k in sm.keys():
                if sm[k] == v:
                    print(k, '  ', end='')
        print

    def getview(self, view, howsort=None):
        if howsort is None:
            howsort = self.display_howsort
        else:
            howsort = pd_utils.listify(howsort)
        for hs in howsort:
            if hs not in self.Records.required:
                raise ValueError("{} sort option not valid.".format(hs))
        if view == 'all':
            view = list(self.data.keys())
        else:
            view = pd_utils.listify(view)
        if howsort is None or not len(howsort):
            thesekeys = view
        else:
            self.sortedKeys = self.sortby(howsort)
            thesekeys = []
            for key in self.sortedKeys:
                if key in view:
                    thesekeys.append(key)
        return thesekeys

    def display_namespace(self, name):
        rec = Namespace(**self.data[name])
        rec.owner = pd_utils.stringify(rec.owner)
        if len(rec.updates):
            s = '\tUpdated\n'
            for uuu in rec.updates:
                s += '\t\t{},  {},  {}\n'.format(uuu[0].strip(), uuu[1].strip(), uuu[2].strip())
        else:
            s = ''
        rec.updates = s
        return rec

    def noshow(self, view):
        """This just returns the keys to view but doesn't display anything"""
        return view

    def show(self, view, output='stdout'):
        if output is not 'stdout':
            save2file = True
            fp = open(output, 'w')
        else:
            save2file = False
        for name in view:
            rec = self.display_namespace(name)
            s = '({}) {}\n'.format(rec.id, name)
            s += '\tvalue:        {}\n'.format(rec.value)
            s += '\tdescription:  {}\n'.format(rec.description)
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
# #                dirName = dbTypes['reqspec'][dbEM['dirName']]
# #                path = os.path.join(pbwd,dirName)
# #                inFile = os.path.join(path,dbTypes['reqspec'][dbEM['inFile']])
# #                rsdata = self.readData(inFile)
# #            else:
# #                rsdata = self.data
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
                                s += '\t\t{}\n:  '.format(xxx)
                                # ---1---#
# #                                try:
# #                                    s+=(rsdata[rrr][self.entryMap['value']]+'\n')
# #                                except:
# #                                    s+='not found in database\n'
            s += rec.updates
            print(s)
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
                rec = self.display_namespace(key)
                if tag == 'csv':
                    s = [rec.value, rec.description, rec.owner, rec.status, rec.other, rec.notes, rec.commentary]
                    csvw.writerow(s)
                else:
                    s = '{} ({:8s}) {}:  {}   ({})\n'.format(rec.value, rec.owner, rec.description, rec.status, key)
                    output_file.write(s)
        print('Writing file to ', self.output_filename)

    def listing(self, view):
        """
        Provides a short listing of the given records (default is all) in fixed widths.
        """
        for key in view:
            rec = self.display_namespace(key)
            print('{:10.10} {} ({})'.format(rec.value, rec.description, rec.status))

    def gantt(self, view):
        if self.dbtype not in self.ganttables:
            print('You can only gantt:  ', self.ganttables)
        for gantt_label in self.gantt_label:
            if gantt_label not in self.Records.required:
                print("{} label not found to use.".format(gantt_label))
                return
        for gantt_annot in self.gantt_annot:
            if gantt_annot not in self.Records.required:
                print("{} annot not found to use.".format(gantt_annot))
                return
        labels = []
        dates = []
        tstats = []
        preds = []
        annots = []
        for v in view:
            label = [self.data[v][gl] for gl in self.gantt_label]
            label = pd_gantt.check_gantt_labels(': '.join(label), labels)[:self.gantt_label_length]
            value = str(self.data[v]['value'])
            status = str(self.data[v]['status']).lower().strip()
            annot = []
            for ga in self.gantt_annot:
                grp = [x for x in self.data[v][ga]]
                annot.append(','.join(grp))
            annot = '; '.join(annot)
            predv = []
            if 'milestoneTrace' in self.data[v].keys():
                milepred = self.data[v]['milestoneTrace']
                if self.dbtype == 'milestone' or self.dbtype == 'wbs':
                    for x in milepred:
                        if x in view:
                            predv.append(self.data[x]['description'][0:self.gantt_label_length])
            if 'taskTrace' in self.data[v].keys():
                taskpred = self.data[v]['taskTrace']
                if self.dbtype == 'task' or self.dbtype == 'wbs':
                    for x in taskpred:
                        if x in view:
                            predv.append(self.data[x]['description'][0:self.gantt_label_length])
            labels.append(label)
            preds.append(predv)
            dates.append(value)
            annots.append(annot)
            status_return = self.check_ganttable_status(status, value)
            tstats.append(status_return)
        if not self.plot_predecessors:
            pred = None
        other_labels = None
        if len(self.gantt_annot):
            other_labels = annots
        show_cdf = self.show_cdf and self.Records.status[0].lower() != 'late'
        pd_gantt.plotGantt(labels, dates, preds, tstats, show_cdf=show_cdf, other_labels=other_labels)
        if self.show_color_bar and self.Records.status[0].lower() != 'late':
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
        elif not isinstance(valuetime, time.struct_time):
            print("Invalid time:  ", valuetime, type(valuetime))
        now = time.localtime()

        lag = 0.0
        if len(status) == 2:
            try:
                lag = float(status[1])
            except ValueError:
                statustime = pd_utils.get_time(status[1])
                if isinstance(statustime, time.struct_time):
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
        sortdict = {}
        if len(sort_it_by) > 1:
            print("Sorting by more than one thing is not yet supported.  Using first term.")
        sb = sort_it_by[0]
        for k in self.data:
            sdt = self.data[k][sb]
            if sdt is None:
                sdt = ' '
            elif isinstance(sdt, list):
                sdt = sdt[0]
            sortdict[k] = sdt
        sk = sorted(sortdict.items(), key=itemgetter(1, 0))
        sl = []
        for k in sk:
            sl.append(k[0])
        return sl
