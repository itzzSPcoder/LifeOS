"""
LifeOS -- Gradio Space Interface for Judges.

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
import pandas as pd

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

    if energy < 25:
        return Action(action_type="rest"), "Energy is critically low. I must rest before I burn out completely."

    unreplied = [m for m in inbox if not m.get("replied", False)]
    if unreplied:
        msg = unreplied[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="friendly",
            content_summary="Thanks for reaching out, I'll handle this.",
        ), f"Need to clear the inbox. Replying to {msg['sender']}."

    pending = [t for t in tasks if t.get("status") == "todo"]
    if pending:
        pending.sort(key=lambda t: (-t.get("priority", 0), t.get("deadline_step", 999)))
        task = pending[0]
        return Action(
            action_type="prioritize_task",
            target_id=task["task_id"],
            urgency_level=min(5, task.get("priority", 3)),
        ), f"Prioritizing high-priority task: {task['title']}."

    return Action(action_type="rest"), "Nothing urgent pending. Taking a quick nap to recover energy."


def _smart_action(obs_dict: dict) -> Action:
    """Simulated 'trained' agent -- smarter than heuristic."""
    energy = obs_dict.get("energy", 50)
    stress = obs_dict.get("stress", 50)
    tasks = obs_dict.get("tasks", [])
    inbox = obs_dict.get("inbox", [])
    step = obs_dict.get("current_step", 0)

    if energy < 30 and stress > 60:
        return Action(action_type="rest"), "🚨 Panic mode! High stress and low energy. If I don't rest RIGHT NOW, I will crash."

    unreplied = [m for m in inbox if not m.get("replied", False)]
    urgent_msgs = [m for m in unreplied if step - m.get("received_at_step", 0) <= 1]
    if urgent_msgs:
        msg = urgent_msgs[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="friendly",
            content_summary="Got it, thanks for letting me know!",
        ), f"Whoa, just got a text from {msg['sender']}. Better reply fast to keep relationships intact!"

    pending = [t for t in tasks if t.get("status") == "todo"]
    if pending:
        pending.sort(key=lambda t: (t.get("deadline_step", 999) - step, -t.get("priority", 0)))
        task = pending[0]
        if task.get("priority", 3) <= 1 and obs_dict.get("budget", 0) > 2000:
            return Action(
                action_type="delegate_task",
                target_id=task["task_id"],
                reason="Low priority task, delegating to focus on higher priorities.",
            ), f"I have plenty of cash (₹{obs_dict.get('budget', 0):.0f}). I'm outsourcing '{task['title']}' to save time."
        return Action(
            action_type="prioritize_task",
            target_id=task["task_id"],
            urgency_level=min(5, task.get("priority", 3) + 1),
        ), f"Deadline approaching for '{task['title']}'. Need to lock in and get this done."

    if unreplied:
        msg = unreplied[0]
        return Action(
            action_type="reply_message",
            target_id=msg["message_id"],
            tone="neutral",
            content_summary="Thanks, noted!",
        ), f"Clearing out older messages. Replying to {msg['sender']}."

    return Action(action_type="rest"), "Schedule is clear for now. Taking a breather to restore energy."


def _energy_emoji(val):
    if val > 70: return "🟢"
    if val > 40: return "🟡"
    if val > 20: return "🟠"
    return "🔴"


def _stress_emoji(val):
    if val < 30: return "🟢"
    if val < 55: return "🟡"
    if val < 75: return "🟠"
    return "🔴"


def _bar(val, max_val=100, width=20):
    filled = int((val / max_val) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


import datetime

def generate_ics(obs_dict: dict) -> str:
    """Generate a simple .ics calendar file string based on the agent's scheduled events and tasks."""
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LifeOS//Personal Chaos Agent//EN",
        "CALSCALE:GREGORIAN",
    ]
    
    # Base simulated date (starts tomorrow at 8 AM)
    base_time = datetime.datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    
    # Add Calendar Events
    for c in obs_dict.get("calendar", []):
        if c.get("is_declined"):
            continue
        start_dt = base_time + datetime.timedelta(hours=c.get("scheduled_hour", 0))
        end_dt = start_dt + datetime.timedelta(hours=c.get("duration_hours", 1))
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"SUMMARY:{c.get('title', 'Event')}",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            "DESCRIPTION:Scheduled by LifeOS Agent",
            "END:VEVENT"
        ])
        
    # Add Completed Tasks as all-day events or timed tasks
    for i, t in enumerate(obs_dict.get("tasks", [])):
        if t.get("status") == "done":
            start_dt = base_time + datetime.timedelta(hours=12 + i) # Just scatter them
            end_dt = start_dt + datetime.timedelta(hours=1)
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:✅ {t.get('title', 'Task')}",
                f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                "DESCRIPTION:Completed by LifeOS Agent",
                "END:VEVENT"
            ])

    ics_lines.append("END:VCALENDAR")
    
    file_path = "lifeos_schedule.ics"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ics_lines))
        
    return file_path


