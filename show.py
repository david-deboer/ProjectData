#! /usr/bin/env python

from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import argparse
import Arch_class
import Data_class

o = argparse.ArgumentParser()
o.add_argument('dbtype', help='allowed data types are milestone, reqspec, interface, risk, architecture (need only first two letters)')
o.add_argument('-v', '--view', help='what record types to see in listing', default='all')
o.add_argument('-s', '--howsort', help='what entryMap field to use to sort', default='value')
args = o.parse_args()


dbtype = args.dbtype[0:2].lower()
dtypeDict = {'mi': 'milestone', 're': 'reqspec', 'in': 'interface', 'ri': 'risk', 'ar': 'architecture'}

if dbtype == 'ar':
    print('Architecture')
    d = Arch_class.Data()
else:
    d = Data_class.Data(dtypeDict[dbtype])
print('----------------Reading in--------------------')
d.readData()
print('\n----------------Listing-----------------------\n')
d.show(howsort=args.howsort, requested_dtype=args.view)
