#! /usr/bin/env python

import argparse

o = argparse.ArgumentParser()
o.add_argument('dtype',help='allowed data types are milestone, reqspec, interface, risk, architecture (need only first two letters)')
o.add_argument('new',help='new value')
o.add_argument('old',help='old value')
args = o.parse_args()

import Data_class

dtype = args.dtype[0:2].lower()
dtypeDict = {'mi':'milestone','re':'reqspec','in':'interface','ri':'risk','ar':'architecture'}
d = Data_class.Data(dtypeDict[dtype])
print
print '----------------Changing-----------------------'
d.changeName(args.old,args.new)
print

