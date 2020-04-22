# ProjectData

This repo houses the HERA milestone database and viewing code.  
Use `pip install .`

For a typical session:

- In [1]: `from project_data import pd`
- In [2]: `pd.find('20/06/01')`
-         This will produce too much - can filter below.
- In [3]: `pd.find('20/06/01', owner='comm', dtype='nsfB', status=pd.undone)`
- In [4]: `r = pd.ref("<Description from plot>")`
-         This will give the data for that entry (need to include enough to be unique.)
- In [5]: `pd.find('20/05/01', '20/06/01', owner='mc,dsp', status=pd.undone, display='show')`

For a mysterious summary plot try:

- In [1]: `project project_data import pd`
- In [2]: `pd.find('20/12/31', dtype='nsfB')`
- In [3]: `pd.mi.dype_info()`

This plots the cumulative milestones, underlayed with squares that are proportional in size to the number
of milestones met that quarter, and the color is the average completion (same color bar as for 'find').
You can also filter the `pd.find` to narrow the scope.

## dtype
* nsfA == MSIP-16
* nsfB == MSIP-18

## owner
Owner     |        Name              | MSIP |_______| Owner | Name                         | MSIP
----------|--------------------------|------|-------|-------|------------------------------|----------
analysis  | analysis                 | 16/18|       | pem   | power estimation and modeling| 16/18
arc       | archive                  | 16   |       | pm    | project management           | 16/18
asp       | analog signal processing | 16   |       | proc  | processing                   |    18
comm      | commissioning            | 16   |       | psp   | power spectrum pipeline      | 16/18
dsp       | digital signal processing| 16   |       | qa    | quality assurance            | 16/18
epo       | edu and public outreach  | 16/18|       | rtp   | real-time processing         | 16
host      | hosting                  | 16/18|       | sims  | simulations                  | 16/18
img       | imaging                  |    18|       | site  | site                         | 16
lib       | librarian                | 16   |       | srdr  | science results/data release | 16/18
mc        | monitor and control      | 16/18|       | stats | statistics                   | 16/18
node      | node                     | 16   |       | sys   | system                       |    18
opm       | offline processing module| 16   |       | val   | validation                   |    18
ops       | operations               |    18|       |       |                              |

## status
* pd.undone is defined as ['late', 'moved', 'none', 'unknown']
* status='complete', will show completed ones.

## display
* show
* listing
* gantt
