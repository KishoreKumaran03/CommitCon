from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_classroom_capacity_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    building: Mapped[str] = mapped_column(String(80), index=True)
    department_preference: Mapped[str] = mapped_column(String(80), default="")
    capacity: Mapped[int] = mapped_column(Integer)
    projector: Mapped[bool] = mapped_column(Boolean, default=False)
    smart_board: Mapped[bool] = mapped_column(Boolean, default=False)
    computers: Mapped[bool] = mapped_column(Boolean, default=False)
    air_conditioning: Mapped[bool] = mapped_column(Boolean, default=False)
    accessibility_support: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="classroom")
    unavailabilities: Mapped[list["RoomUnavailability"]] = relationship(back_populates="classroom")


class CourseClass(Base):
    __tablename__ = "classes"
    __table_args__ = (CheckConstraint("student_count > 0", name="ck_class_student_count_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    department: Mapped[str] = mapped_column(String(80), index=True)
    student_count: Mapped[int] = mapped_column(Integer)
    required_projector: Mapped[bool] = mapped_column(Boolean, default=False)
    required_smart_board: Mapped[bool] = mapped_column(Boolean, default=False)
    required_computers: Mapped[bool] = mapped_column(Boolean, default=False)
    required_accessibility: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_building: Mapped[str] = mapped_column(String(80), default="")
    preferred_department: Mapped[str] = mapped_column(String(80), default="")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="course_class", cascade="all, delete-orphan")


class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date)
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    course_class: Mapped[CourseClass] = relationship(back_populates="schedules")
    allocation: Mapped["Allocation | None"] = relationship(back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    __table_args__ = (
        Index("ix_schedule_date_time", "date", "start_time", "end_time"),
        CheckConstraint("start_time < end_time", name="ck_schedule_time_order"),
    )


class Allocation(Base):
    __tablename__ = "allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), unique=True)
    classroom_id: Mapped[int | None] = mapped_column(ForeignKey("classrooms.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    algorithm_name: Mapped[str] = mapped_column(String(40), default="optimized")
    explanation: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    course_class: Mapped[CourseClass] = relationship(back_populates="allocations")
    schedule: Mapped[Schedule] = relationship(back_populates="allocation")
    classroom: Mapped[Classroom | None] = relationship(back_populates="allocations")
    __table_args__ = (CheckConstraint("status IN ('confirmed', 'unallocated')", name="ck_allocation_status"),)


class RoomUnavailability(Base):
    __tablename__ = "room_unavailabilities"
    __table_args__ = (CheckConstraint("start_time < end_time", name="ck_unavailability_time_order"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(String(240), default="Maintenance")
    classroom: Mapped[Classroom] = relationship(back_populates="unavailabilities")


class SimulationResult(Base):
    __tablename__ = "simulation_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_name: Mapped[str] = mapped_column(String(100))
    algorithm_name: Mapped[str] = mapped_column(String(40))
    successful_allocations: Mapped[int] = mapped_column(Integer)
    unallocated_classes: Mapped[int] = mapped_column(Integer)
    unused_seats: Mapped[int] = mapped_column(Integer)
    utilization_percentage: Mapped[float] = mapped_column(Float)
    preference_penalty: Mapped[float] = mapped_column(Float)
    runtime_ms: Mapped[float] = mapped_column(Float)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OptimizationSettings(Base):
    __tablename__ = "optimization_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    seat_weight: Mapped[float] = mapped_column(Float, default=1.0)
    department_weight: Mapped[float] = mapped_column(Float, default=30.0)
    building_weight: Mapped[float] = mapped_column(Float, default=15.0)
    disruption_weight: Mapped[float] = mapped_column(Float, default=50.0)
    energy_weight: Mapped[float] = mapped_column(Float, default=0.0)
