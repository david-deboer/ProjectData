#! /usr/bin/env python
from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import Data_class
import sqlite3 as lite
import os.path
import argparse
import sys


class Database:
    def __init__(self, dbtype='milestone'):
        self.dbtype = dbtype
        self.tables = {'records': {'schema': '($ TEXT, value TEXT, description TEXT, dtype TEXT, status TEXT, owner TEXT, '
                                             'other TEXT, notes TEXT, commentary TEXT, id INT, PRIMARY KEY($))',
                                   'ref_key': 'refname'},
                       'trace': {'schema': '($ TEXT, tracename TEXT, tracetype TEXT, comment TEXT)',
                                 'ref_key': 'refname'},
                       'types': {'schema': '($ TEXT, description TEXT, PRIMARY KEY($))',
                                 'ref_key': 'name'},
                       'updated': {'schema': '($ TEXT, updated TEXT, by TEXT, note TEXT, level INT)',
                                   'ref_key': 'refname'}}
        dblist = Data_class.pd_utils.get_db_json('databases.json')
        dir_name = dblist[dbtype]['subdirectory']
        self.dbfile = os.path.join(dir_name, dblist[dbtype]['dbfilename'])

    def get_dbfile(self):
        return self.dbfile

    def create_db(self):
        print('Creating {}'.format(self.dbfile))
        db = lite.connect(self.dbfile)
        conn = db.cursor()

        for k in self.tables.keys():
            schema = self.tables[k]['schema'].replace('$', self.tables[k]['ref_key'])
            creat_tbl = "CREATE TABLE {} {}".format(k, schema)
            print(creat_tbl)
            conn.execute(creat_tbl)
        db.commit()
        db.close()

    def get_schema(self):
        m = Data_class.Data(self.dbtype)
        return m.get_sql_map()

    def insert(self, input_file):
        m = Data_class.Data(self.dbtype)
        m.readData()
        refkeys = {}
        refkeys['records'] = {}
        for x in m.data.keys():
            refkeys['records'][x.lower()] = x
        db = lite.connect(self.dbfile)
        conn = db.cursor()

        with open(input_file, 'r') as f:
            for line in f:
                data = line.split('|')
                if len(data) != 4:
                    print("Need 4 values:  table_name, ref_key, field, value")
                    continue
                tbl, ref, fld, val = [x.strip() for x in data]
                tbl = tbl.lower()
                ref = ref.lower()
                fld = fld.lower()
                if tbl not in self.tables.keys():
                    print("Table {} is not in schema.".format(tbl))
                    continue
                if tbl not in refkeys.keys():
                    refkeys[tbl] = {}
                rkeyname = self.tables[tbl]['ref_key']
                if ref in refkeys[tbl].keys():
                    xcmd = "UPDATE {} SET {}='{}' WHERE {}='{}'".format(
                           tbl, fld, val, rkeyname, refkeys[tbl][ref])
                    conn.execute(xcmd)
                else:
                    xcmd = "INSERT INTO {}({}, {}) VALUES(?, ?)".format(
                           tbl, rkeyname, fld)
                    data = (ref, val)
                    conn.execute(xcmd, data)
                    refkeys[tbl][ref.lower()] = ref
                db.commit()
        db.close()

    def generate_input_file(self, sloppy_file):
        """
        A "sloppy file" has a sloppy format, which this translates to the "tidier"
        input_file used for self.insert (see ms.txt example).
        Use this with caution/customization.
        """
        schema = self.get_schema().keys()
        persist = ['dtype', 'other', 'notes', 'owner']
        updated_table = {'updated': '18/01/19', 'by': 'ddeboer', 'note': 'Initial', 'level': 0}
        V = {}
        for s in schema:
            V[s] = ''
        fin = open('generated_input_file.txt', 'w')
        found_refs = []
        idno = 1
        with open(sloppy_file, 'r') as f:
            for line in f:
                if line[0] == '#' or not len(line):  # Comment or blank
                    continue
                if line[0] == '=':  # Write the milestone
                    if len(V['description']):
                        tbl = 'records'
                        ref = V['description'].replace(' ', '').replace('\"', '').lower()[:30]
                        if ref in found_refs:
                            print("Duplicated ref:  {}".format(ref))
                            print(V)
                            sys.exit(1)
                        found_refs.append(ref)
                        for s in V.keys():
                            if s == 'refname' or not len(V[s]):  # Don't need redundant refname info
                                continue
                            fld = s
                            if s == 'value':
                                dt = V[s].split('/')
                                val = "{:d}/{:02d}/{:02d}".format(int(dt[2]), int(dt[0]), int(dt[1]))
                            else:
                                val = V[s]
                            fin.write("{} | {} | {} | {}\n".format(tbl, ref, fld, val))
                        if tbl == 'records':
                            fin.write("{} | {} | {} | {}\n".format(tbl, ref, 'id', idno))
                            idno += 1
                        tbl = 'updated'
                        for u in updated_table.keys():
                            fld = u
                            val = updated_table[u]
                            fin.write("{} | {} | {} | {}\n".format(tbl, ref, fld, val))
                    else:
                        print("Need a description to use it.")
                    # Reset desired values
                    for s in V.keys():
                        if s not in persist:
                            V[s] = ''
                    continue
                if ':' not in line:
                    print('Need parsing symbol :  ', line)
                    continue
                key, tok = [x.strip() for x in line.split(':')]
                if key not in schema:
                    print("{} not allowed.")
                    continue
                if key == 'dtype':
                    fin.write("{} | {} | {} | {}\n".format('types', tok, 'description', tok))
                V[key] = tok


ap = argparse.ArgumentParser()
ap.add_argument('dbtype', help="Name of database type (e.g. milestone).")
ap.add_argument('-i', 'input-file', dest='input_file', help="Name of text input file to insert.", default=None)
ap.add_argument('--sloppy', help="Start with the sloppy file.", action='store_true')
args = ap.parse_args()

db = Database(args.dbtype)
dbfull = db.get_dbfile()
if not os.path.exists(dbfull):
    db.create_db()
if args.input_file:
    if args.sloppy:
        db.generate_input_file(args.input_file)
        args.input_file = 'generated_input_file.txt'
    db.insert(args.input_file)
