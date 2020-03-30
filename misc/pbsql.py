import sqlite3

db = sqlite3.connect('milestones.db')
q = db.cursor()

q.execute('SELECT * FROM milestone WHERE name like "nsfA%" ORDER BY id')

nsfA = q.fetchall()

for rec in nsfA:
    print rec[0]

    squery= "SELECT * FROM reqspecTrace where refName='%s'" % (rec[0])
    q.execute(squery)
    reqspecs = q.fetchall()

    squery= "SELECT * FROM componentTrace where refName='%s'" % (rec[0])
    q.execute(squery)
    components = q.fetchall()

    squery= "SELECT * FROM updated where refName='%s'" % (rec[0])
    q.execute(squery)
    updated = q.fetchall()

    print rec
    print reqspecs
    print components
    print updated
