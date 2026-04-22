from __future__ import annotations

from typing import Any


def choose_action(state: dict[str, Any], tasks: list[dict[str, Any]]) -> tuple[str, str]:
    if state["stress"] > 0.75 and state["energy"] < 0.45:
        return "rest", "Stress high and energy low, recover first."
    urgent = [t for t in tasks if t.get("status") != "done" and t.get("deadline_hours", 999) <= 8]
    if urgent:
        return "prioritize", "Urgent deadline detected, prioritizing critical task."
    if state["relationship"] < 0.45:
        return "message", "Relationship trust is dropping, send a message now."
    if state["money"] < 200:
        return "schedule", "Budget is tight, avoid paid options and schedule focused work."
    if state["energy"] < 0.28:
        return "sleep", "Energy is very low, short sleep block to prevent burnout."
    return "focus", "Defaulting to focused execution to increase task completion."