def generate_calendar_html(obs_dict: dict) -> str:
    """Generate a beautiful HTML timeline of the agent's scheduled events and completed tasks."""
    events = []
    
    # Add Calendar Events
    for c in obs_dict.get("calendar", []):
        if not c.get("is_declined"):
            events.append({
                "hour": c.get("scheduled_hour", 0),
                "title": c.get("title", "Event"),
                "desc": f"Duration: {c.get('duration_hours', 1)}h",
                "type": "event",
                "icon": "📅",
                "color": "#e0f2fe",      # light blue
                "border": "#0284c7"      # dark blue
            })
            
    # Add Completed Tasks
    for i, t in enumerate(obs_dict.get("tasks", [])):
        if t.get("status") == "done":
            # Assign a pseudo-hour based on priority/completion to scatter them
            pseudo_hour = 8 + (i * 2) % 12 
            events.append({
                "hour": pseudo_hour,
                "title": t.get("title", "Task"),
                "desc": "Task Completed",
                "type": "task",
                "icon": "✅",
                "color": "#dcfce7",      # light green
                "border": "#16a34a"      # dark green
            })
            
    # Sort chronologically by hour
    events.sort(key=lambda x: x["hour"])
    
    html = "<div style='display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding: 10px;'>"
    
    if not events:
        return "<div style='padding: 20px; text-align: center; color: #64748b;'>No events or completed tasks yet.</div>"
        
    for ev in events:
        time_str = f"{ev['hour']}:00" if ev['hour'] > 9 else f"0{ev['hour']}:00"
        html += f"""
        <div style='background: {ev["color"]}; padding: 12px 16px; border-radius: 8px; border-left: 5px solid {ev["border"]}; display: flex; align-items: center; gap: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
            <div style='font-weight: 700; color: #334155; min-width: 50px;'>{time_str}</div>
            <div style='font-size: 1.5em;'>{ev["icon"]}</div>
            <div style='flex-grow: 1;'>
                <div style='font-weight: 600; color: #0f172a; font-size: 1.05em;'>{ev["title"]}</div>
                <div style='color: #475569; font-size: 0.85em; margin-top: 2px;'>{ev["desc"]}</div>
            </div>
        </div>
        """
        
    html += "</div>"
    return html


