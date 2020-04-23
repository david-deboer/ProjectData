"""Sqlite base class."""
import sqlite3
from argparse import Namespace
from . import pysqls_util as utils


class DB:
    """Base class."""

    def __init__(self, dbfile):
        """Initialize and setup."""
        self.db = sqlite3.connect(dbfile)
        self.qdb = self.db.cursor()
        self.flag_append_entry = False
        self.get_db_map()

    def close(self):
        """Close db connection."""
        self.db.close()

    def append_entry(self, table, entry_to_update, **new_values):
        """
        Append the values to the already existing entry.

        Parameters
        ----------
        table : str
            Table name
        entry_to_update : int, Namespace, dict
            If int/Namespace, finds/uses associated Namespace and uses the primary_key
            If dict, uses that dict
        """
        self.flag_append_entry = True
        self.update_entry(table=table, entry_to_update=entry_to_update, **new_values)
        self.flag_append_entry = False

    def update_entry(self, table, entry_to_update, **new_values):
        """
        Update the specified table and entry(ies) with kwargs.

        Parameters
        ----------
        table : str
            Table name
        entry_to_update : int, Namespace, dict
            If int/Namespace, finds/uses associated Namespace and uses the primary_key
            If dict, uses that dict
        """
        if isinstance(entry_to_update, int):
            entry_to_update = self.mk_entry_ns(table, entry_to_update)
        if isinstance(entry_to_update, dict):
            where_str = utils.get_where(**entry_to_update)
        else:
            where_str = utils.get_where(**self.mk_pk(table, entry_to_update))
        if self.flag_append_entry:
            self.read_table(table, **self.mk_pk(table, entry_to_update))
            for col, val in new_values.items():
                to_change = getattr(getattr(self, table), col)
                if not len(to_change) or to_change[0] is None or val in to_change:
                    continue
                to_change.append(val)
                new_values[col] = ','.join(to_change)
        for col, val in new_values.items():
            val_ent = "{}".format(val)
            if val is None:
                val_ent = 'null'
            else:
                val_ent = '"{}"'.format(val)
            cmd = 'UPDATE {} SET {} = {} {}'.format(table, col, val_ent, where_str)
            self.qdb.execute(cmd)
        self.db.commit()

    def add_entry(self, table, cols_to_add, rows_to_add=None):
        """
        Add the entry to the database.

        Parameters
        ----------
        table : str
            Name of table
        cols_to_add : Namespace or dictionary of columns/values to add
            Entries to add.  Either of value_lists or values
        rows_to_add : None, int or list-of-ints
            If the entries are lists, only add these rows.  None adds all.
        """
        if table not in self.tables.keys():
            print("{} not found".format(table))
            return
        if isinstance(rows_to_add, int):
            rows_to_add = [rows_to_add]

        valid_col = {}
        data_to_add = {}
        for col, pos in self.tables[table].cols.items():
            if isinstance(cols_to_add, dict):
                try:
                    data = cols_to_add[col]
                except KeyError:
                    continue
            else:
                try:
                    data = getattr(cols_to_add, col)
                except AttributeError:
                    continue
            valid_col[col] = pos
            data_to_add[col] = []
            if isinstance(data, list):
                for i, row in enumerate(data):
                    if rows_to_add is None or i in rows_to_add:
                        data_to_add[col].append(row)
            else:
                data_to_add[col].append(data)
        if not valid_col:
            print("No valid columns to add to {}".format(table))
            return
        scol = sorted(valid_col.keys(), key=valid_col.get)
        scc = ','.join(scol)
        entries_added = 0
        for entry in range(len(data_to_add[scol[0]])):
            db_entry = []
            for col in scol:
                db_entry.append(data_to_add[col][entry])
            qm = ','.join(['?'] * len(db_entry))
            cmd = "INSERT INTO {}({}) VALUES ({})".format(table, scc, qm)
            try:
                self.qdb.execute(cmd, db_entry)
                entries_added += 1
            except sqlite3.IntegrityError:
                print('{} not allowed:  {}'.format(cmd, db_entry))
        self.db.commit()
        if not entries_added:
            print("No new entries in {}".format(table))
        elif entries_added == 1:
            print("New entry in {}".format(entry, table))
        else:
            print("{} new entries in {}".format(entry, table))

    def read_table(self, table, order_by=None, **where):
        """
        Make self.<table>.<field>[].

        Parameters
        ----------
        table : str
            Name of table.  Must be in schema
        order_by : str/None
            If str, the returned table will be ordered by that field.
        **kwargs : <field> = <value>
            Will find where <field> = <value>, may use '%'
        """
        if table not in self.tables.keys():
            print("{} not found".format(table))
            return
        setattr(self, table, Namespace())
        for col in self.tables[table].cols.keys():
            setattr(getattr(self, table), col, [])

        where = utils.get_where(**where)
        order = utils.get_order(order_by)
        cmd = 'SELECT * FROM {}{}{}'.format(table, where, order)
        self.qdb.execute(cmd)
        for rec in self.qdb.fetchall():
            for col, val in self.tables[table].cols.items():
                getattr(getattr(self, table), col).append(rec[val])

    def cast_values(self, table, **values_to_cast):
        """Cast table values to database type."""
        return_values = []
        for col, value in values_to_cast.items():
            entry_type = self.tables[table].type[col]
            if value is None:
                return_values.append(None)
            elif isinstance(value, str) and not len(value):
                return_values.append(None)
            elif entry_type == 'INTEGER':
                return_values.append(int(value))
            elif entry_type == 'TEXT':
                return_values.append(str(value))
            elif entry_type == 'NUMERIC' or entry_type == 'REAL':
                return_values.append(float(value))
            else:
                return_values.append(value)
        if len(return_values) == 1:
            return return_values[0]
        return return_values

    def mk_entry_ns(self, table, table_data):
        """
        Make a Namespace of one entry from the table_data.

        Parameters
        ----------
        table : str
            Name of table.
        table_data : dictionary, Namespace, or int
            If int, it will use that entry of the current table.
        """
        if table not in self.tables.keys():
            print("{} not found".format(table))
            return None

        ns = Namespace()
        for col in self.tables[table].cols.keys():
            if isinstance(table_data, int):
                v = getattr(getattr(self, table), col)[table_data]
            elif isinstance(table_data, dict):
                try:
                    v = table_data[col]
                except KeyError:
                    v = None
            else:
                try:
                    v = getattr(table_data, col)
                except AttributeError:
                    v = None
            setattr(ns, col, v)
        return ns

    def mk_pk(self, table, entry, return_as='dict'):
        """Make primary key dictionary from entry in table."""
        pkd = {}
        pkot = []
        if isinstance(entry, int):
            entry = self.mk_entry_ns(table, entry)
        for pk_i in self.tables[table].pk:
            this_entry = getattr(entry, pk_i)
            pkd[pk_i] = this_entry
            pkot.append(this_entry)
        pkot = tuple(pkot)
        if return_as == 'dict':
            return pkd
        return pkot

    def get_db_map(self):
        """Get the database PRAGMA information for tables."""
        info_n = Namespace(index=0, name=1, type=2, nn=3, unk=4, pk=5)
        self.tables = {}
        self.qdb.execute('SELECT name from sqlite_master where type="table"')
        qtbl = self.qdb.fetchall()
        for tbl in qtbl:
            table = tbl[0]
            self.tables[table] = Namespace(cols={}, type={}, numcol=0, pk=[], notnul=[])
            self.qdb.execute("PRAGMA table_info({})".format(table))
            for data in self.qdb.fetchall():
                self.tables[table].numcol += 1
                self.tables[table].cols[data[info_n.name]] = data[info_n.index]
                self.tables[table].type[data[info_n.name]] = data[info_n.type]
                if data[info_n.nn]:
                    self.tables[table].notnul.append(data[info_n.name])
                if data[info_n.pk]:
                    self.tables[table].pk.append(data[info_n.name])

    def show_pragma(self, tables=None):
        if tables is None:
            tables = list(self.tables.keys())
        elif isinstance(tables, str):
            tables = tables.split(',')
        for tbl in tables:
            cols = {}
            maxnm = 0
            for _t, _ord in self.tables[tbl].cols.items():
                cols[_ord] = _t
                if len(_t) > maxnm:
                    maxnm = len(_t)
            cols_in_order = [cols[x] for x in sorted(list(cols.keys()))]
            print("Table name:  {}".format(tbl))
            print("\tColumns:")
            for _c in cols_in_order:
                print("\t\t{:{maxnm}s}   {}".format(_c, self.tables[tbl].type[_c], maxnm=maxnm))
            print("\tPrimary key:  {}".format(','.join(self.tables[tbl].pk)))
            print("\tNot null:  {}".format(','.join(self.tables[tbl].notnul)))
