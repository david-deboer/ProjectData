import sys
import code_path
base_code_path = code_path.get('ProjectData')
sys.path.append(base_code_path)
import Data_class
#import Arch_class
#import Cost_class

mi = Data_class.Data('milestone')
mi.readData()
print '\tmilestone array mi'
NotOnlyMilestones = False
if NotOnlyMilestones:
    ta = Data_class.Data('task')
    ta.readData()
    print '\ttask array ta'
    wb = Data_class.Data('wbs')
    wb.concatDat([mi, ta])
    print '\twbs array wb'
    rs = Data_class.Data('reqspec')
    rs.readData()
    print '\treqspec array rs'
    ri = Data_class.Data('risk')
    ri.readData()
    print '\trisk array ri'
    ic = Data_class.Data('interface')
    ic.readData()
    print '\tinterface array ic'
    ar = Arch_class.Data(verbosity=False)
    ar.readData()
    print '\tArchitecture array ar'
    co = Cost_class.Cost()
    co.getCost()
    co.getBudget()
    print '\tCost array co'


def getlist(filename):
    try:
        fp = open(filename, 'r')
    except IOError:
        print filename + "doesn't exist"
        return 0

    lines = fp.readlines()
    names = []
    count = 0
    for line in lines:
        count += 1
        names.append(line.split('|')[0].strip())
    fp.close()
    return names


def writelist(filename, names):
    fp = open(filename, 'w')
    count = 0
    for n in names:
        count += 1
        s = n + '\n'
        fp.write(s)
    fp.close()
    return count


def findall(db, field, names=None):
    if names is None:
        names = db.data.keys()
    for v in names:
        if len(db.data[v][field]) > 0:
            print v, db.data[v][field]


name = 0
handle = 1
value = 2
description = 3
reqspecTrace = 4
componentTrace = 5
milestoneTrace = 6
riskTrace = 7
taskTrace = 8
dtype = 9  # 'type' in entryMap
owners = 10
updated = 11
notes = 12
dbid = 13  # 'id' in entryMap
status = 14

print """Read in:
	mi : milestones
    """
if NotOnlyMilestones:
    print """
	ta : tasks
	mi+ta ==> wb: wbs
	rs : reqspecs
	ri : risk
	ic : interfaces
	ar : architecture
	co : cost"""
