from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np

from lifeos.constants import ACTION_SPACE, MAX_TIMESTEPS
from lifeos.env.events import maybe_inject_random_event
from lifeos.env.reward import clip01, compute_step_reward


@dataclass
class StepResult:
    observation: np.ndarray
    reward: float
    done: bool
    info: dict[str, Any]


class LifeOSEnv:
    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario
        self.max_steps = MAX_TIMESTEPS
        self.reset()

    def reset(self) -> np.ndarray:
        self.timestep = 0
        self.profile = copy.deepcopy(self.scenario["profile"])
        self.tasks = copy.deepcopy(self.scenario["tasks"])
        self.events = copy.deepcopy(self.scenario["events"])
        self.event_cursor = 0
        self.total_reward = 0.0
        self.sleep_hours = float(self.profile.get("sleep_hours", 6.0))
        self.state = {
            "energy": clip01(float(self.profile["energy"])),
            "stress": clip01(float(self.profile["stress"])),
            "money": float(self.profile["money"]),
            "relationship": clip01(float(self.profile["relationship"])),
        }
        return self._observation()

    def _completion_ratio(self) -> float:
        completed = sum(1 for t in self.tasks if t.get("status") == "done")
        return completed / max(1, len(self.tasks))

    def _pending_tasks(self) -> list[dict[str, Any]]:
        return [t for t in self.tasks if t.get("status") != "done"]

    def _known_events(self) -> list[dict[str, Any]]:
        horizon = self.timestep + 12
        return [e for e in self.events if self.timestep <= e["timestep"] <= horizon]

    def _observation(self) -> np.ndarray:
        obs = np.array(
            [
                self.timestep / self.max_steps,
                self.state["energy"],
                self.state["stress"],
                min(1.0, max(0.0, self.state["money"] / 5000.0)),
                self.state["relationship"],
                min(1.0, self.sleep_hours / 8.0),
                self._completion_ratio(),
                len(self._pending_tasks()) / max(1, len(self.tasks)),
            ],
            dtype=np.float32,
        )
        return obs

    def _apply_event_impact(self, event: dict[str, Any]) -> None:
        impact = event.get("impact", {})
        self.state["stress"] = clip01(self.state["stress"] + float(impact.get("stress", 0.0)))
        self.state["energy"] = clip01(self.state["energy"] + float(impact.get("energy", 0.0)))
        self.state["money"] += float(impact.get("money", 0.0))
        self.state["relationship"] = clip01(
            self.state["relationship"] + float(impact.get("relationship", 0.0))
        )

    def _complete_task(self, boost: float = 1.0) -> bool:
        pending = sorted(self._pending_tasks(), key=lambda t: (t["deadline_hours"], -t["priority"]))
        if not pending:
            return False
        task = pending[0]
        task["remaining_effort"] = max(0.0, float(task["remaining_effort"]) - boost)
        if task["remaining_effort"] <= 0:
            task["status"] = "done"
            return True
        return False

    def _handle_deadlines(self) -> float:
        penalty = 0.0
        for task in self._pending_tasks():
            if self.timestep > int(task["deadline_hours"]):
                penalty -= 0.03
                self.state["stress"] = clip01(self.state["stress"] + 0.01)
        return penalty

    def step(self, action_type: str, reasoning: str = "") -> StepResult:
        if action_type not in ACTION_SPACE:
            action_type = "prioritize"

        prev_stress = self.state["stress"]
        prev_completion = self._completion_ratio()
        prev_money = self.state["money"]
        prev_sleep = self.sleep_hours

        task_done = False
        if action_type == "schedule":
            task_done = self._complete_task(1.0)
            self.state["energy"] = clip01(self.state["energy"] - 0.07)
            self.state["stress"] = clip01(self.state["stress"] + 0.02)
        elif action_type == "postpone":
            self.state["stress"] = clip01(self.state["stress"] + 0.07)
        elif action_type == "cancel":
            pending = self._pending_tasks()
            if pending:
                pending[0]["status"] = "cancelled"
            self.state["relationship"] = clip01(self.state["relationship"] - 0.03)
            self.state["stress"] = clip01(self.state["stress"] + 0.03)
        elif action_type == "message":
            self.state["relationship"] = clip01(self.state["relationship"] + 0.08)
            self.state["stress"] = clip01(self.state["stress"] - 0.04)
        elif action_type == "rest":
            self.state["energy"] = clip01(self.state["energy"] + 0.15)
            self.state["stress"] = clip01(self.state["stress"] - 0.12)
            self.sleep_hours += 0.5
        elif action_type == "commute":
            self.state["energy"] = clip01(self.state["energy"] - 0.08)
            self.state["stress"] = clip01(self.state["stress"] + 0.01)
        elif action_type == "buy":
            self.state["money"] -= 80.0
            self.state["stress"] = clip01(self.state["stress"] - 0.03)
        elif action_type == "delegate":
            self.state["money"] -= 120.0
            task_done = self._complete_task(1.2)
        elif action_type == "prioritize":
            task_done = self._complete_task(1.4)
            self.state["energy"] = clip01(self.state["energy"] - 0.1)
            self.state["stress"] = clip01(self.state["stress"] + 0.03)
        elif action_type == "sleep":
            self.state["energy"] = clip01(self.state["energy"] + 0.2)
            self.state["stress"] = clip01(self.state["stress"] - 0.1)
            self.sleep_hours += 1.2
        elif action_type == "focus":
            task_done = self._complete_task(1.8)
            self.state["energy"] = clip01(self.state["energy"] - 0.14)
            self.state["stress"] = clip01(self.state["stress"] + 0.05)

        triggered_events = []
        for scripted_event in self.events:
            if int(scripted_event["timestep"]) == self.timestep:
                self._apply_event_impact(scripted_event)
                triggered_events.append(scripted_event)

        random_event = maybe_inject_random_event()
        if random_event:
            self._apply_event_impact(random_event)
            random_event = {**random_event, "is_random": True, "timestep": self.timestep}
            triggered_events.append(random_event)

        deadline_penalty = self._handle_deadlines()

        self.timestep += 1
        done = self.timestep >= self.max_steps

        completion_ratio = self._completion_ratio()
        task_completion_gain = max(0.0, completion_ratio - prev_completion)
        stress_reduction = max(0.0, prev_stress - self.state["stress"])
        sleep_maintained = clip01(self.sleep_hours / 8.0)
        money_saved = clip01(self.state["money"] / max(1.0, prev_money if prev_money > 0 else 1000.0))
        relationship_score = self.state["relationship"]

        reward = compute_step_reward(
            task_completion=task_completion_gain,
            stress_reduction=stress_reduction,
            sleep_maintained=sleep_maintained,
            money_saved=money_saved,
            relationship_score=relationship_score,
        )
        reward += deadline_penalty

        if task_done:
            reward += 0.15
        if self.state["stress"] > 0.9:
            reward -= 0.12
        if self.state["energy"] < 0.1:
            reward -= 0.1
        if self.sleep_hours < prev_sleep and action_type != "focus":
            reward -= 0.02

        if done:
            reward += (
                0.5 * completion_ratio
                + 0.2 * (1.0 - self.state["stress"])
                + 0.2 * self.state["relationship"]
                + 0.1 * clip01(self.state["energy"])
            )

        self.total_reward += reward

        info = {
            "timestep": self.timestep,
            "action": action_type,
            "reasoning": reasoning,
            "task_done": task_done,
            "state": self.state.copy(),
            "sleep_hours": self.sleep_hours,
            "completion": completion_ratio,
            "pending_tasks": len(self._pending_tasks()),
            "known_events": self._known_events(),
            "triggered_events": triggered_events,
            "done": done,
        }
        return StepResult(observation=self._observation(), reward=float(reward), done=done, info=info)
