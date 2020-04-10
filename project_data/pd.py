"""Project Data overall load."""
from project_data import Data_class

# Shortcut for showing things not complete
undone = ['late', 'moved', 'none', 'unknown']
print('undone defined: ', undone)

available_db = sorted(Data_class.pd_utils.get_db_json('databases.json')[0].keys())
available_db = ['milestone']  # for now since I don't use any others
if 'architecture' in available_db:
    from project_data import Arch_class
if 'cost' in available_db:
    from project_data import Cost_class


print("Read in:")
for db in available_db:
    if db == 'milestone':
        mi = Data_class.Data('milestone')
        mi.read_data()
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
        rs = Data_class.Data('reqspec', verbose=False)
        rs.readData()
        print("rs : reqspec")
    elif db == 'risk':
        ri = Data_class.Data('risk', verbose=False)
        ri.readData()
        print("ri : risk")
    elif db == 'interface':
        ic = Data_class.Data('interface', verbose=False)
        ic.readData()
        print("ic : interface")
    elif db == 'architecture':
        ar = Arch_class.Data(verbosity=False)
        ar.readData()
        print("ar : Architecture")
    elif db == 'cost':
        co = Cost_class.Cost(verbosity=False)
        co.getCost()
        co.getBudget()
        print("co : Cost")
