"""Lightweight integrity report used in CI after data generation."""
import sqlite3
from pathlib import Path

db = sqlite3.connect(Path(__file__).parent / 'transport.db')
checks = {
 'orphan_assignments': "SELECT count(*) FROM assignments a LEFT JOIN students s ON s.id=a.student_id LEFT JOIN routes r ON r.id=a.route_id LEFT JOIN stops t ON t.id=a.stop_id WHERE s.id IS NULL OR r.id IS NULL OR t.id IS NULL",
 'over_capacity_routes': "SELECT count(*) FROM (SELECT r.id FROM routes r JOIN buses b ON b.id=r.bus_id LEFT JOIN assignments a ON a.route_id=r.id AND a.status='active' GROUP BY r.id HAVING count(a.id)>b.capacity)",
 'duplicate_active_students': "SELECT count(*) FROM (SELECT student_id FROM assignments WHERE status='active' GROUP BY student_id HAVING count(*)>1)",
}
for name, query in checks.items():
    result = db.execute(query).fetchone()[0]
    print(f'{name}: {result}')
    if result: raise SystemExit(f'Validation failed: {name}')
print('validation: PASS')
