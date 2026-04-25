"""
LifeOS — Gradio Space Interface for Judges.

Interactive demo where judges can run a chaos episode with either a
trained agent or a heuristic agent, and see:
  - Current observation state
  - Agent action taken
  - Reward breakdown per function
  - Running episode total reward
"""
from __future__ import annotations

import json
import random
import sys
import os

# Ensure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

    if unreplied:
        msg = unreplied[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="neutral",
            content_summary="Thanks, noted!",
        )

    return Action(action_type="rest")


def _energy_bar(val):
    color = "#86efac" if val > 50 else "#fde68a" if val > 25 else "#fca5a5"
    return f'<div style="background:rgba(0,0,0,0.08);border-radius:12px;height:18px;overflow:hidden;width:100%"><div style="background:{color};height:100%;width:{val}%;border-radius:12px;transition:width 0.5s ease"></div></div>'


def _stress_bar(val):
    color = "#86efac" if val < 40 else "#fde68a" if val < 70 else "#fca5a5"
    return f'<div style="background:rgba(0,0,0,0.08);border-radius:12px;height:18px;overflow:hidden;width:100%"><div style="background:{color};height:100%;width:{val}%;border-radius:12px;transition:width 0.5s ease"></div></div>'


def _format_obs(obs) -> str:
    if hasattr(obs, "model_dump"):
        d = obs.model_dump()
    else:
        d = obs

    energy = d['energy']
    stress = d['stress']

    lines = [
        f'<div style="background:linear-gradient(135deg,#e0e7ff,#fce7f3);padding:20px;border-radius:16px;margin-bottom:12px">',
        f'<h2 style="margin:0 0 8px;color:#4338ca">Step {d["current_step"]} / {d["max_steps"]}</h2>',
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">',
        f'<div style="background:rgba(255,255,255,0.7);padding:12px;border-radius:12px"><span style="font-size:13px;color:#6366f1;font-weight:600">Energy {energy}/100</span>{_energy_bar(energy)}</div>',
        f'<div style="background:rgba(255,255,255,0.7);padding:12px;border-radius:12px"><span style="font-size:13px;color:#e11d48;font-weight:600">Stress {stress}/100</span>{_stress_bar(stress)}</div>',
        f'<div style="background:rgba(255,255,255,0.7);padding:12px;border-radius:12px"><span style="font-size:22px">&#8377;</span> <b>{d["budget"]:.0f}</b></div>',
        f'<div style="background:rgba(255,255,255,0.7);padding:12px;border-radius:12px"><span style="font-size:13px;color:#7c3aed;font-weight:600">Relationship</span> <b>{d["relationship_score"]:.2f}</b></div>',
        f'</div></div>',
    ]

    # Tasks
    lines.append('<div style="background:rgba(236,254,255,0.6);padding:16px;border-radius:14px;margin-bottom:10px">')
    lines.append('<h3 style="margin:0 0 8px;color:#0891b2">Tasks</h3>')
    for t in d.get("tasks", []):
        if t["status"] == "done":
            lines.append(f'<div style="background:#d1fae5;padding:8px 12px;border-radius:10px;margin:4px 0;border-left:4px solid #34d399"><s>{t["title"]}</s> <span style="color:#059669;font-size:12px">DONE</span></div>')
        else:
            lines.append(f'<div style="background:#fff;padding:8px 12px;border-radius:10px;margin:4px 0;border-left:4px solid #818cf8"><b>{t["title"]}</b> <span style="font-size:12px;color:#6b7280">P{t["priority"]} | deadline step {t["deadline_step"]} | effort {t["effort_remaining"]:.1f}</span></div>')
    lines.append('</div>')

    # Inbox
    lines.append('<div style="background:rgba(254,243,199,0.5);padding:16px;border-radius:14px;margin-bottom:10px">')
    lines.append('<h3 style="margin:0 0 8px;color:#d97706">Inbox</h3>')
    for m in d.get("inbox", []):
        bg = "#d1fae5" if m.get("replied") else "#fef9c3"
        icon = "&#10003;" if m.get("replied") else "&#9993;"
        lines.append(f'<div style="background:{bg};padding:8px 12px;border-radius:10px;margin:4px 0">{icon} <b>{m["sender"]}</b>: {m["content_summary"]}</div>')
    lines.append('</div>')

    # Calendar
    lines.append('<div style="background:rgba(237,233,254,0.5);padding:16px;border-radius:14px;margin-bottom:10px">')
    lines.append('<h3 style="margin:0 0 8px;color:#7c3aed">Calendar</h3>')
    for c in d.get("calendar", []):
        if c.get("is_declined"):
            continue
        conflict = ' <span style="color:#dc2626;font-weight:700">CONFLICT</span>' if c.get("is_conflict") else ""
        lines.append(f'<div style="background:#fff;padding:8px 12px;border-radius:10px;margin:4px 0;border-left:4px solid #a78bfa">Hour {c["scheduled_hour"]}: <b>{c["title"]}</b> ({c["duration_hours"]}h){conflict}</div>')
    lines.append('</div>')

    # Chaos
    chaos = d.get("active_chaos", [])
    if chaos:
        lines.append('<div style="background:rgba(254,202,202,0.4);padding:16px;border-radius:14px;margin-bottom:10px">')
        lines.append('<h3 style="margin:0 0 8px;color:#dc2626">Chaos Events</h3>')
        for c in chaos:
            lines.append(f'<div style="background:#fee2e2;padding:8px 12px;border-radius:10px;margin:4px 0;border-left:4px solid #f87171"><b>{c["event_type"]}</b>: {c["description"]}</div>')
        lines.append('</div>')

    return "\n".join(lines)