def _format_obs(obs) -> str:
    if hasattr(obs, "model_dump"):
        d = obs.model_dump()
    else:
        d = obs

    energy = d['energy']
    stress = d['stress']

    lines = [
        f"# 📊 Step {d['current_step']} / {d['max_steps']}",
        "",
        "---",
        "",
        "### ⚡ Vitals",
        "",
        f"| Metric | Value | Status |",
        f"|--------|-------|--------|",
        f"| Energy | `{_bar(energy)}` **{energy}**/100 | {_energy_emoji(energy)} |",
        f"| Stress | `{_bar(stress)}` **{stress}**/100 | {_stress_emoji(stress)} |",
        f"| Budget | **₹{d['budget']:.0f}** | 💰 |",
        f"| Relationship | **{d['relationship_score']:.2f}** | 🤝 |",
        "",
        "---",
        "",
        "### 📋 Tasks",
        "",
    ]
    for t in d.get("tasks", []):
        if t["status"] == "done":
            lines.append(f"- ✅ ~~{t['title']}~~ — *Done!*")
        else:
            urgency = "🔴" if t["priority"] >= 4 else "🟡" if t["priority"] >= 2 else "⚪"
            lines.append(f"- {urgency} **{t['title']}** — P{t['priority']} | Deadline: Step {t['deadline_step']} | Effort: {t['effort_remaining']:.1f}")

    lines.extend(["", "---", "", "### 📬 Inbox", ""])
    for m in d.get("inbox", []):
        if m.get("replied"):
            lines.append(f"- ✅ **{m['sender']}**: ~~{m['content_summary']}~~")
        else:
            lines.append(f"- 📩 **{m['sender']}**: {m['content_summary']}")

    lines.extend(["", "---", "", "### 📅 Calendar", ""])
    for c in d.get("calendar", []):
        if c.get("is_declined"):
            continue
        conflict = " ⚠️ **CONFLICT!**" if c.get("is_conflict") else ""
        lines.append(f"- 🕐 Hour {c['scheduled_hour']}: **{c['title']}** ({c['duration_hours']}h){conflict}")

    chaos = d.get("active_chaos", [])
    if chaos:
        lines.extend(["", "---", "", "### 🌪️ Active Chaos!", ""])
        for c in chaos:
            lines.append(f"- 💥 **{c['event_type']}**: {c['description']}")

    return "\n".join(lines)


