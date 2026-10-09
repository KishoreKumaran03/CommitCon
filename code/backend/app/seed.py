from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from .models import Classroom, CourseClass, OptimizationSettings, RoomUnavailability, Schedule


def seed_demo_data(db: Session) -> None:
    if db.query(Classroom).first():
        return
    rooms_data = [
        ("A-101", "North Academic", "Computer Science", 40, True, False, True, True, True, 2.4),
        ("A-102", "North Academic", "Computer Science", 60, True, True, True, True, True, 3.2),
        ("A-201", "North Academic", "Mathematics", 80, True, True, False, True, True, 3.8),
        ("A-202", "North Academic", "Mathematics", 120, True, False, False, True, True, 5.0),
        ("A-301", "North Academic", "Physics", 36, True, True, True, False, True, 2.1),
        ("A-302", "North Academic", "Physics", 72, True, True, True, True, True, 3.5),
        ("B-101", "Innovation Hub", "Computer Science", 48, True, True, True, True, True, 2.8),
        ("B-102", "Innovation Hub", "Computer Science", 96, True, True, True, True, True, 4.3),
        ("B-201", "Innovation Hub", "Electronics", 54, True, True, True, True, True, 3.0),
        ("B-202", "Innovation Hub", "Electronics", 110, True, True, True, True, True, 4.8),
        ("C-101", "Central Block", "Business", 45, True, False, False, True, True, 2.5),
        ("C-102", "Central Block", "Business", 90, True, True, False, True, True, 4.0),
        ("C-201", "Central Block", "Arts", 70, True, False, False, False, True, 3.0),
        ("C-202", "Central Block", "Arts", 130, True, True, False, True, True, 5.3),
        ("D-101", "Library Wing", "Humanities", 32, False, False, False, False, True, 1.8),
        ("D-102", "Library Wing", "Humanities", 58, True, False, False, True, True, 2.7),
        ("D-201", "Library Wing", "General", 150, True, True, False, True, True, 5.8),
        ("D-202", "Library Wing", "General", 180, True, True, True, True, True, 6.5),
    ]
    rooms = [
        Classroom(
            name=row[0], building=row[1], department_preference=row[2], capacity=row[3],
            projector=row[4], smart_board=row[5], computers=row[6], air_conditioning=row[7],
            accessibility_support=row[8], estimated_power_kw=row[9],
        )
        for row in rooms_data
    ]
    db.add_all(rooms)
    db.flush()
    departments = ["Computer Science", "Mathematics", "Physics", "Electronics", "Business", "Arts", "Humanities"]
    slots = [(time(9), time(10, 30)), (time(10, 30), time(12)), (time(13), time(14, 30)), (time(14, 30), time(16))]
    base_day = date.today() + timedelta(days=1)
    for index in range(25):
        department = departments[index % len(departments)]
        count = 540 if index == 24 else 22 + (index * 17 % 128)
        course = CourseClass(
            name=("Advanced Systems Lab" if index % 6 == 0 else f"{department} {['Lecture', 'Seminar', 'Workshop', 'Tutorial'][index % 4]} {index + 1}"),
            department=department,
            student_count=count,
            required_projector=index % 3 != 0,
            required_smart_board=index % 7 == 0,
            required_computers=department == "Computer Science" and index % 2 == 0,
            required_accessibility=index % 8 == 0,
            preferred_building=["North Academic", "Innovation Hub", "Central Block", "Library Wing"][index % 4],
            preferred_department=department,
            priority=1 + index % 3,
        )
        db.add(course)
        db.flush()
        day = base_day + timedelta(days=(index // 16))
        start, end = slots[(index // 4 + index % 4) % len(slots)]
        db.add(Schedule(class_id=course.id, date=day, start_time=start, end_time=end))
    db.flush()
    db.add(RoomUnavailability(
        classroom_id=rooms[1].id, date=base_day, start_time=time(10, 30), end_time=time(12),
        reason="Projector maintenance",
    ))
    db.add(OptimizationSettings())
    db.commit()

