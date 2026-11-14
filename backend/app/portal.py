from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .database import SessionLocal, get_db
from .models import (
    AppUser,
    Assignment,
    AttendanceEvent,
    Bus,
    BusLocation,
    Driver,
    GuardianContact,
    Notification,
    Route,
    RouteStop,
    Stop,
    Student,
    StudentTripEvent,
    Trip,
    UserSession,
)

router = APIRouter(prefix="/api/v1")
PBKDF2_ITERATIONS = 210_000
SESSION_HOURS = 12


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=200)
    role: str = Field(pattern="^(admin|driver|parent)$")


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=10000)


class TripUpdate(BaseModel):
    action: str = Field(pattern="^(start|complete)$")


class StudentEventRequest(BaseModel):
    student_id: str
    event_type: str = Field(pattern="^(boarded|absent|dropped_off)$")
    stop_id: str | None = None
    note: str | None = Field(default=None, max_length=500)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        iterations, salt_hex, expected_hex = stored.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def seed_demo_users() -> None:
    """Create deterministic demo identities without replacing existing credentials."""
    db = SessionLocal()
    try:
        accounts = [
            ("USR-ADMIN-001", "admin@smartroute.local", "Admin@2026", "admin", "Operations Admin", None, None),
            ("USR-PARENT-001", "parent1@smartroute.local", "Parent@2026", "parent", "Parent of Aarav Sharma", None, "GDN-000001"),
        ]
        drivers = db.scalars(select(Driver).order_by(Driver.id)).all()
        accounts.extend(
            (
                f"USR-DRIVER-{index:03}",
                f"driver{index}@smartroute.local",
                "Driver@2026",
                "driver",
                driver.name,
                driver.id,
                None,
            )
            for index, driver in enumerate(drivers, start=1)
        )
        for user_id, username, password, role, display_name, driver_id, guardian_id in accounts:
            existing = db.scalar(select(AppUser).where(AppUser.username == username))
            if not existing:
                db.add(AppUser(
                    id=user_id,
                    username=username,
                    password_hash=_hash_password(password),
                    role=role,
                    display_name=display_name,
                    driver_id=driver_id,
                    guardian_id=guardian_id,
                    active=True,
                ))
            else:
                existing.display_name = display_name
        db.commit()
    finally:
        db.close()


def current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AppUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in required")
    token = authorization.removeprefix("Bearer ").strip()
    session = db.get(UserSession, _session_hash(token))
    if not session or session.expires_at <= datetime.utcnow():
        if session:
            db.delete(session)
            db.commit()
        raise HTTPException(401, "Session expired. Please sign in again")
    user = db.get(AppUser, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Account unavailable")
    return user


def require_role(*roles: str):
    def dependency(user: AppUser = Depends(current_user)) -> AppUser:
        if user.role not in roles:
            raise HTTPException(403, f"This area is available to {', '.join(roles)} users only")
        return user
    return dependency


def _user_view(user: AppUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "driver_id": user.driver_id,
        "guardian_id": user.guardian_id,
    }


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(AppUser).where(func.lower(AppUser.username) == payload.username.lower()))
    if not user or user.role != payload.role or not user.active or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect role, email, or password")
    raw_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    db.add(UserSession(
        token_hash=_session_hash(raw_token),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(hours=SESSION_HOURS),
    ))
    db.commit()
    return {"token": raw_token, "expires_in_hours": SESSION_HOURS, "user": _user_view(user)}


@router.get("/auth/demo-drivers")
def demo_drivers(db: Session = Depends(get_db)):
    """Expose synthetic driver choices used by the local demonstration login."""
    users = db.scalars(
        select(AppUser)
        .where(AppUser.role == "driver", AppUser.active.is_(True))
        .order_by(AppUser.driver_id)
    ).all()
    return [
        {"display_name": user.display_name, "username": user.username, "driver_id": user.driver_id}
        for user in users
    ]


@router.get("/auth/me")
def me(user: AppUser = Depends(current_user)):
    return _user_view(user)


