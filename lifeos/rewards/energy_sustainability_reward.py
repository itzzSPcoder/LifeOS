"""
Energy Sustainability Reward — independent reward signal.

+0.2 for each time step where energy stays above 40.
-1.5 if energy hits 0 (burnout — triggers episode penalty).
+0.4 for proactive rest actions taken before energy drops below 30.
"""
from __future__ import annotations


def compute(energy: int, action_type: str, is_done: bool) -> float:
    """
    Compute the energy sustainability reward for this step.

    Called once per step. Rewards maintaining healthy energy levels
    and proactive rest. Penalizes burnout.
    """
    reward = 0.0

    # Reward for maintaining energy above 40
    if energy > 40:
        reward += 0.2

    # Reward proactive rest before energy drops below 30
    if action_type == "rest" and energy < 30:
        reward += 0.4

    # Burnout penalty is applied by the environment directly
    # (energy <= 0 check) — we don't duplicate it here

    return reward
