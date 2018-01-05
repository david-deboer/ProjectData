from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import Data_class
# import Arch_class
# import Cost_class

mi = Data_class.Data('milestone')
mi.readData()
ta = Data_class.Data('task', verbose=False)
ta.readData()
wb = Data_class.Data('wbs', verbose=False)
wb.concatDat([mi, ta])
if False:
    rs = Data_class.Data('reqspec')
    rs.readData()
    print('\treqspec array rs')
    ri = Data_class.Data('risk')
    ri.readData()
    print('\trisk array ri')
    ic = Data_class.Data('interface')
    ic.readData()
    print('\tinterface array ic')
    ar = Arch_class.Data(verbosity=False)
    ar.readData()
    print('\tArchitecture array ar')
    co = Cost_class.Cost()
    co.getCost()
    co.getBudget()
    print('\tCost array co')

print("""Read in:
    mi : milestones
    ta : tasks
    wb = mi+ta: wbs""")
if False:
    print(""")
    rs : reqspecs
    ri : risk
    ic : interfaces
    ar : architecture
    co : cost""")
