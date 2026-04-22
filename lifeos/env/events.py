from __future__ import annotations

import random
from typing import Any


RANDOM_EVENT_POOL: list[dict[str, Any]] = [
    {
        "event_type": "laptop_break",
        "description": "Laptop battery died during deep work.",
        "impact": {"stress": 0.08, "energy": -0.05, "money": -150.0},
    },
    {
        "event_type": "friend_angry",
        "description": "A close friend is upset that you ignored messages.",
        "impact": {"stress": 0.06, "relationship": -0.08},
    },
    {
        "event_type": "rain_delay",
        "description": "Unexpected rain delayed commute.",
        "impact": {"stress": 0.04, "energy": -0.03},
    },
    {
        "event_type": "small_win",
        "description": "A small win lifted your mood.",
        "impact": {"stress": -0.06, "relationship": 0.04},
    },
]


def maybe_inject_random_event(probability: float = 0.15) -> dict[str, Any] | None:
    if random.random() > probability:
        return None
    return random.choice(RANDOM_EVENT_POOL)
