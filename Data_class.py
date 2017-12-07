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
    def __init__(self, dbtype, projectStart='14/09/01', verbose=True):
        """This class has the functions to read in the data file [milestones/reqspecs/interfaces/risks.db] and write out
           a number of tex files.  See README and Architecture.dat
               dbtype is the type of database [milestones, reqspecs, interfaces, risks]
               self.data is the "internal" database and self.db is the read-in sqlite3 database, the Maps convert between the self.data dictionary and the self.db list
               entryMap are the common fields of the internal python database
               entryHelp has information on the different fields per dbtype
               sqlMap are the fields in the sqlite3 database (read from the .db file, but should correspond to entryMap strings)
               each db file has the following tables (dbtype, trace, type, updated)"""

        self.displayTypes = {'show': self.show, 'listing': self.listing, 'gantt': self.gantt, 'noshow': self.noshow, 'file': self.fileout}
        self.show_cdf = True
        self.projectStart = projectStart
        self.dbTypes = self.get_db_json('databases.json')
        self.dirName = self.dbTypes[dbtype]['subdirectory']
        self.inFile = os.path.join(self.dirName, self.dbTypes[dbtype]['dbfilename'])
        self.ganttables = []
        if self.dbTypes[dbtype]['ganttable'] == 'True':
            self.ganttables.append(dbtype)
        self.traceables = []
        if self.dbTypes[dbtype]['traceable'] == 'True':
            self.traceables.append(dbtype)
        self.caption = self.dbTypes[dbtype]['caption']
        self.dbtype = dbtype

    def readData(self, inFile=None):
        """This reads in the sqlite3 database and puts it into db and data arrays.
           If inFile==None:
                it reads self.inFile and makes the data, db and sqlMap arrays 'self':  this is the 'normal' way,
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
            sm = self.getSQLmap(inFile)
        except IOError:
            if '+' in inFile:
                print(inFile + ' is a concatenated database -- read in and concatDat')
            else:
                print('Sorry, ' + inFile + ' is not a valid database')
            return None
        dbconnect = sqlite3.connect(inFile)
        qdb = dbconnect.cursor()

        # get allowed types
        qdb_exec = "SELECT * FROM types"
        qdb.execute(qdb_exec)
        db = qdb.fetchall()
        allowedTypes = []
        for t in db:
            allowedTypes.append(str(t[0]))

        # get all records in dbtype database table
        qdb_exec = "SELECT * FROM records ORDER BY id"
        qdb.execute(qdb_exec)
        db = qdb.fetchall()

        # put database records into data dictionary (records/trace tables)
        data = {}
        for rec in db:
            refName = rec[sm['refName']].lower()
            # ...get a single entry
            entry = {}
            for v in sm.keys():
                entry[v] = rec[sm[v]]  # This maps db -> internal
            if 'status' in entry.keys() and entry['status'] is None:
                entry['status'] = 'No status'
            if 'owners' in entry.keys() and entry['owners'] is not None:
                entry['owners'] = entry['owners'].split(',')  # make csv list a python list
            # ...trace
            for traceType in self.traceables:
                fieldName = traceType + 'Trace'
                qdb_exec = "SELECT * FROM trace WHERE refName='{}' COLLATE NOCASE and traceType='{}' ORDER BY level".format(refName, traceType)
                qdb.execute(qdb_exec)
                trace = qdb.fetchall()
                entry[fieldName] = []
                for v in trace:
                    entry[fieldName].append(v[1])
            # ...read in updated table
            qdb_exec = "SELECT * FROM updated WHERE refName='{}' COLLATE NOCASE ORDER BY level".format(refName)
            qdb.execute(qdb_exec)
            updates = qdb.fetchall()
            entry['updated'] = []
            for v in updates:
                entry['updated'].append([v[1], v[2], v[3]])
            # ...put in dictionary if not a duplicate
            if refName in data.keys():
                existingEntry = data[refName]
                print('name collision:  ' + refName)
                print('--> not adding to data')
                print('[\n', existingEntry)
                print('\n]\n[\n', entry)
                print('\n]')
            else:
                data[refName] = entry
            # ...give warning if not in 'allowedTypes' (but keep anyway)
            if 'type' in entry.keys() and entry['type'] not in allowedTypes and entry['type'] is not None:
                print('Warning type not in allowed list: ' + entry['type'])
                print('Allowed types are:')
                print(allowedTypes)

        # check Trace table to ensure that all refNames are valid
        for tracetype in self.traceables:
            fieldName = traceType + 'Trace'
            qdb_exec = "SELECT * FROM trace where traceType='{}'".format(traceType)
            qdb.execute(qdb_exec)
            trace = qdb.fetchall()
            for t in trace:
                t_refName = t[0].lower()
                if t_refName not in data.keys():
                    print('{} not in data records:  {}'.format(fieldName, t[0]))
        # check Updated table to ensure that all refNames are valid
        qdb_exec = "SELECT * FROM updated"
        qdb.execute(qdb_exec)
        updates = qdb.fetchall()
        already_found = []
        for u in updates:
            u_refName = u[0].lower()
            if u_refName not in data.keys() and u_refName not in already_found:
                already_found.append(u_refName)
                print('updated not in data records:  ', u[0])
        dbconnect.close()
        if 'projectstart' in data.keys():
            self.projectStart = data['projectstart']['value']
            print('Setting project start to ' + self.projectStart)
        if selfVersion:
            self.data = data
            self.db = db
            self.sqlMap = sm
            return len(data)
        else:
            return data

    def get_db_json(self, dbjson='databases.json'):
        import json
        with open(dbjson, 'r') as f:
            x = json.load(f)
        return x

    def getSQLmap(self, inFile):
        if os.path.exists(inFile):
            dbconnect = sqlite3.connect(inFile)
        else:
            print(inFile + ' not found')
            return 0
        qdb = dbconnect.cursor()
        qdb.execute("PRAGMA table_info(records)")
        sqlMap = {}
        for t in qdb.fetchall():
            sqlMap[str(t[1])] = t[0]
        dbconnect.close()
        return sqlMap

    def concatDat(self, dblist):
        """This will concatentate the database list into a single database, which is useful to make WBS=TASK+MILESTONE"""
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
    def find(self, value, value2=None, dtype='all', field='value', owner='all', match='weak', howsort='value', display='gantt_o', returnList=False):
        """This will find records matching value1, except for milestones which looks between value1,value2 dates (time format is yy/m/d)
            value: value for which to search
            value2: second value if used [None]
            dtype:  data type (db dependent, can use 'any'/'all') [nsfB]
            field:  field in which to search (or 'any'/'all')  [value]
            owner:  string for one owner (can use 'any'/'all')
            match:  strength of match (weak, moderate, strong, verystrong) [weak]
            howsort:  field on which to sort display [value]
            display:  how to return data ('show'/'listing'/'gantt[_o]'/'file')  [gantt_o]
            returnList: True/[False]"""

        pthru = ['any', 'all']
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
                print(value, value2)
                return 'Incorrect ganttable value term'
            for dat in self.data.keys():
                etype = str(self.data[dat]['type']).lower()  # dtype of entry
                eowners = (self.data[dat]['owners'] if self.data[dat]['owners'] is not None else [])
                use_this_rec = False
                # Check stuff
                dtype_check = (dtype.lower() in pthru) or (dtype.lower() == etype) or (etype.lower() == 'na')
                owner_check = (owner.lower() in pthru) or (owner in eowners)
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
                    foundrec.append(dat)
        else:
            for dat in self.data.keys():
                foundType = False
                if dtype.lower() in ['any', 'all'] and self.data[dat]['type'].lower() != 'na':
                    foundType = True
                elif dtype.lower() in self.data[dat]['type'].lower():
                    foundType = True
                if foundType:
                    foundMatch = False
                    if field.lower() in ['any', 'all']:
                        for fff in self.data[dat].keys():
                            foundMatch = self.__searchfield(value, self.data[dat][fff], match)
                            if foundMatch:
                                break
                    elif field in self.data[dat].keys():
                        foundMatch = self.__searchfield(value, self.data[dat][field], match)
                    else:
                        print('Invalid field for search')
                        return
                    if foundMatch:
                        foundrec.append(dat)
        if len(foundrec):
            foundrec = self._getview(foundrec, howsort)
            if display == 'gantt_o':
                self.owner_gantt_labels = True
                display = 'gantt'
            elif display == 'gantt':
                self.owner_gantt_labels = False
            if display not in self.displayTypes.keys():
                display = 'listing'
            self.displayTypes[display](foundrec, howsort=None)
        else:
            print('No records found.')
        if returnList:
            return foundrec

    def __searchfield(self, value, infield, match):
        foundMatch = False
        if type(infield) == list:
            foundMatch = self.__searchlist(value, infield, match)
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

    def __searchlist(self, value, inlist, match):
        foundMatch = False
        for v in inlist:
            if type(v) == list:
                foundMatch = self.__searchlist(value, v, match)
            else:
                foundMatch = self.__searchfield(value, v, match)
        return foundMatch

    def list_unique(self, field, returnList=False):
        unique_values = []
        for dat in self.data.keys():
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

    def findref(self, desc):
        fndk = []
        d = desc.lower()
        for dat in self.data.keys():
            dbdesc = self.data[dat]['description']
            if dbdesc is not None:
                if d in dbdesc.lower():
                    fndk.append(dat)
        fnd = []
        for f in fndk:
            refName = self.data[f]['refName']
            fnd.append(refName)
            dbdesc = self.data[f]['description']
            value = self.data[f]['value']
            status = self.data[f]['status']
            notes = self.data[f]['notes']
            print(refName, ':  ', dbdesc, ' [', value, ']')
            print('\t', status, ':  ', notes)
        return str(fnd[0])

    def since(self, dstr):
        dbconnect = sqlite3.connect(self.inFile)
        qdb = dbconnect.cursor()
        qdb_exec = "SELECT refName FROM updated WHERE updated>'{}'".format(dstr)
        qdb.execute(qdb_exec)
        updates = qdb.fetchall()
        refNames = []
        for u in updates:
            print(u)
            refNames.append(u[0].lower())
        self.show(refNames, showTrace=False)

# ##################################################################UPDATE##################################################################
    def update(self, refName, field=None, new_value=None, dt=None, updater=None, upnote=None):
        """Updates a record field as well as the updated db, adds if not present
            name is the refName of the record, if not present a new entry is made
            field is the field(s) (can be a list) to be updated
            new_value is the new value(s) (should match field)
            dt is the YY/MM/DD of updated time (default is now)
            updater is the name of the updater (default is to query)
            upnote is the note to be included in updated record (default is to query or 'initial' on creation)"""
        self.readData()
        if field is None:
            field, new_value = self._getRecordItems4Input(refName)
            if field is False:
                return False
        if type(field) is not list:
            field = [field]
        if type(new_value) is not list:
            new_value = [new_value]
        if len(field) != len(new_value):
            print('Number of fields and values does not match')
            print('==> returning without update')
            return False
        if 'refName' in field and field[-1] != 'refName':
            print('refName should be last field changed - or outcome may not be what is desired')
            print('==> returning without update')
            return False
        db = sqlite3.connect(self.inFile)
        qdb = db.cursor()
        qdb.execute("SELECT * FROM records WHERE refName='{}'".format(refName))
        changing = qdb.fetchall()
        if len(changing) > 1:
            print('Duplicated refName in ' + self.inFile + ' (' + refName + ')')
            print('==> returning without update, so fix that!')
            db.close()
            return False
        changed = False
        if len(changing) == 0:
            print('Adding new entry ' + refName)
            qdb.execute("SELECT * FROM records ORDER BY id")
            cnt = qdb.fetchall()
            new_id = cnt[-1][self.sqlMap['id']] + 1  # works since we SORT BY id
            field.append('id')
            new_value.append(new_id)
            qdb.execute("INSERT INTO records(refName) VALUES (?)", (refName,))
            changed = True
            if upnote is None:
                upnote = 'Initial'
            db.commit()
        for i, fld in enumerate(field):
            if 'trace' in fld.lower():
                ttype = fld[0:-5]
                if ',' in new_value[i]:
                    trlist = new_value[i].split(',')
                else:
                    trlist = [new_value[i]]
                for tr in trlist:
                    print('\tAdding trace ' + ttype + '.' + tr + ' to ' + refName)
                    qf = (refName, tr, 0, ttype)
                    qdb.execute("INSERT INTO trace(refName,traceName,level,traceType) VALUES (?,?,?,?)", qf)
            elif fld not in self.sqlMap.keys():
                print('{} is not a database field'.format(fld))
            elif fld == 'refName':
                print('\tChanging name {} to {}'.format(refName, new_value[i]))
                print("==> I'm not entirely sure this is comprehensive yet or not")
                if self.changeName(refName, new_value[i]):
                    changed = True
            else:
                print('\tChanging {}.{} to {}'.format(refName, fld, new_value[i]))
                qdb_exec = "UPDATE records SET {}='{}' WHERE refName='{}'".format(fld, new_value[i], refName)
                qdb.execute(qdb_exec)
                changed = True
        if changed:  # Need to update 'updated' database
            db.commit()
            db.close()
            self.readData()
            db = sqlite3.connect(self.inFile)
            qdb = db.cursor()
            qdb_exec = "SELECT * FROM updated where refName='{}' ORDER BY level".format(refName)
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
                upnote = raw_input("Update note:  ")
            qv = (refName, dt, updater, upnote, new_update)
            qdb.execute(qdb_exec, qv)
            db.commit()
            self.checkTrace(refName)
        db.close()
        return changed

    def changeName(self, old_name=None, new_name=None):
        """Need to update all dbs when the refName is changed"""
        print("This will change the refName '{}' to '{}' in all databases".format(old_name, new_name))
        print("\tFirst in " + self.inFile)
        db = sqlite3.connect(self.inFile)
        qdb = db.cursor()
        qdb_exec = "SELECT * FROM records WHERE refName='{}'".format(old_name)
        qdb.execute(qdb_exec)
        changing = qdb.fetchall()
        if len(changing) == 1:
            qdb_exec = "UPDATE records SET refName='{}' WHERE refName='{}'".format(new_name, old_name)
            qdb.execute(qdb_exec)
            qdb_exec = "UPDATE trace SET refName='{}' WHERE refName='{}'".format(new_name, old_name)
            qdb.execute(qdb_exec)
            qdb_exec = "UPDATE updated SET refName='{}' WHERE refName='{}'".format(new_name, old_name)
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
                qdb_exec = "SELECT * FROM trace WHERE traceName='{}' and traceType='{}'".format(old_name, self.dbtype)
                qdb.execute(qdb_exec)
                changing = qdb.fetchall()
                if len(changing) > 0:
                    plural = 's'
                    if len(changing) == 1:
                        plural = ''
                    print('\t\t{} record{}'.format(len(changing), plural))
                    qdb_exec = "UPDATE trace SET traceName='{}' WHERE traceName='{}' and traceType='{}'".format(new_name, old_name, self.dbtype)
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
                        qdb_exec = "SELECT * FROM records WHERE refName='{}'".format(rs)
                        qdb.execute(qdb_exec)
                        checking = qdb.fetchall()
                        if len(checking) == 0:
                            print(rs + ' not found in entry ' + self.dbtype + ':' + rec)

    def checkHandle(self, handle):
        badHandle = not handle.isalpha()
        if badHandle:
            print("Note that tex can't have any digits or non-alpha characters")
            useHandle = raw_input('Please try a new handle:  ')
            self.checkHandle(useHandle)
        else:
            useHandle = handle
        return useHandle

    def makeHandle(self, refName):
        if refName.isalpha():
            return refName
        r = {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six',
             '7': 'seven', '8': 'eight', '9': 'nine', '0': 'zero',
             '-': 'dash', ':': '', '.': 'dot', ',': 'comma', '_': 'underscore'}
        handle = ''
        for c in refName:
            if c in r.keys():
                handle += r[c]
            else:
                handle += c
        handle = self.checkHandle(handle)
        return handle

    def _getRecordItems4Input(self, name):
        print('Fields for ' + name)
        print('Hit <return> if none')
        print
        field = []
        new_values = []
        emsort = utils.sortByValue(self.sqlMap)
        for e in emsort:
            if e == 'refName' or e == ' id':
                continue
            cursor = 'Input ' + e + ':  '
            nv = raw_input(cursor)
            if len(nv) > 0:
                field.append(e)
                new_values.append(nv)
        print('Input trace values:  (<return> for none or comma-separated list for multiple)')
        for tr in self.traceables:
            e = tr + 'Trace'
            cursor = '\tInput ' + e + ':  '
            nv = raw_input(cursor)
            if len(nv) > 0:
                field.append(e)
                new_values.append(nv)
        print
        return field, new_values


# ##################################################################VIEW##################################################################
    def show_schema(self):
        sm = self.getSQLmap(self.inFile)
        for v in sorted(sm.values()):
            for k in sm.keys():
                if sm[k] == v:
                    print(k, '  ', end='')
        print

    def _getview(self, view, howsort):
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

    def noshow(self, view='all', howsort='name'):
        """This just returns the keys to view but doesn't display anything"""
        view = self._getview(view, howsort)
        return view

    def show(self, view='all', output='stdout', howsort='refName', showTrace=True):
        view = self._getview(view, howsort)
        if output is not 'stdout':
            save2file = True
            fp = open(output, 'w')
        else:
            save2file = False
        for name in view:
            handle = self.makeHandle(self.refName)
            other = self.data[name]['other']
            value = self.data[name]['value']
            description = self.data[name]['description']
            dtype = self.data[name]['type']
            owners = self.data[name]['owners']
            updated = self.data[name]['updated']
            notes = self.data[name]['notes']
            idno = self.data[name]['id']
            status = self.data[name]['status']
            s = '({}) Name:  {}     (\\def\\{})\n'.format(idno, name, handle)
            s += '\tValue:       {}\n'.format(value)
            s += '\tDescription: {}\n'.format(description)
            s += '\tType:        {}\n'.format(dtype)
            s += '\tStatus:      {}\n'.format(status)
            s += '\tNotes:       {}\n'.format(notes)
            s += '\tOther:       {}\n'.format(other)
            s += '\tOwner:       '
            if owners:
                for o in owners:
                    s += (o + ', ')
                s = s.strip().strip(',')
            s += '\n'
            # ---1---# implement this later for all tracetypes
