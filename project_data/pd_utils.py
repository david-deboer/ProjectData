import datetime


def get_time(timestr):
    if timestr is None:
        return None
    timestr = timestr.strip()
    try:
        timeval = datetime.datetime.strptime(timestr, '%y/%m/%d')
    except ValueError:
        try:
            timeval = datetime.datetime.strptime(timestr, '%Y/%m/%d')
        except ValueError:
            print('Incorrect time:  ', timestr)
            timeval = None
    return timeval


def get_db_json(dbjson='databases.json', consolidate=['ganttable', 'traceable']):
    import json
    with open(dbjson, 'r') as f:
        x = json.load(f)
    databases = x['databases']
    for dbcon in consolidate:
        databases[dbcon] = []
        for chkdb, able in databases.items():
            if isinstance(able, dict) and able[dbcon] == 'True':
                databases[dbcon].append(chkdb)
    return databases, x['ganttable_status']


def searchfield(value, entry_val, match):
    foundMatch = False
    if type(entry_val) == list:
        foundMatch = searchlist(value, entry_val, match)
    elif isinstance(entry_val, str) and isinstance(value, str):
        value = value.strip()
        entry_val = entry_val.strip()
        if match == 'weak':
            foundMatch = value.lower() in entry_val.lower()
        elif match == 'moderate':
            foundMatch = value in entry_val
        elif match == 'strong':
            foundMatch = value.lower() == entry_val.lower()
        elif match == 'verystrong':
            foundMatch = value == entry_val
        else:  # default is weak
            foundMatch = value.lower() in entry_val.lower()
    else:
        foundMatch = value == entry_val
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
        useHandle = input('Please try a new handle:  ')
        check_handle(useHandle)
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


def make_refname(description, length=30):
    ref = description.replace(' ', '').replace('\"', '').lower()[:length]
    return ref


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
            print('sortByValue key [ ' + str(nk) + ' ] already exists, overwriting...')
        ind[nk] = v
    sind = ind.keys()
    sind.sort()
    sk = []
    for s in sind:
        sk.append(ind[s])
    return sk


def quarter_symbol(q, y):
    if q % 4 == 0 or q % 4 == 3:
        py_sym = '-'
    else:
        py_sym = ' '
    return y * py_sym + str(y)


def get_qtr_date(q, start):
    dy = start.day
    mn = start.month
    yr = start.year
    d, m, y = (int(dy), int((mn + q * 3) % 12), int(yr + int((mn + q * 3) / 12)))
    if not m:
        m = 12
        y -= 1
    return datetime.datetime(y, m, d)


def listify(X):
    if X is None:
        return None
    if isinstance(X, str) and ',' in X:
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
