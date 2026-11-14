from datetime import date
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from .allocation import choose_collectively, candidates_for
from .database import Base, engine, get_db
from .models import Assignment, AttendanceEvent, AuditEvent, Bus, Driver, Route, Student, Zone
from .portal import router as portal_router, seed_demo_users

Base.metadata.create_all(engine)
seed_demo_users()
app = FastAPI(title="SmartRoute AI API", version="2.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parents[2] / "frontend"), name="static")
app.include_router(portal_router)

class ManualAssignment(BaseModel):
    student_id: str; route_id: str; stop_id: str; effective_from: date = Field(default_factory=date.today)
class AllocationRun(BaseModel): student_ids: list[str] | None = None
class ReallocationRequest(BaseModel): resource_type: str = Field(pattern="^(bus|driver)$"); resource_id: str
def admin(x_role: str = Header(default="")):
    if x_role.lower() != "admin": raise HTTPException(403, "Administrator role required")
def view(db, a):
    s=db.get(Student,a.student_id); r=db.get(Route,a.route_id); b=db.get(Bus,r.bus_id)
    return {"assignment_id":a.id,"student_id":s.id,"student":s.name,"bus":b.id,"route":r.id,"stop":a.stop_id,"score":a.allocation_score,"status":a.status,"explanation":a.allocation_explanation}
def save(db, student, candidate, event):
    current=db.scalar(select(Assignment).where(Assignment.student_id==student.id,Assignment.status=="active"))
    if current:
        current.status="ended"; current.effective_to=date.today(); db.add(AuditEvent(assignment_id=current.id,event_type="ended",detail="Superseded by allocation"))
    aid=f"ASN-{student.id}-2026-{candidate.route.id[-3:]}"
    item=Assignment(id=aid,student_id=student.id,route_id=candidate.route.id,stop_id=candidate.stop.id,effective_from=date.today(),status="active",allocation_score=candidate.score,allocation_explanation=candidate.explanation)
    db.add(item); db.flush(); db.add(AuditEvent(assignment_id=aid,event_type=event,detail=candidate.explanation)); return item

@app.get("/api/v1/health")
def health(): return {"status":"ok"}
@app.get("/api/v1/allocation/overview")
def overview(db:Session=Depends(get_db)):
    active=Assignment.status=="active"; eligible=db.scalar(select(func.count()).select_from(Student).where(Student.status=="active")) or 0; allocated=db.scalar(select(func.count()).select_from(Assignment).where(active)) or 0; cap=db.scalar(select(func.sum(Bus.capacity)).where(Bus.available.is_(True),Bus.lifecycle=="active")) or 0
    return {"eligible_students":eligible,"allocated":allocated,"unallocated":max(0,eligible-allocated),"available_buses":db.scalar(select(func.count()).select_from(Bus).where(Bus.available.is_(True),Bus.lifecycle=="active")) or 0,"remaining_seats":max(0,cap-allocated),"average_score":round(db.scalar(select(func.avg(Assignment.allocation_score)).where(active)) or 0,1),"capacity_utilization":round(allocated/cap*100,1) if cap else 0}
@app.get("/api/v1/allocation/assignments")
def assignments(db:Session=Depends(get_db)): return [view(db,x) for x in db.scalars(select(Assignment).where(Assignment.status=="active")).all()]
@app.get("/api/v1/analytics")
def analytics(db:Session=Depends(get_db)):
    attendance_counts={status:count for status,count in db.execute(select(AttendanceEvent.status,func.count()).group_by(AttendanceEvent.status)).all()}
    attendance_counts={status:attendance_counts.get(status,0) for status in ("boarded","absent","missed_pickup")}
    attendance_total=sum(attendance_counts.values())
    boarded_rate=round(attendance_counts["boarded"]/attendance_total*100,1) if attendance_total else 0
    active_students=db.scalar(select(func.count()).select_from(Student).where(Student.status=="active")) or 0
    active_assignments=db.scalar(select(func.count()).select_from(Assignment).where(Assignment.status=="active")) or 0
    recent_days=select(AttendanceEvent.event_date).distinct().order_by(AttendanceEvent.event_date.desc()).limit(14).subquery()
    trend_rows=db.execute(
        select(AttendanceEvent.event_date,AttendanceEvent.status,func.count())
        .where(AttendanceEvent.event_date.in_(select(recent_days.c.event_date)))
        .group_by(AttendanceEvent.event_date,AttendanceEvent.status)
        .order_by(AttendanceEvent.event_date)
    ).all()
    trend_by_day={}
    for event_date,status,count in trend_rows:
        day=event_date.isoformat()
        trend_by_day.setdefault(day,{"date":day,"statuses":{"boarded":0,"absent":0,"missed_pickup":0}})
        if status in trend_by_day[day]["statuses"]:
            trend_by_day[day]["statuses"][status]=count
    zone_rows=db.execute(
        select(
            Zone.name,
            func.count(func.distinct(Student.id)),
            func.count(func.distinct(Assignment.student_id)),
        )
        .select_from(Zone)
        .outerjoin(Student,and_(Student.zone_id==Zone.id,Student.status=="active"))
        .outerjoin(Assignment,and_(Assignment.student_id==Student.id,Assignment.status=="active"))
        .group_by(Zone.id,Zone.name)
        .order_by(Zone.name)
    ).all()
    route_rows=db.execute(
        select(Route.id,func.count(func.distinct(Assignment.student_id)),Bus.capacity)
        .join(Bus,Route.bus_id==Bus.id)
        .outerjoin(Assignment,and_(Assignment.route_id==Route.id,Assignment.status=="active"))
        .where(Route.status=="active",Bus.lifecycle=="active")
        .group_by(Route.id,Bus.capacity)
    ).all()
    routes=[
        {"route":route_id,"allocated":allocated,"capacity":capacity,"utilization":round(allocated/capacity*100,1) if capacity else 0}
        for route_id,allocated,capacity in route_rows
    ]
    routes.sort(key=lambda route:(-route["utilization"],route["route"]))
    return {
        "summary":{
            "active_students":active_students,
            "active_assignments":active_assignments,
            "unallocated_students":max(0,active_students-active_assignments),
            "attendance_events":attendance_total,
            "boarded_rate":boarded_rate,
        },
        "attendance":attendance_counts,
        "attendance_trend":list(trend_by_day.values()),
        "zone_allocation":[
            {"zone":name,"students":students,"allocated":allocated,"unallocated":students-allocated}
            for name,students,allocated in zone_rows
        ],
        "route_utilization":routes[:8],
    }
@app.get("/api/v1/allocation/unallocated")
def unallocated(db:Session=Depends(get_db)):
    ids=select(Assignment.student_id).where(Assignment.status=="active"); result=[]
    for s in db.scalars(select(Student).where(Student.status=="active",Student.id.not_in(ids))).all():
        _, reasons=candidates_for(db,s); result.append({"student_id":s.id,"student":s.name,"reasons":reasons or ["Awaiting allocation"],"action":"Run automatic allocation or add capacity"})
    return result
@app.post("/api/v1/allocation/run")
def run(payload:AllocationRun,_=Depends(admin),db:Session=Depends(get_db)):
    ids=select(Assignment.student_id).where(Assignment.status=="active"); q=select(Student).where(Student.status=="active",Student.id.not_in(ids))
    if payload.student_ids: q=q.where(Student.id.in_(payload.student_ids))
    students=list(db.scalars(q).all()); picks, failures=choose_collectively(db,students); saved=[view(db,save(db,s,picks[s.id],"automatic_allocation")) for s in students if s.id in picks]; db.commit()
    return {"allocated":saved,"unallocated":[{"student_id":k,"reasons":v} for k,v in failures.items()]}
@app.post("/api/v1/allocation/manual")
def manual(p:ManualAssignment,_=Depends(admin),db:Session=Depends(get_db)):
    s=db.get(Student,p.student_id)
    if not s: raise HTTPException(404,"Student not found")
    options,reasons=candidates_for(db,s); candidate=next((x for x in options if x.route.id==p.route_id and x.stop.id==p.stop_id),None)
    if not candidate: raise HTTPException(409,{"message":"Manual assignment violates constraints","reasons":reasons})
    item=save(db,s,candidate,"manual_allocation"); db.commit(); return view(db,item)
@app.post("/api/v1/allocation/reallocate")
def reallocate(p:ReallocationRequest,_=Depends(admin),db:Session=Depends(get_db)):
    resource=db.get(Bus if p.resource_type=="bus" else Driver,p.resource_id)
    if not resource: raise HTTPException(404,"Resource not found")
    resource.available=False; routes=select(Route.id).where(Route.bus_id==p.resource_id) if p.resource_type=="bus" else select(Route.id).where(Route.driver_id==p.resource_id)
    affected=list(db.scalars(select(Assignment).where(Assignment.status=="active",Assignment.route_id.in_(routes))).all()); students=[db.get(Student,x.student_id) for x in affected]
    for x in affected: x.status="ended"; x.effective_to=date.today(); db.add(AuditEvent(assignment_id=x.id,event_type="resource_unavailable",detail=f"{p.resource_type} unavailable"))
    db.flush(); picks,failures=choose_collectively(db,students); saved=[view(db,save(db,s,picks[s.id],"automatic_reallocation")) for s in students if s.id in picks]; db.commit(); return {"reallocated":saved,"unallocated":[{"student_id":k,"reasons":v} for k,v in failures.items()]}
@app.get("/api/v1/allocation/{student_id}/history")
def history(student_id:str,db:Session=Depends(get_db)): return [view(db,x) for x in db.scalars(select(Assignment).where(Assignment.student_id==student_id).order_by(Assignment.effective_from.desc())).all()]
@app.get("/")
def ui(): return FileResponse(Path(__file__).parents[2]/"frontend"/"index.html")
@app.get("/analytics")
def analytics_ui(): return FileResponse(Path(__file__).parents[2]/"frontend"/"analytics.html")
@app.get("/login")
def login_ui(): return FileResponse(Path(__file__).parents[2]/"frontend"/"login.html")
@app.get("/portal/admin")
def admin_portal(): return FileResponse(Path(__file__).parents[2]/"frontend"/"admin.html")
@app.get("/portal/driver")
def driver_portal(): return FileResponse(Path(__file__).parents[2]/"frontend"/"driver.html")
@app.get("/portal/parent")
def parent_portal(): return FileResponse(Path(__file__).parents[2]/"frontend"/"parent.html")
