class MSProjectTask:
    def __init__(self):
        self.UID=0          #integer	The unique ID for the task.
        self.ID=0	    #integer	The position identifier of the task in the list of tasks.
        self.Name=''        #string(512)	The name of the task.
        self.Type=1         #integer	The type of task:
 #                              0	Fixed units
 #                              1	Fixed duration
 #                              2	Fixed work
        self.IsNull=0       #Boolean	Indicates whether a task is null.
        self.Active=1       #Boolean    NOT FROM WEBSITE, BUT RATHER FROM SAVED PROJECT XML
        self.Manual=1       #Boolean    NOT FROM WEBSITE,   "
        self.CreateDate=''  #datetime	The date and time that a task was added to a project.
        self.Contact=''     #string(512)	The name of the individual who is responsible for a task.
        self.WBS=0          #integer	A unique code (WBS) used to represent a task's position within the hierarchical structure of the project.
        self.WBSLevel=0     #integer	The right-most level of the task. For example, if the task level was A.01.03, the right-most level would be 03.
        self.OutlineNumber=''#string(512)	The number that indicates the level of a task in the project outline hierarchy.
        self.OutlineLevel=0 #integer	Indicates the exact position of a task in the outline. For example, 7.2 indicates that a task is the second subtask under the seventh top-level summary task.
        self.Priority=0     #integer	Indicates the level of importance assigned to a task, with 500 being no priority; the higher the number, the higher the priority:
        self.Start=''       #datetime	The date and time that a task is scheduled to begin.
        self.ManualStart='' #datetime   NOT FROM WEBSITE
        self.Finish=''      #datetime	The date and time that a task is scheduled to be completed.
        self.ManualFinish=''#datetime
        self.Duration=''    #duration	The total span of active working time for a task.
        self.ManualDuration=''#duration
        self.DurationFormat=''#integer	The format used to show the duration of the task:
        self.Work=''        #duration	The total amount of work scheduled to be performed on a task by all assigned resources.
        self.Stop=''        #datetime	The date that represents the end of the actual portion of a task.
        self.Resume=''      #datetime	The date the remaining portion of a task is scheduled to resume.
        self.ResumeValid=0  #Boolean	Indicates whether the task can be resumed.
        self.EffortDriven=0 #Boolean	Indicates whether scheduling for a task is effort-driven.
        self.Recurring=0    #Boolean	Indicates whether a task is a recurring task.
        self.OverAllocated=0#Boolean	Indicates whether an assigned resource on a task has been assigned to more work on the task than can be done within the normal working capacity.
        self.Estimated=0    #Boolean	Indicates whether the task's duration is flagged as an estimate.
        self.Milestone=0    #Boolean	Indicates whether a task is a milestone.
        self.Summary=0      #Boolean	Indicates whether a task is a summary task.
        self.Critical=0     #Boolean	Indicates whether a task has room in the schedule to slip, or if it is on the critical path.
