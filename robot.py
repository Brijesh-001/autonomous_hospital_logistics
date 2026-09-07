"""Robot model and movement state."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Point = Tuple[int, int]


@dataclass
class Robot:
    robot_id: str
    position: Point
    battery: float = 100.0
    speed: float = 1.0
    payload_capacity: float = 10.0
    status: str = "IDLE"
    current_task: Optional[str] = None
    route: List[Point] = field(default_factory=list)
    route_index: int = 0
    failed: bool = False
    safety: str = "SAFE"
    safety_stops: int = 0
    distance_travelled: float = 0.0
    battery_used: float = 0.0

    def reset(self, position: Point):
        self.position = position
        self.battery = 100.0
        self.speed = 1.0
        self.status = "IDLE"
        self.current_task = None
        self.route = []
        self.route_index = 0
        self.failed = False
        self.safety = "SAFE"
        self.safety_stops = 0
        self.distance_travelled = 0.0
        self.battery_used = 0.0

    def set_route(self, route: List[Point]):
        self.route = route
        self.route_index = 0

    def remaining_steps(self) -> int:
        return max(0, len(self.route) - 1 - self.route_index)

    def move_one_step(self, battery_per_cell: float = 0.55) -> bool:
        if self.failed or self.status == "CHARGING":
            return False
        if self.route_index >= len(self.route) - 1:
            return False

        self.route_index += 1
        self.position = self.route[self.route_index]
        self.battery = max(0.0, self.battery - battery_per_cell)
        self.battery_used += battery_per_cell
        self.distance_travelled += 1.0
        return True

    def eta_seconds(self, seconds_per_cell: int = 10) -> int:
        return int(self.remaining_steps() * seconds_per_cell / max(self.speed, 0.1))
