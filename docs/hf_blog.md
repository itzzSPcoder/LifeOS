# LifeOS: Training an LLM to Survive a Chaotic Week

## The Gap — Why Personal Task Handling Is Hard for LLMs

LLMs are surprisingly good at structured reasoning: solving math problems, writing code, answering questions from documents. But ask one to manage a chaotic week — juggling a moved-up deadline, an angry friend's text, a surprise expense, and declining energy — and it falls apart. The reason is simple: **personal life decisions have cascading social and temporal consequences that current models can't reason about in a structured RL setting.**

There's no existing RL environment that models this uniquely human challenge. Code execution environments test programming. Game environments test strategy. But nothing tests the messy, multi-dimensional trade-offs of real personal life under pressure. LifeOS fills this gap.

## The Environment — Chaos Events, Action Space, Episode Structure

LifeOS simulates a **student navigating a chaotic week** as an OpenEnv-compliant RL environment. Each episode runs for 30 time steps. The agent observes its calendar (with conflicts), inbox (with pending messages), task list (with approaching deadlines), energy level, stress level, budget, and a queue of random "chaos events" that inject surprises throughout the episode.

The action space includes six structured actions: `reply_message`, `reschedule_event`, `prioritize_task`, `delegate_task`, `decline_event`, and `rest`. Each action has typed parameters (target IDs, tones, urgency levels, reasons), so the LLM must generate well-formed structured outputs — not just pick from a menu.

Chaos events fire randomly: an assignment deadline moves up, a roommate gets upset, a freelance payment arrives, Wi-Fi goes down. The agent can't see the chaos queue directly — it can only react when events are revealed. An episode ends after 30 steps or immediately if energy hits zero (burnout).

## The Reward Design — 4 Independent Signals, Anti-Hack Measures

Instead of a single composite reward (which models can easily hack), LifeOS uses **four independent reward functions**, each measuring a different dimension:

| Signal | What It Rewards | What It Penalizes |
|---|---|---|
| **Task Completion** | Meeting deadlines (+1.0 each) | Missed deadlines (-1.0), unnecessary delegation (-0.5) |
| **Social Coherence** | Timely replies within 1 step (+0.5) | Unanswered messages at end (-0.8 each) |
| **Energy Sustainability** | Keeping energy above 40 (+0.2/step) | Burnout, energy=0 (-1.5) |
| **Format Compliance** | Valid action schema (+0.1) | Malformed actions (-0.5), hack attempts (-1.0) |

Anti-hacking safeguards include: a 30-second step timeout (-2.0 penalty), action loop detection (repeating the same action 3+ times costs -0.5), locked chaos queue (agent can't read or modify it), and detection of attempts to reference protected internal state.

All four reward components are **logged separately per episode**, making reward hacking detectable during monitoring.

## Training Results — Reward Curve + Qualitative Example

We trained using GRPO (Group Relative Policy Optimization) via HuggingFace TRL + Unsloth for efficient 4-bit LoRA training. Over 50 episodes, the trained agent learned to prioritize urgent tasks, reply to messages promptly, and rest proactively before burnout.

**Same scenario, different agents:**
- **Heuristic agent** at Step 1 with a deadline 8 steps away: calls `rest()`, wasting a critical step.
- **Trained agent** at Step 1: calls `prioritize_task(t2, urgency=5)`, tackling the closest deadline immediately.
- **Heuristic** at Step 8 with energy=25: continues `prioritize_task`, leading to burnout.
- **Trained** at Step 8: calls `rest()`, recovering energy before it's too late.

Result: trained agent completes 6/8 tasks vs 3/8 for heuristic, avoids burnout, and maintains higher relationship scores.

## What's Next

LifeOS is designed to grow. Immediate next steps include:
- **Multi-persona support**: Different character profiles (working parent, startup founder, freelancer) with different constraint trade-offs
- **Long-horizon episodes**: Simulating full weeks or months with compounding consequences
- **LLM-as-judge**: Using a separate LLM to evaluate the quality of reply messages and delegation reasons, adding a fifth reward signal
- **Real calendar integration**: Connecting to Google Calendar / Notion APIs for personalized scenario generation

The ultimate vision: an RL-trained personal AI that doesn't just *schedule* your life, but *navigates* it.