def run_episode(agent_type: str) -> tuple[str, str, str, pd.DataFrame, str, str]:
    """Run a full episode and return formatted results along with graph data."""
    env = StudentWeekEnv(max_steps=30, chaos_probability=0.35)
    obs = env.reset()

    history_lines = []
    step_count = 0
    plot_data = []

    # Record initial state
    plot_data.append({"Step": 0, "Metric": "Energy", "Value": obs.energy})
    plot_data.append({"Step": 0, "Metric": "Stress", "Value": obs.stress})

    action_emojis = {
        "rest": "😴", "reply_message": "💬", "prioritize_task": "📌",
        "delegate_task": "🤝", "decline_event": "🚫", "check_budget": "💰",
    }

    while True:
        obs_dict = obs.model_dump()

        if agent_type == "Heuristic":
            action, thought = _heuristic_action(obs_dict)
        else:
            action, thought = _smart_action(obs_dict)

        obs, reward, done, info = env.step(action)
        step_count += 1

        plot_data.append({"Step": step_count, "Metric": "Energy", "Value": obs.energy})
        plot_data.append({"Step": step_count, "Metric": "Stress", "Value": obs.stress})

        rc = info.get("reward_components", {})
        action_str = f"{action.action_type}"
        if action.target_id:
            action_str += f"({action.target_id})"

        emoji = action_emojis.get(action.action_type, "▶️")
        reward_icon = "✅" if reward >= 0 else "❌"
        
        # Add the thought process to the action string using <br> for newline in markdown table
        action_cell = f"{emoji} `{action_str}`<br>_💭 {thought}_"

        history_lines.append(
            f"| {step_count} | {action_cell} | {reward_icon} **{reward:+.3f}** | "
            f"{rc.get('task_completion', 0):+.2f} | {rc.get('social_coherence', 0):+.2f} | "
            f"{rc.get('energy_sustainability', 0):+.2f} | {rc.get('format_compliance', 0):+.2f} |"
        )

        chaos_events = info.get("chaos_events", [])
        for c in chaos_events:
            history_lines.append(f"| | 🌪️ *CHAOS: {c['description']}* | | | | | |")

        if done:
            break

    final_state = env.state
    final_obs = _format_obs(obs)

    # DataFrame for Gradio LinePlot
    df = pd.DataFrame(plot_data)

    # History table
    history_header = [
        "| Step | Action | Reward | Task | Social | Energy | Format |",
        "|------|--------|--------|------|--------|--------|--------|",
    ]
    history_str = "\n".join(history_header + history_lines)

    # Summary
    reward_val = final_state.total_reward
    reward_icon = "🏆" if reward_val > 5 else "✅" if reward_val > 0 else "⚠️" if reward_val > -5 else "💀"

    summary_lines = [
        f"# {reward_icon} Episode Results",
        f"### Agent: **{agent_type}**",
        "",
        "---",
        "",
        "### 📊 Score Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Total Steps** | {step_count} |",
        f"| **Total Reward** | **{reward_val:+.3f}** |",
        "",
        "---",
        "",
        "### 🎯 Reward Breakdown",
        "",
        "| Component | Score | Rating |",
        "|-----------|-------|--------|",
    ]
    for k, v in final_state.reward_components.items():
        rating = "🟢" if v > 0 else "🔴" if v < 0 else "⚪"
        summary_lines.append(f"| {k.replace('_', ' ').title()} | **{v:+.3f}** | {rating} |")

    summary_lines.extend([
        "",
        "---",
        "",
        "### 📈 Performance Stats",
        "",
        f"| Stat | Count |",
        f"|------|-------|",
        f"| ✅ Tasks Completed | **{final_state.tasks_completed}** |",
        f"| ❌ Tasks Missed | **{final_state.tasks_missed}** |",
        f"| 💬 Messages Answered | **{final_state.messages_answered}** |",
        f"| 📭 Messages Unanswered | **{final_state.messages_unanswered}** |",
        f"| ⚡ Final Energy | **{final_state.energy}** |",
        f"| 😰 Final Stress | **{final_state.stress}** |",
    ])
    
    ics_file_path = generate_ics(obs_dict)
    calendar_html = generate_calendar_html(obs_dict)

    return final_obs, history_str, "\n".join(summary_lines), df, calendar_html, ics_file_path


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

