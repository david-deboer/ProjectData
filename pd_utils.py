import os


def get_db_json(dbjson='databases.json'):
    import json
    with open(dbjson, 'r') as f:
        x = json.load(f)
    return x


def searchfield(value, infield, match):
    foundMatch = False
    if type(infield) == list:
        foundMatch = searchlist(value, infield, match)
    elif type(infield) == str or type(infield) == unicode and type(value) == str:
        value = value.strip()
        infield = infield.strip()
        if match == 'weak':
            foundMatch = value.lower() in infield.lower()
        elif match == 'moderate':
            foundMatch = value in infield
        elif match == 'strong':
            foundMatch = value.lower() == infield.lower()
        elif match == 'verystrong':
            foundMatch = value == infield
        else:  # default is weak
            foundMatch = value.lower() in infield.lower()
    else:
        foundMatch = value == infield
    return foundMatch


def searchlist(value, inlist, match):
    foundMatch = False
    for v in inlist:
        if type(v) == list:
            foundMatch = searchlist(value, v, match)
        else:
            foundMatch = searchfield(value, v, match)
    return foundMatch


def check_handle(handle):
    badHandle = not handle.isalpha()
    if badHandle:
        print("Note that tex can't have any digits or non-alpha characters")
        useHandle = raw_input('Please try a new handle:  ')
        checkHandle(useHandle)
    else:
        useHandle = handle
    return useHandle


def make_handle(refname):
    if refname.isalpha():
        return refname
    r = {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six',
         '7': 'seven', '8': 'eight', '9': 'nine', '0': 'zero',
         '-': 'dash', ':': '', '.': 'dot', ',': 'comma', '_': 'underscore'}
    handle = ''
    for c in refname:
        if c in r.keys():
            handle += r[c]
        elif not c.isalpha():
            handle += 'X'
        else:
            handle += c
    handle = check_handle(handle)
    return handle


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


def listify(X):
    if X is None:
        return None
    if isinstance(X, (str, unicode)) and ',' in X:
        return X.split(',')
    if isinstance(X, list):
        return X
    return [X]


def stringify(X):
    if X is None:
        return None
    if isinstance(X, str):
        return X
    if isinstance(X, list):
        return ','.join(X)
    return str(X)
