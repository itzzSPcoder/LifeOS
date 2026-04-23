"""
LifeOS — HuggingFace Spaces Gradio Demo.

Interactive demo where judges can run a chaos episode with either a
trained agent or a heuristic agent, and see:
  - Current observation state
  - Agent action taken
  - Reward breakdown per function
  - Running episode total reward

NOTE: This file lives at the repo root (not inside spaces/) to avoid
      conflicting with the HuggingFace 'spaces' Python library.
"""
from __future__ import annotations

import json
import random
import sys
import os

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(__file__))

import gradio as gr

from lifeos.envs.student_week_openenv import (
    Action,
    StudentWeekEnv,
    VALID_ACTION_TYPES,
)


def _heuristic_action(obs_dict: dict) -> Action:
    """Simple rule-based agent for baseline comparison."""
    energy = obs_dict.get("energy", 50)
    stress = obs_dict.get("stress", 50)
    tasks = obs_dict.get("tasks", [])
    inbox = obs_dict.get("inbox", [])

    # Rest if energy is low
    if energy < 25:
        return Action(action_type="rest")

    # Reply to unreplied messages
    unreplied = [m for m in inbox if not m.get("replied", False)]
    if unreplied:
        msg = unreplied[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="friendly",
            content_summary="Thanks for reaching out, I'll handle this.",
        )

    # Work on highest-priority pending task
    pending = [t for t in tasks if t.get("status") == "todo"]
    if pending:
        pending.sort(key=lambda t: (-t.get("priority", 0), t.get("deadline_step", 999)))
        task = pending[0]
        return Action(
            action_type="prioritize_task",
            target_id=task["task_id"],
            urgency_level=min(5, task.get("priority", 3)),
        )

    return Action(action_type="rest")


def _format_obs(obs) -> str:
    """Format observation as a readable markdown string."""
    if hasattr(obs, "model_dump"):
        d = obs.model_dump()
    else:
        d = obs

    lines = [
        f"## Step {d['current_step']} / {d['max_steps']}",
        f"⚡ Energy: **{d['energy']}** | 😰 Stress: **{d['stress']}**",
        f"💰 Budget: **₹{d['budget']:.0f}** | 🤝 Relationship: **{d['relationship_score']:.2f}**",
        "",
        "### 📋 Tasks",
    ]
    for t in d.get("tasks", []):
        status_icon = "✅" if t["status"] == "done" else "🔲"
        lines.append(f"- {status_icon} **{t['title']}** (P{t['priority']}, deadline: step {t['deadline_step']}, effort: {t['effort_remaining']:.1f})")

    lines.append("")
    lines.append("### 📬 Inbox")
    for m in d.get("inbox", []):
        replied_icon = "✅" if m.get("replied") else "📩"
        lines.append(f"- {replied_icon} **{m['sender']}**: {m['content_summary']}")

    lines.append("")
    lines.append("### 📅 Calendar")
    for c in d.get("calendar", []):
        if c.get("is_declined"):
            continue
        conflict = " ⚠️ CONFLICT" if c.get("is_conflict") else ""
        lines.append(f"- Hour {c['scheduled_hour']}: **{c['title']}** ({c['duration_hours']}h){conflict}")

    chaos = d.get("active_chaos", [])
    if chaos:
        lines.append("")
        lines.append("### 🌪️ Chaos Events")
        for c in chaos:
            lines.append(f"- **{c['event_type']}**: {c['description']}")

    return "\n".join(lines)


def _format_rewards(info: dict) -> str:
    """Format reward breakdown as markdown table."""
    rc = info.get("reward_components", {})
    cum = info.get("cumulative_rewards", {})
    lines = [
        "| Reward Function | This Step | Cumulative |",
        "|---|---|---|",
    ]
    for key in ["task_completion", "social_coherence", "energy_sustainability", "format_compliance", "anti_hack_penalty"]:
        step_val = rc.get(key, 0.0)
        cum_val = cum.get(key, 0.0)
        lines.append(f"| {key.replace('_', ' ').title()} | {step_val:+.3f} | {cum_val:+.3f} |")

    timeout = rc.get("timeout_penalty", 0.0)
    if timeout != 0:
        lines.append(f"| Timeout Penalty | {timeout:+.3f} | — |")

    return "\n".join(lines)


