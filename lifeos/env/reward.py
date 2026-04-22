from __future__ import annotations


def compute_step_reward(
    task_completion: float,
    stress_reduction: float,
    sleep_maintained: float,
    money_saved: float,
    relationship_score: float,
) -> float:
    return (
        0.4 * task_completion
        + 0.2 * stress_reduction
        + 0.2 * sleep_maintained
        + 0.1 * money_saved
        + 0.1 * relationship_score
    )


def clip01(value: float) -> float:
    return max(0.0, min(1.0, value))
