#! /usr/bin/env python

import argparse

o = argparse.ArgumentParser()
o.add_argument('dtype',help='allowed data types are milestone, reqspec, interface, risk, architecture (need only first two letters)')
o.add_argument('-v','--view',help='what record types to see in listing',default='all')
o.add_argument('-s','--howsort',help='what entryMap field to use to sort',default='value')
args = o.parse_args()

import Arch_class
import Data_class

dtype = args.dtype[0:2].lower()
dtypeDict = {'mi':'milestone','re':'reqspec','in':'interface','ri':'risk','ar':'architecture'}

if dtype == 'ar':
    print 'Architecture'
    d = Arch_class.Data()
else:
    d = Data_class.Data(dtypeDict[dtype])
print '----------------Reading in--------------------'
d.readData()
print
print '----------------Listing-----------------------'
d.showData(args.view,args.howsort)
print

