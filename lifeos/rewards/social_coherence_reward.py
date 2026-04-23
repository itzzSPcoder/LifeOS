"""
Social Coherence Reward — independent reward signal.

+0.5 for each message replied to within 1 time step of receipt.
-0.8 for each unanswered message at episode end.
+0.3 if rescheduling an event includes a valid reason in the action.
"""
from __future__ import annotations

from typing import Any


def compute(inbox: list[Any], current_step: int, action: Any, is_done: bool) -> float:
    """
    Compute the social coherence reward for this step.

    Called once per step. Rewards timely replies and penalizes
    unanswered messages. End-of-episode penalties are applied by
    the environment separately.
    """
    reward = 0.0

    # Check if a message was replied to this step
    if action.action_type == "reply_message" and action.target_id:
        msg = next((m for m in inbox if m.message_id == action.target_id and m.replied), None)
        if msg and msg.reply_step is not None:
            # Replied within 1 step of receipt
            if msg.reply_step - msg.received_at_step <= 1:
                reward += 0.5
            else:
                reward += 0.15  # Late reply — partial credit

    # Bonus for rescheduling with a valid reason
    if action.action_type == "reschedule_event" and action.reason.strip():
        if len(action.reason.strip()) >= 5:  # Must be a meaningful reason
            reward += 0.3

    return reward
