from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Zone(Base):
    __tablename__ = "address_zones"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)

class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    zone_id: Mapped[str] = mapped_column(ForeignKey("address_zones.id"))
    needs_accessible_bus: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_stop_id: Mapped[str | None] = mapped_column(ForeignKey("stops.id"), nullable=True)
    max_wait_minutes: Mapped[int] = mapped_column(Integer, default=30)
    safety_restriction: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")

class GuardianContact(Base):
    __tablename__ = "guardian_contacts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    phone: Mapped[str] = mapped_column(String)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)

class Stop(Base):
    __tablename__ = "stops"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    zone_id: Mapped[str] = mapped_column(ForeignKey("address_zones.id"))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)

class Bus(Base):
    __tablename__ = "buses"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer)
    accessible: Mapped[bool] = mapped_column(Boolean, default=False)
    lifecycle: Mapped[str] = mapped_column(String, default="active")
    available: Mapped[bool] = mapped_column(Boolean, default=True)

class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    license_status: Mapped[str] = mapped_column(String, default="active")
    available: Mapped[bool] = mapped_column(Boolean, default=True)

class Route(Base):
    __tablename__ = "routes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    bus_id: Mapped[str] = mapped_column(ForeignKey("buses.id"))
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")

class RouteStop(Base):
    __tablename__ = "route_stops"
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), primary_key=True)
    stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer)
    pickup_window: Mapped[str] = mapped_column(String)
    distance_km: Mapped[float] = mapped_column(default=0.0)
    wait_minutes: Mapped[int] = mapped_column(Integer, default=15)

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"))
    stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    allocation_score: Mapped[float | None] = mapped_column(nullable=True)
    allocation_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

class AuditEvent(Base):
    __tablename__ = "assignment_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id"))
    event_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    detail: Mapped[str] = mapped_column(Text)

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    event_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("guardian_contacts.id"))
    event_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)

class DataIssue(Base):
    __tablename__ = "data_issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_type: Mapped[str] = mapped_column(String)
    entity_ref: Mapped[str] = mapped_column(String)
    ground_truth: Mapped[str] = mapped_column(String)

class AppUser(Base):
    __tablename__ = "app_users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str] = mapped_column(String)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    guardian_id: Mapped[str | None] = mapped_column(ForeignKey("guardian_contacts.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String, default="not_started", index=True)
    current_stop_id: Mapped[str | None] = mapped_column(ForeignKey("stops.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("route_id", "service_date", name="uq_trip_route_date"),)

class BusLocation(Base):
    __tablename__ = "bus_locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class StudentTripEvent(Base):
    __tablename__ = "student_trip_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    stop_id: Mapped[str | None] = mapped_column(ForeignKey("stops.id"), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