def _format_rewards(info: dict) -> str:
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
        lines.append(f"| Timeout Penalty | {timeout:+.3f} | -- |")

    return "\n".join(lines)


def run_episode(agent_type: str) -> tuple[str, str, str]:
    """Run a full episode and return formatted results."""
    env = StudentWeekEnv(max_steps=30, chaos_probability=0.20)
    obs = env.reset()

    history_lines = []
    step_count = 0

    action_colors = {
        "rest": "#bfdbfe",
        "reply_message": "#fef3c7",
        "prioritize_task": "#c7d2fe",
        "delegate_task": "#ddd6fe",
        "decline_event": "#fecdd3",
        "check_budget": "#d1fae5",
    }

    while True:
        obs_dict = obs.model_dump()

        if agent_type == "Heuristic":
            action = _heuristic_action(obs_dict)
        else:
            action = _smart_action(obs_dict)

        obs, reward, done, info = env.step(action)
        step_count += 1

        rc = info.get("reward_components", {})
        action_str = f"{action.action_type}"
        if action.target_id:
            action_str += f"({action.target_id})"

        bg = action_colors.get(action.action_type, "#f3f4f6")
        reward_color = "#059669" if reward >= 0 else "#dc2626"
        history_lines.append(
            f'<div style="background:{bg};padding:10px 14px;border-radius:12px;margin:6px 0;display:flex;justify-content:space-between;align-items:center">'
            f'<span><b>Step {step_count}</b> &rarr; <code>{action_str}</code></span>'
            f'<span style="color:{reward_color};font-weight:700">{reward:+.3f}</span>'
            f'</div>'
        )

        chaos_events = info.get("chaos_events", [])
        for c in chaos_events:
            history_lines.append(
                f'<div style="background:#fee2e2;padding:8px 14px;border-radius:10px;margin:2px 0 6px 20px;border-left:4px solid #f87171;font-size:13px">'
                f'CHAOS: {c["description"]}</div>'
            )

        if done:
            break

    final_state = env.state
    final_obs = _format_obs(obs)

    # Summary card
    reward_val = final_state.total_reward
    reward_color = "#059669" if reward_val > 0 else "#dc2626"
    summary_lines = [
        f'<div style="background:linear-gradient(135deg,#c7d2fe,#fbcfe8);padding:24px;border-radius:18px">',
        f'<h2 style="margin:0 0 12px;color:#312e81">Episode Complete ({agent_type})</h2>',
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Total Steps</span><br><b style="font-size:24px">{step_count}</b></div>',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Total Reward</span><br><b style="font-size:24px;color:{reward_color}">{reward_val:+.3f}</b></div>',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Tasks Done</span><br><b style="font-size:24px;color:#059669">{final_state.tasks_completed}</b></div>',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Tasks Missed</span><br><b style="font-size:24px;color:#dc2626">{final_state.tasks_missed}</b></div>',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Msgs Answered</span><br><b style="font-size:24px;color:#2563eb">{final_state.messages_answered}</b></div>',
        f'<div style="background:rgba(255,255,255,0.75);padding:14px;border-radius:14px;text-align:center"><span style="font-size:12px;color:#6b7280">Msgs Missed</span><br><b style="font-size:24px;color:#d97706">{final_state.messages_unanswered}</b></div>',
        f'</div>',
        f'<div style="margin-top:14px;background:rgba(255,255,255,0.65);padding:14px;border-radius:14px">',
        f'<h3 style="margin:0 0 8px;color:#4338ca">Reward Breakdown</h3>',
    ]
    for k, v in final_state.reward_components.items():
        bar_w = max(0, min(100, (v + 1) * 50))
        bar_color = "#86efac" if v > 0 else "#fca5a5"
        summary_lines.append(
            f'<div style="margin:4px 0"><span style="font-size:12px;display:inline-block;width:180px">{k.replace("_"," ").title()}</span>'
            f'<span style="font-weight:700;width:60px;display:inline-block">{v:+.3f}</span>'
            f'<div style="display:inline-block;background:rgba(0,0,0,0.06);border-radius:6px;height:10px;width:120px;vertical-align:middle"><div style="background:{bar_color};height:100%;width:{bar_w}%;border-radius:6px"></div></div></div>'
        )
    summary_lines.append('</div></div>')

    return final_obs, "\n".join(history_lines), "\n".join(summary_lines)


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

