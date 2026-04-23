"""
Task Completion Reward — independent reward signal.

+1.0 for each deadline met before expiry.
-1.0 for each missed deadline.
-0.5 for each task delegated unnecessarily (low-priority tasks that
     could have been self-completed).
"""
from __future__ import annotations

from typing import Any


def compute(tasks: list[Any], current_step: int) -> float:
    """
    Compute the task completion reward for this step.

    Called once per step. Returns a float reward signal based on
    tasks newly completed or missed *at this step*.
    """
    reward = 0.0

    for task in tasks:
        # Reward for tasks completed in this step window
        if task.status == "done" and _just_completed(task, current_step):
            if current_step <= task.deadline_step:
                reward += 1.0  # Met deadline
            else:
                reward += 0.3  # Late completion (partial credit)

        # Penalize unnecessary delegation (priority <= 2 and effort <= 1.5)
        if task.status == "delegated" and _just_delegated(task, current_step):
            if task.priority <= 2 and task.effort_remaining <= 1.5:
                reward -= 0.5  # Could have done it yourself

    return reward


def _just_completed(task: Any, current_step: int) -> bool:
    """Heuristic: a task was just completed if its remaining effort is 0 and status is done."""
    return task.effort_remaining <= 0 and task.status == "done"


def _just_delegated(task: Any, current_step: int) -> bool:
    """A task was just delegated if its status is delegated."""
    return task.status == "delegated"
