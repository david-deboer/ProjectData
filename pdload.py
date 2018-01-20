from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import Data_class
# import Arch_class
# import Cost_class

available_db = Data_class.pd_utils.get_db_json('databases.json').keys()
print ("Read in:")
for db in available_db:
    if db == 'milestone':
        mi = Data_class.Data('milestone')
        mi.readData()
        print("mi : milestone")
    elif db == 'task':
        ta = Data_class.Data('task', verbose=False)
        ta.readData()
        print("ta : task")
    elif db == 'wb':
        wb = Data_class.Data('wbs', verbose=False)
        wb.concatDat([mi, ta])
        print("wb : mi+ta=wbs")
    elif db == 'reqspec':
        rs = Data_class.Data('reqspec')
        rs.readData()
        print("rs : reqspec")
    elif db == 'risk':
        ri = Data_class.Data('risk')
        ri.readData()
        print("ri : risk")
    elif db == 'interface':
        ic = Data_class.Data('interface')
        ic.readData()
        print("ic : interface")
    elif db == 'architecture':
        ar = Arch_class.Data(verbosity=False)
        ar.readData()
        print("ar : Architecture")
    elif db == 'cost':
        co = Cost_class.Cost()
        co.getCost()
        co.getBudget()
        print("co : Cost")
