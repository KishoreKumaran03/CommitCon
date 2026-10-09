from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, time
from typing import Any


@dataclass(frozen=True)
class Weights:
    seat: float = 1.0
    department: float = 30.0
    building: float = 15.0
    energy: float = 0.0


def overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return start_a < end_b and start_b < end_a


def rejection_reasons(room: Any, item: dict, unavailabilities: list[dict], occupied: list[dict]) -> list[str]:
    reasons: list[str] = []
    if room.capacity < item["student_count"]:
        reasons.append(f"Capacity {room.capacity} is below {item['student_count']} students")
    if not room.is_active:
        reasons.append("Room is marked unavailable")
    requirements = (
        ("required_projector", "projector", "projector"),
        ("required_smart_board", "smart_board", "smart board"),
        ("required_computers", "computers", "computers"),
        ("required_accessibility", "accessibility_support", "accessibility support"),
    )
    missing = [label for requirement, feature, label in requirements if item[requirement] and not getattr(room, feature)]
    if missing:
        reasons.append(f"Missing required {' and '.join(missing)}")
    for block in unavailabilities:
        if block["classroom_id"] == room.id and block["date"] == item["date"] and overlaps(
            block["start_time"], block["end_time"], item["start_time"], item["end_time"]
        ):
            reasons.append(f"Room unavailable: {block.get('reason', 'scheduled outage')}")
            break
    for current in occupied:
        if current["room_id"] == room.id and current["date"] == item["date"] and overlaps(
            current["start_time"], current["end_time"], item["start_time"], item["end_time"]
        ):
            reasons.append(f"Timetable conflict with {current.get('name', 'another class')}")
            break
    return reasons


def preference_penalty(room: Any, item: dict) -> float:
    penalty = 0.0
    if item.get("preferred_department") and room.department_preference != item["preferred_department"]:
        penalty += 1.0
    if item.get("preferred_building") and room.building != item["preferred_building"]:
        penalty += 1.0
    return penalty


def candidate_score(room: Any, item: dict, weights: Weights) -> float:
    duration = (
        item["end_time"].hour * 60 + item["end_time"].minute
        - item["start_time"].hour * 60 - item["start_time"].minute
    ) / 60
    energy = (room.estimated_power_kw or 0) * max(duration, 0)
    return (
        (room.capacity - item["student_count"]) * weights.seat
        + (weights.department if item.get("preferred_department") and room.department_preference != item["preferred_department"] else 0)
        + (weights.building if item.get("preferred_building") and room.building != item["preferred_building"] else 0)
        + energy * weights.energy
    )


def _allocation_result(room: Any, item: dict, weights: Weights) -> dict:
    explanation = (
        f"{room.name} fits {item['student_count']} students with {room.capacity - item['student_count']} "
        "unused seats, satisfies all required facilities, and is free for the full session."
    )
    if item.get("preferred_building"):
        explanation += " It matches the preferred building." if room.building == item["preferred_building"] else f" It does not match the preferred building ({item['preferred_building']})."
    if item.get("preferred_department"):
        explanation += " It matches the department preference." if room.department_preference == item["preferred_department"] else " It does not match the department preference."
    duration = (
        item["end_time"].hour * 60 + item["end_time"].minute
        - item["start_time"].hour * 60 - item["start_time"].minute
    ) / 60
    return {
        "schedule_id": item["id"], "class_id": item["class_id"], "class_name": item["name"],
        "department": item.get("department", ""),
        "date": item["date"], "start_time": item["start_time"], "end_time": item["end_time"],
        "classroom_id": room.id, "classroom_name": room.name, "classroom_building": room.building,
        "status": "allocated",
        "student_count": item["student_count"], "capacity": room.capacity,
        "unused_seats": room.capacity - item["student_count"],
        "utilization_percentage": round(item["student_count"] / room.capacity * 100, 1),
        "preference_penalty": preference_penalty(room, item),
        "score": round(candidate_score(room, item, weights), 2),
        "energy_kwh": round(room.estimated_power_kw * max(duration, 0), 2)
        if room.estimated_power_kw is not None else None,
        "explanation": explanation,
    }


def _reasons_for_unassigned(item: dict, rooms: list, unavailabilities: list[dict], occupied: list[dict]) -> str:
    reasons = [reason for room in rooms for reason in rejection_reasons(room, item, unavailabilities, occupied)]
    if not rooms:
        return "No classrooms are configured."
    active_rooms = [room for room in rooms if room.is_active]
    if not active_rooms:
        return "No active classroom is available."
    if all(room.capacity < item["student_count"] for room in active_rooms):
        if any(not room.is_active for room in rooms):
            return "No active room has sufficient capacity."
        return "No room has sufficient capacity."
    if any("Missing required" in reason for reason in reasons):
        available = [room for room in rooms if room.is_active and room.capacity >= item["student_count"]]
        if available and all(
            any("Missing required" in reason for reason in rejection_reasons(candidate, item, unavailabilities, occupied))
            for candidate in available
        ):
            return "No room satisfies the required facilities."
    if any("Timetable conflict" in reason for reason in reasons):
        return "All suitable rooms are occupied in this time slot."
    if any("Room unavailable:" in reason for reason in reasons):
        return "All suitable rooms are unavailable during this time slot."
    return "No room satisfies the combined capacity, facility, and availability constraints."


