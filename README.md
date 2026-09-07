# 🤖 Autonomous Hospital Logistics Simulation

A local Python/Streamlit simulation demonstrating autonomous hospital robot logistics.

## Features

- Multiple autonomous robots
- Dynamic task prioritization
- CRITICAL/HIGH/MEDIUM/LOW/NORMAL priorities
- Deadline urgency
- Dynamic robot assignment
- A* safe path planning using NetworkX
- Restricted areas
- High-human-traffic areas
- Temporary blocked corridors
- Human safety stops
- Battery consumption and automatic charging
- Emergency delivery mode
- Robot failure and task recovery
- Dynamic route recalculation
- Simulation clock
- Live robot movement
- Planned route lines
- Interactive hospital map
- Robot detail panel
- Assignment-decision explanation
- Performance metrics
- Event/safety log
- Predefined demonstration scenarios

## Architecture

```text
Delivery Request
       ↓
Task Queue
       ↓
Priority Evaluation
       ↓
Robot Selection
       ↓
Safety Validation
       ↓
A* Path Planning
       ↓
Task Assignment
       ↓
Robot Navigation
       ↓
Human/Obstacle Detection
       ↓
Route Recalculation
       ↓
Delivery
       ↓
Performance Metrics
```

## Dynamic data

The dashboard is not a static mockup.

Values such as:

- robot status
- battery
- current task
- ETA
- route safety
- route line
- robot position
- task assignment
- deadline
- safety stops

are read from the live simulation objects and change as the simulation advances.

## Algorithms

### Task priority

A task receives a score based on:

- base medical priority
- deadline urgency
- waiting time

Tasks approaching their deadline automatically become more urgent.

### Robot selection

Available robots are evaluated using:

- distance to pickup
- delivery route length
- battery reserve
- payload capacity
- route safety

The lowest-cost feasible robot is selected.

### Path planning

A* search is used over a hospital grid.

Approximate costs:

- normal cell: 1
- high-traffic cell: 3
- blocked/restricted: unavailable

Therefore the robot searches for a safe route instead of blindly using a geometric shortest path.

## Run

Create/activate a virtual environment if desired:

```bash
python -m venv .venv
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start:

```bash
streamlit run app.py
```

## Demonstration

Recommended demo order:

1. Start **Normal Hospital Operations**.
2. Click Start and observe robots receiving tasks.
3. Select R1/R2/R3 and observe changing status, battery and ETA.
4. Load **High Human Traffic** and observe safety stops.
5. Load **Blocked Corridor** and observe safe route changes.
6. Load **Low Battery** and observe charging behavior.
7. Load **Emergency Medicine Delivery** and observe critical task prioritization.
8. Load **Robot Failure** and observe task recovery/reassignment.
9. Load **Multiple Critical Deliveries** to demonstrate autonomous coordination.

## Academic scope

This is a simulation/prototype, not a real hospital deployment system. It is intended to demonstrate autonomous task planning, navigation, safety logic and visualization.