@router.post("/auth/logout")
def logout(
    authorization: str = Header(default=""),
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    token = authorization.removeprefix("Bearer ").strip()
    session = db.get(UserSession, _session_hash(token))
    if session:
        db.delete(session)
        db.commit()
    return {"signed_out": True, "user_id": user.id}


def _driver_route(db: Session, user: AppUser) -> Route:
    if not user.driver_id:
        raise HTTPException(409, "Driver account is not linked to a driver record")
    route = db.scalar(select(Route).where(Route.driver_id == user.driver_id, Route.status == "active"))
    if not route:
        raise HTTPException(404, "No active route is assigned to this driver")
    return route


def _today_trip(db: Session, route: Route, driver_id: str) -> Trip:
    trip = db.scalar(select(Trip).where(Trip.route_id == route.id, Trip.service_date == date.today()))
    if not trip:
        trip = Trip(
            id=f"TRIP-{date.today().isoformat()}-{route.id[-6:]}",
            route_id=route.id,
            driver_id=driver_id,
            service_date=date.today(),
            status="not_started",
        )
        db.add(trip)
        db.flush()
    return trip


def _location_view(location: BusLocation | None) -> dict | None:
    if not location:
        return None
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy_meters": location.accuracy_meters,
        "recorded_at": location.recorded_at.isoformat(),
    }


def _event_view(db: Session, event: StudentTripEvent) -> dict:
    student = db.get(Student, event.student_id)
    stop = db.get(Stop, event.stop_id) if event.stop_id else None
    driver = db.get(Driver, event.driver_id)
    return {
        "id": event.id,
        "student_id": event.student_id,
        "student": student.name if student else event.student_id,
        "event_type": event.event_type,
        "route_id": event.route_id,
        "stop_id": event.stop_id,
        "stop": stop.name if stop else None,
        "driver": driver.name if driver else event.driver_id,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "note": event.note,
        "created_at": event.created_at.isoformat(),
    }


@router.get("/driver/dashboard")
def driver_dashboard(
    user: AppUser = Depends(require_role("driver")),
    db: Session = Depends(get_db),
):
    route = _driver_route(db, user)
    trip = _today_trip(db, route, user.driver_id)
    bus = db.get(Bus, route.bus_id)
    driver = db.get(Driver, user.driver_id)
    stop_rows = db.execute(
        select(RouteStop, Stop)
        .join(Stop, Stop.id == RouteStop.stop_id)
        .where(RouteStop.route_id == route.id)
        .order_by(RouteStop.sequence)
    ).all()
    assignment_rows = db.execute(
        select(Assignment, Student, Stop)
        .join(Student, Student.id == Assignment.student_id)
        .join(Stop, Stop.id == Assignment.stop_id)
        .where(Assignment.route_id == route.id, Assignment.status == "active")
        .order_by(Student.name)
    ).all()
    latest_location = db.scalar(select(BusLocation).where(
        BusLocation.route_id == route.id,
        func.date(BusLocation.recorded_at) == date.today().isoformat(),
    ).order_by(BusLocation.recorded_at.desc()))
    event_query = select(StudentTripEvent).where(StudentTripEvent.trip_id == trip.id)
    if trip.started_at:
        event_query = event_query.where(StudentTripEvent.created_at >= trip.started_at)
        event_rows = db.scalars(event_query.order_by(StudentTripEvent.created_at.desc())).all()
    else:
        event_rows = []
    latest_by_student = {}
    for event in event_rows:
        latest_by_student.setdefault(event.student_id, event.event_type)
    db.commit()
    return {
        "user": _user_view(user),
        "driver": {"id": driver.id, "name": driver.name} if driver else None,
        "route": {"id": route.id, "status": route.status},
        "bus": {"id": bus.id, "capacity": bus.capacity, "accessible": bus.accessible} if bus else None,
        "trip": {"id": trip.id, "status": trip.status, "service_date": trip.service_date.isoformat(), "started_at": trip.started_at.isoformat() if trip.started_at else None},
        "location": _location_view(latest_location),
        "stops": [{"id": stop.id, "name": stop.name, "sequence": route_stop.sequence, "pickup_window": route_stop.pickup_window} for route_stop, stop in stop_rows],
        "students": [{"id": student.id, "name": student.name, "stop_id": stop.id, "stop": stop.name, "status": latest_by_student.get(student.id, "waiting")} for assignment, student, stop in assignment_rows],
    }


