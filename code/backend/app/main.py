from __future__ import annotations

import time as clock
import threading
from contextlib import asynccontextmanager
from datetime import date as Date, datetime, time, timedelta
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .database import Base, SessionLocal, engine, get_db
from .models import (
    Allocation, Classroom, CourseClass, OptimizationSettings, RoomUnavailability, Schedule,
    SimulationResult,
)
from .seed import seed_demo_data
from .services.allocation_engine import Weights, allocate, candidate_score, metrics, overlaps, rejection_reasons


class RoomInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    building: str = Field(min_length=1, max_length=80)
    department_preference: str = Field(default="", max_length=80)
    capacity: int = Field(gt=0, le=2000)
    projector: bool = False
    smart_board: bool = False
    computers: bool = False
    air_conditioning: bool = False
    accessibility_support: bool = False
    is_active: bool = True
    estimated_power_kw: float | None = Field(default=None, ge=0, le=1000)


class ClassInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=80)
    student_count: int = Field(gt=0, le=2000)
    required_projector: bool = False
    required_smart_board: bool = False
    required_computers: bool = False
    required_accessibility: bool = False
    preferred_building: str = Field(default="", max_length=80)
    preferred_department: str = Field(default="", max_length=80)
    priority: int = Field(default=1, ge=1, le=5)


class ClassScheduleInput(ClassInput):
    date: Date | None = None
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        values = (self.date, self.start_time, self.end_time)
        if any(value is not None for value in values) and not all(value is not None for value in values):
            raise ValueError("Date, start time, and end time must be provided together.")
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValueError("Start time must be earlier than end time.")
        return self


