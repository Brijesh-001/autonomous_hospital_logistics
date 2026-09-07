"""Hospital graph and map model."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set
import networkx as nx

Point = Tuple[int, int]


@dataclass
class HospitalMap:
    width: int = 18
    height: int = 12
    locations: Dict[str, Point] = field(default_factory=dict)
    restricted: Set[Point] = field(default_factory=set)
    high_traffic: Set[Point] = field(default_factory=set)
    blocked: Set[Point] = field(default_factory=set)
    charging_stations: Set[Point] = field(default_factory=set)

    def __post_init__(self):
        self._build_layout()

    def _build_layout(self):
        self.locations = {
            "Pharmacy": (2, 2),
            "Laboratory": (15, 2),
            "Emergency Department": (15, 9),
            "ICU": (3, 9),
            "General Ward": (9, 9),
            "Operating Theatre": (9, 2),
            "Storage Room": (2, 6),
            "Reception": (9, 6),
            "Charging Station": (5, 6),
        }
        self.charging_stations = {self.locations["Charging Station"]}

        # Restricted zone: an internal staff-only block that robots must avoid.
        self.restricted = {
            (7, 4), (8, 4), (9, 4), (10, 4),
            (7, 5), (8, 5), (9, 5), (10, 5),
        }

        # High-traffic cells around reception/main hall.
        self.high_traffic = {
            (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6),
            (8, 7), (9, 7), (10, 7),
            (8, 8), (9, 8), (10, 8),
        }

    def in_bounds(self, p: Point) -> bool:
        return 0 <= p[0] < self.width and 0 <= p[1] < self.height

    def is_walkable(self, p: Point) -> bool:
        return self.in_bounds(p) and p not in self.restricted and p not in self.blocked

    def neighbors(self, p: Point) -> List[Point]:
        candidates = [
            (p[0] + 1, p[1]), (p[0] - 1, p[1]),
            (p[0], p[1] + 1), (p[0], p[1] - 1),
        ]
        return [q for q in candidates if self.is_walkable(q)]

    def graph(self) -> nx.Graph:
        g = nx.Graph()
        for x in range(self.width):
            for y in range(self.height):
                p = (x, y)
                if not self.is_walkable(p):
                    continue
                g.add_node(p)
                for q in self.neighbors(p):
                    cost = 3.0 if q in self.high_traffic else 1.0
                    g.add_edge(p, q, weight=cost)
        return g

    def location(self, name: str) -> Point:
        return self.locations[name]

    def location_name(self, point: Point) -> str:
        for name, p in self.locations.items():
            if p == point:
                return name
        return ""

    def toggle_block(self, point: Point):
        if point in self.locations.values() or point in self.restricted:
            return
        if point in self.blocked:
            self.blocked.remove(point)
        else:
            self.blocked.add(point)

    def clear_blocks(self):
        self.blocked.clear()

    def scenario_blocked_corridor(self):
        self.blocked = {
            (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7)
        }
