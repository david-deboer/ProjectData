from __future__ import absolute_import, print_function
import os
import pd_utils


def get_level(line, key=False):
    if not key:
        ctr = 1
        for c in line:
            if c == '\t':
                ctr += 1
            else:
                return ctr
    else:
        return len(line.split('.'))


def parent(p):
    return increment(p, truncate=True, _off=0)


def increment(p, truncate=True, _off=1):
    spar = p.split('.')
    if truncate:
        ioff = 2
        if len(spar) == 2:
            return str(int(spar[0]) + _off)
    else:
        ioff = 1
    tai = spar[0]
    for i in range(1, len(spar) - (ioff - 1)):
        if i == len(spar) - ioff:
            s = '.' + str(int(spar[-1 * ioff]) + _off)
        else:
            s = '.' + spar[i]
        tai += s
    return tai


class System:
    def __init__(self, line):
        self.name = line

    def show(self, k, raw=False):
        level = get_level(k, key=True)
        print((level - 1) * '\t', end='')
        pad = level * 2
        print('{:{spad}s} {}'.format(k, self.name, spad=pad))


class Component:
    def __init__(self, line):
        nso = line.split('@')[0].split(':')
        ns = nso[0].strip().split()
        self.name = ns[0]
        if len(ns) > 1:
            self.subdirectory = ns[1]
        else:
            self.subdirectory = self.name
        if len(nso) > 1:
            self.owner = nso[1].strip()
        else:
            self.owner = None
        qe = line.split('@')[1].split('$')
        self.qty = int(qe[0])
        if len(qe) > 1:
            costs = qe[1].split('+')
            self.each = 0.0
            for c in costs:
                self.each += float(c)
        else:
            self.each = None

    def show(self, k, raw=False):
        level = get_level(k, key=True)
        print((level - 1) * '\t', end='')
        if raw:
            print(self.name, self.owner, self.qty, self.each)
        else:
            tot = self.qty * self.each
            cost = '{:3d} at ${:.0f} = ${:.0f}'.format(self.qty, self.each, tot)
            pad = level * 2
            print('{:{spad}s} {:15s} {:12s} {:15s}'.format(k, self.name, self.owner, cost, spad=pad))


class Data:
    db_json_file = 'databases.json'

    def __init__(self, verbosity=True):
        """This class reads in the architecture data file and does
           various functions to pull out pieces etc
           All dictionary keys are lowercase"""
        self.dbtype = 'architecture'
        self.dbTypes = pd_utils.get_db_json(self.db_json_file)
        self.verbosity = verbosity
        self.path = self.dbTypes[self.dbtype]['subdirectory']
        self.archFile = os.path.join(self.path, self.dbTypes[self.dbtype]['dbfilename'])

    def readData(self, verbosity=None):
        """This reads in the file and sets the following:
            list of strings
               self.clist = components [[wbs,name],[wbs,name],...]
               self.slist = systems [[wbs,name],[wbs,name],...]
               self.comments = comment lines in file
            dictionaries
               self.comp/self.sys (via self._setDict)
               self.ccross/self.scross (via self._setDict)
        """
        if verbosity is None:
            verbosity = self.verbosity
        fp = open(self.archFile, 'r')
        self.previous = None
        self.components = {}
        self.clev_keys = []
        self.systems = {}
        self.slev_keys = []
        self.comments = []
        reading = None
        for line in fp:
            if line[0] == '#':
                self.comments.append(line)
                if line[:7] == '#%===>C':
                    self.previous = '1'
                    reading = 'component'
                elif line[:7] == '#%===>S':
                    self.previous = '1'
                    reading = 'system'
                continue
            if len(line) < 2:
                continue
            if reading:
                self.readElement(reading, line, verbosity)
        fp.close()
        self.rollup()

    def readElement(self, reading, line, verbosity):
        plev = len(self.previous.split('.'))
        clev = get_level(line)
        if clev < plev:
            current = increment(self.previous, truncate=True)
        elif clev == plev:
            current = increment(self.previous, truncate=False)
        else:
            current = self.previous + '.1'
        if reading == 'component':
            self.components[current] = Component(line.strip())
            self.clev_keys.append(current)
            self.previous = current
        elif reading == 'system':
            self.systems[current] = System(line.strip())
            self.slev_keys.append(current)
            self.previous = current

    def rollup(self):
        for ckey in self.clev_keys:
            if self.components[ckey].owner is None:
                self.components[ckey].owner = self.components[parent(ckey)].owner
            self.components[ckey].elements = []
            clev = get_level(ckey, True)
            for k in self.clev_keys:
                if k == ckey:
                    continue
                klev = get_level(k, True)
                if ckey == k[:len(ckey)] and klev == clev + 1:
                    self.components[ckey].elements.append(k)
        all_summed_up = False
        while not all_summed_up:
            all_summed_up = True
            for ckey in self.clev_keys:
                if len(self.components[ckey].elements):
                    r = 0.0
                    for k in self.components[ckey].elements:
                        if self.components[k].each is not None:
                            r += self.components[k].qty * self.components[k].each
                    if self.components[ckey].each is None or int(r) != int(self.components[ckey].each):
                        self.components[ckey].each = r
                        all_summed_up = False

    def showData(self, dtype='component', max_level=10):
        """
        Parameters:
        ------------
        max_level:  plot levels at and below (10 is effectively 'all')
        """
        d0 = dtype[0].lower()
        if d0 == 'c':
            klist = self.clev_keys
        elif d0 == 's':
            klist = self.slev_keys
        for k in klist:
            level = get_level(k, key=True)
            if level <= max_level:
                if d0 == 'c':
                    self.components[k].show(k, raw=False)
                elif d0 == 's':
                    self.systems[k].show(k)
        return

    def printComments(self):
        print('Comments for ' + self.archFile)
        for line in self.comments:
            print('\t' + line, end='')
