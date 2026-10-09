from datetime import date, time, timedelta
from types import SimpleNamespace

from app.services.allocation_engine import Weights, allocate, metrics, rejection_reasons


def room(**values):
    defaults = dict(
        id=1, name="A-101", building="North", department_preference="CS", capacity=50,
        projector=True, smart_board=True, computers=True, accessibility_support=True,
        estimated_power_kw=2.0, is_active=True,
    )
    return SimpleNamespace(**(defaults | values))


def item(**values):
    defaults = dict(
        id=1, class_id=1, name="Systems", department="CS", student_count=32,
        required_projector=False, required_smart_board=False, required_computers=False,
        required_accessibility=False, preferred_building="North", preferred_department="CS",
        priority=1, date=date(2026, 10, 10), start_time=time(9), end_time=time(10),
    )
    return defaults | values


def test_allocates_to_suitable_room_with_explanation():
    result = allocate([room()], [item()], [], "optimized")["results"][0]
    assert result["status"] == "allocated"
    assert result["classroom_name"] == "A-101"
    assert result["unused_seats"] == 18
    assert "satisfies all required facilities" in result["explanation"]


def test_insufficient_capacity_is_rejected():
    result = allocate([room(capacity=20)], [item()], [], "optimized")["results"][0]
    assert result["status"] == "unallocated"
    assert result["reason"] == "No room has sufficient capacity."


def test_missing_projector_is_rejected():
    result = allocate([room(projector=False)], [item(required_projector=True)], [], "optimized")["results"][0]
    assert result["status"] == "unallocated"
    assert "required facilities" in result["reason"]


def test_missing_smart_board_is_rejected():
    result = allocate([room(smart_board=False)], [item(required_smart_board=True)], [], "optimized")["results"][0]
    assert result["status"] == "unallocated"


def test_overlapping_assignments_are_not_double_booked():
    classes = [item(id=1), item(id=2, class_id=2, name="Networks")]
    result = allocate([room()], classes, [], "first_fit")["results"]
    assert sum(row["status"] == "allocated" for row in result) == 1
    assert any("occupied" in row.get("reason", "") for row in result)


def test_back_to_back_sessions_can_use_same_room():
    classes = [item(id=1), item(id=2, class_id=2, name="Networks", start_time=time(10), end_time=time(11))]
    result = allocate([room()], classes, [], "first_fit")["results"]
    assert all(row["status"] == "allocated" for row in result)


def test_same_times_on_different_dates_do_not_conflict():
    classes = [item(id=1), item(id=2, class_id=2, name="Networks", date=date(2026, 10, 11))]
    result = allocate([room()], classes, [], "first_fit")["results"]
    assert all(row["status"] == "allocated" for row in result)


def test_unavailable_room_is_rejected():
    outage = [{
        "classroom_id": 1, "date": date(2026, 10, 10), "start_time": time(9),
        "end_time": time(10), "reason": "Maintenance",
    }]
    result = allocate([room()], [item()], outage, "optimized")["results"][0]
    assert result["status"] == "unallocated"
    assert "unavailable" in result["reason"]


def test_inactive_room_is_rejected():
    result = allocate([room(is_active=False)], [item()], [], "optimized")["results"][0]
    assert result["status"] == "unallocated"
    assert result["reason"] == "No active classroom is available."


def test_capacity_explanation_ignores_inactive_large_rooms():
    rooms = [room(capacity=20), room(id=2, capacity=80, is_active=False)]
    result = allocate(rooms, [item()], [], "optimized")["results"][0]
    assert result["reason"] == "No active room has sufficient capacity."


def test_random_method_is_reproducible_with_fixed_seed():
    rooms = [room(id=i, name=f"R-{i}", capacity=40 + i, building="North") for i in range(1, 8)]
    classes = [item(id=i, class_id=i, start_time=time(9 + (i % 2)), end_time=time(10 + (i % 2))) for i in range(1, 7)]
    first = allocate(rooms, classes, [], "random", seed=27)
    second = allocate(rooms, classes, [], "random", seed=27)
    assert [(x["schedule_id"], x["classroom_id"]) for x in first["results"]] == [
        (x["schedule_id"], x["classroom_id"]) for x in second["results"]
    ]


def test_metrics_are_consistent_across_methods():
    room_set = [room(), room(id=2, name="A-102", capacity=40)]
    classes = [item(id=1), item(id=2, class_id=2, start_time=time(10), end_time=time(11))]
    totals = []
    for method in ("random", "first_fit", "optimized"):
        result = allocate(room_set, classes, [], method, Weights(), seed=4)["results"]
        summary = metrics(result, len(classes), 1.0)
        totals.append(summary["successful_allocations"] + summary["unallocated_classes"])
        assert summary["success_rate"] == 100.0
        assert summary["unused_seats"] == sum(row["unused_seats"] for row in result)
    assert totals == [2, 2, 2]


def test_metrics_do_not_count_overlapping_room_assignments_as_successful():
    classes = [item(id=1), item(id=2, class_id=2, name="Networks")]
    results = allocate([room(), room(id=2, name="A-102", capacity=60)], classes, [], "first_fit")["results"]
    results[1]["classroom_id"] = results[0]["classroom_id"]
    result = metrics(results, 2, 1.0)
    assert result["conflicts"] == 1
    assert result["successful_allocations"] == 0
    assert result["unallocated_classes"] == 2


def test_overlap_uses_half_open_interval():
    assert rejection_reasons(room(), item(start_time=time(10), end_time=time(11)), [], [{
        "room_id": 1, "date": date(2026, 10, 10), "start_time": time(9), "end_time": time(10),
    }]) == []
