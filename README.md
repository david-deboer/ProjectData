# ProjectData

This repo houses the HERA milestone database and viewing code.  
Use `pip install .`

For a typical session:

- In [1]: `from project_data import pd`
- In [2]: `pd.find('20/06/01')`
- In [3]: `pd.find('20/06/01', owner='comm', dtype='nsfB', status=pd.undone)`
- In [4]: `r = pd.ref("<Description from plot>")`
- In [5]: `pd.find('20/05/01', '20/06/01', owner='mc', status=pd.undone, display='show')`

## dtype
* nsfA == MSIP-16
* nsfB == MSIP-18

## owner
Owner     |        Name              | MSIP |_______| Owner | Name                         | MSIP
----------|--------------------------|------|-------|-------|------------------------------|----------
analysis  | analysis                 | 16/18|       | pem   | power estimation and modeling| 16/18
arc       | archive                  | 16   |       | pm    | project management           | 16/18
asp       | analog signal processing | 16   |       | proc  | processing                   | 18
comm      | commissioning            | 16   |       | psp   | power spectrum pipeline      | 16/18
dsp       | digital signal processing| 16   |       | qa    | quality assurance            |
epo       | edu and public outreach  | 16/18|       | rtp   | real-time processing         | 16
host      | hosting                  | 18   |       | sims  | simulations                  |
img       | imaging                  |      |       | site  | site                         |
lib       | librarian                | 16   |       | srdr  | science results/data release |
mc        | monitor and control      | 16   |       | stats | statistics                   |
node      | node                     | 16   |       | sys   | system                       | 18
opm       | offline processing module| 16   |       | val   | validation                   |
ops       | operations               | 18   |       |       |                              |

## status
* pd.undone is defined as ['late', 'moved', 'none', 'unknown']
* status='complete', will show completed ones.

## display
* show
* listing
* gantt
