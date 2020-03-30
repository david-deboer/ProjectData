import Data_class
import datetime, os
import utils
import string
pbwd = utils.getBase('ProjectBook')

now = datetime.datetime.now()
def setXMLdate(dt,dateback='xml'):
    if type(dt) == type(now):
        xmldate = '%d-%02d-%02dT%02d:%02d:%02d' % (dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)
        dtdate = dt
    elif type(dt) == str:
        d = dt.split('/')
        year = d[0]
        if len(year)==2:
            year = '20'+year
        year = int(year)
        month = int(d[1])
        day = int(d[2])
        hour = 12
        minute = 0
        second = 0
        xmldate = '%d-%02d-%02dT%02d:%02d:%02d' % (year,month,day,hour,minute,second)
        dtdate = datetime.datetime(year,month,day,hour,minute,second)
    if dateback=='xml':
        dateback = xmldate
    else:
        dateback = dtdate
    return dateback

import Task_class
class WBS:
    def __init__(self,calendar='Project/wbs/calendar.xml',milestones='Project/wbs/milestone.tex',author='ddeboer'):
        """MSProject XML (see http://www2.esm.vt.edu/~jlesko/Project/DOCS/1033/PROJXML.HTM#saveAsXML)"""
        self.calendarFile = os.path.join(pbwd,calendar)
        self.milestoneFile = os.path.join(pbwd,milestones)
        self.wbs = {'schema':' ',
                    'Author':author,
                    'CreationDate':' ',
                    'ScheduleFromStart':1,
                    'StartDate':' ',
                    'FinishDate':' ',
                    'Calendars':'',
                    'Tasks':'',
                    'end':'</Project>'}                                              
        self.wbsFormat = ['Author','CreationDate','ScheduleFromStart','StartDate','FinishDate','Calendars','Tasks']                                               
        self.wbs['schema']='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Project xmlns="http://schemas.microsoft.com/project">\n'
        self.wbs['CreationDate'] = setXMLdate(now)
        self.wbs['StartDate'] = setXMLdate(now)            # can reset later
        self.wbs['FinishDate'] = setXMLdate('2015/12/31')  # can reset later
        self.tasks = []
        self.setCalendar()
        self.MSPtask = Task_class.MSProjectTask()
        self.MSPtask.UID = 0
        self.Project = []

    def setCalendar(self):
        cfp = open(self.calendarFile,'r')
        for line in cfp:
            self.wbs['Calendars']+=line
        cfp.close()

    def ganttMilestones(self,ignoreType=None):
        self.ms = Data_class.Data('milestone')
        self.ms.readData()
        for key in self.ms.entriesInOrder:
            self.setTask(self.ms.data[key],idkey=key)
        self.fullTaskSet(ignoreType=ignoreType)

    def setTask(self,event,idkey=None):
        ###Look at value to determine type
        date = event[self.ms.entryMap['value']].split('-')
        Start = setXMLdate(date[0].strip(),dateback='datetime')
        if len(date)==1:
            eventType = 'milestone'
        else:
            eventType = 'activity'
            Finish = setXMLdate(date[1].strip(),dateback='datetime')
            duration = Finish-Start
            self.MSPtask.Duration  = 'PT%.0fH0M0S' % (duration.days*8.0 + duration.seconds/3600.0)
            self.MSPtask.DurationType = 8
            
        self.MSPtask.UID+=1
        self.MSPtask.ID = self.MSPtask.UID
        self.MSPtask.Type = 1
        self.MSPtask.Active=1
        self.MSPtask.Manual=1
        self.MSPtask.IsNull=0
        self.MSPtask.Milestone=0
        indent1 = 2*'\t'
        indent2 = 3*'\t'
        self.MSPtask.CalendarUID=-1
        taskString = '%s<Task>\n' % (indent1)
        taskString+= '%s<UID>%d</UID>\n' % (indent2,self.MSPtask.UID)
        taskString+= '%s<ID>%d</ID>\n' % (indent2,self.MSPtask.ID)
        taskString+= '%s<Name>%s</Name>\n' % (indent2,event[self.ms.entryMap['description']])
        taskString+= '%s<Active>%d</Active>\n' % (indent2,self.MSPtask.Active)
        taskString+= '%s<Manual>%d</Manual>\n' % (indent2,self.MSPtask.Manual)
        taskString+= '%s<Type>%s</Type>\n' % (indent2,self.MSPtask.Type)
        taskString+= '%s<IsNull>%d</IsNull>\n' % (indent2,self.MSPtask.IsNull)
        taskString+= '%s<CreateDate>%s</CreateDate>\n' % (indent2,self.wbs['CreationDate'])
        taskString+= '%s<Start>%s</Start>\n' % (indent2,setXMLdate(Start))
        taskString+= '%s<ManualStart>%s</ManualStart>\n' % (indent2,setXMLdate(Start))
        taskString+= '%s<ConstraintDate>%s</ConstraintDate>\n' % (indent2,setXMLdate(Start))
        self.MSPtask.ConstraintType=2
        taskString+= '%s<ConstraintType>%d</ConstraintType>\n' % (indent2,self.MSPtask.ConstraintType)
        if eventType=='activity':
            taskString+='%s<Finish>%s</Finish>\n' % (indent2,setXMLdate(Finish))
            taskString+='%s<ManualFinish>%s</ManualFinish>\n' % (indent2,setXMLdate(Finish))
            taskString+='%s<Duration>%s</Duration>\n' % (indent2,self.MSPtask.Duration)
            taskString+='%s<ManualDuration>%s</ManualDuration>\n' % (indent2,self.MSPtask.Duration)
            taskString+='%s<DurationType>%d</DurationType>\n' % (indent2,self.MSPtask.DurationType)
        elif eventType=='milestone':
            self.MSPtask.Milestone=1
        taskString+= '%s<Milestone>%d</Milestone>\n' % (indent2,self.MSPtask.Milestone)

        taskString+= '%s<CalendarUID>%d</CalendarUID>\n' % (indent2,self.MSPtask.CalendarUID)
        if idkey:
            Notes = idkey+' [_'+str(event[self.ms.entryMap['type']])+'_]'+'  '+event[self.ms.entryMap['notes']].strip('\n')
            Notes.strip()
            taskString+= '%s<Notes>%s</Notes>\n' % (indent2,Notes)
        taskString+= '%s</Task>\n' % (indent1)
        self.tasks.append(taskString)

    def fullTaskSet(self,ignoreType=None):
        """This takes the list of tasks and assembles the wbs.  This allows resorting, ignoring etc"""
        if ignoreType is not None:
            if type(ignoreType)==int and ignoreType<0:
                ignoreType= None
            elif type(ignoreType) is not list:
                ignoreType = list(ignoreType)
            elif type(ignoreType) is str:
                print ignoreType+"  don't know what to do yet"
            else:
                print 'ignoreType unknown:  ',ignoreType
        for task in self.tasks:
            useTask = True
            if ignoreType is not None:
                if '</Notes>' in task:
                    chk = task.split('_')
                    try:
                        chkType = int(chk[1])
                        if chkType in ignoreType:
                            useTask = False
                    except:
                        print task+"  split didn't work  --",chk
            if useTask:
                self.wbs['Tasks']+=task

    def writeGantt(self,outFile='Project/wbs/wbs_pygen.xml'):
        self.outFile = os.path.join(pbwd,outFile)
        print 'Writing '+self.outFile
        fp = open(self.outFile,'w')
        fp.write(self.wbs['schema'])
        for out in self.wbsFormat:
            fp.write('\t<'+out+'>')
            if out=='Tasks' or out=='Calendars':
                fp.write('\n')
            fp.write(str(self.wbs[out]))
            fp.write('\t</'+out+'>\n')
        fp.write(self.wbs['end']+'\n')
        fp.close()
            
        