def allocate(
    rooms: list,
    items: list[dict],
    unavailabilities: list[dict],
    method: str = "optimized",
    weights: Weights | None = None,
    seed: int = 42,
) -> dict:
    weights = weights or Weights()
    rng = random.Random(seed)
    assigned: list[dict] = []
    output: list[dict] = []
    ordered = list(items)
    if method == "optimized":
        ordered.sort(key=lambda item: (
            sum(not rejection_reasons(room, item, unavailabilities, []) for room in rooms),
            -item.get("priority", 1), item["date"], item["start_time"], item["id"],
        ))
    else:
        ordered.sort(key=lambda item: (item["date"], item["start_time"], item["id"]))
    room_order = sorted(rooms, key=lambda room: (room.capacity, room.id))

    for item in ordered:
        candidates = [
            room for room in room_order
            if not rejection_reasons(room, item, unavailabilities, assigned)
        ]
        if method == "random":
            rng.shuffle(candidates)
        elif method == "optimized":
            candidates.sort(key=lambda room: (candidate_score(room, item, weights), room.id))
        if not candidates:
            output.append({
                "schedule_id": item["id"], "class_id": item["class_id"], "class_name": item["name"],
                "department": item.get("department", ""),
                "date": item["date"], "start_time": item["start_time"], "end_time": item["end_time"],
                "classroom_id": None, "classroom_name": None, "status": "unallocated",
                "student_count": item["student_count"],
                "reason": _reasons_for_unassigned(item, rooms, unavailabilities, assigned),
            })
            continue
        room = candidates[0]
        result = _allocation_result(room, item, weights)
        output.append(result)
        assigned.append({
            "room_id": room.id, "date": item["date"], "start_time": item["start_time"],
            "end_time": item["end_time"], "name": item["name"], "schedule_id": item["id"],
        })
    if method == "optimized":
        items_by_id = {item["id"]: item for item in ordered}
        changed = True
        while changed:
            changed = False
            for pending in [row for row in output if row["status"] == "unallocated"]:
                pending_item = items_by_id[pending["schedule_id"]]
                possible = [
                    room for room in rooms
                    if not rejection_reasons(room, pending_item, unavailabilities, [])
                ]
                options = []
                for room in possible:
                    blockers = [
                        current for current in assigned
                        if current["room_id"] == room.id and current["date"] == pending_item["date"]
                        and overlaps(current["start_time"], current["end_time"], pending_item["start_time"], pending_item["end_time"])
                    ]
                    if len(blockers) != 1:
                        continue
                    blocker = blockers[0]
                    blocker_item = items_by_id[blocker["schedule_id"]]
                    other_assignments = [current for current in assigned if current is not blocker]
                    pending_occupancy = {
                        "room_id": room.id, "date": pending_item["date"],
                        "start_time": pending_item["start_time"], "end_time": pending_item["end_time"],
                        "name": pending_item["name"],
                    }
                    alternatives = [
                        alternative for alternative in rooms
                        if alternative.id != room.id
                        and not rejection_reasons(
                            alternative, blocker_item, unavailabilities, other_assignments + [pending_occupancy],
                        )
                    ]
                    for alternative in alternatives:
                        options.append((
                            candidate_score(room, pending_item, weights) + candidate_score(alternative, blocker_item, weights),
                            room.id, alternative.id, room, alternative, blocker,
                        ))
                if not options:
                    continue
                _, _, _, destination, alternative, blocker = min(options, key=lambda option: option[:3])
                blocker_item = items_by_id[blocker["schedule_id"]]
                blocker_result = next(row for row in output if row["schedule_id"] == blocker["schedule_id"])
                blocker_result.update(_allocation_result(alternative, blocker_item, weights))
                blocker["room_id"] = alternative.id
                pending.update(_allocation_result(destination, pending_item, weights))
                pending.pop("reason", None)
                assigned.append({
                    "room_id": destination.id, "date": pending_item["date"],
                    "start_time": pending_item["start_time"], "end_time": pending_item["end_time"],
                    "name": pending_item["name"], "schedule_id": pending_item["id"],
                })
                changed = True
                break
    output.sort(key=lambda row: (row["date"], row["start_time"], row["schedule_id"]))
    return {"method": method, "results": output}


def metrics(results: list[dict], total: int, runtime_ms: float, seed: int | None = None) -> dict:
    allocated = [row for row in results if row["status"] == "allocated"]
    conflicts = [
        (first, second)
        for index, first in enumerate(allocated)
        for second in allocated[index + 1:]
        if first["classroom_id"] == second["classroom_id"]
        and first["date"] == second["date"]
        and overlaps(first["start_time"], first["end_time"], second["start_time"], second["end_time"])
    ]
    conflicted_schedules = {
        row["schedule_id"] for conflict in conflicts for row in conflict
    }
    valid = [row for row in allocated if row["schedule_id"] not in conflicted_schedules]
    students = sum(row["student_count"] for row in valid)
    capacity = sum(row["capacity"] for row in valid)
    unused = sum(row["unused_seats"] for row in valid)
    return {
        "successful_allocations": len(valid),
        "unallocated_classes": total - len(valid),
        "success_rate": round(len(valid) / total * 100, 1) if total else 0.0,
        "unused_seats": unused,
        "average_unused_seats": round(unused / len(valid), 1) if valid else 0.0,
        "utilization_percentage": round(students / capacity * 100, 1) if capacity else 0.0,
        "preference_penalty": round(sum(row["preference_penalty"] for row in valid), 2),
        "conflicts": len(conflicts),
        "runtime_ms": round(runtime_ms, 2),
        "random_seed": seed,
    }
