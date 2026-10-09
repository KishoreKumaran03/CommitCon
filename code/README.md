# CampusFlow

CampusFlow is an AI-powered classroom allocation and campus resource optimization MVP. It allocates scheduled classes to rooms using hard-constraint validation and a weighted objective, compares the optimized result with reproducible random and first-fit baselines, and proposes emergency room replacements.

## Features

- Dashboard metrics and room utilization based on live API data.
- Classroom and class management with server-side validation.
- Schedules, room unavailability, and overlap detection.
- Random-feasible, first-fit, and optimized allocation strategies.
- Explainable allocation results and meaningful unallocated reasons.
- Emergency room reassignment proposals that require explicit approval.
- Reproducible benchmark comparisons, configurable optimization weights, and demo-data reset.
- SQLite persistence, reproducible seed data, and automated backend tests.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS, Recharts, and Lucide.
- `backend/app/`: FastAPI, Pydantic, SQLAlchemy, SQLite, and allocation services.
- The allocation engine is independent from API routes. Hard constraints are evaluated before candidate scoring. The optimizer maximizes allocated classes first, then minimizes weighted unused seats and preference penalties using a deterministic greedy construction and improvement pass.

## Requirements

- Node.js 18+ and npm.
- Python 3.10+.

## Start locally

Open two terminals in the `code` directory.

### Backend (PowerShell)

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is at <http://127.0.0.1:8000>, interactive docs at <http://127.0.0.1:8000/docs>, and health check at <http://127.0.0.1:8000/api/health>. The SQLite database is created in `backend/campusflow.db`; demonstration records are seeded on first start.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://localhost:5173>). Vite proxies `/api` calls to the backend.

## Tests and build

```powershell
cd backend
python -m pytest
```

```powershell
cd frontend
npm run build
```

## Demonstration workflow

1. Start the backend and frontend; view the seeded dashboard.
2. Open **Smart Allocation** and run the optimizer. The result is persisted and explanations describe evaluated constraints and preferences.
3. Run **Compare algorithms** to compare all three methods on the same current classes, rooms, schedules, and unavailability. Random results use a fixed default seed and can be repeated.
4. Add a room or class in their management views and rerun allocation.
5. Use **Emergency reassignment** on an assigned room to see feasible alternatives; apply only after reviewing the proposal.
6. View **Availability** to inspect occupied and unavailable time blocks.
7. Use **Settings → Reset demo data** to restore the sample rooms and timetable and clear generated allocations/history.

## Benchmark methodology

All strategies receive the same current dataset and use the same hard-constraint validation. Success rate is successfully allocated classes divided by all scheduled classes. Seat utilization is allocated students divided by capacity of assigned rooms. Unused seats are summed only across valid assignments. Preference penalty is computed from department and building mismatches. Runtimes are measured during each actual run. No benchmark values are preloaded.

The dashboard’s potential energy difference compares first-fit with optimized room estimates only for schedules both strategies allocate and only where both rooms have estimated power values. A negative difference means the optimized assignment estimates more energy. The estimate is room rated kW × scheduled hours, not metered energy or verified savings.

The optimized strategy prioritizes allocation count, then minimizes:

`unused_seats × seat_weight + department_mismatch × department_weight + building_mismatch × building_weight + energy_kwh × energy_weight`

Weights can be adjusted in **Settings**. Room capacity, required facilities, room activity, unavailability, and overlapping occupancy remain hard constraints. Energy is an estimate based on room kW multiplied by scheduled session hours; it does not infer savings from empty seats or claim carbon reductions.

## API overview

- `/api/health`, `/api/dashboard`
- `/api/classrooms`, `/api/classes`, `/api/schedules`
- `/api/allocations/run`, `/api/allocations`, `/api/allocations/conflicts`
- `/api/classrooms/{id}/unavailability`, `/api/unavailability`
- `/api/simulations/compare`, `/api/simulations/history`
- `/api/analytics/utilization`, `/api/analytics/sustainability`
- `/api/settings`, `/api/demo/reset`

## Limitations and future work

The optimizer is a transparent heuristic, not a mathematical proof of a global optimum. This keeps the MVP dependency-light and responsive for the demonstration dataset. Future work could add CP-SAT, authentication and role-based access, richer timetable editing, persisted simulation history, and configurable institutional calendars.
