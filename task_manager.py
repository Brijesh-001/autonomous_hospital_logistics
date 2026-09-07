"""Priority queue and autonomous task/robot assignment."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config import PRIORITY_VALUES, BATTERY_LOW_THRESHOLD
from path_planner import PathPlanner
from hospital_map import HospitalMap
from robot import Robot


@dataclass
class Task:
    task_id: str
    item: str
    pickup: str
    destination: str
    priority: str
    deadline_seconds: int
    weight: float = 1.0
    created_at: int = 0
    required_delivery_time: int = 0
    status: str = "PENDING"
    assigned_robot: Optional[str] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    route_length: float = 0.0
    delay_reason: str = ""

    def urgency_bonus(self, now: int) -> float:
        elapsed = max(0, now - self.created_at)
        remaining = self.deadline_seconds - elapsed
        if remaining <= 0:
            return 10.0
        ratio = remaining / max(self.deadline_seconds, 1)
        if ratio < 0.30:
            return 4.0
        if ratio < 0.60:
            return 2.0
        return 0.0

    def score(self, now: int) -> float:
        elapsed = max(0, now - self.created_at)
        return (
            PRIORITY_VALUES[self.priority] * 10
            + self.urgency_bonus(now)
            + min(elapsed / 20.0, 5.0)
        )

    def priority_label(self, now: int) -> str:
        if self.deadline_seconds <= 0:
            return "DELAYED"
        elapsed = max(0, now - self.created_at)
        ratio = (self.deadline_seconds - elapsed) / max(self.deadline_seconds, 1)
        if elapsed >= self.deadline_seconds:
            return "DELAYED"
        if ratio < 0.30:
            return "CRITICAL"
        return self.priority


class TaskManager:
    def __init__(self, hospital_map: HospitalMap, planner: PathPlanner):
        self.map = hospital_map
        self.planner = planner
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task):
        self.tasks[task.task_id] = task

    def pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == "PENDING"]

    def active_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status in ("ASSIGNED", "MOVING", "DELIVERING")]

    def completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == "COMPLETED"]

    def delayed_tasks(self, now: int) -> List[Task]:
        return [
            t for t in self.tasks.values()
            if t.status != "COMPLETED"
            and now - t.created_at > t.deadline_seconds
        ]

    def rank_tasks(self, now: int) -> List[Task]:
        return sorted(self.pending_tasks(), key=lambda t: t.score(now), reverse=True)

    def choose_robot(
        self, task: Task, robots: List[Robot], now: int
    ) -> Tuple[Optional[Robot], List[str], List]:
        best_robot = None
        best_score = float("inf")
        best_route = []
        reasons = []

        pickup = self.map.location(task.pickup)
        destination = self.map.location(task.destination)

        for robot in robots:
            if robot.failed or robot.status not in ("IDLE",):
                continue
            if robot.battery < BATTERY_LOW_THRESHOLD:
                continue
            if robot.payload_capacity < task.weight:
                continue

            to_pickup = self.planner.find_safe_path(robot.position, pickup)
            delivery_route = self.planner.find_safe_path(pickup, destination)
            if not to_pickup or not delivery_route:
                continue

            total_steps = len(to_pickup) + len(delivery_route) - 2
            estimated_battery = total_steps * 0.55
            if robot.battery - estimated_battery < 8:
                continue

            safety_penalty = 15 if self.planner.route_safety(delivery_route) == "CAUTION" else 0
            score = (
                total_steps
                + max(0, 50 - robot.battery) * 0.15
                + safety_penalty
            )

            if score < best_score:
                best_score = score
                best_robot = robot
                best_route = to_pickup[:-1] + delivery_route
                reasons = [
                    f"{robot.robot_id} is {len(to_pickup)-1} steps from pickup",
                    f"Battery is sufficient ({robot.battery:.0f}%)",
                    f"Estimated travel: {total_steps} steps",
                    f"Route safety: {self.planner.route_safety(delivery_route)}",
                    "Robot is currently idle and payload-capable",
                ]

        return best_robot, reasons, best_route

    def assign_next_tasks(self, robots: List[Robot], now: int) -> List[str]:
        events = []
        for task in self.rank_tasks(now):
            robot, reasons, route = self.choose_robot(task, robots, now)
            if robot is None:
                continue

            robot.current_task = task.task_id
            robot.status = "MOVING"
            robot.set_route(route)
            robot.safety = self.planner.route_safety(route)
            task.assigned_robot = robot.robot_id
            task.status = "MOVING"
            task.started_at = now
            task.route_length = max(0, len(route) - 1)

            task._assignment_reasons = reasons
            events.append(
                f"{now:04d}s - {robot.robot_id} assigned {task.task_id} "
                f"({task.priority_label(now)})"
            )
        return events
