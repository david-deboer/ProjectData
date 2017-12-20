from __future__ import absolute_import, division, print_function
import code_path
base_code_path = code_path.set('ProjectData')
import Data_class

mi = Data_class.Data('milestone')
mi.readData()
print('\tmilestone class:  mi')


def hera(v):
    mi.set_state_var(description_length=65)
    mi.set_state_var(show_color_bar=False)
    mi.set_state_var(show_cdf=False)
    mi.find(v, only_late=True, dtype='nsfB')
    plt.show()


def gref(desc):
    """
    Shortcut function to get and show a record from its description.
    """
    k = mi.getref(desc)
    mi.show(k)
    return k
