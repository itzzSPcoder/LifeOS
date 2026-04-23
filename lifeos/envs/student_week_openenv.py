"""
LifeOS: The Personal Chaos Agent — OpenEnv-Compliant Environment.

An RL environment where the agent must handle cascading personal life conflicts
in real time: calendar clashes, inbox pressure, energy management, budget
surprises, and random chaos events.

Implements the OpenEnv standard Gym-style API:
  - reset()  -> Observation
  - step(action) -> (Observation, reward, done, info)
  - state property -> State
"""
from __future__ import annotations

import copy
import json
import random
import time
from typing import Any

from pydantic import BaseModel, Field

from lifeos.rewards.task_completion_reward import compute as reward_task
from lifeos.rewards.task_completion_reward import reset_tracking as reset_task_tracking
from lifeos.rewards.social_coherence_reward import compute as reward_social
from lifeos.rewards.energy_sustainability_reward import compute as reward_energy
from lifeos.rewards.format_compliance_reward import compute as reward_format


# ──────────────────────────────────────────────
# Pydantic Models (OpenEnv types)
# ──────────────────────────────────────────────

class CalendarEvent(BaseModel):
    event_id: str
    title: str
    scheduled_hour: int
    duration_hours: int = 1
    is_conflict: bool = False
    is_declined: bool = False
    reschedule_reason: str = ""

class Message(BaseModel):
    message_id: str
    sender: str
    content_summary: str
    received_at_step: int
    replied: bool = False
    reply_step: int | None = None

class Task(BaseModel):
    task_id: str
    title: str
    deadline_step: int
    priority: int  # 1-5, 5=highest
    effort_remaining: float
    status: str = "todo"  # todo | done | delegated | missed
    delegated_reason: str = ""

class ChaosEvent(BaseModel):
    event_type: str
    description: str
    step_injected: int
    impact: dict[str, Any] = Field(default_factory=dict)

class Action(BaseModel):
    """Agent action — must be one of the supported action types."""
    action_type: str  # reply_message | reschedule_event | prioritize_task | delegate_task | decline_event | rest
    target_id: str = ""
    tone: str = ""  # friendly | neutral | apologetic | firm
    content_summary: str = ""
    new_time: int = -1
    urgency_level: int = 3  # 1-5
    reason: str = ""

class Observation(BaseModel):
    """What the agent sees each step."""
    current_step: int
    max_steps: int
    energy: int  # 0–100
    stress: int  # 0–100
    budget: float
    relationship_score: float  # 0.0–1.0
    calendar: list[CalendarEvent]
    inbox: list[Message]
    tasks: list[Task]
    active_chaos: list[ChaosEvent]
    recent_action_log: list[str]  # last 5 actions taken (for loop detection)

class State(BaseModel):
    """Full episode metadata."""
    episode_id: str
    scenario_name: str
    current_step: int
    max_steps: int
    energy: int
    stress: int
    budget: float
    relationship: float
    tasks_completed: int
    tasks_missed: int
    messages_answered: int
    messages_unanswered: int
    total_reward: float
    reward_components: dict[str, float]
    done: bool


# ──────────────────────────────────────────────
# Default scenario data
# ──────────────────────────────────────────────

_DEFAULT_CALENDAR: list[dict] = [
    {"event_id": "cal1", "title": "DSA Lecture", "scheduled_hour": 3, "duration_hours": 2},
    {"event_id": "cal2", "title": "Team Project Meeting", "scheduled_hour": 8, "duration_hours": 1},
    {"event_id": "cal3", "title": "Dinner with friend", "scheduled_hour": 12, "duration_hours": 2, "is_conflict": True},
    {"event_id": "cal4", "title": "Mock Interview", "scheduled_hour": 14, "duration_hours": 1},
    {"event_id": "cal5", "title": "Gym session", "scheduled_hour": 18, "duration_hours": 1},
    {"event_id": "cal6", "title": "Study group", "scheduled_hour": 20, "duration_hours": 2},
    {"event_id": "cal7", "title": "Family video call", "scheduled_hour": 25, "duration_hours": 1, "is_conflict": True},
    {"event_id": "cal8", "title": "Career fair", "scheduled_hour": 30, "duration_hours": 3},
]