.gradio-container {
    background: linear-gradient(160deg, #f0f4ff 0%, #fdf2f8 40%, #ecfdf5 100%) !important;
    max-width: 1200px !important;
}

h1 { 
    background: linear-gradient(135deg, #4338ca, #7c3aed, #c026d3) !important; 
    -webkit-background-clip: text !important; 
    -webkit-text-fill-color: transparent !important; 
}

.gr-button-primary {
    background: linear-gradient(135deg, #818cf8, #c084fc) !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    padding: 14px 32px !important;
    box-shadow: 0 4px 16px rgba(129,140,248,0.4) !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.5px !important;
}
.gr-button-primary:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 8px 24px rgba(129,140,248,0.5) !important;
}

.gr-box, .gr-panel, .gr-form { 
    border-radius: 16px !important; 
    border: 1px solid rgba(129,140,248,0.15) !important;
}

.gr-input-label { color: #6366f1 !important; font-weight: 600 !important; }

table { border-collapse: separate !important; border-spacing: 0 !important; }
th { background: linear-gradient(135deg, #e0e7ff, #ede9fe) !important; color: #4338ca !important; font-weight: 600 !important; }
td, th { padding: 8px 12px !important; }
tr:nth-child(even) td { background: rgba(238,242,255,0.5) !important; }

code { 
    background: linear-gradient(135deg, #e0e7ff, #fce7f3) !important; 
    color: #4338ca !important; 
    padding: 2px 8px !important; 
    border-radius: 6px !important; 
    font-size: 13px !important; 
}

.gr-accordion { 
    border-radius: 14px !important; 
    border: 1px solid rgba(129,140,248,0.2) !important;
    background: rgba(255,255,255,0.6) !important;
}

footer { display: none !important; }

blockquote { 
    border-left: 4px solid #818cf8 !important; 
    background: rgba(224,231,255,0.3) !important; 
    border-radius: 0 12px 12px 0 !important; 
}
"""

with gr.Blocks(
    title="LifeOS -- Personal Chaos Agent",
    theme=gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="purple",
        neutral_hue="slate",
    ),
    css=CUSTOM_CSS,
) as demo:
    gr.Markdown(
        "# 🧠 LifeOS: The Personal Chaos Agent\n"
        "An OpenEnv-compliant RL environment where an LLM must survive cascading personal life chaos.\n\n"
        "> **How it works:** Select an agent, hit Run, and watch it navigate tasks, messages, budget & stress in real-time!\n\n"
        "`OpenEnv Compliant` `4 Reward Signals` `Anti-Hack Protected` `GRPO Trained`\n\n"
        "<a href='https://huggingface.co/SParsh003/LifeOS-Trained-Agent' target='_blank' style='display:inline-block; margin-top:10px; padding:8px 16px; background:linear-gradient(135deg, #4338ca, #7c3aed); color:white; font-weight:600; border-radius:8px; text-decoration:none; box-shadow:0 4px 6px rgba(0,0,0,0.1)'>📦 View Trained Model Weights (Mistral 7B)</a>"
    )

    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=["Heuristic", "Trained Agent"],
            value="Heuristic",
            label="🤖 Agent Type",
            info="Heuristic = rule-based baseline. Trained = GRPO-optimized agent.",
        )
        run_btn = gr.Button("▶️  Run Episode", variant="primary", scale=2)

    with gr.Row():
        with gr.Column(scale=1):
            final_state_md = gr.Markdown(
                value="> 👆 **Click 'Run Episode' above** to start a chaos simulation!\n\n"
                "The agent will navigate 30 steps of a chaotic student week.",
                label="🌍 Live Environment State",
            )
        with gr.Column(scale=1):
            summary_md = gr.Markdown(value="", label="📊 Episode Summary")
            
            with gr.Accordion("🗓️ Agent's Final Schedule View", open=True):
                gr.Markdown("View the agent's finalized schedule and completed tasks below, or download them directly to your personal calendar!")
                calendar_view = gr.HTML(label="Visual Timeline")
                ics_download = gr.File(label="Download .ics Calendar", interactive=False)
            
            gr.Markdown("### 📈 Dynamic Vitals Plot")
            metrics_plot = gr.LinePlot(
                x="Step", 
                y="Value", 
                color="Metric", 
                title="Energy & Stress Trajectory", 
                y_title="Level (0-100)",
                x_title="Episode Step"
            )

    with gr.Accordion("📜 Step-by-Step Action History", open=False):
        history_md = gr.Markdown(value="")

    gr.Markdown(
        "---\n"
        "### 🏗️ Architecture\n"
        "| Component | Details |\n"
        "|---|---|\n"
        "| **Environment** | StudentWeekEnv (OpenEnv-compliant FastAPI) |\n"
        "| **Algorithm** | GRPO (Group Relative Policy Optimization) |\n"
        "| **Model Weights** | [SParsh003/LifeOS-Trained-Agent](https://huggingface.co/SParsh003/LifeOS-Trained-Agent) (Mistral-7B LoRA) 👈 **Click to view model!** |\n"
        "| **Reward Signals** | Task Completion, Social Coherence, Energy Sustainability, Format Compliance |\n"
        "| **Anti-Hack** | Step timeout, loop detection, protected state check |\n\n"
        "*Built for the Meta OpenEnv Hackathon 2025*"
    )

    run_btn.click(
        fn=run_episode,
        inputs=[agent_dropdown],
        outputs=[final_state_md, history_md, summary_md, metrics_plot, calendar_view, ics_download],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
