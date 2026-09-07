"""Main simulation engine."""

from typing import List, Dict
import random
from hospital_map import HospitalMap
from path_planner import PathPlanner
from robot import Robot
from task_manager import Task, TaskManager
from config import BATTERY_CRITICAL_THRESHOLD, CHARGE_PER_STEP, BATTERY_PER_CELL, SIM_SECONDS_PER_TICK


class HospitalSimulation:
    def __init__(self):
        self.map = HospitalMap()
        self.planner = PathPlanner(self.map)
        self.manager = TaskManager(self.map, self.planner)
        self.robots: List[Robot] = [
            Robot("R1", self.map.location("Reception"), battery=92, speed=1.0),
            Robot("R2", self.map.location("Charging Station"), battery=76, speed=1.1),
            Robot("R3", self.map.location("Storage Room"), battery=58, speed=0.9),
        ]
        self.now = 0
        self.running = False
        self.next_task_number = 5
        self.humans = set()
        self.obstacles = set()
        self.event_log: List[str] = []
        self.total_safety_stops = 0
        self.total_replans = 0
        self.scenario = "Normal Hospital Operations"
        self._seed_tasks()

    def _seed_tasks(self):
        tasks = [
            Task("T001", "Medicine", "Pharmacy", "ICU", "CRITICAL", 300, created_at=0),
            Task("T002", "Blood Sample", "Emergency Department", "Laboratory", "HIGH", 420, created_at=0),
            Task("T003", "Medical Supplies", "Storage Room", "Operating Theatre", "HIGH", 600, created_at=0),
            Task("T004", "Medicine", "Pharmacy", "General Ward", "MEDIUM", 720, created_at=0),
        ]
        for task in tasks:
            self.manager.add_task(task)

    def reset(self):
        self.__init__()
        self.log("Simulation reset")

    def log(self, message: str):
        self.event_log.insert(0, message)
        self.event_log = self.event_log[:100]

    def add_task(self, item, pickup, destination, priority, deadline):
        tid = f"T{self.next_task_number:03d}"
        self.next_task_number += 1
        task = Task(
            tid, item, pickup, destination, priority,
            int(deadline), created_at=self.now
        )
        self.manager.add_task(task)
        self.log(f"{self.now:04d}s - New task {tid} created: {item} → {destination}")
        return tid

    def add_emergency(self):
        tid = self.add_task(
            "Emergency Medicine", "Pharmacy", "ICU", "CRITICAL", 180
        )
        self.log(f"{self.now:04d}s - 🚨 EMERGENCY DELIVERY {tid} created")
        return tid

    def add_human(self):
        candidates = [
            (x, y) for x in range(self.map.width) for y in range(self.map.height)
            if self.map.is_walkable((x, y))
            and (x, y) not in self.map.locations.values()
        ]
        if candidates:
            p = random.choice(candidates)
            self.humans.add(p)
            self.log(f"{self.now:04d}s - Human detected at {p}")

    def add_obstacle(self):
        candidates = [
            (x, y) for x in range(self.map.width) for y in range(self.map.height)
            if self.map.is_walkable((x, y))
            and (x, y) not in self.map.locations.values()
        ]
        if candidates:
            p = random.choice(candidates)
            self.obstacles.add(p)
            self.map.blocked.add(p)
            self.log(f"{self.now:04d}s - Obstacle added at {p}")

    def apply_scenario(self, scenario: str):
        self.scenario = scenario
        self.map.clear_blocks()
        self.humans.clear()
        self.obstacles.clear()

        if scenario == "Emergency Medicine Delivery":
            self.add_emergency()
        elif scenario == "High Human Traffic":
            for _ in range(10):
                self.add_human()
        elif scenario == "Blocked Corridor":
            self.map.scenario_blocked_corridor()
            self.log(f"{self.now:04d}s - Corridor blocked; routes will be recalculated")
        elif scenario == "Low Battery":
            self.robots[2].battery = 18
            self.log(f"{self.now:04d}s - R3 battery deliberately reduced to 18%")
        elif scenario == "Multiple Critical Deliveries":
            self.add_task("Emergency Medicine", "Pharmacy", "Emergency Department", "CRITICAL", 220)
            self.add_task("Blood", "Laboratory", "ICU", "CRITICAL", 260)
            self.add_task("Medicine", "Pharmacy", "Operating Theatre", "CRITICAL", 300)
        elif scenario == "Robot Failure":
            self.robots[1].failed = True
            self.robots[1].status = "FAILED"
            self.log(f"{self.now:04d}s - ⚠️ R2 FAILURE DETECTED")

    def _human_conflict(self, robot: Robot) -> bool:
        if not self.humans:
            return False
        return robot.position in self.humans or any(
            abs(robot.position[0] - h[0]) + abs(robot.position[1] - h[1]) <= 1
            for h in self.humans
        )

    def _replan_if_needed(self, robot: Robot, task: Task):
        destination = self.map.location(task.destination)
        route = self.planner.find_safe_path(robot.position, destination)
        if route and route != robot.route[robot.route_index:]:
            robot.set_route(route)
            self.total_replans += 1
            self.log(f"{self.now:04d}s - {robot.robot_id} recalculated a safe route")

    def _complete_task_if_needed(self, robot: Robot):
        if not robot.current_task:
            return
        task = self.manager.tasks[robot.current_task]

        destination = self.map.location(task.destination)
        if robot.position != destination:
            return

        robot.status = "DELIVERING"
        task.status = "DELIVERING"
        self.log(f"{self.now:04d}s - {robot.robot_id} arrived at {task.destination}; delivering")

        task.status = "COMPLETED"
        task.completed_at = self.now
        robot.status = "IDLE"
        robot.current_task = None
        robot.route = []
        robot.route_index = 0
        robot.safety = "SAFE"
        self.log(f"{self.now:04d}s - ✅ {task.task_id} completed by {robot.robot_id}")

    def _charge_low_robot(self, robot: Robot):
        if robot.failed:
            return
        station = next(iter(self.map.charging_stations))
        if robot.position == station:
            robot.status = "CHARGING"
            robot.battery = min(100.0, robot.battery + CHARGE_PER_STEP)
            if robot.battery >= 95:
                robot.status = "IDLE"
                robot.safety = "SAFE"
                self.log(f"{self.now:04d}s - {robot.robot_id} finished charging")
            return

        route = self.planner.find_safe_path(robot.position, station)
        if route:
            robot.status = "RETURNING"
            robot.set_route(route)

    def tick(self):
        if not self.running:
            return

        self.now += SIM_SECONDS_PER_TICK

        # Random human movement: keep a few human obstacles in the map.
        if self.scenario == "High Human Traffic" and random.random() < 0.35:
            self.add_human()

        # Reassign tasks belonging to failed robots.
        for robot in self.robots:
            if robot.failed and robot.current_task:
                task = self.manager.tasks[robot.current_task]
                task.status = "PENDING"
                task.assigned_robot = None
                task.started_at = None
                robot.current_task = None
                robot.route = []
                self.log(f"{self.now:04d}s - {task.task_id} recovered after {robot.robot_id} failure")

        # Low battery robots go charge if idle.
        for robot in self.robots:
            if robot.status == "IDLE" and robot.battery < BATTERY_CRITICAL_THRESHOLD:
                self._charge_low_robot(robot)

        # Assign tasks to available robots.
        for event in self.manager.assign_next_tasks(self.robots, self.now):
            self.log(event)

        # Move robots.
        for robot in self.robots:
            if robot.failed or robot.status not in ("MOVING", "RETURNING"):
                continue

            # If a corridor on the current route is blocked, recalculate.
            if robot.route and any(p in self.map.blocked for p in robot.route[robot.route_index:]):
                if robot.current_task:
                    task = self.manager.tasks[robot.current_task]
                    self._replan_if_needed(robot, task)
                else:
                    self._charge_low_robot(robot)

            if self._human_conflict(robot):
                robot.status = "WAITING"
                robot.safety = "CAUTION"
                robot.safety_stops += 1
                self.total_safety_stops += 1
                self.log(f"{self.now:04d}s - {robot.robot_id} stopped for human safety")
                continue

            if robot.status == "WAITING":
                robot.status = "MOVING" if robot.current_task else "RETURNING"

            if robot.battery <= BATTERY_CRITICAL_THRESHOLD:
                if robot.current_task:
                    task = self.manager.tasks[robot.current_task]
                    # Only continue if enough battery for current remaining route.
                    if robot.remaining_steps() * BATTERY_PER_CELL + 5 > robot.battery:
                        self.log(f"{self.now:04d}s - {robot.robot_id} battery too low; diverting to charge")
                        task.status = "PENDING"
                        task.assigned_robot = None
                        robot.current_task = None
                        robot.route = []
                        self._charge_low_robot(robot)
                        continue
                else:
                    self._charge_low_robot(robot)
                    continue

            robot.move_one_step(BATTERY_PER_CELL)

            if robot.current_task:
                task = self.manager.tasks[robot.current_task]
                if robot.position == self.map.location(task.pickup):
                    # Rebuild route from pickup to destination after reaching pickup.
                    delivery = self.planner.find_safe_path(
                        robot.position, self.map.location(task.destination)
                    )
                    if delivery:
                        robot.set_route(delivery)
                        self.log(f"{self.now:04d}s - {robot.robot_id} picked up {task.item}")
                self._complete_task_if_needed(robot)
            elif robot.status == "RETURNING" and robot.position in self.map.charging_stations:
                robot.status = "CHARGING"

        # Deadline handling.
        for task in self.manager.tasks.values():
            if task.status != "COMPLETED" and self.now - task.created_at > task.deadline_seconds:
                if task.status != "DELAYED":
                    task.status = "DELAYED"
                    task.delay_reason = "Deadline exceeded"
                    self.log(f"{self.now:04d}s - ⚠️ {task.task_id} deadline exceeded")

        # Charge returning robots.
        for robot in self.robots:
            if robot.status == "CHARGING":
                robot.battery = min(100.0, robot.battery + CHARGE_PER_STEP)
                if robot.battery >= 95:
                    robot.status = "IDLE"

    def metrics(self) -> Dict[str, float]:
        completed = self.manager.completed_tasks()
        total = len(self.manager.tasks)
        delayed = len([t for t in self.manager.tasks.values() if t.status == "DELAYED"])
        avg_delivery = 0.0
        avg_route = 0.0
        if completed:
            times = [
                max(0, t.completed_at - t.created_at)
                for t in completed if t.completed_at is not None
            ]
            avg_delivery = sum(times) / len(times) if times else 0.0
            avg_route = sum(t.route_length for t in completed) / len(completed)

        utilization = (
            sum(1 for r in self.robots if r.status in ("MOVING", "DELIVERING", "WAITING", "RETURNING"))
            / len(self.robots) * 100
        )
        deadline_success = ((len(completed) / total) * 100) if total else 100.0

        return {
            "active": sum(1 for r in self.robots if not r.failed),
            "pending": len(self.manager.pending_tasks()),
            "completed": len(completed),
            "critical": sum(1 for t in self.manager.tasks.values() if t.priority == "CRITICAL" and t.status != "COMPLETED"),
            "delayed": delayed,
            "avg_delivery": avg_delivery,
            "avg_route": avg_route,
            "utilization": utilization,
            "battery_used": sum(r.battery_used for r in self.robots),
            "safety_stops": self.total_safety_stops,
            "replans": self.total_replans,
            "deadline_success": deadline_success,
        }
