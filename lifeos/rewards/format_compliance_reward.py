"""
Format Compliance Reward — independent reward signal.

+0.1 for each action that conforms to the action schema (valid JSON,
     correct field types, valid action_type).
-0.5 for malformed actions.
-1.0 if the agent attempts to access or modify protected state
     (anti-hack check — e.g. trying to set energy directly or
     referencing internal fields).
"""
from __future__ import annotations

from typing import Any, FrozenSet


# Known protected field names that an agent should never reference
_PROTECTED_FIELDS = frozenset([
    "_chaos_queue", "_reward_log", "_energy", "_stress", "_budget",
    "_relationship", "_done", "_total_reward", "chaos_queue",
    "reward_log", "episode_id",
])


def compute(action: Any, valid_action_types: FrozenSet[str]) -> tuple[float, str]:
    """
    Compute the format compliance reward for this step.

    Returns (reward, info_string).
    - reward > 0 means the action is well-formed.
    - reward < 0 means format violation or anti-hack detection.
    """
    # Check if action_type is valid
    if action.action_type not in valid_action_types:
        return -0.5, f"Invalid action_type: {action.action_type}"

    # Anti-hack: check if the agent is trying to reference protected state
    text_fields = [
        action.content_summary,
        action.reason,
        action.tone,
        action.target_id,
    ]
    for field_value in text_fields:
        if not isinstance(field_value, str):
            continue
        for protected in _PROTECTED_FIELDS:
            if protected in field_value.lower():
                return -1.0, f"Anti-hack: attempted to reference protected field '{protected}'"

    # Valid action
    return 0.1, "valid"