class ScheduleInput(BaseModel):
    class_id: int
    date: Date
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def valid_interval(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be earlier than end time.")
        return self


class AllocationRunInput(BaseModel):
    algorithm: str = Field(default="optimized", pattern="^(optimized|first_fit|random)$")
    replace_existing: bool = False
    random_seed: int = 42


class UnavailabilityInput(BaseModel):
    date: Date
    start_time: time
    end_time: time
    reason: str = Field(default="Maintenance", max_length=240)
    apply: bool = False

    @model_validator(mode="after")
    def valid_interval(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be earlier than end time.")
        return self


class SettingsInput(BaseModel):
    seat_weight: float = Field(ge=0, le=10000)
    department_weight: float = Field(ge=0, le=10000)
    building_weight: float = Field(ge=0, le=10000)
    disruption_weight: float = Field(ge=0, le=10000)
    energy_weight: float = Field(ge=0, le=10000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(title="CampusFlow API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
_allocation_lock = threading.Lock()
P = ParamSpec("P")
R = TypeVar("R")


def allocation_serialized(endpoint: Callable[P, R]) -> Callable[P, R]:
    @wraps(endpoint)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        with _allocation_lock:
            return endpoint(*args, **kwargs)
    return guarded


def _class_dict(course: CourseClass) -> dict:
    return {key: getattr(course, key) for key in (
        "id", "name", "department", "student_count", "required_projector", "required_smart_board",
        "required_computers", "required_accessibility", "preferred_building", "preferred_department",
        "priority", "created_at",
    )}


def _room_dict(room: Classroom) -> dict:
    return {key: getattr(room, key) for key in (
        "id", "name", "building", "department_preference", "capacity", "projector", "smart_board",
        "computers", "air_conditioning", "accessibility_support", "is_active", "estimated_power_kw",
        "created_at",
    )}


def _schedule_dict(schedule: Schedule) -> dict:
    return {
        "id": schedule.id, "class_id": schedule.class_id, "date": schedule.date,
        "start_time": schedule.start_time, "end_time": schedule.end_time,
        "class": _class_dict(schedule.course_class),
    }


def _item_dict(schedule: Schedule) -> dict:
    course = schedule.course_class
    return {
        "id": schedule.id, "class_id": course.id, "name": course.name, "department": course.department,
        "student_count": course.student_count, "required_projector": course.required_projector,
        "required_smart_board": course.required_smart_board, "required_computers": course.required_computers,
        "required_accessibility": course.required_accessibility, "preferred_building": course.preferred_building,
        "preferred_department": course.preferred_department, "priority": course.priority,
        "date": schedule.date, "start_time": schedule.start_time, "end_time": schedule.end_time,
    }


def _unavailability_rows(db: Session) -> list[dict]:
    return [{
        "classroom_id": row.classroom_id, "date": row.date, "start_time": row.start_time,
        "end_time": row.end_time, "reason": row.reason,
    } for row in db.query(RoomUnavailability).all()]


def _weights(db: Session) -> Weights:
    settings = db.query(OptimizationSettings).first()
    return Weights(
        seat=settings.seat_weight if settings else 1,
        department=settings.department_weight if settings else 30,
        building=settings.building_weight if settings else 15,
        energy=settings.energy_weight if settings else 0,
    )


def _allocation_dict(row: Allocation) -> dict:
    sched = row.schedule
    room = row.classroom
    course = row.course_class
    return {
        "id": row.id, "schedule_id": sched.id, "class_id": course.id, "class_name": course.name,
        "department": course.department, "student_count": course.student_count, "date": sched.date,
        "start_time": sched.start_time, "end_time": sched.end_time, "classroom_id": room.id if room else None,
        "classroom_name": room.name if room else None, "building": room.building if room else None,
        "capacity": room.capacity if room else None,
        "unused_seats": room.capacity - course.student_count if room else None,
        "utilization_percentage": round(course.student_count / room.capacity * 100, 1) if room else None,
        "status": row.status, "algorithm_name": row.algorithm_name, "explanation": row.explanation,
        "reason": row.explanation if row.status == "unallocated" else None,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CampusFlow API"}


@app.get("/api/classrooms")
def list_classrooms(db: Session = Depends(get_db), search: str = "", building: str = "", facility: str = ""):
    query = db.query(Classroom)
    if search:
        query = query.filter(or_(Classroom.name.ilike(f"%{search}%"), Classroom.building.ilike(f"%{search}%")))
    if building:
        query = query.filter(Classroom.building == building)
    if facility:
        allowed = {"projector": Classroom.projector, "smart_board": Classroom.smart_board, "computers": Classroom.computers, "accessibility": Classroom.accessibility_support}
        if facility not in allowed:
            raise HTTPException(422, "Unknown facility filter.")
        query = query.filter(allowed[facility].is_(True))
    return [_room_dict(row) for row in query.order_by(Classroom.name).all()]


@app.post("/api/classrooms", status_code=201)
def create_classroom(payload: RoomInput, db: Session = Depends(get_db)):
    if db.query(Classroom).filter(Classroom.name == payload.name).first():
        raise HTTPException(409, "A classroom with this name already exists.")
    row = Classroom(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _room_dict(row)


@app.get("/api/classrooms/{room_id}")
def get_classroom(room_id: int, db: Session = Depends(get_db)):
    row = db.get(Classroom, room_id)
    if not row:
        raise HTTPException(404, "Classroom not found.")
    return {**_room_dict(row), "allocations": [_allocation_dict(a) for a in row.allocations]}


@app.put("/api/classrooms/{room_id}")
def update_classroom(room_id: int, payload: RoomInput, db: Session = Depends(get_db)):
    row = db.get(Classroom, room_id)
    if not row:
        raise HTTPException(404, "Classroom not found.")
    duplicate = db.query(Classroom).filter(Classroom.name == payload.name, Classroom.id != room_id).first()
    if duplicate:
        raise HTTPException(409, "A classroom with this name already exists.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _room_dict(row)


@app.delete("/api/classrooms/{room_id}", status_code=204)
def delete_classroom(room_id: int, db: Session = Depends(get_db)):
    row = db.get(Classroom, room_id)
    if not row:
        raise HTTPException(404, "Classroom not found.")
    if db.query(Allocation).filter(Allocation.classroom_id == room_id).first():
        raise HTTPException(409, "This room has allocations; mark it unavailable instead of deleting it.")
    db.delete(row)
    db.commit()


@app.get("/api/classes")
def list_classes(db: Session = Depends(get_db), search: str = "", department: str = ""):
    query = db.query(CourseClass)
    if search:
        query = query.filter(CourseClass.name.ilike(f"%{search}%"))
    if department:
        query = query.filter(CourseClass.department == department)
    return [{
        **_class_dict(row),
        "schedules": [{
            "id": s.id, "date": s.date, "start_time": s.start_time, "end_time": s.end_time,
            "allocation": _allocation_dict(s.allocation) if s.allocation else None,
        } for s in row.schedules],
    } for row in query.order_by(CourseClass.name).all()]


@app.post("/api/classes", status_code=201)
def create_class(payload: ClassScheduleInput, db: Session = Depends(get_db)):
    values = payload.model_dump(exclude={"date", "start_time", "end_time"})
    row = CourseClass(**values)
    db.add(row)
    db.flush()
    if payload.date and payload.start_time and payload.end_time:
        db.add(Schedule(
            class_id=row.id, date=payload.date, start_time=payload.start_time, end_time=payload.end_time,
        ))
    db.commit()
    db.refresh(row)
    return _class_dict(row)


@app.get("/api/classes/{class_id}")
def get_class(class_id: int, db: Session = Depends(get_db)):
    row = db.get(CourseClass, class_id)
    if not row:
        raise HTTPException(404, "Class not found.")
    return {**_class_dict(row), "schedules": [_schedule_dict(s) for s in row.schedules]}


@app.put("/api/classes/{class_id}")
def update_class(class_id: int, payload: ClassScheduleInput, db: Session = Depends(get_db)):
    row = db.get(CourseClass, class_id)
    if not row:
        raise HTTPException(404, "Class not found.")
    schedule = row.schedules[0] if row.schedules else None
    schedule_values = (payload.date, payload.start_time, payload.end_time)
    if all(value is not None for value in schedule_values):
        if schedule and schedule.allocation and (schedule.date, schedule.start_time, schedule.end_time) != schedule_values:
            raise HTTPException(409, "Clear the existing allocation before changing this schedule.")
        if not schedule:
            schedule = Schedule(class_id=row.id)
            db.add(schedule)
    for key, value in payload.model_dump(exclude={"date", "start_time", "end_time"}).items():
        setattr(row, key, value)
    if schedule and all(value is not None for value in schedule_values):
        schedule.date, schedule.start_time, schedule.end_time = schedule_values
    db.commit()
    db.refresh(row)
    return _class_dict(row)


@app.delete("/api/classes/{class_id}", status_code=204)
def delete_class(class_id: int, db: Session = Depends(get_db)):
    row = db.get(CourseClass, class_id)
    if not row:
        raise HTTPException(404, "Class not found.")
    db.delete(row)
    db.commit()


@app.get("/api/schedules")
def list_schedules(db: Session = Depends(get_db), on_date: Date | None = Query(default=None, alias="date")):
    query = db.query(Schedule).options(joinedload(Schedule.course_class)).order_by(Schedule.date, Schedule.start_time)
    if on_date:
        query = query.filter(Schedule.date == on_date)
    return [_schedule_dict(row) for row in query.all()]


@app.get("/api/unavailability")
def list_unavailabilities(db: Session = Depends(get_db)):
    rows = db.query(RoomUnavailability).options(joinedload(RoomUnavailability.classroom)).order_by(
        RoomUnavailability.date, RoomUnavailability.start_time,
    ).all()
    return [{
        "id": row.id, "classroom_id": row.classroom_id, "classroom_name": row.classroom.name,
        "date": row.date, "start_time": row.start_time, "end_time": row.end_time, "reason": row.reason,
    } for row in rows]


@app.post("/api/schedules", status_code=201)
def create_schedule(payload: ScheduleInput, db: Session = Depends(get_db)):
    if not db.get(CourseClass, payload.class_id):
        raise HTTPException(404, "Class not found.")
    row = Schedule(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _schedule_dict(row)


@app.put("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleInput, db: Session = Depends(get_db)):
    row = db.get(Schedule, schedule_id)
    if not row or not db.get(CourseClass, payload.class_id):
        raise HTTPException(404, "Schedule or class not found.")
    if row.allocation and row.allocation.classroom_id is not None and (row.date, row.start_time, row.end_time) != (payload.date, payload.start_time, payload.end_time):
        raise HTTPException(409, "Clear the existing allocation before changing this schedule.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return _schedule_dict(row)


def _dataset(db: Session):
    rooms = db.query(Classroom).order_by(Classroom.id).all()
    schedules = db.query(Schedule).options(joinedload(Schedule.course_class)).order_by(Schedule.date, Schedule.start_time).all()
    return rooms, schedules, _unavailability_rows(db)


@app.post("/api/allocations/run")
@allocation_serialized
def run_allocations(payload: AllocationRunInput, db: Session = Depends(get_db)):
    existing = db.query(Allocation).count()
    if existing and not payload.replace_existing:
        raise HTTPException(409, "Confirmed allocations already exist. Confirm replacement to regenerate them.")
    rooms, schedules, unavailabilities = _dataset(db)
    started = clock.perf_counter()
    result = allocate(rooms, [_item_dict(row) for row in schedules], unavailabilities, payload.algorithm, _weights(db), payload.random_seed)
    runtime = (clock.perf_counter() - started) * 1000
    try:
        if payload.replace_existing:
            db.query(Allocation).delete(synchronize_session=False)
        for row in result["results"]:
            db.add(Allocation(
                class_id=row["class_id"], schedule_id=row["schedule_id"], classroom_id=row["classroom_id"],
                status="confirmed" if row["status"] == "allocated" else "unallocated",
                algorithm_name=payload.algorithm,
                explanation=row.get("explanation", row.get("reason", "")),
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, "Allocation transaction failed; previous allocations were preserved.")
    result["metrics"] = metrics(result["results"], len(schedules), runtime, payload.random_seed if payload.algorithm == "random" else None)
    return result


@app.get("/api/allocations")
def list_allocations(db: Session = Depends(get_db), on_date: Date | None = Query(default=None, alias="date")):
    query = db.query(Allocation).options(
        joinedload(Allocation.schedule), joinedload(Allocation.classroom), joinedload(Allocation.course_class),
    ).join(Schedule).order_by(Schedule.date, Schedule.start_time)
    if on_date:
        query = query.filter(Schedule.date == on_date)
    return [_allocation_dict(row) for row in query.all()]


@app.get("/api/allocations/conflicts")
def list_conflicts(db: Session = Depends(get_db)):
    rows = db.query(Allocation).filter(Allocation.classroom_id.is_not(None)).options(
        joinedload(Allocation.schedule), joinedload(Allocation.classroom), joinedload(Allocation.course_class),
    ).all()
    conflicts = []
    for index, first in enumerate(rows):
        for second in rows[index + 1:]:
            if first.classroom_id == second.classroom_id and first.schedule.date == second.schedule.date and overlaps(
                first.schedule.start_time, first.schedule.end_time, second.schedule.start_time, second.schedule.end_time
            ):
                conflicts.append({"type": "overlap", "allocations": [first.id, second.id], "message": f"{first.classroom.name} is double-booked."})
        item = _item_dict(first.schedule)
        if first.classroom.capacity < first.course_class.student_count or not first.classroom.is_active:
            conflicts.append({"type": "hard_constraint", "allocations": [first.id], "message": f"{first.course_class.name} violates room capacity or room activity."})
        if rejection_reasons(first.classroom, item, _unavailability_rows(db), []):
            reasons = rejection_reasons(first.classroom, item, _unavailability_rows(db), [])
            if reasons:
                conflicts.append({"type": "room_constraint", "allocations": [first.id], "message": f"{first.course_class.name}: {'; '.join(reasons)}"})
    return conflicts


@app.get("/api/allocations/{allocation_id}")
def get_allocation(allocation_id: int, db: Session = Depends(get_db)):
    row = db.query(Allocation).options(
        joinedload(Allocation.schedule), joinedload(Allocation.classroom), joinedload(Allocation.course_class),
    ).filter(Allocation.id == allocation_id).first()
    if not row:
        raise HTTPException(404, "Allocation not found.")
    return _allocation_dict(row)


@app.post("/api/classrooms/{room_id}/unavailability")
@allocation_serialized
def create_unavailability(room_id: int, payload: UnavailabilityInput, db: Session = Depends(get_db)):
    room = db.get(Classroom, room_id)
    if not room:
        raise HTTPException(404, "Classroom not found.")
    affected = db.query(Allocation).options(joinedload(Allocation.schedule), joinedload(Allocation.course_class)).filter(
        Allocation.classroom_id == room_id
    ).all()
    affected = [row for row in affected if row.schedule.date == payload.date and overlaps(
        row.schedule.start_time, row.schedule.end_time, payload.start_time, payload.end_time
    )]
    all_rooms, _, all_unavailabilities = _dataset(db)
    weights = _weights(db)
    settings = db.query(OptimizationSettings).first()
    disruption_weight = settings.disruption_weight if settings else 50.0
    outage = {
        "classroom_id": room_id, "date": payload.date, "start_time": payload.start_time,
        "end_time": payload.end_time, "reason": payload.reason,
    }
    new_unavailability = all_unavailabilities + [outage]
    moved_schedule_ids = {row.schedule_id for row in affected}
    occupied = [{
        "room_id": row.classroom_id, "date": row.schedule.date, "start_time": row.schedule.start_time,
        "end_time": row.schedule.end_time, "name": row.course_class.name,
    } for row in db.query(Allocation).options(joinedload(Allocation.schedule), joinedload(Allocation.course_class)).all()
        if row.schedule_id not in moved_schedule_ids]
    proposals = []
    schedule_items = []
    for allocation in affected:
        item = _item_dict(allocation.schedule)
        eligible = [
            candidate for candidate in all_rooms
            if candidate.id != room_id and not rejection_reasons(candidate, item, new_unavailability, occupied)
        ]
        eligible.sort(key=lambda candidate: (
            candidate_score(candidate, item, weights)
            + (disruption_weight if candidate.building != room.building else 0),
            candidate.id,
        ))
        replacement = eligible[0] if eligible else None
        proposals.append({
            "allocation_id": allocation.id, "schedule_id": allocation.schedule_id, "class_name": allocation.course_class.name,
            "from_room": room.name, "to_room": replacement.name if replacement else None,
            "status": "proposed" if replacement else "unresolved",
            "reason": f"{replacement.name} meets room and timetable constraints with minimal preference/capacity cost." if replacement else "No valid alternative room is available for this time.",
        })
        if replacement:
            occupied.append({
                "room_id": replacement.id, "date": allocation.schedule.date,
                "start_time": allocation.schedule.start_time, "end_time": allocation.schedule.end_time,
                "name": allocation.course_class.name,
            })
            schedule_items.append((allocation, replacement))
    if payload.apply:
        if any(item["status"] == "unresolved" for item in proposals):
            raise HTTPException(409, "Not all affected classes have valid alternatives; no changes were applied.")
        try:
            db.add(RoomUnavailability(**outage))
            for allocation, replacement in schedule_items:
                allocation.classroom_id = replacement.id
                allocation.explanation = f"Emergency reassignment to {replacement.name}: suitable and available for the complete session."
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(500, "Reassignment failed; no changes were committed.")
    return {
        "room": room.name, "date": payload.date, "affected_count": len(affected),
        "applied": payload.apply, "proposals": proposals,
        "message": "Reassignments applied atomically." if payload.apply else "Review these proposed changes; set apply=true to confirm.",
    }


@app.post("/api/simulations/compare")
def compare_algorithms(seed: int = 42, scenario_name: str = "Current timetable", db: Session = Depends(get_db)):
    rooms, schedules, unavailabilities = _dataset(db)
    items = [_item_dict(row) for row in schedules]
    comparisons = []
    for method in ("random", "first_fit", "optimized"):
        started = clock.perf_counter()
        outcome = allocate(rooms, items, unavailabilities, method, _weights(db), seed)
        elapsed = (clock.perf_counter() - started) * 1000
        summary = metrics(outcome["results"], len(items), elapsed, seed if method == "random" else None)
        energy_values = [
            row["energy_kwh"] for row in outcome["results"]
            if row["status"] == "allocated" and row["energy_kwh"] is not None
        ]
        summary["estimated_energy_kwh"] = round(sum(energy_values), 2)
        summary["sessions_with_energy_estimate"] = len(energy_values)
        comparisons.append({"algorithm": method, **summary})
        db.add(SimulationResult(
            scenario_name=scenario_name, algorithm_name=method,
            successful_allocations=summary["successful_allocations"], unallocated_classes=summary["unallocated_classes"],
            unused_seats=summary["unused_seats"], utilization_percentage=summary["utilization_percentage"],
            preference_penalty=summary["preference_penalty"], runtime_ms=summary["runtime_ms"],
            random_seed=seed if method == "random" else None,
        ))
    db.commit()
    return {"scenario_name": scenario_name, "random_seed": seed, "total_scheduled_classes": len(items), "results": comparisons}


@app.get("/api/simulations/history")
def simulation_history(db: Session = Depends(get_db)):
    rows = db.query(SimulationResult).order_by(SimulationResult.created_at.desc()).limit(50).all()
    return [{
        "id": row.id, "scenario_name": row.scenario_name, "algorithm_name": row.algorithm_name,
        "successful_allocations": row.successful_allocations, "unallocated_classes": row.unallocated_classes,
        "unused_seats": row.unused_seats, "utilization_percentage": row.utilization_percentage,
        "preference_penalty": row.preference_penalty, "runtime_ms": row.runtime_ms,
        "random_seed": row.random_seed, "created_at": row.created_at,
    } for row in rows]


@app.get("/api/analytics/utilization")
def utilization(db: Session = Depends(get_db)):
    rows = db.query(Allocation).filter(Allocation.classroom_id.is_not(None)).options(joinedload(Allocation.classroom), joinedload(Allocation.course_class)).all()
    by_room: dict[int, dict] = {}
    for row in rows:
        record = by_room.setdefault(row.classroom_id, {
            "classroom_id": row.classroom_id, "classroom_name": row.classroom.name,
            "building": row.classroom.building, "capacity": row.classroom.capacity, "students": 0, "sessions": 0,
        })
        record["students"] += row.course_class.student_count
        record["sessions"] += 1
    return [{
        **row, "seat_utilization": round(row["students"] / (row["capacity"] * row["sessions"]) * 100, 1)
        if row["capacity"] and row["sessions"] else 0.0,
    } for row in by_room.values()]


@app.get("/api/analytics/sustainability")
def sustainability(db: Session = Depends(get_db)):
    allocated = db.query(Allocation).filter(Allocation.classroom_id.is_not(None)).options(
        joinedload(Allocation.schedule), joinedload(Allocation.classroom), joinedload(Allocation.course_class),
    ).all()
    known = [row for row in allocated if row.classroom.estimated_power_kw is not None]
    energy = sum(
        row.classroom.estimated_power_kw * max(
            (row.schedule.end_time.hour * 60 + row.schedule.end_time.minute - row.schedule.start_time.hour * 60 - row.schedule.start_time.minute) / 60, 0
        ) for row in known
    )
    return {
        "estimated_energy_kwh": round(energy, 2), "sessions_with_power_estimate": len(known),
        "sessions_without_power_estimate": len(allocated) - len(known),
        "assumption": "Estimate = room rated kW × scheduled session hours; does not imply measured consumption or carbon savings.",
    }


@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(OptimizationSettings).first()
    if not settings:
        settings = OptimizationSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return {key: getattr(settings, key) for key in (
        "seat_weight", "department_weight", "building_weight", "disruption_weight", "energy_weight",
    )}


@app.put("/api/settings")
def update_settings(payload: SettingsInput, db: Session = Depends(get_db)):
    settings = db.query(OptimizationSettings).first()
    if not settings:
        settings = OptimizationSettings()
        db.add(settings)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    return payload.model_dump()


@app.post("/api/demo/reset")
def reset_demo_data(db: Session = Depends(get_db)):
    try:
        db.query(Allocation).delete(synchronize_session=False)
        db.query(Schedule).delete(synchronize_session=False)
        db.query(CourseClass).delete(synchronize_session=False)
        db.query(RoomUnavailability).delete(synchronize_session=False)
        db.query(Classroom).delete(synchronize_session=False)
        db.query(SimulationResult).delete(synchronize_session=False)
        db.query(OptimizationSettings).delete(synchronize_session=False)
        db.flush()
        seed_demo_data(db)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Demo data reset failed; no partial reset was committed.")
    return {"message": "Demonstration data reset.", "classrooms": db.query(Classroom).count(), "classes": db.query(CourseClass).count()}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    rooms, schedules, _ = _dataset(db)
    allocations = db.query(Allocation).filter(Allocation.classroom_id.is_not(None)).options(
        joinedload(Allocation.schedule), joinedload(Allocation.classroom), joinedload(Allocation.course_class),
    ).all()
    conflicts = list_conflicts(db)
    valid_ids = {item["allocations"][0] for item in conflicts if "allocations" in item}
    valid = [row for row in allocations if row.id not in valid_ids]
    students = sum(row.course_class.student_count for row in valid)
    capacity = sum(row.classroom.capacity for row in valid)
    today = Date.today()
    used_now = {row.classroom_id for row in allocations if row.schedule.date == today and
                row.schedule.start_time <= datetime.now().time() < row.schedule.end_time}
    utilization_by_room = {}
    for row in allocations:
        entry = utilization_by_room.setdefault(row.classroom_id, {"name": row.classroom.name, "capacity": row.classroom.capacity, "students": 0, "count": 0})
        entry["students"] += row.course_class.student_count
        entry["count"] += 1
    chart = []
    for room in rooms:
        entry = utilization_by_room.get(room.id, {
            "name": room.name, "capacity": room.capacity, "students": 0, "count": 0,
        })
        chart.append({
            "name": entry["name"],
            "utilization": round(entry["students"] / (entry["capacity"] * entry["count"]) * 100, 1)
            if entry["capacity"] and entry["count"] else 0,
            "sessions": entry["count"],
        })
    allocations_by_schedule = {row.schedule_id: row for row in allocations}
    items = [_item_dict(row) for row in schedules]
    weights = _weights(db)
    baseline = allocate(rooms, items, _unavailability_rows(db), "first_fit", weights)["results"]
    optimized = allocate(rooms, items, _unavailability_rows(db), "optimized", weights)["results"]
    baseline_by_schedule = {row["schedule_id"]: row for row in baseline if row["status"] == "allocated"}
    optimized_by_schedule = {row["schedule_id"]: row for row in optimized if row["status"] == "allocated"}
    common_schedules = set(baseline_by_schedule) & set(optimized_by_schedule)
    energy_savings = None
    if common_schedules and all(
        baseline_by_schedule[key]["energy_kwh"] is not None
        and optimized_by_schedule[key]["energy_kwh"] is not None
        for key in common_schedules
    ):
        energy_savings = round(sum(
            baseline_by_schedule[key]["energy_kwh"] - optimized_by_schedule[key]["energy_kwh"]
            for key in common_schedules
        ), 2)
    next_sessions = [{
        "id": row.id, "class_name": row.course_class.name, "department": row.course_class.department,
        "room": allocations_by_schedule[row.id].classroom.name if row.id in allocations_by_schedule else "Unallocated",
        "date": row.date, "start_time": row.start_time, "end_time": row.end_time,
    } for row in sorted(schedules, key=lambda item: (item.date, item.start_time)) if row.date >= today][:6]
    return {
        "total_classrooms": len(rooms), "active_classrooms": sum(room.is_active for room in rooms),
        "available_classrooms": max(sum(room.is_active for room in rooms) - len(used_now), 0),
        "total_classes": db.query(CourseClass).count(), "total_scheduled": len(schedules),
        "successful_allocations": len(valid), "unallocated_classes": max(len(schedules) - len(valid), 0),
        "conflicts_detected": len(conflicts),
        "average_seat_utilization": round(students / capacity * 100, 1) if capacity else 0,
        "estimated_energy_kwh": sustainability(db)["estimated_energy_kwh"],
        "potential_energy_savings_kwh": energy_savings,
        "energy_comparison_sessions": len(common_schedules),
        "room_utilization": chart, "allocation_status": [
            {"name": "Allocated", "value": len(valid)}, {"name": "Unallocated", "value": max(len(schedules) - len(valid), 0)},
        ],
        "recent_activity": [{
            "class_name": row.course_class.name, "room": row.classroom.name,
            "date": row.schedule.date, "algorithm": row.algorithm_name,
        } for row in sorted(allocations, key=lambda item: item.created_at, reverse=True)[:5]],
        "upcoming_classes": next_sessions, "conflicts": conflicts[:5],
    }
