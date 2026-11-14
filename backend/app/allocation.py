"""Constraint-first allocation policy. This module has no HTTP concerns."""
from dataclasses import dataclass
from typing import Iterable
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Assignment, Bus, Driver, Route, RouteStop, Stop, Student, Zone

DEFAULT_WEIGHTS = {"proximity": 25, "route": 25, "capacity": 15, "wait": 15, "distance": 10, "accessibility": 10}

@dataclass(frozen=True)
class Candidate:
    route: Route; bus: Bus; stop: Stop; score: float; distance_km: float; wait_minutes: int; explanation: str

def _active_count(db: Session, route_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Assignment).where(Assignment.route_id == route_id, Assignment.status == "active")) or 0

def candidates_for(db: Session, student: Student, weights: dict = DEFAULT_WEIGHTS) -> tuple[list[Candidate], list[str]]:
    """Return only mandatory-constraint-compliant candidates, plus rejection reasons."""
    zone = db.get(Zone, student.zone_id)
    if student.status != "active": return [], ["Student is inactive"]
    if not zone or not zone.approved: return [], ["Student address zone is not approved"]
    rows = db.execute(select(Route, Bus, Driver, RouteStop, Stop).join(Bus, Route.bus_id == Bus.id).join(Driver, Route.driver_id == Driver.id).join(RouteStop, RouteStop.route_id == Route.id).join(Stop, Stop.id == RouteStop.stop_id)).all()
    valid, rejected = [], []
    for route, bus, driver, route_stop, stop in rows:
        reasons = []
        if route.status != "active": reasons.append("route unavailable")
        if bus.lifecycle != "active" or not bus.available: reasons.append("vehicle unavailable")
        if driver.license_status != "active" or not driver.available: reasons.append("driver unavailable")
        if _active_count(db, route.id) >= bus.capacity: reasons.append("bus capacity exceeded")
        if student.needs_accessible_bus and not bus.accessible: reasons.append("accessible vehicle required")
        if not stop.approved or stop.restricted: reasons.append("pickup stop restricted or unapproved")
        if route_stop.wait_minutes > student.max_wait_minutes: reasons.append("pickup wait exceeds student maximum")
        if student.safety_restriction == "zone_only" and stop.zone_id != student.zone_id: reasons.append("safety restriction blocks stop zone")
        if reasons:
            rejected.extend(reasons); continue
        used = _active_count(db, route.id); remaining = bus.capacity - used
        proximity = 100 if stop.zone_id == student.zone_id else 45
        route_fit = 100 if stop.id == student.preferred_stop_id else 75
        capacity = min(100, remaining / bus.capacity * 100)
        waiting = max(0, 100 - route_stop.wait_minutes / max(student.max_wait_minutes, 1) * 100)
        distance = max(0, 100 - route_stop.distance_km * 12)
        access = 100 if (not student.needs_accessible_bus or bus.accessible) else 0
        score = sum((proximity, route_fit, capacity, waiting, distance, access)[i] * list(weights.values())[i] / 100 for i in range(6))
        explanation = f"Approved stop; {remaining} seats remain; {route_stop.distance_km:.1f} km; {route_stop.wait_minutes} min wait."
        valid.append(Candidate(route, bus, stop, round(score, 2), route_stop.distance_km, route_stop.wait_minutes, explanation))
    return sorted(valid, key=lambda c: (-c.score, c.distance_km, c.route.id)), sorted(set(rejected))

def choose_collectively(db: Session, students: Iterable[Student]) -> tuple[dict[str, Candidate], dict[str, list[str]]]:
    """Least-flexible students go first; this avoids greedy allocation starving constrained students."""
    options = {s.id: candidates_for(db, s) for s in students}
    ordered = sorted(students, key=lambda s: (len(options[s.id][0]), s.id))
    selected, rejected = {}, {}
    reserved: dict[str, int] = {}
    for student in ordered:
        candidates, reasons = options[student.id]
        pick = next((c for c in candidates if _active_count(db, c.route.id) + reserved.get(c.route.id, 0) < c.bus.capacity), None)
        if pick: selected[student.id] = pick; reserved[pick.route.id] = reserved.get(pick.route.id, 0) + 1
        else: rejected[student.id] = reasons or ["No remaining capacity after collective allocation"]
    return selected, rejected
