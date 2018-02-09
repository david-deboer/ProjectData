from __future__ import absolute_import, division, print_function
import os
try:
    import code_path
    base_code_path = code_path.set('ProjectData')
except ImportError:
    import sys
    base_code_path = raw_input('Full path to ProjectData code:  ')
    if os.path.exists(os.path.joing(base_code_path, 'Data_class.py')):
        sys.path.append(base_code_path)
import Data_class

available_db = sorted(Data_class.pd_utils.get_db_json('databases.json').keys())
if 'architecture' in available_db:
    import Arch_class
if 'cost' in available_db:
    import Cost_class

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

cwd = os.getcwd().lower()
if 'hera' in cwd:
    project_name = 'HERA'
elif 'breakthroughlisten' in cwd:
    project_name = 'BreakthroughListen'
print("\nSetting defaults for {}".format(project_name))

if project_name.lower()[0] == 'h':
    mi.set_state(description_length=65)
    mi.set_state(default_find_dtype=['nsfB', 'internal'])
elif project_name.lower()[0] == 'b':
    mi.set_state(description_length=65)
    mi.set_state(gantt_label_prefix='other')
    mi.set_state(default_find_dtype=['T1', 'T2'])
