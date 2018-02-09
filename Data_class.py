#! usr/bin/env python
from __future__ import absolute_import, print_function
import os
from operator import itemgetter
import subprocess
import math
import sqlite3
import datetime
import time
import matplotlib.pyplot as plt
#  Project specific modules
import pd_gantt
import pd_utils
import fields_class as FC


class Data:
    db_json_file = 'databases.json'
    Records = FC.Records_fields()

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
        self.init_state_variables()
        if verbose:
            self.show_state()
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
        self.default_find_dtype = None
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
            entry['updates'] = []
            latest = pd_utils.get_time(self.projectStart)
            entry['initialized'] = None
            for v in updates:
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

# ##################################################################FIND##################################################################
    def find(self, value, value2=None, field='value', match='weak', display='gantt', return_list=False, **kwargs):
        """This will find records matching value1, except for milestones which looks between value1,value2 dates (time format is yy/m/d)
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
                    if 'upda' in match.lower() or 'init' in match.lower():
                        if rec.filter_on_updates(match, value1time, value2time, self.data[dat]):
                            foundrec.append(dat)
                    else:
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
                            foundMatch = pd_utils.searchfield(value, self.data[dat][fff], match)
                            if foundMatch:
                                break
                    elif field in self.data[dat].keys():
                        foundMatch = pd_utils.searchfield(value, self.data[dat][field], match)
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

    def list_unique(self, field, filter_on=None, returnList=False):
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
    def new(self, refname=None, dt=None, updater=None, upnote=None, **kwargs):
        """Adds a new record (essentially a wrapper for update which generates a refname and enables new)
        """
        self.__enable_new_entry = True
        if 'refname' in kwargs.keys():
            print("New entries shouldn't include 'refname' in the kwargs entries.\nNot adding record.")
            return
        if 'description' not in kwargs.keys():
            print("New entries must include a description.\nNot adding record.")
            return
        if refname is None:
            refname_len = 30
            refname = pd_utils.make_refname(kwargs['description'], refname_len)
            while refname in self.data.keys():
                refname_len += 5
                if refname_len > 80:
                    print("Not unique description:  {}\nNot adding record.".kwargs['description'])
                    return
                refname = pd_utils.make_refname(kwargs['description'], refname_len)
        self.update(refname, dt, updater, upnote, **kwargs)  # Make sure they match!
        self.__enable_new_entry = False
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
        ok_to_change = True
        new_entry = False
        if len(changing) > 1:
            print('Duplicated refname in ' + self.inFile + ' (' + refname + ')')
            ok_to_change = False
        elif not len(changing):  # Not present
            if self.__enable_new_entry:
                print('Adding new entry ' + refname)
                qdb.execute("SELECT * FROM records ORDER BY id")
                cnt = qdb.fetchall()
                new_id = cnt[-1][self.sql_map['id'][0]] + 1  # works since we SORT BY id
                kwargs['id'] = new_id
                qdb.execute("INSERT INTO records(refname) VALUES (?)", (refname,))
                changed = True
                if upnote is None:
                    upnote = 'Initial'
                db.commit()
                new_entry = True
            else:
                print("{} not present to update.".format(refname))
                ok_to_change = False
        else:  # The refname exists and is unique
            if self.__enable_new_entry:
                print("{} already exists, can't add it as new.".format(refname))
                ok_to_change = False
            else:
                refname = changing[0][self.sql_map['refname'][0]]
        if not ok_to_change:
            print("---returning without update---")
            db.close()
            return False

        # Process it
        changed = False
        for fld, new_value in kwargs.iteritems():
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
                print('\tChanging {}.{} to {}'.format(refname, fld, new_value))
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
                updater = raw_input("Who is updating:  ")
            if upnote is None:
                upnote = raw_input("Update note to append previous record notes:  ")
            if new_entry:
                full_upnote = upnote
            else:
                full_upnote = upnote + ' :: <Previous note: ' + changing[0][self.sql_map['notes'][0]] + '>'
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
            handle = pd_utils.make_handle(name)
            value = self.data[name]['value']
            description = self.data[name]['description']
            dtype = self.data[name]['dtype']
            if self.show_dtype.lower() == 'all' or self.show_dtype.lower() == dtype.lower():
                pass
            else:
                continue
            owner = self.data[name]['owner']
            other = self.data[name]['other']
            updated = self.data[name]['updates']
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
                                s += '\t\t{}:  '.format(xxx)
                                # ---1---#
# #                                try:
# #                                    s+=(rsdata[rrr][self.entryMap['value']]+'\n')
# #                                except:
# #                                    s+='not found in database\n'
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
                owner = pd_utils.stringify(self.data[key]['owner'])
                other = pd_utils.stringify(self.data[key]['other'])
                notes = pd_utils.stringify(self.data[key]['notes'])
                commentary = pd_utils.stringify(self.data[key]['commentary'])
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
            owner = pd_utils.stringify(self.data[key]['owner'])
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
            label = pd_gantt.check_gantt_labels(label, labels)
            labels.append(label)
            value = str(self.data[v]['value'])
            status = str(self.data[v]['status']).lower().strip()
            othlab = self.data[v][self.other_gantt_label]
            if othlab is None:
                othlab = ' '
            else:
                othlab = pd_utils.stringify(othlab)
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
        pd_gantt.plotGantt(labels, dates, pred, tstat, show_cdf=show_cdf, other_labels=other_labels)
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
