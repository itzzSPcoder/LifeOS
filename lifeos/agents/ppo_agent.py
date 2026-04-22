from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from lifeos.agents.heuristic import choose_action as heuristic_choose_action
from lifeos.constants import ACTION_SPACE


HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model_id}"


def choose_action(
    state: dict[str, Any],
    tasks: list[dict[str, Any]],
    model: str | None = None,
) -> tuple[str, str]:
    model = model or os.getenv("LIFEOS_HF_MODEL")
    token = os.getenv("HF_API_TOKEN")
    if not model or not token:
        action, reason = heuristic_choose_action(state, tasks)
        return action, f"[fallback] {reason}"

    prompt = {
        "inputs": (
            "You are a PPO-trained life planner. Return JSON with keys action and reasoning. "
            f"Allowed actions: {ACTION_SPACE}. "
            f"State: {json.dumps(state)}. Open tasks count: {len([t for t in tasks if t.get('status') != 'done'])}."
        )
    }
    try:
        response = requests.post(
            HF_INFERENCE_URL.format(model_id=model),
            headers={"Authorization": f"Bearer {token}"},
            json=prompt,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        text = _extract_text(payload)
        action, reasoning = _parse_action_reasoning(text)
        if action not in ACTION_SPACE:
            raise ValueError("Invalid action from model")
        return action, reasoning
    except Exception:
        action, reason = heuristic_choose_action(state, tasks)
        return action, f"[hf-error->fallback] {reason}"


def _extract_text(payload: Any) -> str:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        generated = payload[0].get("generated_text")
        if isinstance(generated, str):
            return generated
    if isinstance(payload, dict):
        if isinstance(payload.get("generated_text"), str):
            return payload["generated_text"]
    return str(payload)


def _parse_action_reasoning(text: str) -> tuple[str, str]:
    cleaned = text.strip()

    # Handle fenced JSON outputs from chat models.
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Extract first JSON object from noisy outputs.
    if "{" in cleaned and "}" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return _normalize_action(parsed.get("action")), str(parsed.get("reasoning", "No reasoning"))
        except Exception:
            pass

    try:
        parsed = json.loads(cleaned)
        return _normalize_action(parsed.get("action")), str(parsed.get("reasoning", "No reasoning"))
    except Exception:
        lowered = cleaned.lower()
        for action in ACTION_SPACE:
            if action in lowered:
                return action, cleaned[:240]
        return "prioritize", cleaned[:240]


def _normalize_action(value: Any) -> str:
    action = str(value or "prioritize").strip().lower().replace("-", "_")
    aliases = {
        "study": "focus",
        "work": "focus",
        "sleeping": "sleep",
        "text": "message",
    }
    action = aliases.get(action, action)
    if action not in ACTION_SPACE:
        return "prioritize"
    return action
