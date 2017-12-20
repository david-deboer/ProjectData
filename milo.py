from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import Data_class

print("Loading milestone class as 'mi'")
mi = Data_class.Data('milestone')
mi.readData()
print("\nmilo courtesy functions: 'gref', 'hera'")


def gref(v, search='description'):
    """
    Shortcut function to get and show a record from its description.
    """
    k = mi.getref(v, search)
    mi.show(k)
    return k


def hera(v):
    mi.set_state(description_length=65)
    mi.set_state(show_color_bar=False)
    mi.set_state(show_cdf=False)
    mi.find(v, only_late=True, dtype='nsfB')