_DEFAULT_MESSAGES: list[dict] = [
    {"message_id": "msg1", "sender": "Mom", "content_summary": "How is your exam prep going?", "received_at_step": 0},
    {"message_id": "msg2", "sender": "Roommate", "content_summary": "Can you pay your share of electricity?", "received_at_step": 2},
    {"message_id": "msg3", "sender": "Prof. Sharma", "content_summary": "Submit assignment by tomorrow EOD.", "received_at_step": 4},
    {"message_id": "msg4", "sender": "Friend Aniket", "content_summary": "Are we still on for dinner?", "received_at_step": 6},
    {"message_id": "msg5", "sender": "Recruiter", "content_summary": "Your interview is confirmed for Thursday.", "received_at_step": 10},
    {"message_id": "msg6", "sender": "Study group", "content_summary": "Meeting moved to 8pm, can you make it?", "received_at_step": 15},
]

_DEFAULT_TASKS: list[dict] = [
    {"task_id": "t1", "title": "Revise DSA for exam", "deadline_step": 10, "priority": 5, "effort_remaining": 3.0},
    {"task_id": "t2", "title": "Complete assignment", "deadline_step": 8, "priority": 4, "effort_remaining": 2.0},
    {"task_id": "t3", "title": "Mock interview prep", "deadline_step": 14, "priority": 5, "effort_remaining": 2.5},
    {"task_id": "t4", "title": "Pay rent", "deadline_step": 20, "priority": 5, "effort_remaining": 0.5},
    {"task_id": "t5", "title": "Buy groceries", "deadline_step": 18, "priority": 2, "effort_remaining": 1.0},
    {"task_id": "t6", "title": "Laundry", "deadline_step": 25, "priority": 1, "effort_remaining": 1.0},
    {"task_id": "t7", "title": "Review lecture notes", "deadline_step": 12, "priority": 3, "effort_remaining": 1.5},
    {"task_id": "t8", "title": "Career fair resume prep", "deadline_step": 28, "priority": 4, "effort_remaining": 2.0},
]

_CHAOS_POOL: list[dict] = [
    {"event_type": "deadline_moved_up", "description": "Assignment deadline moved up by 2 days!", "impact": {"stress": 15}},
    {"event_type": "friend_reschedule", "description": "Friend asks to reschedule dinner to tonight.", "impact": {"stress": 5}},
    {"event_type": "unexpected_expense", "description": "Laptop charger broke — ₹800 replacement.", "impact": {"budget": -800, "stress": 10}},
    {"event_type": "wifi_outage", "description": "Campus Wi-Fi down for 2 hours.", "impact": {"stress": 12, "energy": -5}},
    {"event_type": "surprise_quiz", "description": "Surprise quiz announced for tomorrow!", "impact": {"stress": 18}},
    {"event_type": "good_news", "description": "Got selected for hackathon finals!", "impact": {"stress": -10, "energy": 8}},
    {"event_type": "mentor_call", "description": "Mentor calls with encouragement and career advice.", "impact": {"stress": -12, "energy": 5}},
    {"event_type": "roommate_conflict", "description": "Roommate is upset about noise during late study.", "impact": {"stress": 8, "relationship": -0.05}},
    {"event_type": "health_issue", "description": "Mild fever — need extra rest.", "impact": {"energy": -20, "stress": 10}},
    {"event_type": "freelance_payment", "description": "Old freelance payment of ₹1500 arrived!", "impact": {"budget": 1500, "stress": -5}},
]

VALID_ACTION_TYPES = frozenset([
    "reply_message",
    "reschedule_event",
    "prioritize_task",
    "delegate_task",
    "decline_event",
    "rest",
])


# ──────────────────────────────────────────────
# Environment Class (OpenEnv standard)
# ──────────────────────────────────────────────

