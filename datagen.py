#! /usr/bin/env python
import argparse
import Data_class

o = argparse.ArgumentParser()
o.add_argument('dbtype', help='allowed data types are milestone, reqspec, risk, interface')
o.add_argument('-n', '--nothing', help='currently a placeholder', action='store_false')
o.add_argument('-o', '--outType', help="output type:  'table','long','short'", default='table')
o.add_argument('-s', '--howsort', help="sortoption:  'key' or other entryMap", default='key')
o.add_argument('-c', '--cp_mv', help='cp or mv the files', default='mv')
args = o.parse_args()
dbtype = args.dbtype[0:2].lower()
dbtypeDict = {'mi': 'milestone', 're': 'reqspec', 'in': 'interface', 'ri': 'risk'}

d = Data_class.Data(dbtypeDict[dbtype])
print 'Generate ' + dbtypeDict[dbtype] + ' documentation'
d.readData()
d.writeLatexDefFile()
d.writeTex(args.outType, args.howsort)

print dbtypeDict[dbtype] + ' flowdown'
flowdown = [[1, 'components'], [1, 'systems'], [2, 'components'], [3, 'components']]
for fl in flowdown:
    d.splitOnComponents(splitLevel=fl[0], splitType=fl[1], ver=args.outType, cp_mv=args.cp_mv, verbosity=False, deleteEmpty=True)
