operator_options = ['<', '>', '=']


def get_where(**kwargs):
    where = ''
    bwha = True
    for k, v in kwargs.items():
        andkpr = ' WHERE ' if bwha else ' AND '
        if v is None:
            continue
        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                pass
        if isinstance(v, str):
            vstr = '"{}"'.format(v)
        else:
            vstr = ' {}'.format(str(v))
        operator = ' = '
        if '%' in vstr:
            operator = ' LIKE '
        elif k[-1] in operator_options:
            new_op = k[-1]
            operator = ' {} '.format(new_op)
            k = k.replace(new_op, '')
        elif vstr[1] in operator_options:
            new_op = vstr[1]
            operator = ' {} '.format(new_op)
            vstr = vstr.replace(new_op, '')
        where += '{}{}{}{}'.format(andkpr, k, operator, vstr.strip())
        bwha = False
    return where


def get_order(order_by):
    order = ''
    if order_by is not None:
        order = ' ORDER BY {}'.format(order_by)
    return order
