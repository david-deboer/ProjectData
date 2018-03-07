from __future__ import absolute_import, print_function
import os
import pd_utils


class Entry:
    name = ''
    subdirectory = ''
    qty = 0
    each = 0.0


class Data:
    db_json_file = 'databases.json'

    def __init__(self, verbosity=True):
        """This class reads in the architecture data file and does
           various functions to pull out pieces etc
           All dictionary keys are lowercase"""
        self.dbtype = 'architecture'
        self.dbTypes = pd_utils.get_db_json(self.db_json_file)
        print(self.dbTypes['architecture'])
        # self.dirName = dirName
        # self.path = os.path.join(pbwd, dirName)
        # self.archFile = os.path.join(self.path,'Architecture.dat')
        # self.outFile = os.path.join(self.path,'arch_pygen.tex')
        self.verbosity = verbosity
        self.path = self.dbTypes[self.dbtype]['subdirectory']
        self.archFile = os.path.join(self.path, self.dbTypes[self.dbtype]['dbfilename'])
        self.entryMap = {'level': 0, 'idnum': 1, 'components': 2, 'idpath': 3}

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
        # current ad hoc variable passes to make it work...
        self.prevlevel = 1
        self.cn = ''
        self.cc = ''
        self.tag = ''
        self.ctr = ''
        self.stars = []
        # ...
        self.entries = {}
        self.clist = []
        self.cctr = 0
        self.slist = []
        self.sctr = 0
        self.comments = []
        reading = 'component'
        for line in fp:
            if line[0] == '#':
                self.comments.append(line)
                if line[:7] == '#%===>C':
                    reading = 'component'
                elif line[:7] == '#%===>S':
                    reading = 'system'
                continue
            if len(line) < 2:
                continue
            self._readElement(reading, line, verbosity)
        self.comp, self.ccross = self._setDict(self.clist)
        self.sys, self.scross = self._setDict(self.slist)
        fp.close()
        print('\tComponent/system lists are:  self.clist, self.slist')
        print('\tDictionaries are: self.comp, self.ccross, self.sys, self.scross')

    def showData(self, howsort='value', handleSpace=25, descSpace=50, short=True):
        """the arguments are to make it consistent with showData for milestones/requirements/etc
        -- maybe I'll use them someday"""
        inLevs = True
        n = 1
        print('\nCOMPONENTS:')
        while inLevs:
            inLevs = self.getLevel(n, self.clist)
            print('----Level = ' + str(n) + '----')
            if inLevs:
                for g in inLevs:
                    print(g, end='  ')
                n += 1
                print()
            else:
                print('None')