@router.post("/driver/trip")
def update_trip(
    payload: TripUpdate,
    user: AppUser = Depends(require_role("driver")),
    db: Session = Depends(get_db),
):
    route = _driver_route(db, user)
    trip = _today_trip(db, route, user.driver_id)
    now = datetime.utcnow()
    if payload.action == "start":
        if trip.status == "in_progress":
            raise HTTPException(409, "This trip is already in progress")
        trip.status = "in_progress"
        trip.started_at = now
        trip.completed_at = None
    else:
        if trip.status != "in_progress":
            raise HTTPException(409, "Start the trip before completing it")
        trip.status = "completed"
        trip.completed_at = now
    db.commit()
    return {"trip_id": trip.id, "status": trip.status}


@router.post("/driver/location")
def update_location(
    payload: LocationUpdate,
    user: AppUser = Depends(require_role("driver")),
    db: Session = Depends(get_db),
):
    route = _driver_route(db, user)
    trip = _today_trip(db, route, user.driver_id)
    if trip.status != "in_progress":
        raise HTTPException(409, "Start the trip before sharing location")
    location = BusLocation(
        route_id=route.id,
        driver_id=user.driver_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        recorded_at=datetime.utcnow(),
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return _location_view(location)


@router.post("/driver/student-event")
def add_student_event(
    payload: StudentEventRequest,
    user: AppUser = Depends(require_role("driver")),
    db: Session = Depends(get_db),
):
    route = _driver_route(db, user)
    trip = _today_trip(db, route, user.driver_id)
    if trip.status != "in_progress":
        raise HTTPException(409, "Start the trip before updating student status")
    assignment = db.scalar(select(Assignment).where(
        Assignment.student_id == payload.student_id,
        Assignment.route_id == route.id,
        Assignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(403, "This student is not assigned to your route")
    stop_id = payload.stop_id or assignment.stop_id
    if not db.scalar(select(RouteStop).where(RouteStop.route_id == route.id, RouteStop.stop_id == stop_id)):
        raise HTTPException(409, "The selected stop is not on this route")
    latest_location = db.scalar(select(BusLocation).where(
        BusLocation.route_id == route.id,
        func.date(BusLocation.recorded_at) == date.today().isoformat(),
    ).order_by(BusLocation.recorded_at.desc()))
    event = StudentTripEvent(
        trip_id=trip.id,
        student_id=payload.student_id,
        route_id=route.id,
        driver_id=user.driver_id,
        event_type=payload.event_type,
        stop_id=stop_id,
        latitude=latest_location.latitude if latest_location else None,
        longitude=latest_location.longitude if latest_location else None,
        note=payload.note,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    if payload.event_type in ("boarded", "absent"):
        db.add(AttendanceEvent(student_id=payload.student_id, event_date=date.today(), status=payload.event_type))
    contacts = db.scalars(select(GuardianContact).where(GuardianContact.student_id == payload.student_id, GuardianContact.valid.is_(True))).all()
    for contact in contacts:
        db.add(Notification(id=f"NOT-{uuid4().hex[:16].upper()}", contact_id=contact.id, event_type=payload.event_type, status="queued"))
    db.commit()
    db.refresh(event)
    return _event_view(db, event)


@router.get("/admin/operations")
def admin_operations(
    user: AppUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    route_rows = db.execute(
        select(Route, Bus, Driver)
        .join(Bus, Bus.id == Route.bus_id)
        .outerjoin(Driver, Driver.id == Route.driver_id)
        .where(Route.status != "inactive")
        .order_by(Route.id)
    ).all()
    routes = []
    for route, bus, driver in route_rows:
        trip = db.scalar(select(Trip).where(Trip.route_id == route.id, Trip.service_date == date.today()))
        location = db.scalar(select(BusLocation).where(
            BusLocation.route_id == route.id,
            func.date(BusLocation.recorded_at) == date.today().isoformat(),
        ).order_by(BusLocation.recorded_at.desc()))
        assigned = db.scalar(select(func.count()).select_from(Assignment).where(Assignment.route_id == route.id, Assignment.status == "active")) or 0
        if trip and trip.started_at:
            boarded_students = set(db.scalars(select(StudentTripEvent.student_id).where(
                StudentTripEvent.route_id == route.id,
                StudentTripEvent.event_type == "boarded",
                StudentTripEvent.created_at >= trip.started_at,
            )).all())
            dropped_students = set(db.scalars(select(StudentTripEvent.student_id).where(
                StudentTripEvent.route_id == route.id,
                StudentTripEvent.event_type == "dropped_off",
                StudentTripEvent.created_at >= trip.started_at,
            )).all())
        else:
            boarded_students, dropped_students = set(), set()
        routes.append({
            "id": route.id,
            "status": route.status,
            "bus": bus.id,
            "capacity": bus.capacity,
            "driver": driver.name if driver else "Unassigned",
            "trip_status": trip.status if trip else "not_started",
            "assigned_students": assigned,
            "students_on_bus": len(boarded_students - dropped_students),
            "location": _location_view(location),
        })
    recent = db.scalars(select(StudentTripEvent).order_by(StudentTripEvent.created_at.desc()).limit(30)).all()
    active_trips = sum(1 for route in routes if route["trip_status"] == "in_progress")
    return {
        "user": _user_view(user),
        "summary": {
            "active_routes": len(routes),
            "active_trips": active_trips,
            "students_on_buses": sum(route["students_on_bus"] for route in routes),
            "routes_reporting_location": sum(1 for route in routes if route["location"]),
        },
        "routes": routes,
        "recent_events": [_event_view(db, event) for event in recent],
    }


@router.get("/parent/dashboard")
def parent_dashboard(
    user: AppUser = Depends(require_role("parent")),
    db: Session = Depends(get_db),
):
    if not user.guardian_id:
        raise HTTPException(409, "Parent account is not linked to a guardian record")
    guardian = db.get(GuardianContact, user.guardian_id)
    if not guardian:
        raise HTTPException(404, "Guardian record not found")
    student = db.get(Student, guardian.student_id)
    assignment = db.scalar(select(Assignment).where(Assignment.student_id == student.id, Assignment.status == "active"))
    if not assignment:
        return {"user": _user_view(user), "student": {"id": student.id, "name": student.name}, "status": "unassigned", "assignment": None, "events": []}
    route = db.get(Route, assignment.route_id)
    bus = db.get(Bus, route.bus_id)
    driver = db.get(Driver, route.driver_id) if route.driver_id else None
    stop = db.get(Stop, assignment.stop_id)
    trip = db.scalar(select(Trip).where(Trip.route_id == route.id, Trip.service_date == date.today()))
    location = db.scalar(select(BusLocation).where(
        BusLocation.route_id == route.id,
        func.date(BusLocation.recorded_at) == date.today().isoformat(),
    ).order_by(BusLocation.recorded_at.desc()))
    events = db.scalars(select(StudentTripEvent).where(StudentTripEvent.student_id == student.id).order_by(StudentTripEvent.created_at.desc()).limit(20)).all()
    current_events = [event for event in events if trip and trip.started_at and event.created_at >= trip.started_at]
    latest = current_events[0] if current_events else None
    status = latest.event_type if latest else (
        "trip_in_progress" if trip and trip.status == "in_progress"
        else "trip_completed" if trip and trip.status == "completed"
        else "waiting"
    )
    return {
        "user": _user_view(user),
        "student": {"id": student.id, "name": student.name},
        "status": status,
        "assignment": {
            "route": route.id,
            "bus": bus.id,
            "driver": driver.name if driver else "Awaiting driver",
            "stop": stop.name,
            "stop_id": stop.id,
        },
        "trip": {"status": trip.status, "started_at": trip.started_at.isoformat() if trip.started_at else None} if trip else {"status": "not_started", "started_at": None},
        "location": _location_view(location),
        "events": [_event_view(db, event) for event in events],
    }
