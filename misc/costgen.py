#! /usr/bin/env python
import sys, os.path
#sys.path.append('../scripts')
import utils
pbwd = utils.getBase('ProjectBook')
import shutil

import Cost_class

c = Cost_class.Cost()
c.getCost()
c.getBudget()
c.writeTex()

origFile = os.path.join(pbwd,'Costing/cost_pygen.tex')
copyTo = os.path.join(pbwd,'Project/cost_pygen.tex')
shutil.copyfile(origFile,copyTo)

#sys.path.append('graphics')
#import hexsheet

origFile = os.path.join(pbwd,'Costing/graphics/cost_by_n.png')
copyTo = os.path.join(pbwd,'Project/graphics/cost_by_n.png')
shutil.copyfile(origFile,copyTo)