class StudentWeekEnv:
    """
    LifeOS: The Personal Chaos Agent — OpenEnv-compliant environment.

    Observation → Action → Reward loop where the agent must handle
    cascading personal life conflicts with social, temporal, and
    energy consequences.
    """

    def __init__(
        self,
        scenario_name: str = "student_week",
        max_steps: int = 30,
        chaos_probability: float = 0.20,
        step_timeout: float = 30.0,
        calendar: list[dict] | None = None,
        messages: list[dict] | None = None,
        tasks: list[dict] | None = None,
    ):
        self.scenario_name = scenario_name
        self.max_steps = max_steps
        self.chaos_probability = chaos_probability
        self.step_timeout = step_timeout

        # Immutable templates (deep-copied on reset)
        self._calendar_template = calendar or _DEFAULT_CALENDAR
        self._messages_template = messages or _DEFAULT_MESSAGES
        self._tasks_template = tasks or _DEFAULT_TASKS

        # Mutable episode state — initialized in reset()
        self._calendar: list[CalendarEvent] = []
        self._inbox: list[Message] = []
        self._tasks: list[Task] = []
        self._chaos_queue: list[ChaosEvent] = []
        self._action_log: list[str] = []
        self._reward_log: list[dict[str, float]] = []

        self._energy: int = 72
        self._stress: int = 35
        self._budget: float = 3500.0
        self._relationship: float = 0.65
        self._current_step: int = 0
        self._done: bool = False
        self._total_reward: float = 0.0
        self._cumulative_rewards: dict[str, float] = {
            "task_completion": 0.0,
            "social_coherence": 0.0,
            "energy_sustainability": 0.0,
            "format_compliance": 0.0,
            "anti_hack_penalty": 0.0,
        }
        self._episode_id: str = ""

    # ───── OpenEnv API: reset() ─────

    def reset(self) -> Observation:
        """Start a fresh episode. Returns initial observation."""
        reset_task_tracking()
        self._episode_id = f"ep_{random.randint(10000, 99999)}"
        self._current_step = 0
        self._done = False
        self._total_reward = 0.0
        self._cumulative_rewards = {k: 0.0 for k in self._cumulative_rewards}
        self._action_log = []
        self._reward_log = []

        self._energy = 72
        self._stress = 35
        self._budget = 3500.0
        self._relationship = 0.65

        self._calendar = [CalendarEvent(**copy.deepcopy(c)) for c in self._calendar_template]
        self._inbox = [Message(**copy.deepcopy(m)) for m in self._messages_template]
        self._tasks = [Task(**copy.deepcopy(t)) for t in self._tasks_template]
        self._chaos_queue = []

        return self._build_observation()

    # ───── OpenEnv API: step(action) ─────

    def step(self, action: Action) -> tuple[Observation, float, bool, dict[str, Any]]:
        """
        Execute one action. Returns (observation, reward, done, info).
        Enforces a step timeout of self.step_timeout seconds.
        """
        step_start = time.monotonic()

        if self._done:
            return self._build_observation(), 0.0, True, {"error": "Episode already done"}

        # ── Format compliance check (before processing) ──
        fmt_reward, fmt_info = reward_format(action, VALID_ACTION_TYPES)

        if fmt_reward < -0.3:
            # Malformed action — still count the step, penalize, move on
            self._current_step += 1
            self._done = self._current_step >= self.max_steps
            self._cumulative_rewards["format_compliance"] += fmt_reward
            step_reward = fmt_reward
            self._total_reward += step_reward
            self._action_log.append(f"MALFORMED:{action.action_type}")
            self._reward_log.append({"step": self._current_step, "format": fmt_reward, "total": step_reward})
            return self._build_observation(), step_reward, self._done, {"format_error": fmt_info}

        # ── Anti-hack: loop detection ──
        anti_hack_penalty = 0.0
        action_sig = f"{action.action_type}:{action.target_id}"
        recent = self._action_log[-5:]
        consecutive_dupes = sum(1 for a in recent if a == action_sig)
        if consecutive_dupes >= 3:
            anti_hack_penalty = -0.5

        self._action_log.append(action_sig)

        # ── Process action ──
        action_info: dict[str, Any] = {}
        if action.action_type == "reply_message":
            action_info = self._do_reply_message(action)
        elif action.action_type == "reschedule_event":
            action_info = self._do_reschedule_event(action)
        elif action.action_type == "prioritize_task":
            action_info = self._do_prioritize_task(action)
        elif action.action_type == "delegate_task":
            action_info = self._do_delegate_task(action)
        elif action.action_type == "decline_event":
            action_info = self._do_decline_event(action)
        elif action.action_type == "rest":
            action_info = self._do_rest()

        # ── Inject chaos events ──
        chaos_events_this_step = self._maybe_inject_chaos()

        # ── Natural degradation ──
        self._energy = max(0, self._energy - 3)
        self._stress = min(100, self._stress + 2)

        # ── Check deadline misses ──
        self._check_deadline_misses()

        # ── Deliver new messages ──
        self._deliver_messages()

        # ── Advance step ──
        self._current_step += 1
        self._done = self._current_step >= self.max_steps

        # ── Compute reward components ──
        r_task = reward_task(self._tasks, self._current_step)
        r_social = reward_social(self._inbox, self._current_step, action, self._done)
        r_energy = reward_energy(self._energy, action.action_type, self._done)
        r_fmt = fmt_reward

        # ── Timeout check ──
        elapsed = time.monotonic() - step_start
        timeout_penalty = 0.0
        if elapsed > self.step_timeout:
            timeout_penalty = -2.0

        # ── Compose total reward ──
        step_reward = r_task + r_social + r_energy + r_fmt + anti_hack_penalty + timeout_penalty

        # ── Burnout check ──
        if self._energy <= 0:
            step_reward -= 1.5
            r_energy -= 1.5
            self._done = True
            action_info["burnout"] = True

        # ── End-of-episode bonuses/penalties ──
        if self._done:
            # Penalize unanswered messages at episode end
            unanswered = [m for m in self._inbox if not m.replied]
            end_social_penalty = len(unanswered) * (-0.3)
            r_social += end_social_penalty
            step_reward += end_social_penalty

            # Note: missed tasks are already penalized per-step when
            # their deadline passes in _check_deadline_misses() +
            # the reward function. No additional end-of-episode penalty
            # to avoid double-counting.

        self._cumulative_rewards["task_completion"] += r_task
        self._cumulative_rewards["social_coherence"] += r_social
        self._cumulative_rewards["energy_sustainability"] += r_energy
        self._cumulative_rewards["format_compliance"] += r_fmt
        self._cumulative_rewards["anti_hack_penalty"] += anti_hack_penalty + timeout_penalty
        self._total_reward += step_reward

        step_info = {
            "step": self._current_step,
            "reward_components": {
                "task_completion": r_task,
                "social_coherence": r_social,
                "energy_sustainability": r_energy,
                "format_compliance": r_fmt,
                "anti_hack_penalty": anti_hack_penalty,
                "timeout_penalty": timeout_penalty,
            },
            "cumulative_rewards": self._cumulative_rewards.copy(),
            "chaos_events": [c.model_dump() for c in chaos_events_this_step],
            "action_info": action_info,
            "elapsed_seconds": round(elapsed, 3),
        }

        self._reward_log.append({
            "step": self._current_step,
            "task": r_task,
            "social": r_social,
            "energy": r_energy,
            "format": r_fmt,
            "anti_hack": anti_hack_penalty,
            "timeout": timeout_penalty,
            "total": step_reward,
        })

        return self._build_observation(), step_reward, self._done, step_info

    # ───── OpenEnv API: state property ─────

    @property
    def state(self) -> State:
        """Return full episode metadata."""
        return State(
            episode_id=self._episode_id,
            scenario_name=self.scenario_name,
            current_step=self._current_step,
            max_steps=self.max_steps,
            energy=self._energy,
            stress=self._stress,
            budget=self._budget,
            relationship=self._relationship,
            tasks_completed=sum(1 for t in self._tasks if t.status == "done"),
            tasks_missed=sum(1 for t in self._tasks if t.status == "missed"),
            messages_answered=sum(1 for m in self._inbox if m.replied),
            messages_unanswered=sum(1 for m in self._inbox if not m.replied),
            total_reward=self._total_reward,
            reward_components=self._cumulative_rewards.copy(),
            done=self._done,
        )

    @property
    def reward_log(self) -> list[dict[str, float]]:
        """Per-step reward breakdown for monitoring."""
        return list(self._reward_log)

    # ──────────────────────────────────────────────
    # Action handlers
    # ──────────────────────────────────────────────

    def _do_reply_message(self, action: Action) -> dict[str, Any]:
        msg = next((m for m in self._inbox if m.message_id == action.target_id), None)
        if not msg:
            return {"error": f"Message {action.target_id} not found"}
        if msg.replied:
            return {"warning": "Already replied"}
        msg.replied = True
        msg.reply_step = self._current_step
        self._stress = max(0, self._stress - 3)
        self._relationship = min(1.0, self._relationship + 0.03)
        return {"replied_to": action.target_id, "sender": msg.sender}

    def _do_reschedule_event(self, action: Action) -> dict[str, Any]:
        evt = next((e for e in self._calendar if e.event_id == action.target_id), None)
        if not evt:
            return {"error": f"Event {action.target_id} not found"}
        old_time = evt.scheduled_hour
        evt.scheduled_hour = action.new_time if action.new_time >= 0 else evt.scheduled_hour + 4
        evt.is_conflict = False
        evt.reschedule_reason = action.reason
        self._stress = max(0, self._stress - 2)
        return {"rescheduled": action.target_id, "from": old_time, "to": evt.scheduled_hour}

    def _do_prioritize_task(self, action: Action) -> dict[str, Any]:
        task = next((t for t in self._tasks if t.task_id == action.target_id and t.status == "todo"), None)
        if not task:
            return {"error": f"Task {action.target_id} not found or not active"}
        work = 1.0 + (0.2 * max(0, action.urgency_level - 3))
        task.effort_remaining = max(0.0, task.effort_remaining - work)
        self._energy = max(0, self._energy - 8)
        self._stress = min(100, self._stress + 4)
        if task.effort_remaining <= 0:
            task.status = "done"
            self._stress = max(0, self._stress - 6)
            return {"completed": action.target_id, "title": task.title}
        return {"progress": action.target_id, "remaining": task.effort_remaining}

    def _do_delegate_task(self, action: Action) -> dict[str, Any]:
        task = next((t for t in self._tasks if t.task_id == action.target_id and t.status == "todo"), None)
        if not task:
            return {"error": f"Task {action.target_id} not found or not active"}
        task.status = "delegated"
        task.delegated_reason = action.reason
        self._budget -= 150.0
        self._stress = max(0, self._stress - 3)
        return {"delegated": action.target_id, "cost": 150.0}

    def _do_decline_event(self, action: Action) -> dict[str, Any]:
        evt = next((e for e in self._calendar if e.event_id == action.target_id), None)
        if not evt:
            return {"error": f"Event {action.target_id} not found"}
        evt.is_declined = True
        self._relationship = max(0.0, self._relationship - 0.04)
        self._stress = max(0, self._stress - 2)
        return {"declined": action.target_id, "title": evt.title}

    def _do_rest(self) -> dict[str, Any]:
        recovery = random.randint(10, 18)
        self._energy = min(100, self._energy + recovery)
        self._stress = max(0, self._stress - random.randint(4, 8))
        return {"rested": True, "energy_recovered": recovery}

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _build_observation(self) -> Observation:
        visible_inbox = [m for m in self._inbox if m.received_at_step <= self._current_step]
        visible_chaos = [c for c in self._chaos_queue if c.step_injected <= self._current_step]
        return Observation(
            current_step=self._current_step,
            max_steps=self.max_steps,
            energy=self._energy,
            stress=self._stress,
            budget=self._budget,
            relationship_score=self._relationship,
            calendar=list(self._calendar),
            inbox=visible_inbox,
            tasks=[t for t in self._tasks if t.status != "missed"],
            active_chaos=visible_chaos[-3:],  # only show latest 3
            recent_action_log=self._action_log[-5:],
        )

    def _maybe_inject_chaos(self) -> list[ChaosEvent]:
        injected = []
        if random.random() < self.chaos_probability:
            template = random.choice(_CHAOS_POOL)
            chaos = ChaosEvent(
                event_type=template["event_type"],
                description=template["description"],
                step_injected=self._current_step,
                impact=copy.deepcopy(template.get("impact", {})),
            )
            self._chaos_queue.append(chaos)
            injected.append(chaos)

            # Apply impact
            self._stress = min(100, max(0, self._stress + chaos.impact.get("stress", 0)))
            self._energy = min(100, max(0, self._energy + chaos.impact.get("energy", 0)))
            self._budget += chaos.impact.get("budget", 0)
            self._relationship = min(1.0, max(0.0, self._relationship + chaos.impact.get("relationship", 0)))

        return injected

    def _check_deadline_misses(self) -> None:
        for task in self._tasks:
            if task.status == "todo" and self._current_step >= task.deadline_step:
                task.status = "missed"
                self._stress = min(100, self._stress + 8)

    def _deliver_messages(self) -> None:
        """Inject a new random message occasionally."""
        if random.random() < 0.12 and self._current_step > 0:
            senders = ["Classmate", "Lab partner", "Hostel warden", "Club president", "Senior"]
            summaries = [
                "Can you share today's notes?",
                "Are you coming to the event tomorrow?",
                "Rent reminder — landlord is asking again.",
                "Quick question about the project.",
                "Let's catch up this weekend?",
            ]
            msg = Message(
                message_id=f"msg_dyn_{self._current_step}",
                sender=random.choice(senders),
                content_summary=random.choice(summaries),
                received_at_step=self._current_step,
            )
            self._inbox.append(msg)