# ###############CUT-AND-PASTE COMPONENTS INTO SYSTEM
        inLevs = True
        n = 1
        print('\nSYSTEMS:')
        while inLevs:
            inLevs = self.getLevel(n, self.slist)
            print('----Level = ' + str(n) + '----')
            if inLevs:
                for g in inLevs:
                    print(g, end='  ')
                n += 1
                print()
            else:
                print('None')

    def _readElement(self, reading, line, verbosity):
        if '*' in line:
            sc = line.strip().strip('*').strip()
            if len(self.stars) > 0:
                self.stars.append(sc)
            else:
                self.stars = [sc]
            return
        else:
            if len(self.stars) > 0:
                if reading is 'system':
                    self.slist[self.sctr - 1][3] = self.stars
                elif reading is 'component':
                    self.clist[self.cctr - 1][3] = self.stars
                self.stars = []
        level = line.count('\t') + 1
        tab = (level - 1) * '\t'
        b = line.split(':')
        idnum = b[0].strip()
        identry = b[1].split()
        idname = identry[0].strip()

        if level == 1:
            self.tag = idname
            self.cn = self.tag
            self.ctr = idnum
            self.cc = self.ctr
        elif level > self.prevlevel:
            self.cn = self.cn + '/' + idname
            self.tag = self.cn
            self.cc = self.cc + '.' + idnum
            self.ctr = self.cc
        else:
            self.tag = self._newlowertag(self.tag, level, '/')
            self.cn = self.tag + idname
            self.ctr = self._newlowertag(self.ctr, level, '.')
            self.cc = self.ctr + idnum
        self.prevlevel = level
        idpath = 'Architecture/'
        if len(identry) == 1:
            idpath = os.path.join(idpath, self.cn)
        elif len(identry) == 2:
            idpath = os.path.join(idpath, identry[1].strip())
        else:
            print('invalid entry:  ' + str(identry), end='')
            idpath = os.path.join(idpath, self.cn)
            print('  ==> set path to ' + idpath)
        if verbosity:
            print(reading + ' =\t' + self.cc + '\t' + self.cn + '  (' + idpath + ')')
        if reading is 'component':
            self.clist.append([self.cc, self.cn, idpath, []])
            self.cctr += 1
        elif reading is 'system':
            self.slist.append([self.cc, self.cn, idpath, []])
            self.sctr += 1

    def _newlowertag(self, tag, level, delim='/'):
        ts = tag.split(delim)
        if len(ts) < level:
            print('Invalid tag/level')
            return tag
        nt = ''
        for i in range(level - 1):
            nt += ts[i] + delim
        return nt

    def printComments(self):
        print('Comments for ' + self.archFile)
        for line in self.comments:
            print('\t' + line, end='')

    def _setDict(self, elist):
        """This takes the component/system list and puts it into a dictionary.
           The key is the full path name, the first value is the wbs number
               then subsequent terms are the path components
           All keys are lowercase."""
        ed = {}
        for e in elist:
            k = e[1].lower()
            data = e[1].split('/')
            level = len(data)
            ed[k] = [level]
            ed[k].append(e[0])
            ccc = []
            for d in data:
                ccc.append(d)
            ed[k].append(ccc)
            ed[k].append(e[2])
            ed[k].append(e[3])
        cross = {}
        for k in ed.keys():
            shorthand = k.split('/')[-1].lower()
            if shorthand not in cross.keys():
                cross[shorthand] = [k]          # ##String version
                # cross[shorthand] = [ed[k]]     # ##List version
            else:
                cross[shorthand].append(k)      # ##String version
                # cross[shorthand].append(ed[k]) ###List version
        return ed, cross

    def getLevel(self, n, el):
        """This returns a list of strings containing the components at level N.
              Could loop over a, b or c ==> chose c and split on '.'
              It converts to lowercase for keying"""
        self.level = []
        for e in el:
            level = len(e[0].split('.'))
            if level == n:
                self.level.append(e[1])
        if len(self.level) == 0:
            self.level = False
        return self.level

    def _getTexRow(self, level1, level2, level3):
        l2 = ''
        for l in level2:
            l2 += (l + ', ')
        l2 = l2.strip().strip(',')
        l3 = ''
        for l in level3:
            l3 += (l + ', ')
        l3 = l3.strip().strip(',')
        texline = '%s & %s & %s\\\\ \\hline\n' % (level1, l2, l3)
        return texline

    def writeTex(self, outFile=None):
        if outFile is None:
            outFile = self.outFile

        fp = open(outFile, 'w')
        texline = '\\begin{table}[ht]\n\caption{Components}\n   \\begin{tabular}{| p{1in} | p{2.75in} | p{2.0in}|}\n\\hline\n'
        fp.write(texline)
        texline = '\\textbf{Level 1}  & \\textbf{Level 2}   &  \\textbf{Level 3+} \\\\ \\hline\n'
        fp.write(texline)
        level1 = ''
        level2 = []
        level3 = []
        firstOne = True
        for comp in self.clist:
            data = comp[1].split('/')
            level = len(data)
            if level == 1:
                if not firstOne:
                    texline = self._getTexRow(level1, level2, level3)
                    fp.write(texline)
                else:
                    firstOne = False
                level1 = data[-1]
                level2 = []
                level3 = []
            elif level == 2:
                level2.append(data[-1])
            elif level > 2:
                level3.append(comp[1])
        texline = self._getTexRow(level1, level2, level3)
        fp.write(texline)
        texline = '   \\end{tabular}\n\\label{componentTable}\n\\end{table}\n'
        fp.write(texline)
# ####################JUST CUT-AND-PASTE COMPONENT FOR SYSTEM...(changing names appropriately)
        texline = '\\begin{table}[ht]\n\caption{Systems}\n   \\begin{tabular}{| p{1in} | p{2.75in} | p{2.0in}|}\n\\hline\n'
        fp.write(texline)
        texline = '\\textbf{Level 1}  & \\textbf{Level 2}   &  \\textbf{Level 3+} \\\\ \\hline\n'
        fp.write(texline)
        level1 = ''
        level2 = []
        level3 = []
        firstOne = True
        for c in self.slist:
            data = c[1].split('/')
            level = len(data)
            if level == 1:
                if not firstOne:
                    texline = self._getTexRow(level1,level2,level3)
                    fp.write(texline)
                else:
                    firstOne=False
                level1 = data[-1]
                level2 = []
                level3 = []
            elif level == 2:
                level2.append(data[-1])
            elif level > 2:
                level3.append(c[1])
        texline = self._getTexRow(level1,level2,level3)
        fp.write(texline)
        texline = '   \\end{tabular}\n\\label{systemTable}\n\\end{table}\n'
        fp.write(texline)

#####################OLD SYSTEM OUTPUT
##        texline = '\\vspace{0.25in}\n\\noindent\n'
##        texline+= 'The Systems are:  \\begin{itemize}\n'
##        fp.write(texline)
##        for sy in self.slist:
##            texline = '\\item '+sy[1]
##            sk = sy[1].lower()
##            if len(self.sys[sk][self.entryMap['components']]) > 1:
##                subs='\t('
##                for ss in self.sys[sk][self.entryMap['components']]:
##                    if ss!=sys:
##                        subs+=(ss+', ')
##                subs=subs.rstrip().rstrip(',')
##                subs+=')'
##                texline+=subs
##            texline+='\n'
##            fp.write(texline)
##        texline = '\\end{itemize}\n'
##        fp.write(texline)

        fp.close()
