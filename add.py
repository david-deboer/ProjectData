#! /usr/bin/env python

import argparse

o = argparse.ArgumentParser()
o.add_argument('name', help='name of addition')
o.add_argument('as', help='gratuitous as')
o.add_argument('dbtype', help='allowed data types are milestone, reqspec, risk, interface, task')
o.add_argument('-s', '--show', help='show entries (use defaults)', action='store_true')
args = o.parse_args()
dbtype = args.dbtype[0:2].lower()
dbtypeDict = {'mi':'milestone','re':'reqspec','in':'interface','ri':'risk'}

import Data_class
d = Data_class.Data(dbtypeDict[dbtype])

d.update(args.name)
if args.show:
    d.show()
