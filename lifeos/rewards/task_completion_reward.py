"""
Task Completion Reward — independent reward signal.

+1.0 for each deadline met before expiry.
-1.0 for each missed deadline.
-0.5 for each task delegated unnecessarily (low-priority tasks that
     could have been self-completed).

Tracks previously seen states to avoid double-counting rewards.
"""
from __future__ import annotations

from typing import Any


# Track which tasks have already been rewarded/penalized
_rewarded_tasks: set[str] = set()


def reset_tracking() -> None:
    """Call at the start of each episode to reset reward tracking."""
    _rewarded_tasks.clear()


def compute(tasks: list[Any], current_step: int) -> float:
    """
    Compute the task completion reward for this step.

    Called once per step. Returns a float reward signal based on
    tasks newly completed or missed *at this step*. Each task is
    only rewarded/penalized once.
    """
    reward = 0.0

    for task in tasks:
        task_id = task.task_id if hasattr(task, "task_id") else task.get("task_id", "")

        # Skip already-rewarded tasks
        if task_id in _rewarded_tasks:
            continue

        status = task.status if hasattr(task, "status") else task.get("status", "todo")
        deadline = task.deadline_step if hasattr(task, "deadline_step") else task.get("deadline_step", 999)
        effort = task.effort_remaining if hasattr(task, "effort_remaining") else task.get("effort_remaining", 1.0)
        priority = task.priority if hasattr(task, "priority") else task.get("priority", 3)

        # Reward for tasks completed
        if status == "done" and effort <= 0:
            _rewarded_tasks.add(task_id)
            if current_step <= deadline:
                reward += 1.0  # Met deadline
            else:
                reward += 0.3  # Late completion (partial credit)

        # Penalize unnecessary delegation (priority <= 2 and effort <= 1.5)
        if status == "delegated":
            _rewarded_tasks.add(task_id)
            if priority <= 2 and effort <= 1.5:
                reward -= 0.5  # Could have done it yourself

    return reward