# #            if self.dbtype!='reqspec':
# #                dirName = dbTypes['reqspec'][dbEM['dirName']]
# #                path = os.path.join(pbwd,dirName)
# #                inFile = os.path.join(path,dbTypes['reqspec'][dbEM['inFile']])
# #                rsdata = self.readData(inFile)
# #            else:
# #                rsdata = self.data
            if len(self.traceables) and showTrace:
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
        return view

    def fileout(self, view='all', howsort='value', output_filename='fileout.txt'):
        """Provides a short listing of the given records (default is all).  If 'short' is True, it truncates fields per the "spaces", otherwise not"""
        view = self._getview(view, howsort)
        output_file = open(output_filename, 'w')
        for key in view:
            desc = self.data[key]['description']
            val = self.data[key]['value']
            stat = self.data[key]['status']
            owners = self.data[key]['owners']
            oss = '({})'.format(owners[0])
            s = '{} {:8s} {}:  {}\n'.format(val, oss, desc, stat)
            output_file.write(s)
        print('Writing file to ', output_filename)
        output_file.close()
        return view

    def listing(self, view='all', howsort='value', short=True, nameSpace=40, descSpace=50, statSpace=9):
        """Provides a short listing of the given records (default is all).  If 'short' is True, it truncates fields per the "spaces", otherwise not"""
        view = self._getview(view, howsort)
        for key in view:
            desc = self.data[key]['description']
            val = self.data[key]['value']
            stat = self.data[key]['status']
            owners = self.data[key]['owners']
            namepad = nameSpace - len(key)
            statpad = statSpace - len(stat)
            if short:
                sss = stat[0:statSpace] + statpad * ' '
                kss = key + namepad * ' '
                dss = desc[0:descSpace]
                print('[{}] ({}) \t {} ({})'.format(val, owners[0], desc, key))
            else:
                print(key + namepad * ' ' + ' [' + val + '] ' + desc + '  ==> ' + stat)
        print
        return view

    def gantt(self, view='all', howsort='value', plotPredecessors=True, labelLength=46):
        view = self._getview(view, howsort)
        if self.dbtype not in self.ganttables:
            print('You can only gantt:  ', self.ganttables)
        if type(view) != list:
            view = [view]
        labels = []
        dates = []
        tstat = []
        pred = []
        owner = []
        removedColor = 'w'
        lateColor = 'red'  # 'darkorange'
        movedColor = 'y'
        notyetColor = 'k'
        for v in view:
            label = str(self.data[v]['description'])[0:labelLength]
            label = pd_gantt.check_gantt_labels(label, labels)
            labels.append(label)
            value = str(self.data[v]['value'])
            status = str(self.data[v]['status']).lower().strip()
            milepred = self.data[v]['milestoneTrace']
            predss = []
            if 'milestoneTrace' in self.data[v].keys():
                ownlab = self.data[v]['owners']
                if self.dbtype == 'milestone' or self.dbtype == 'wbs':
                    for x in milepred:
                        if x in view:
                            predss.append(str(self.data[x]['description'])[0:labelLength])
            if 'taskTrace' in self.data[v].keys():
                taskpred = self.data[v]['taskTrace']
                if self.dbtype == 'task' or self.dbtype == 'wbs':
                    for x in taskpred:
                        if x in view:
                            predss.append(str(self.data[x]['description'])[0:labelLength])
            pred.append(predss)
            dates.append(value)
            owner.append(ownlab)

            tcode = notyetColor
            if '-' in value:
                tcode = notyetColor
            else:  # Get milestone marker color code
                valuetime = time.mktime(time.strptime(value, '%y/%m/%d'))
                now = time.time()
                status = status.split()
                if len(status) > 0:
                    if status[0].lower() == 'removed':  # no longer used
                        tcode = removedColor
                    elif now > valuetime and status[0].lower() != 'complete':  # it's late
                        tcode = lateColor
                    elif now > valuetime and status[0].lower() == 'complete':
                        tcode = 'b'
                        if len(status) > 1:
                            try:
                                lag = int(status[1])
                            except ValueError:
                                lag = 0
                            tcode = self._lag2rgb(lag)
                    elif status[0].lower() == 'moved':  # date was moved
                        tcode = movedColor
                    else:
                        tcode = notyetColor
            tstat.append(tcode)
        if plotPredecessors:
            pass
        else:
            pred = None
        owner_labels = None
        if self.owner_gantt_labels:
            owner_labels = owner
        pd_gantt.plotGantt(labels, dates, pred, tstat, show_cdf=self.show_cdf, other_labels=owner_labels)
        if self.show_cdf:
            self.colorBar()
        return view

    def colorBar(self):
        fff = plt.figure('ColorBar')
        ax = fff.add_subplot(111)
        ax.set_yticklabels([])
        plt.xlabel('Days')
        for j in range(180):
            i = j - 90.0
            c = self._lag2rgb(i)
            plt.plot([i], [1.0], 's', markersize=20, color=c, markeredgewidth=0.0, fillstyle='full')
        ar = plt.axis()
        boxx = [ar[0], ar[1], ar[1], ar[0], ar[0]]
        boxy = [-5.0, -5.0, 6.0, 6.0, -5.0]
        plt.plot(boxx, boxy, 'k')
        plt.axis('image')

    def colorCurve(self):
        plt.figure('ColorCurve')
        plt.xlabel('Days')
        for j in range(180):
            i = j - 90.0
            c = self._lag2rgb(i)
            plt.plot(i, c[0], 'r.')
            plt.plot(i, c[1], 'g.')
            plt.plot(i, c[2], 'b.')

    def _lag2rgb0(self, lag):
        if lag < -90.0:
            c = (0.0, 1.0, 0.0)
        elif lag > 90.0:
            c = (1.0, 0.0, 0.0)
        else:
            if lag > -5.0:
                a = 2.0 * (50.0)**2
                r = math.exp(-(lag - 90.0)**2 / a)
            else:
                r = 0.0
            if lag < 5.0:
                a = 2.0 * (50.0)**2
                g = math.exp(-(lag + 90.0)**2 / a)
            else:
                g = 0.0
            a = 2.0 * (30.0)**2
            b = math.exp(-(lag)**2 / a)
            c = (r, g, b)
        return c

    def _lag2rgb(self, lag):
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

    def getEntryString(self, key, ver='short', valueORdef='value'):
        """key is the dictionary key
           ver:  long/[short]/table
           valueORdef:  [value]/def
           ==>this is from the 'legacy' tex output stuff"""
        print('getEntryString:  NEED TO ADD IN TYPE, OWNER, UPDATE TO OUTPUT')
        if valueORdef == 'value':
            value = self.data[key]['value']
            description = self.data[key]['description']
            reqspec = ''
            for t in self.data[key]['reqspecTrace']:
                reqspec += (t + ', ')
            reqspec = reqspec.strip().strip(',')
            component = ''
            for c in self.data[key]['componentTrace']:
                component += (c + ', ')
            component = component.strip().strip(',')
        else:
            value = '\\' + key
            description = '\\' + key + 'Description'
            reqspec = '\\' + key + 'Trace'
            component = '\\' + key + 'Trace'  # duplicate or set to '-'...?
        notes = self.data[key]['notes']

        if ver[0:2] == 'lo':
            sout = '\\' + dbTypes[self.dbtype][dbEM['texdef']] + '\{{}\}\{{}\}\{{}\}\{{}\}\{{}\}\n'.format(key, value, description, reqspec, component)
            if notes != '-' and notes != 'Notes':
                sout += ('\\noindent\n' + notes + '\n\n')
            sout += ('\\vspace * {0.25in}\n\n')
        elif ver[0:2] == 'sh':
            sout = '\\item \\underline\{{}\}: {} [{}] : [{}]\n'.format(key, value, reqspec, component)
        elif ver[0:2] == 'ta':
            sout = '\\textbf\{{}:\} {} & {} & {} & {} \\\\ \\hline\n'.format(key, description, value, reqspec, component)
        else:
            sout = ver + ':  Incorrect version set'
            print(sout)
        return sout

# ########################################################################################################################################
