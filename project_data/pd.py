"""Project Data overall load."""
from project_data import Data_class, pd_tools

# Shortcut for showing things not complete
undone = ['late', 'moved', 'none', 'unknown']
print('undone defined: ', undone)

available_db = sorted(Data_class.pd_utils.get_db_json('databases.json')[0].keys())
available_db = ['milestone']  # for now since I don't use any others
if 'architecture' in available_db:
    from project_data import Arch_class
if 'cost' in available_db:
    from project_data import Cost_class


class ProjectDataShortcut:
    def __init__(self, db):
        self.db = db

    def getref(self, desc, **kwargs):
        """Provides a call to getref for the usual case of looking for a description."""
        self.ref = self.db.getref(desc, **kwargs)

    def find(self, end_date, **kwargs):
        """Provides a call to the db find method."""
        self.db.find(end_date, **kwargs)

    def update(self, **kwargs):
        """Provides a call to the db update method."""
        self.db.update(self.ref, **kwargs)


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

pdshortcut = ProjectDataShortcut(mi)
print("\npd.ref() shortcut for pd.mi.getref() via ProjectDataShortcut")
ref = pdshortcut.getref
print("pd.find() shortcut for pd.mi.find() via ProjectDataShortcut with auto-ref")
find = pdshortcut.find
print("pd.update() shortcut for pd.mi.update() via ProjectDataShortcut")
update = pdshortcut.update

print("NSF-B")
x = pd_tools.generate_recurring('9/1/16', '12/31/21')
print("NSF-C")
x = pd_tools.generate_recurring('10/1/18', '12/31/21')