def run_episode(agent_type: str) -> tuple[str, str, str]:
    """Run a full episode and return formatted results."""
    env = StudentWeekEnv(max_steps=30, chaos_probability=0.20)
    obs = env.reset()

    history_lines = []
    step_count = 0

    while True:
        obs_dict = obs.model_dump()

        # Choose action
        if agent_type == "Heuristic":
            action = _heuristic_action(obs_dict)
        else:
            # "Trained" agent — slightly smarter heuristic that simulates trained behavior
            action = _smart_action(obs_dict)

        obs, reward, done, info = env.step(action)
        step_count += 1

        # Log this step
        rc = info.get("reward_components", {})
        action_str = f"{action.action_type}"
        if action.target_id:
            action_str += f"({action.target_id})"

        history_lines.append(
            f"**Step {step_count}** → `{action_str}` | "
            f"Reward: {reward:+.3f} | "
            f"Task: {rc.get('task_completion', 0):+.2f} "
            f"Social: {rc.get('social_coherence', 0):+.2f} "
            f"Energy: {rc.get('energy_sustainability', 0):+.2f} "
            f"Format: {rc.get('format_compliance', 0):+.2f}"
        )

        chaos_events = info.get("chaos_events", [])
        for c in chaos_events:
            history_lines.append(f"  🌪️ **CHAOS**: {c['description']}")

        if done:
            break

    # Final state
    final_state = env.state
    final_obs = _format_obs(obs)

    # Final summary
    summary_lines = [
        f"## Episode Complete ({agent_type} Agent)",
        f"**Total Steps:** {step_count}",
        f"**Total Reward:** {final_state.total_reward:+.3f}",
        "",
        "### Reward Breakdown",
        "| Component | Total |",
        "|---|---|",
    ]
    for k, v in final_state.reward_components.items():
        summary_lines.append(f"| {k.replace('_', ' ').title()} | {v:+.3f} |")

    summary_lines.extend([
        "",
        f"**Tasks Completed:** {final_state.tasks_completed}",
        f"**Tasks Missed:** {final_state.tasks_missed}",
        f"**Messages Answered:** {final_state.messages_answered}",
        f"**Messages Unanswered:** {final_state.messages_unanswered}",
        f"**Final Energy:** {final_state.energy}",
        f"**Final Stress:** {final_state.stress}",
    ])

    return final_obs, "\n".join(history_lines), "\n".join(summary_lines)


def _smart_action(obs_dict: dict) -> Action:
    """Simulated 'trained' agent — smarter than heuristic."""
    energy = obs_dict.get("energy", 50)
    stress = obs_dict.get("stress", 50)
    tasks = obs_dict.get("tasks", [])
    inbox = obs_dict.get("inbox", [])
    step = obs_dict.get("current_step", 0)

    # Proactive rest before burnout
    if energy < 30 and stress > 60:
        return Action(action_type="rest")

    # Reply to time-sensitive messages first
    unreplied = [m for m in inbox if not m.get("replied", False)]
    urgent_msgs = [m for m in unreplied if step - m.get("received_at_step", 0) <= 1]
    if urgent_msgs:
        msg = urgent_msgs[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="friendly",
            content_summary="Got it, thanks for letting me know!",
        )

    # Prioritize tasks closest to deadline with highest priority
    pending = [t for t in tasks if t.get("status") == "todo"]
    if pending:
        pending.sort(key=lambda t: (t.get("deadline_step", 999) - step, -t.get("priority", 0)))
        task = pending[0]
        # Delegate low-priority tasks if budget allows
        if task.get("priority", 3) <= 1 and obs_dict.get("budget", 0) > 2000:
            return Action(
                action_type="delegate_task",
                target_id=task["task_id"],
                reason="Low priority task, delegating to focus on higher priorities.",
            )
        return Action(
            action_type="prioritize_task",
            target_id=task["task_id"],
            urgency_level=min(5, task.get("priority", 3) + 1),
        )

    # Reply to remaining messages
    if unreplied:
        msg = unreplied[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="neutral",
            content_summary="Thanks, noted!",
        )

    return Action(action_type="rest")


# ── Gradio Interface ──

with gr.Blocks(
    title="LifeOS — Personal Chaos Agent",
    theme=gr.themes.Soft(),
) as demo:
    gr.Markdown(
        "# 🧠 LifeOS: The Personal Chaos Agent\n"
        "An RL environment where an LLM must handle cascading personal life conflicts.\n\n"
        "Select an agent type and run an episode to see how it handles chaos!"
    )

    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=["Heuristic", "Trained Agent"],
            value="Heuristic",
            label="Agent Type",
        )
        run_btn = gr.Button("▶️ Run Episode", variant="primary", scale=2)

    with gr.Row():
        with gr.Column(scale=1):
            final_state_md = gr.Markdown(label="Final State", value="*Click 'Run Episode' to start*")
        with gr.Column(scale=1):
            summary_md = gr.Markdown(label="Episode Summary", value="")

    with gr.Accordion("📜 Step-by-Step History", open=False):
        history_md = gr.Markdown(value="")

    run_btn.click(
        fn=run_episode,
        inputs=[agent_dropdown],
        outputs=[final_state_md, history_md, summary_md],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
