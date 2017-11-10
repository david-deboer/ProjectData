#! /usr/bin/env python

import WBS_class

wbs = WBS_class.WBS()
wbs.ganttMilestones(ignoreType=-1)
wbs.writeGantt()


