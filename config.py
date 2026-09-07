"""Configuration constants for the Autonomous Hospital Logistics Simulation."""

GRID_WIDTH = 18
GRID_HEIGHT = 12

NORMAL_COST = 1.0
HIGH_TRAFFIC_COST = 3.0
BLOCKED_COST = float("inf")

BATTERY_LOW_THRESHOLD = 25.0
BATTERY_CRITICAL_THRESHOLD = 10.0
BATTERY_PER_CELL = 0.55
CHARGE_PER_STEP = 8.0

SIM_SECONDS_PER_TICK = 10
DEFAULT_SPEED = 1.0

PRIORITY_VALUES = {
    "NORMAL": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}

STATUS_COLORS = {
    "IDLE": "green",
    "MOVING": "blue",
    "DELIVERING": "purple",
    "RETURNING": "orange",
    "CHARGING": "cyan",
    "WAITING": "gold",
    "EMERGENCY_STOP": "red",
    "FAILED": "black",
}
