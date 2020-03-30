##import csv
##
##costfile = open('costing.csv','rb')
##
##cfreader = csv.reader(costfile)
##for row in cfreader:
##    print row

import xlrd
import os
import utils
import Arch_class

class Cost:
    def __init__(self,dirName='Costing'):
        """This reads in the costing data etc etc uses xlrd"""
        self.dirName = dirName
        self.path = os.path.join(pbwd,dirName)
        print 'Cost path = ',self.path

    def getCost(self,costfile='costing.xlsx'):
        """This reads in the costfile in the proper format
           It generates the following:
           list of doublet strings
               self.level = [[lev1a,lev1b,...],[lev2a,lev2b...]
            dictionary
               self.amt[lev] = float"""

        costfile = os.path.join(self.path,costfile)
        cost = xlrd.open_workbook(costfile)
        sheet = cost.sheet_by_name('Summary')

        inLevel = False
        level = [[],[]]
        amt = {}
        self.N = 0

        for r in range(sheet.nrows):
            r1v = sheet.cell_value(r,0)
            r2v = sheet.cell_value(r,1)
            r3v = sheet.cell_value(r,2)
            #print 'r1v,r2v,r3v',r1v,r2v,r3v
            if len(r1v)>0 and r1v[0]=='#':
                #print r1v
                continue
            elif len(r1v)>0 and r1v[0]=='@':
                self.N = r2v
                continue
            if len(r1v)>1:
                inLevel = True
                lev1 = r1v
                level[0].append(str(lev1))
                #for c in range(sheet.ncols):
                    #print str(sheet.cell_value(r,c))+'\t',
            elif inLevel and len(r2v)>1:
                level[1].append(str(lev1+'/'+r2v))
                k = str(lev1+'/'+r2v).lower()
                if type(r3v) != float:
                    r3v = 0.0
                amt[k] = r3v
            else:
                inLevel = False
            #print

        for lev1 in level[0]:
            k1 = lev1.lower()
            tot = 0.0
            for lev2 in level[1]:
                data = lev2.split('/')
                l1 = data[0].lower()
                if l1 == k1:
                    k2 = lev2.lower()
                    tot+=amt[k2]
            amt[k1] = tot
        self.level = level
        self.amt = amt

        self.grandTotal = 0.0
        for lev1 in level[0]:
            k1 = lev1.lower()
            self.grandTotal+=amt[k1]
        g = utils.money(self.grandTotal,0)
        #print '\tEquipment sub-total = ' + g
        print '\tScope = %.0f' % self.N

        return len(level[1])

    def getBudget(self,costfile='budget.xlsx',verbose=False):
        costfile = os.path.join(self.path,costfile)
        cost = xlrd.open_workbook(costfile)
        sheet = cost.sheet_by_name('Summary')
        self.expenses = {}
        self.inst = []
        blankcol = 2  # number of columns to ignore for money
        usedcols = 13 # number of columns really used (used to use sheet.ncols, but doodling in sheet broke it)
        usedrows = 6  # number of rows really used    (  "         sheet.nrows,   "  )
        for c in range(usedcols):
            inst = str(sheet.cell_value(0,c))
            if len(inst) > 1:
                self.inst.append(inst)
                self.expenses[inst] = []
        self.category = []
        for r in range(1,usedrows):
            self.category.append(str(sheet.cell_value(r,0)))
            for c in range(blankcol,usedcols):
                self.expenses[self.inst[c-blankcol]].append(float(sheet.cell_value(r,c)))
        if verbose:
            print 10*' ',
            for inst in self.inst:
                print '%11s  ' % (inst.center(11)),
            print
            for c,cat in enumerate(self.category):
                print '%-10s' % (cat),
                for inst in self.inst:
                    print '%11s  ' % (utils.money(self.expenses[inst][c],0)),
                print

    def writeTex(self, outFile=None, filt=True, outType='table'):
        """Writes the simple costing output tex file, to be used in other compiling files"""

        writeBoth = False
        if outFile==None:
            writeBoth=True
        if writeBoth:
            outFile='cost_pygen.tex'
        outType = outType[0:3].lower()

        if outFile == 'cost_pygen.tex':
            outFile = os.path.join(self.path,outFile)
            fp = open(outFile,'w')

            ###Scope and grand total
            texline = '\\noindent\n{\\bf Scope:}  %.0f antennas\n\\vspace{0.3in}\n\n' % (self.N)
            fp.write(texline)
            g = utils.money(self.grandTotal,0,'\$')
            texline = '\\noindent\n{\\bf Total:}  %s\n\\vspace{0.3in}\n\n' % (g)
            fp.write(texline)

            ###Table
            numCol = 3
            if outType=='tab':
                texline ='\\begin{table}[t]\n'
                texline+='\\centering\n'
                texline+='\\caption{System Cost Summary}\n'
                texline+='\\label{tab:budgetsummary}\n'
                texline+='\\begin{tabular}{| ' + numCol*'p{2in} | ' + '} \\hline\n'
                fp.write(texline)
            colCtr=0
            for lev1 in self.level[0]:
                colCtr+=1
                k1 = lev1.lower()
                g = utils.money(self.amt[k1],0,'\$')
                texline = '\\noindent\n\\textbf{%s:}  %s\n\\vspace{-0.1in}\n\\begin{itemize}[parsep=-2pt, itemsep=-3pt]\n' % (lev1,g)

                fp.write(texline)
                for lev2 in self.level[1]:
                    data = lev2.split('/')
                    l1 = data[0].lower()
                    if k1 == l1:
                        k2 = lev2.lower()
                        if filt and self.amt[k2]>0:
                            texline = '\\item %s:   %s\n' % (data[1],utils.money(self.amt[k2],0,'\$'))
                            fp.write(texline)
                texline = '\\vspace{-.1in}\n\\end{itemize}\n'
                if outType!='tab':
                    texline+='\\vspace{.3in}\n'
                fp.write(texline)
                if outType=='tab':
                    texline=''
                    if colCtr%numCol:
                        texline=' &\n '
                    else:
                        texline+='\\\\ \\hline\n'
                    fp.write(texline)
            if outType=='tab':
                texline='\\end{tabular}\n\\end{table}'
                fp.write(texline)

            if outType!='tab':
                texline = '\\begin{figure}[H]\n'
                texline+= '\\includegraphics[width=\\textwidth]{graphics/cost_by_n.png}\n'
                texline+= '\\caption{Cost as a function of N.}\n'
                texline+= '\\label{fig:costN}\n'
                texline+= '\\end{figure}\n'
                fp.write(texline)
            fp.close()
            if writeBoth:
                outFile='institutional_pygen.tex'

        if outFile == 'institutional_pygen.tex':
            outFile = os.path.join(self.path,outFile)
            fp = open(outFile,'w')
            texline = '\n\n\\begin{table}[h]\n'
            texline+='\\centering\n'
            texline+='\\caption{Total budget summary}\n'
            texline+='\\label{tab:expenses}\n'
            grid = '| p{0.5in} |'+(len(self.inst))*' p{.6in} | '
            texline+= '\\begin{tabular}{'+grid+'}\\hline\n'
            fp.write(texline)
            texline = '  k\\$  '
            for inst in self.inst:
                texline+= ' & \\textbf{%s}' % (inst[:6])
            texline+='\\\\\\hline\n'
            fp.write(texline)
            for c,cat in enumerate(self.category):
                texline = '\\textbf{%s}' % (cat[0:6])
                for inst in self.inst:
                    texline+= '& %11s  ' % (utils.money(self.expenses[inst][c]/1000.0,0,''))
                texline+='\\\\\\hline\n'
                fp.write(texline)
            texline ='\\end{tabular}\n'
            texline+='\\end{table}\n'
            fp.write(texline)
            fp.close()

        return 1

###Read Architecture and get level 1 and level 2 to compare...
