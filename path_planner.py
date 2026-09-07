"""Safe A* path planning."""

from typing import List, Tuple, Set
import networkx as nx
from hospital_map import HospitalMap

Point = Tuple[int, int]


class PathPlanner:
    def __init__(self, hospital_map: HospitalMap):
        self.map = hospital_map

    def heuristic(self, a: Point, b: Point) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_safe_path(self, start: Point, goal: Point) -> List[Point]:
        if not self.map.is_walkable(start) or not self.map.is_walkable(goal):
            return []

        graph = self.map.graph()
        try:
            return nx.astar_path(
                graph,
                start,
                goal,
                heuristic=self.heuristic,
                weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def route_cost(self, route: List[Point]) -> float:
        if len(route) < 2:
            return 0.0
        cost = 0.0
        for p in route[1:]:
            cost += 3.0 if p in self.map.high_traffic else 1.0
        return cost

    def route_safety(self, route: List[Point]) -> str:
        if not route:
            return "UNSAFE"
        if any(p in self.map.restricted or p in self.map.blocked for p in route):
            return "UNSAFE"
        if any(p in self.map.high_traffic for p in route):
            return "CAUTION"
        return "SAFE"