##        self.IsSubproject=0 #Boolean	Indicates whether the task is an inserted project.
##        self.IsSubprojectReadOnly=0#Boolean	Indicates whether the inserted project is a read-only project.
##        self.SubprojectName=''#string(512)	The source location of the inserted project.
##        self.ExternalTask=0 #Boolean	Indicates whether the task is linked from another project or whether it originated in the current project.
##        self.ExternalTaskProject=''#string(512)	The source of an external task.
##        self.EarlyStart     #datetime	The earliest date that a task could possibly begin, based on the early start dates of predecessor and successor tasks and other constraints.
##        self.EarlyFinish    #datetime	The earliest date that a task could possibly finish, based on early finish dates of predecessor and successor tasks, other constraints, and any leveling delay.
##        self.LateStart      #datetime	The latest date that a task can start without delaying the finish of the project.
##        self.LateFinish     #datetime	The latest date that a task can finish without delaying the finish of the project.
##        self.StartVariance  #integer	The difference between a task's baseline start date and its currently scheduled start date.
##        self.FinishVariance #integer	The amount of time that represents the difference between a task's baseline finish date and its current finish date.
##        self.WorkVariance   #Float	        The difference between a task's baseline work and the currently scheduled work.
##        self.FreeSlack      #integer	The amount of time that a task can be delayed without delaying any successor tasks; if a task has zero successor tasks, free slack is the amount of time a task can be delayed without delaying the entire project.
##        self.TotalSlack     #integer	The amount of time a task can be delayed without delaying a project's finish date.
##        self.FixedCost      #Float	        A task expense that is not associated with a resource cost.
##        self.FixedCostAccrual#integer	Indicates how fixed costs are to be charged, or accrued, to the cost of a task:
##        self.PercentComplete#integer	The current status of a task, expressed as the percentage of the task's duration that has been completed.
##        self.PercentWorkComplete#integer	The current status of a task, expressed as the percentage of the task's work that has been completed.
##        self.Cost           #decimal	The total scheduled, or projected, cost for a task, based on costs already incurred for work performed by all resources assigned to the task, in addition to the costs planned for the remaining work for the assignment.
##        self.OvertimeCost   #decimal	The sum of the actual overtime cost for the task.
##        self.OvertimeWork   #duration	The amount of overtime scheduled to be performed by all resources assigned to a task and charged at overtime rates.
##        self.ActualStart    #datetime	The date and time that a task actually began.
##        self.ActualFinish   #datetime	The date and time that a task actually finished.
##        self.ActualDuration #duration	The span of actual working time for a task so far, based on the scheduled duration and current remaining work or percent complete. Actual duration can be calculated in two ways, either based on Percent Complete or Remaining Duration.
##        self.ActualCost     #decimal	The costs incurred for work already performed by all resources on a task, along with any other recorded costs associated with the task.
##        self.ActualOvertimeCost#decimal	The costs incurred for overtime work already performed on a task by all assigned resources.
##        self.ActualWork     #duration	The amount of work that has already been done by the resources assigned to a task.
##        self.ActualOvertimeWork#duration	The actual amount of overtime work already performed by all resources assigned to a task.
##        self.RegularWork    #duration	The total amount of non-overtime work scheduled to be performed by all resources assigned to a task.
##        self.RemainingDuration#duration	The amount of time required to complete the unfinished portion of a task. Remaining duration can be calculated in two ways (either based on Percent Complete or Actual Duration).
##        self.RemainingCost  #decimal	The remaining scheduled expense of a task that will be incurred in completing the remaining scheduled work by all resources assigned to a task.
##        self.RemainingWork  #duration	The amount of time still required by all assigned resources to complete a task.
##        self.RemainingOvertimeCost#decimal	The remaining scheduled overtime expense for a task.
##        self.RemainingOvertimeWork#duration	The amount of remaining overtime scheduled by all assigned resources to complete a task.
##        self.ACWP	    #decimal	The costs incurred for work already done on a task, up to the project status date or today's date.
##        self.CV             #decimal	The difference between how much it should have cost to achieve the current level of completion on the task and how much it has actually cost to achieve the current level of completion up to the status date or today's date; also called cost variance.
        self.ConstraintType=0 #integer	The constraint on a scheduled task:
 #                              0	As soon as possible
 #                              1	As late as possible
 #                              2	Must start on
 #                              3	Must finish on
 #                              4	Start no earlier than
 #                              5	Start no later than
 #                              6	Finish no earlier than
 #                              7	Finish no later than
        self.CalendarUID=0    #integer	Refers to a valid UID in the Calendar section of the Microsoft Project XML Schema.
