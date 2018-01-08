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


class Data:
    db_json_file = 'databases.json'
    required_db_cols = ['refname', 'value', 'description', 'type', 'status', 'owner', 'other', 'notes', 'id', 'commentary']

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
            self.show_state_var()
        self.cache_lower_data_keys = []

    def init_state_variables(self):
        self.state_vars = ['show_cdf', 'description_length', 'gantt_label_to_use', 'other_gantt_label',
                           'display_howsort', 'plot_predecessors', 'show_dtype', 'show_trace', 'show_color_bar']
        self.show_cdf = True
        self.show_color_bar = True
        self.description_length = 50
        self.gantt_label_to_use = 'description'
        self.other_gantt_label = 'owner'
        self.display_howsort = 'value'
        self.plot_predecessors = True
        self.show_dtype = 'all'
        self.show_trace = True

    def set_state(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k in self.state_vars:
                setattr(self, k, v)
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
        for r in self.required_db_cols:
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
            allowedTypes.append(str(t[0]))
        self.allowedTypes = allowedTypes

        # get all records in dbtype database table
        qdb_exec = "SELECT * FROM records ORDER BY id"
        qdb.execute(qdb_exec)
        db = qdb.fetchall()

        # put database records into data dictionary (records/trace tables)
        data = {}
        self.cache_lower_data_keys = []
        for rec in db:
            refname = rec[sm['refname']]
            # ...get a single entry
            entry = {}
            for v in sm.keys():
                entry[v] = rec[sm[v]]  # This makes the entry dictionary
            if entry['status'] is None:
                entry['status'] = 'No status'
            if entry['owner'] is not None:
                entry['owner'] = entry['owner'].split(',')  # make csv list a python list
            # ...get trace information
            for traceType in self.traceables:
                fieldName = traceType + 'Trace'
                qdb_exec = "SELECT * FROM trace WHERE refname='{}' COLLATE NOCASE and tracetype='{}' ORDER BY level".format(refname, traceType)
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
            if entry['type'] not in allowedTypes and entry['type'] is not None:
                print('Warning type not in allowed list for {}: {}'.format(refname, entry['type']))
                print('Allowed types are:')
                print(allowedTypes)

        # check Trace table to ensure that all refnames are valid
        for traceType in self.traceables:
            fieldName = traceType + 'Trace'
            qdb_exec = "SELECT * FROM trace where tracetype='{}' COLLATE NOCASE".format(traceType)
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
        for tbl in tables:
            qdb.execute("PRAGMA table_info({})".format(tbl))
            if show_detail:
                print("Table name: {}".format(tbl))
            for t in qdb.fetchall():
                if show_detail:
                    print('\t', t)
                if tbl == 'records':
                    sql_map[str(t[1])] = t[0]
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
    def find(self, value, value2=None, dtype='all', field='value', owner='all',
             match='weak', howsort='value', display='gantt', only_late=False, return_list=False):
        """This will find records matching value1, except for milestones which looks between value1,value2 dates (time format is yy/m/d)
            value: value for which to search
            value2: second value if used [None]
            dtype:  data type (db dependent, can use 'any'/'all') [all] (can be list or string)
            field:  field in which to search (or 'any'/'all')  [value]
            owner:  string for one owner (can use 'any'/'all'), (can be list or string)
            match:  strength of match (weak, moderate, strong, verystrong) [weak]
            howsort:  field on which to sort display [value]
            display:  how to return data ('show'/'listing'/'gantt'/'file')  [gantt]
            only_late:  if True, will only display late items [False]
            return_list: if True, will return the list [False]"""

        pthru = ['any', 'all', 'n/a']  # do all owner/dtype if one of these
        if isinstance(owner, str):
            owner = [owner]
        if isinstance(dtype, str):
            dtype = [dtype]
        if len(self.data) == 0:
            print('Please read in the data')
            return 0
        foundrec = []
        if self.dbtype in self.ganttables and field.lower() == 'value':
            # ...value is a date, so checking dtype and date(s)
            if value2 is None:
                value2 = value
                value = self.projectStart
            try:
                value1time = time.mktime(time.strptime(value, '%y/%m/%d'))
                value2time = time.mktime(time.strptime(value2, '%y/%m/%d'))
            except ValueError:
                try:
                    value1time = time.mktime(time.strptime(value, '%Y/%m/%d'))
                    value2time = time.mktime(time.strptime(value2, '%Y/%m/%d'))
                except ValueError:
                    print(value, value2)
                    return 'Incorrect ganttable value term'
            for dat in self.data.keys():  # Loop over all records
                rec_dtype = str(self.data[dat]['type']).lower()
                rec_owner = (self.data[dat]['owner'] if self.data[dat]['owner'] is not None else [])
                for i_owner in owner:
                    for i_dtype in dtype:
                        use_this_rec = False
                        # Check stuff
                        dtype_check = (i_dtype.lower() in pthru) or (i_dtype.lower() == rec_dtype)
                        owner_check = (i_owner.lower() in pthru) or (i_owner in rec_owner)
                        field_check = self.data[dat][field] is not None
                        if dtype_check and owner_check and field_check:
                            if '-' in self.data[dat][field]:
                                val2check = self.data[dat][field].split('-')[0].strip()
                                print(dat + ':  Date range given - looking at start: ', val2check)
                            else:
                                val2check = str(self.data[dat][field])
                            try:
                                timevalue = time.mktime(time.strptime(val2check, '%y/%m/%d'))
                            except ValueError:
                                print('Improper time: {} ({})'.format(self.data[dat][field], self.data[dat]['name']))
                                timevalue = time.mktime(time.strptime('50/12/31', '%y/%m/%d'))
                            if timevalue >= value1time and timevalue <= value2time:
                                use_this_rec = True
                        if use_this_rec:
                            if only_late:
                                status = self.check_ganttable_status(self.data[dat]['status'], val2check)
                                if status[0] != 'late':
                                    use_this_rec = False
                        if use_this_rec:
                            foundrec.append(dat)
        else:
            for dat in self.data.keys():
                foundType = False
                if dtype.lower() in pthru and self.data[dat]['type'].lower() != 'na':
                    foundType = True
                elif dtype.lower() in self.data[dat]['type'].lower():
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

    def getref(self, v, search='description'):
        fndk = []
        d = v.lower()
        for dat in self.data.keys():
            dbdesc = self.data[dat][search]
            if dbdesc is not None:
                if d in dbdesc.lower():
                    fndk.append(dat)
        if len(fndk) == 1:
            return fndk[0]
        else:
            print("{} found (should be 1).".format(len(fndk)))
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
    def update(self, refname, field, new_value, dt=None, updater=None, upnote=None):
        """Updates a record field as well as the updated db, adds if not present
            name is the refname of the record, if not present a new entry is made
            field is the field(s) (can be a list) to be updated
            new_value is the new value(s) (should match field)
            dt is the YY/MM/DD of updated time (default is now)
            updater is the name of the updater (default is to query)
            upnote is the note to be included in updated record (default is to query or 'initial' on creation)"""
        self.readData()
        field = pd_utils.listify(field)
        new_value = pd_utils.listify(new_value)  # Beware of extra commas!!!
        if len(field) != len(new_value):
            print('Number of fields and values does not match')
            print('==> returning without update')
            return False
        if 'refname' in field and field[-1] != 'refname':
            print('refname should be last field changed - or outcome may not be what is desired')
            print('==> returning without update')
            return False
        db = sqlite3.connect(self.inFile)
        qdb = db.cursor()
        qdb.execute("SELECT * FROM records WHERE refname='{}' COLLATE NOCASE".format(refname))
        changing = qdb.fetchall()
        if len(changing) > 1:
            print('Duplicated refname in ' + self.inFile + ' (' + refname + ')')
            print('==> returning without update, so fix that!')
            db.close()
            return False
        changed = False
        if not len(changing):
            print('Adding new entry ' + refname)
            qdb.execute("SELECT * FROM records ORDER BY id")
            cnt = qdb.fetchall()
            new_id = cnt[-1][self.sql_map['id']] + 1  # works since we SORT BY id
            field.append('id')
            new_value.append(new_id)
            qdb.execute("INSERT INTO records(refname) VALUES (?)", (refname,))
            changed = True
            if upnote is None:
                upnote = 'Initial'
            db.commit()
        else:
            refname = changing[0][self.sql_map['refname']]
        for i, fld in enumerate(field):
            if 'trace' in fld.lower():
                ttype = fld[0:-5]
                if ',' in new_value[i]:
                    trlist = new_value[i].split(',')
                else:
                    trlist = [new_value[i]]
                for tr in trlist:
                    print('\tAdding trace ' + ttype + '.' + tr + ' to ' + refname)
                    qf = (refname, tr, 0, ttype)
                    qdb.execute("INSERT INTO trace(refname,tracename,level,tracetype) VALUES (?,?,?,?)", qf)
            elif fld not in self.sql_map.keys():
                print('{} is not a database field'.format(fld))
            elif fld == 'refname':
                print('\tChanging name {} to {}'.format(refname, new_value[i]))
                print("==> I'm not entirely sure this is comprehensive yet or not")
                if self.change_refName(refname, new_value[i]):
                    changed = True
            else:
                print('\tChanging {}.{} to {}'.format(refname, fld, new_value[i]))
                qdb_exec = "UPDATE records SET {}='{}' WHERE refname='{}'".format(fld, new_value[i], refname)
                qdb.execute(qdb_exec)
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
            full_upnote = upnote + ' :: <Previous note: ' + changing[0][self.sql_map['notes']] + '>'
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
        if howsort not in self.required_db_cols:
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
            dtype = self.data[name]['type']
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
            s += '\tValue:       {}\n'.format(value)
            s += '\tDescription: {}\n'.format(description)
            s += '\tType:        {}\n'.format(dtype)
            s += '\tStatus:      {}\n'.format(status)
            s += '\tNotes:       {}\n'.format(notes)
            s += '\tOwner:       '
            if owner:
                for o in owner:
                    s += (o + ', ')
                s = s.strip().strip(',')
            s += '\n'
            if other:
                s += '\tOther:       {}\n'.format(other)
            if commentary:
                s += '\tCommentary:  {}\n'.format(commentary)
            # ---1---# implement this later for all tracetypes
# #            if self.dbtype!='reqspec':
# #                dirName = dbTypes['reqspec'][dbEM['dirName']]
# #                path = os.path.join(pbwd,dirName)
# #                inFile = os.path.join(path,dbTypes['reqspec'][dbEM['inFile']])
# #                rsdata = self.readData(inFile)
# #            else:
# #                rsdata = self.data
            if len(self.traceables) and self.show_trace:
                for traceType in self.traceables:
                    fieldName = traceType + 'Trace'
                    s += '\t' + traceType + ' trace\n'
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

    def fileout(self, view='all', output_filename='fileout.txt'):
        view = self._getview(view, self.display_howsort)
        output_file = open(output_filename, 'w')
        for key in view:
            desc = self.data[key]['description']
            val = self.data[key]['value']
            stat = self.data[key]['status']
            owner = pd_utils.stringify(self.data[key]['owner'])
            s = '{} ({:8s}) {}:  {}   ({})\n'.format(val, owner, desc, stat, key)
            output_file.write(s)
        print('Writing file to ', output_filename)
        output_file.close()

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
        if self.gantt_label_to_use not in self.required_db_cols:
            print("{} label not found to use.".format(self.gantt_label_to_use))
            return
        if self.other_gantt_label is not None and self.other_gantt_label not in self.required_db_cols:
            print("{} other label not found to use.".format(self.other_gantt_label))
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
            label = '{:{prec}}'.format(str(self.data[v][self.gantt_label_to_use]), prec=label_prec)
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
        pd_gantt.plotGantt(labels, dates, pred, tstat, show_cdf=self.show_cdf, other_labels=other_labels)
        if self.show_color_bar:
            colorBar()

    def check_ganttable_status(self, status, value_date):
        if status is None or status.lower() == 'no status':
            status = 'none'
        status = status.lower().split()
        status_code = status[0]
        tcode = self.ganttable_status['none']
        if status_code in self.ganttable_status.keys():
            tcode = self.ganttable_status[status_code]
        if status_code == 'removed':
            return (status_code, tcode)

        if '-' in value_date:
            value_date = value_data.split('-')[-1]
        valuetime = time.mktime(time.strptime(value_date, '%y/%m/%d'))
        now = time.time()

        lag = 0.0
        if len(status) == 2:
            try:
                statustime = time.mktime(time.strptime(status[1], '%y/%m/%d'))
                lag = (statustime - valuetime) / 3600.0 / 24.0
                # Interpreted as "completed at X" or "moved to X"
                if status_code == 'complete' or status_code == 'moved':
                    valuetime = statustime
            except ValueError:
                lag = float(status[1])

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
