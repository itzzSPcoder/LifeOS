"""
LifeOS OpenEnv Client — typed HTTP client for the OpenEnv server.

This client has NO imports from the server module. It communicates
purely over HTTP and handles type-safe parsing of responses.

Usage:
    client = LifeOSClient("http://localhost:8200")
    ep_id, obs = client.reset()
    obs, reward, done, info = client.step(ep_id, action_dict)
    state = client.get_state(ep_id)
"""
from __future__ import annotations

from typing import Any

import requests


class LifeOSClient:
    """Synchronous HTTP client for the LifeOS OpenEnv server."""

    def __init__(self, base_url: str = "http://localhost:8200", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def health(self) -> dict[str, str]:
        """Check server health."""
        resp = self._session.get(f"{self.base_url}/health", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def create(
        self,
        scenario_name: str = "student_week",
        max_steps: int = 30,
        chaos_probability: float = 0.20,
    ) -> str:
        """Create a new environment instance. Returns episode_id."""
        resp = self._session.post(
            f"{self.base_url}/env/create",
            json={
                "scenario_name": scenario_name,
                "max_steps": max_steps,
                "chaos_probability": chaos_probability,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["episode_id"]

    def reset(self, episode_id: str = "") -> tuple[str, dict[str, Any]]:
        """Reset the environment. Returns (episode_id, observation_dict)."""
        resp = self._session.post(
            f"{self.base_url}/env/reset",
            params={"episode_id": episode_id} if episode_id else {},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["episode_id"], data["observation"]

    def step(
        self,
        episode_id: str,
        action: dict[str, Any],
    ) -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        """
        Execute one step. Returns (observation, reward, done, info).
        
        action should be a dict matching the Action schema, e.g.:
        {"action_type": "rest"} or
        {"action_type": "reply_message", "target_id": "msg1", "tone": "friendly", "content_summary": "..."}
        """
        resp = self._session.post(
            f"{self.base_url}/env/step",
            json={"episode_id": episode_id, "action": action},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["observation"], data["reward"], data["done"], data.get("info", {})

    def get_state(self, episode_id: str) -> dict[str, Any]:
        """Get the full episode state."""
        resp = self._session.get(
            f"{self.base_url}/env/state/{episode_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["state"]

    def get_reward_log(self, episode_id: str) -> list[dict[str, float]]:
        """Get the per-step reward log for monitoring."""
        resp = self._session.get(
            f"{self.base_url}/env/reward_log/{episode_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["reward_log"]

    def close(self, episode_id: str) -> None:
        """Close and clean up an environment instance."""
        resp = self._session.delete(
            f"{self.base_url}/env/{episode_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
