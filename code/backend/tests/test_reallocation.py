from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import Allocation


def test_emergency_reallocation_is_proposed_then_applied(client):
    response = client.post("/api/allocations/run", json={"algorithm": "optimized"})
    assert response.status_code == 200
    allocations = client.get("/api/allocations").json()
    allocation = allocations[0]
    outage = {
        "date": allocation["date"], "start_time": allocation["start_time"],
        "end_time": allocation["end_time"], "reason": "Electrical repair", "apply": False,
    }
    path = f"/api/classrooms/{allocation['classroom_id']}/unavailability"
    proposal = client.post(path, json=outage)
    assert proposal.status_code == 200
    assert proposal.json()["affected_count"] == 1
    assert proposal.json()["proposals"][0]["status"] == "proposed"
    assert client.get("/api/allocations").json()[0]["classroom_id"] == allocation["classroom_id"]

    outage["apply"] = True
    applied = client.post(path, json=outage)
    assert applied.status_code == 200
    updated = client.get("/api/allocations").json()
    moved = next(row for row in updated if row["id"] == allocation["id"])
    assert moved["classroom_id"] != allocation["classroom_id"]


def test_no_valid_emergency_alternative_keeps_existing_allocation(client):
    client.post("/api/allocations/run", json={"algorithm": "optimized"})
    allocation = client.get("/api/allocations").json()[0]
    for room in client.get("/api/classrooms").json():
        room["is_active"] = False
        response = client.put(f"/api/classrooms/{room['id']}", json=room)
        assert response.status_code == 200
    request = {
        "date": allocation["date"], "start_time": allocation["start_time"],
        "end_time": allocation["end_time"], "reason": "Emergency", "apply": True,
    }
    response = client.post(f"/api/classrooms/{allocation['classroom_id']}/unavailability", json=request)
    assert response.status_code == 409
    assert client.get("/api/allocations").json()[0]["classroom_id"] == allocation["classroom_id"]


def test_failed_replacement_transaction_preserves_previous_allocations(client):
    client.post("/api/allocations/run", json={"algorithm": "optimized"})
    before = client.get("/api/allocations").json()
    engine = client.app.state.test_engine

    def fail_before_commit(_session):
        raise RuntimeError("simulated database failure")

    event.listen(Session, "before_commit", fail_before_commit)
    response = client.post("/api/allocations/run", json={"algorithm": "first_fit", "replace_existing": True})
    event.remove(Session, "before_commit", fail_before_commit)
    assert response.status_code == 500
    after = client.get("/api/allocations").json()
    assert [row["id"] for row in after] == [row["id"] for row in before]


def test_invalid_class_schedule_is_rejected(client):
    response = client.post("/api/classes", json={
        "name": "Invalid interval", "department": "Computer Science", "student_count": 24,
        "date": "2026-10-15", "start_time": "14:00", "end_time": "13:00",
    })
    assert response.status_code == 422
    assert all(row["name"] != "Invalid interval" for row in client.get("/api/classes").json())


def test_class_and_schedule_are_created_together(client):
    response = client.post("/api/classes", json={
        "name": "Atomic schedule", "department": "Computer Science", "student_count": 28,
        "date": "2026-10-15", "start_time": "09:00", "end_time": "10:30",
    })
    assert response.status_code == 201
    created = client.get(f"/api/classes/{response.json()['id']}").json()
    assert len(created["schedules"]) == 1
    assert created["schedules"][0]["start_time"] == "09:00:00"


def test_unallocated_result_and_reason_are_persisted(client):
    response = client.post("/api/allocations/run", json={"algorithm": "optimized"})
    assert response.status_code == 200
    persisted = client.get("/api/allocations").json()
    unallocated = next(row for row in persisted if row["status"] == "unallocated")
    assert unallocated["classroom_id"] is None
    assert unallocated["reason"] == "No room has sufficient capacity."


def test_existing_confirmed_allocations_require_replacement_confirmation(client):
    first = client.post("/api/allocations/run", json={"algorithm": "optimized"})
    assert first.status_code == 200
    before = [row["id"] for row in client.get("/api/allocations").json()]
    denied = client.post("/api/allocations/run", json={"algorithm": "first_fit"})
    assert denied.status_code == 409
    assert [row["id"] for row in client.get("/api/allocations").json()] == before


def test_allocated_room_cannot_be_deleted_and_class_delete_cascades(client):
    client.post("/api/allocations/run", json={"algorithm": "optimized"})
    allocation = next(row for row in client.get("/api/allocations").json() if row["classroom_id"] is not None)
    room_delete = client.delete(f"/api/classrooms/{allocation['classroom_id']}")
    assert room_delete.status_code == 409
    class_delete = client.delete(f"/api/classes/{allocation['class_id']}")
    assert class_delete.status_code == 204
    assert all(row["class_id"] != allocation["class_id"] for row in client.get("/api/allocations").json())


def test_conflict_endpoint_is_reachable_and_reports_no_seeded_conflicts(client):
    client.post("/api/allocations/run", json={"algorithm": "optimized"})
    response = client.get("/api/allocations/conflicts")
    assert response.status_code == 200
    assert response.json() == []


def test_comparison_runs_all_methods_on_same_live_scenario(client):
    response = client.post("/api/simulations/compare?seed=19")
    assert response.status_code == 200
    result = response.json()
    assert result["total_scheduled_classes"] == 25
    assert {row["algorithm"] for row in result["results"]} == {"random", "first_fit", "optimized"}
    for row in result["results"]:
        assert row["successful_allocations"] + row["unallocated_classes"] == 25
        assert row["conflicts"] == 0
        assert row["estimated_energy_kwh"] >= 0


def test_demo_data_reset_clears_derived_data_and_restores_seed(client):
    client.post("/api/allocations/run", json={"algorithm": "optimized"})
    client.post("/api/simulations/compare?seed=12")
    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    assert response.json()["classrooms"] == 18
    assert response.json()["classes"] == 25
    assert client.get("/api/allocations").json() == []
    assert client.get("/api/simulations/history").json() == []
