import os


def money(v, a=2, d='$'):
    """I thought about using e.g. pyMoney etc, but overkill and others
       would have to download the package...
          v is the amount
          a is the accuracy (but only no decimal and two-decimal options for display)
          d is the currency sign"""

    r = round(v, a)

    if a > 0:
        g = str("{:s}{:,.2f}".format(d, r))
    else:
        g = str("{:s}{:,.0f}".format(d, r))
    return g


def sortByValue(inDict):
    ind = {}
    for i, v in enumerate(inDict):
        nk = inDict[v]
        if nk in ind.keys():
            print 'sortByValue key [ ' + str(nk) + ' ] already exists, overwriting...'
        ind[nk] = v
    sind = ind.keys()
    sind.sort()
    sk = []
    for s in sind:
        sk.append(ind[s])
    return sk