.gradio-container {
    background: linear-gradient(160deg, #f0f4ff 0%, #fdf2f8 40%, #ecfdf5 100%) !important;
    max-width: 1100px !important;
}

.gr-button-primary {
    background: linear-gradient(135deg, #818cf8, #c084fc) !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    padding: 12px 28px !important;
    box-shadow: 0 4px 14px rgba(129,140,248,0.35) !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}
.gr-button-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(129,140,248,0.45) !important;
}

.gr-box, .gr-panel { border-radius: 16px !important; }

footer { display: none !important; }
"""

HEADER_HTML = """
<div style="text-align:center;padding:30px 20px 16px">
    <div style="display:inline-block;background:linear-gradient(135deg,#818cf8,#c084fc);padding:14px 18px;border-radius:18px;margin-bottom:12px">
        <span style="font-size:36px">&#129504;</span>
    </div>
    <h1 style="margin:8px 0 4px;font-size:32px;background:linear-gradient(135deg,#4338ca,#9333ea);-webkit-background-clip:text;-webkit-text-fill-color:transparent">LifeOS: Personal Chaos Agent</h1>
    <p style="color:#6b7280;font-size:15px;margin:0">An RL environment where an LLM must survive cascading personal life chaos.<br>Select an agent and run an episode to watch it handle tasks, messages, budget & stress!</p>
    <div style="display:flex;justify-content:center;gap:12px;margin-top:14px;flex-wrap:wrap">
        <span style="background:#e0e7ff;color:#4338ca;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600">OpenEnv Compliant</span>
        <span style="background:#fce7f3;color:#be185d;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600">4 Reward Signals</span>
        <span style="background:#d1fae5;color:#047857;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600">Anti-Hack Protected</span>
        <span style="background:#ede9fe;color:#6d28d9;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600">GRPO Trained</span>
    </div>
</div>
"""

with gr.Blocks(
    title="LifeOS -- Personal Chaos Agent",
    theme=gr.themes.Soft(),
    css=CUSTOM_CSS,
) as demo:
    gr.HTML(HEADER_HTML)

    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=["Heuristic", "Trained Agent"],
            value="Heuristic",
            label="Select Agent",
        )
        run_btn = gr.Button("Run Episode", variant="primary", scale=2)

    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML('<h3 style="color:#4338ca;margin:0 0 4px">Live Environment State</h3>')
            final_state_md = gr.HTML(value='<div style="text-align:center;padding:40px;color:#9ca3af">Click <b>Run Episode</b> to start a simulation</div>')
        with gr.Column(scale=1):
            gr.HTML('<h3 style="color:#9333ea;margin:0 0 4px">Episode Summary</h3>')
            summary_md = gr.HTML(value="")

    with gr.Accordion("Step-by-Step Action History", open=False):
        history_md = gr.HTML(value="")

    run_btn.click(
        fn=run_episode,
        inputs=[agent_dropdown],
        outputs=[final_state_md, history_md, summary_md],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