##        self.ConstraintDate #datetime	Indicates the constrained start or finish date as defined in TaskConstraintType. Required unless TaskContstraintType is set to As late as possible or As soon as possible.
##        self.Deadline       #datetime	The date entered as a deadline for the task.
##        self.LevelAssignments#Boolean	Indicates whether the leveling function can delay and split individual assignments (rather than the entire task) to resolve overallocations.
##        self.LevelingCanSplit#Boolean	Indicates whether the resource leveling function can cause splits on remaining work on a task.
##        self.LevelingDelay  #integer	The amount of time that a task is to be delayed from its early start date as a result of resource leveling.
##        self.PreLeveledStart#datetime	The start date of a task as it was before resource leveling was done.
##        self.PreLeveledFinish#datetime	The finish date of a task as it was before resource leveling was done.
##        self.Hyperlink      #string(512)	The title or explanatory text for a hyperlink associated with a task.
##        self.HyperlinkAddress#string(512)	The address for a hyperlink associated with a task.
##        self.HyperlinkSubAddress#string(512)	The specific location in a document within a hyperlink associated with a task.
##        self.IgnoreResourceCalendar#Boolean	Indicates whether the scheduling of the task takes into account the calendars of the resources assigned to the task.
##        self.Notes	    #string	        Notes entered about a task.
##        self.HideBar	    #Boolean	Indicates whether the Gantt bars and Calendar bars for a task are hidden.
##        self.Rollup	    #Boolean	Indicates whether the summary task bar displays rolled-up bars or whether information on the subtask Gantt bars will be rolled up to the summary task bar; must be set to True for subtasks to be rolled up to summary tasks.
##        self.BCWS	    #decimal	The cumulative timephased baseline costs up to the status date or today's date; also known as budgeted cost of work performed.
##        self.BCWP	    #decimal	The cumulative value of the task's timephased percent complete multiplied by the task's timephased baseline cost, up to the status date or today's date; also known as budgeted cost of work performed.
##        self.PhysicalPercentComplete#integer	The physical percent of the total work on a task that has been completed.
##        self.EarnedValueMethod#integer	Indicates the type of earned value method to use:
 #                              0	Use % complete
 #                              1	Use physical % complete
        self.PredecessorUID=0#(PredecessorLink)	integer	The unique ID number for the predecessor tasks on which this task depends before it can be started or finished.
        self.PredecessorType=0#(PredecessorLink)	integer	
 #                              0	FF (finish-to-finish)
 #                              1	FS (finish-to-start)
 #                              2	SF (start-to-finish)
 #                              3	SS (start-to-start)
##        self.PredecessorCrossProject#(PredecessorLink)	Boolean	Indicates whether the task predecessor is part of another project.
##        self.PredecessorCrossProject#Name #(PredecessorLink)	string	The external predecessor project.
##        self.PredecessorLinkLag#(PredecessorLink)	integer	The amount of lag.
##        self.PredecessorLagFormat#(PredecessorLink)	integer	Indicates the format for the amount of lag specified in PredecessorLag:
##        self.ExtendedUID    #(ExtendedAttribute)	integer	The unique ID for the extended attribute.
##        self.ExtendedFieldID#(ExtendedAttribute)	integer	The field ID for the extended attribute.
##        self.ExtendedValue  #(ExtendedAttribute)	string	The actual value of the extended attribute.
##        self.ExtendedValueID# (ExtendedAttribute)	string	The ID of the value in the extended attribute lookup table.
##        self.ExtendedDurationFormat#(ExtendedAttribute)	string	The duration format for the extended attribute:
##        self.BaselineTimephasedData#(Baseline)	TimePhased DataType	The timephased data block associated with the task baseline.
##        self.BaselineNumber #(Baseline)	intetger	The unique number of the baseline data record.
##        self.BaselineInterim#(Baseline)	Boolean	Indicates whether the baseline is an interim baseline.
##        self.BaselineStart  #(Baseline)	datetime	The scheduled start date of the task when the baseline was saved.
##        self.BaselineFinish #(Baseline)	datetime	The scheduled finish date of the task when the baseline was saved.
##        self.BaselineDuration#(Baseline)	duration	The scheduled duration of the task when the baseline was saved.
##        self.BaselineDurationFormat#(Baseline)	duration	The format for expressing the Duration of the Task baseline:
##        self.BaselineEstimatedDuration#(Baseline)	Boolean	Indicates whether the duration of the task is estimated.
##        self.BaselineWork   #(Baseline)	duration	The scheduled work for the task when the baseline was saved.
##        self.BaselineCost   #(Baseline)	decimal	The projected cost of the task when the baseline was saved.
##        self.BaselineBCWS   #(Baseline)	decimal	The cumulative timephased baseline costs up to the status date or today's date; also known as budgeted cost of work scheduled.
##        self.BaselineBCWP   #(Baseline)	decimal	The cumulative value of the task's timephased percent complete multiplied by the task's timephased baseline cost, up to the status date or today's date; also known as budgeted cost of work performed.
##        self.OutlineCodeUID #(OutlineCode)	integer	The unique ID for the value in the outline code collection.
##        self.OutlineCodeFieldID#(OutlineCode)	string	The localized name of the field.
##        self.OutlineCodeValueID#(OutlineCode)	integer	The unique ID in the value list associated with the definition in the outline code collection.
##        self.TimephasedData #TimePhased DataType	The timephased data block associated with the task.
