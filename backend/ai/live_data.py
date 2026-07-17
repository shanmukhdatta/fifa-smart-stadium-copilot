"""
Mocked live data sources.

In production these would be async clients calling CCTV analytics, IoT
sensor gateways, a parking API, a weather API, and a transit API. For the
MVP they are deterministic-but-varied in-memory functions so the pipeline,
caching, and demo are fully reproducible without external dependencies or
API keys. Swapping these for real HTTP clients later requires no change
to callers -- only this file.
"""

import random
from datetime import datetime, timezone

_GATES = ["Gate 1", "Gate 2", "Gate 3", "Gate 4", "North Concourse", "South Concourse"]


def get_crowd_density() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gates": {gate: random.choice(["low", "moderate", "high"]) for gate in _GATES},
    }


def get_weather() -> dict:
    return {
        "condition": random.choice(["clear", "cloudy", "light rain"]),
        "temp_c": round(random.uniform(22, 34), 1),
    }


def get_parking_availability() -> dict:
    return {
        lot: random.randint(0, 500)
        for lot in ["Lot A", "Lot B", "Lot C (Accessible)"]
    }


def get_transport_status() -> dict:
    return {
        "metro": random.choice(["on time", "5 min delay", "10 min delay"]),
        "shuttle_wait_minutes": random.randint(2, 20),
    }
