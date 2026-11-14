"""Deterministic synthetic seed generator; no personal or external data."""
import argparse, json, random, sqlite3
from datetime import date, timedelta
from pathlib import Path
from seed_names import indian_student_name

SEED=20261022; ROOT=Path(__file__).parent; DB=ROOT/'transport.db'
SCHEMA=ROOT/'schema.sql'
def main():
 p=argparse.ArgumentParser(); p.add_argument('--scale', choices=['starter','full'],default='starter'); a=p.parse_args(); random.seed(SEED)
 students,buses,stops=(100,10,30) if a.scale=='starter' else (5000,100,300)
 if DB.exists(): DB.unlink()
 c=sqlite3.connect(DB); c.executescript(SCHEMA.read_text())
 for i in range(10): c.execute('insert into address_zones values(?,?,?)',(f'ZONE-{i:03}',f'Zone {i}',1))
 for i in range(stops): c.execute('insert into stops values(?,?,?,?,?)',(f'STOP-{i+1:06}',f'Approved Stop {i+1}',f'ZONE-{i%10:03}',1,0))
 for i in range(buses):
  c.execute('insert into buses values(?,?,?,?,?)',(f'BUS-{i+1:06}',50,i%5==0,'active',1))
  c.execute('insert into drivers values(?,?,?,?)',(f'DRV-{i+1:06}',f'Driver {i+1}','active',1))
  c.execute('insert into routes values(?,?,?,?)',(f'ROUTE-2026-{i+1:06}',f'BUS-{i+1:06}',f'DRV-{i+1:06}','active'))
 for i in range(stops): c.execute('insert into route_stops values(?,?,?,?,?,?)',(f'ROUTE-2026-{i%buses+1:06}',f'STOP-{i+1:06}',i//buses+1,'07:30-07:45',round(0.4+(i%8)*0.35,2),10+(i%4)*5))
 for i in range(students):
  sid=f'STU-{i+1:06}'; zid=f'ZONE-{i%10:03}'; preferred=f'STOP-{i%buses+1:06}'; c.execute('insert into students values(?,?,?,?,?,?,?,?)',(sid,indian_student_name(i),zid,i%5==0,preferred,30,'zone_only' if i%13==0 else None,'active')); c.execute('insert into guardian_contacts values(?,?,?,?)',(f'GDN-{i+1:06}',sid,f'+1555{i:07}',1))
  # only assignments consistent with capacity (starter intentionally has some unassigned)
  if i < int(students * .8):
   route=f'ROUTE-2026-{i%buses+1:06}'; stop=f'STOP-{i%buses+1:06}'; aid=f'ASN-{sid}-2026'; c.execute('insert into assignments values(?,?,?,?,?,?,?,?,?)',(aid,sid,route,stop,'2026-01-01',None,'active',85.0,'Seeded valid assignment')); c.execute('insert into assignment_events(assignment_id,event_type,created_at,detail) values(?,?,?,?)',(aid,'created','2026-01-01T00:00:00','seeded valid assignment'))
 # Event history covers the required 200 school-day period (20,000 starter / 1,000,000 full events).
 notification_counter = 1
 for day_offset in range(200):
  event_day = (date(2026, 1, 5) + timedelta(days=day_offset)).isoformat()
  for i in range(students):
   sid = f'STU-{i+1:06}'
   marker = i + day_offset
   status = 'missed_pickup' if marker % 47 == 0 else ('absent' if marker % 23 == 0 else 'boarded')
   c.execute('insert into attendance_events(student_id,event_date,status) values(?,?,?)', (sid, event_day, status))
   if status == 'missed_pickup':
    c.execute('insert into notifications values(?,?,?,?)', (f'NOT-2026-{notification_counter:06}', f'GDN-{i+1:06}', 'missed_pickup', 'sent'))
    notification_counter += 1
 issues=[('capacity_exceeded','ROUTE-2026-000001','reject_assignment'),('incompatible_route','STU-000017','reject_assignment'),('impossible_travel_time','ROUTE-2026-000002','route_invalid'),('invalid_notification_contact','GDN-999999','do_not_send'),('unapproved_address_exposed','ZONE-999','access_denied')]
 c.executemany('insert into data_issues(issue_type,entity_ref,ground_truth) values(?,?,?)',issues); c.commit(); c.close()
 (ROOT/'ground_truth.json').write_text(json.dumps({'seed':SEED,'issues':[dict(type=x[0],entity=x[1],expected=x[2]) for x in issues]},indent=2))
 print(f'Created {DB} with {students} students, {buses} buses, {stops} stops (seed {SEED})')
if __name__=='__main__': main()
