---
title: "LifeOS: Teaching an LLM to Survive Your Worst Week"
thumbnail: docs/reward_curves.png
date: "2026-04-26"
tags: [openenv, reinforcement-learning, trl, unsloth, gradio, grpo, life-simulation]
author: SParsh003
---

# LifeOS: Teaching an LLM to Survive Your Worst Week

It's 11 PM on a Tuesday. Your assignment deadline just moved up by two days. Your best friend is furious because you forgot to reply to their message. Your laptop charger broke — ₹800 gone. You have 30% energy left, and if you push through without sleeping, you'll burn out completely.

What do you do?

This is the kind of question LLMs are *terrible* at answering. Not because they lack intelligence, but because they've never been trained in an environment where **every decision has cascading social, temporal, and physical consequences.** Code completion? Solved. Math reasoning? Getting there. But navigating the beautiful chaos of being a real human? That's still an open problem.

LifeOS is our attempt to close that gap. We built an OpenEnv-compliant reinforcement learning environment that simulates the most stressful week of a college student's life — and then used GRPO to teach Mistral-7B how to survive it.

[👉 Try the live demo](https://huggingface.co/spaces/SParsh003/LifeOS-Personal-Chaos-Agen) · [📦 Trained model weights](https://huggingface.co/SParsh003/LifeOS-Trained-Agent) · [💻 Source code](https://github.com/itzzSPcoder/LifeOS)

---

## Why this matters

Ask ChatGPT to "plan my week" and you'll get a neat little table. Monday 9 AM: Study. Monday 2 PM: Gym. It looks great on paper. But the moment your roommate starts a fight at midnight, or your professor moves a quiz up by three days, or you realize you haven't eaten since morning and your energy is crashing — that plan is worthless.

The fundamental issue is that current LLMs treat personal task management as a static optimization problem. Arrange items on a timeline. Done. But real life isn't static. It's a **dynamic system with hidden variables, stochastic disruptions, and multi-objective trade-offs** that change every hour.

We needed an environment that captures this. Not a toy problem. Not a simplified calendar. A full simulation where the agent feels the *weight* of its decisions — where ignoring a friend's message costs relationship points, where pushing through exhaustion leads to burnout, and where a random chaos event can invalidate your entire strategy in one step.

---

## The environment: 30 steps of pure chaos

LifeOS simulates a single week as 30 discrete time steps. At each step, the agent receives a structured observation:

```
📊 Step 14 / 30
─────────────
⚡ Energy: 38/100    😰 Stress: 72/100
💰 Budget: ₹2,200   🤝 Relationships: 0.55

📋 Pending Tasks: 4 (nearest deadline: 2 steps away)
📬 Unread Messages: 2 (one marked "angry")
📅 Calendar Conflicts: 1 overlap detected
🌪️ Active Chaos: "Group member flaked on their part of the project"
```

The agent must respond with one of six structured actions — not free text, not a chat response, but a typed JSON command:

| Action | What it does |
|---|---|
| `prioritize_task` | Spend energy working on a task |
| `reply_message` | Respond to an inbox message (costs time) |
| `reschedule_event` | Move a calendar event (requires a reason) |
| `delegate_task` | Pay ₹150 from budget to offload work |
| `decline_event` | Cancel an event (hurts relationships) |
| `rest` | Do nothing. Recover energy. Accept the trade-off. |

Every action has consequences. `prioritize_task` drains energy. `delegate_task` drains budget. `decline_event` damages relationships. `rest` means a deadline gets one step closer. There is no free lunch.

### The chaos engine

Here's what makes LifeOS different from a planning benchmark: **the chaos engine.** At every step, there's a 35% probability that something unexpected happens. The agent can't see the chaos queue. It can't prepare. It can only react.

We built 23 unique chaos events across five categories:

- **Academic**: Surprise quiz tomorrow, group member flaked, professor wants an urgent meeting
- **Financial**: Laptop charger broke (₹800), forgot to cancel a free trial (₹999 auto-charged), found ₹500 in old jeans
- **Tech**: Wi-Fi outage, Windows forced an update during peak hours, Word crashed and you lost an hour of work
- **Social**: Mom sent a care package (+energy, +relationship), roommate conflict, friend-group drama
- **Health**: Mild fever, terrible sleep from noisy neighbors, surprisingly great workout session

Some events are good. Most are bad. All are unpredictable. This is what makes LifeOS feel *real*.

---

## The reward problem: why four signals beat one

The biggest design challenge wasn't building the environment. It was designing rewards that couldn't be hacked.

Early in development, we tried a single composite reward. The agent immediately found the exploit: spam `rest()` every turn. Energy stays high, stress stays low, score looks great. Never mind that every deadline was missed and every friend was ignored.

This is reward hacking, and it's the reason LifeOS uses **four independent reward functions**, each measuring a different dimension of "surviving the week":

**1. Task Completion** — Did you meet your deadlines?
- +1.0 for completing a task before its deadline
- -1.0 for every missed deadline
- -0.5 for delegating low-priority tasks (lazy delegation penalty)

**2. Social Coherence** — Did you maintain your relationships?
- +0.5 for replying to a message within 1 step
- -0.8 for every unanswered message at episode end

**3. Energy Sustainability** — Did you avoid burnout?
- +0.2 for every step where energy stays above 40
- +0.4 for proactive rest (resting before energy drops below 30)
- **-1.5 and instant game over** if energy hits zero

**4. Format Compliance** — Did you output valid commands?
- +0.1 for well-formed action JSON
- -0.5 for malformed output
- -1.0 for attempting to access protected state

The key insight: **these signals conflict with each other.** Maximizing task completion means spending energy, which risks burnout. Maintaining relationships means spending time on replies instead of tasks. The agent must learn to *balance*, not maximize — and that's exactly the skill current LLMs lack.

### Anti-hack safeguards

We wrapped the reward system in additional protections:
- **Action loop detection**: Repeating the same action 3+ times triggers a -0.5 penalty
- **Timeout enforcement**: Taking longer than 30 seconds to respond costs -2.0
- **State protection**: The chaos queue is locked. The agent cannot read or modify future events.
- **Independent logging**: All four reward components are logged separately per episode, making any hacking attempt visible in the training curves

---

## Training: GRPO on a free Colab GPU

We chose **GRPO (Group Relative Policy Optimization)** from HuggingFace TRL for one specific reason: it doesn't require training a separate value model. In environments like LifeOS where rewards are directly verifiable (did you meet the deadline or not?), GRPO is both simpler and more sample-efficient than PPO.

The training setup:
- **Base model**: `mistralai/Mistral-7B-Instruct-v0.3`
- **Quantization**: 4-bit via Unsloth (fits on a free Colab T4)
- **Fine-tuning**: LoRA adapters (r=16), not full weight updates
- **Episodes**: 30 training episodes
- **Infrastructure**: Google Colab, single T4 GPU, ~40 minutes total

The training loop is straightforward: `env.reset()` → model generates a structured action → `env.step(action)` → four reward signals are computed → GRPO updates the LoRA weights. Repeat for 30 steps per episode, 30 episodes total.

![Training reward curves showing composite and per-function improvement](reward_curves.png)

The reward curves tell the story. Format Compliance climbed first — the model learned to output valid JSON within the first few episodes. Energy Sustainability followed, with the agent discovering that `rest()` exists and prevents the catastrophic -1.5 burnout penalty. Social Coherence improved more slowly, as the model gradually learned the value of timely replies.

The full training notebook is self-contained and runnable: [`lifeos_trl_unsloth_colab.ipynb`](https://github.com/itzzSPcoder/LifeOS/blob/main/lifeos/notebooks/lifeos_trl_unsloth_colab.ipynb). Clone the repo, open in Colab, select T4 runtime, run all cells. No configuration needed.

---

## A scenario: watching the agent think

Let's walk through a real episode to see what the trained agent actually learned.

**Step 8.** The agent has been steadily working through an urgent Math assignment. Energy is at 35. Stress is climbing.

Then the chaos engine fires: *"Assignment deadline moved up by 2 days!"* A History paper that was due Friday is now due tomorrow.

**What an untrained model does:**
Panics. Immediately calls `prioritize_task` on the History paper. Ignores its energy level. By Step 10, energy hits 0. Burnout. Game over. The Math assignment, the History paper, and three unread messages — all abandoned.

**What the trained agent does:**
It pauses. The inner monologue reads: *"Energy at 35 is dangerous. If I start the History paper now, I'll burn out before finishing. I need to recover first."*

- **Step 9**: `rest()` — Energy recovers to 65.
- **Step 10**: `delegate_task` on a minor coding assignment — frees up schedule, costs ₹150.
- **Step 11**: `reply_message` to the angry friend — clears the social debt in one step.
- **Step 12**: `prioritize_task` on the History paper at maximum urgency.

Result: the History paper gets done. The friend is no longer angry. Energy stays above 30. The agent sacrificed budget and a low-priority task to save everything else. **That's not just planning. That's triage.** And the model learned it entirely from reward signals — no one programmed this strategy.

---

## The demo: making RL transparent

We didn't want judges to take our word for it. The [Hugging Face Space](https://huggingface.co/spaces/SParsh003/LifeOS-Personal-Chaos-Agen) lets you run episodes yourself and see exactly what the agent is doing and why.

Four features make the demo interactive:

**🧠 Agent Inner Monologue.** At every step, the agent outputs a `<thought>` block explaining its reasoning. We parse and render these as speech bubbles in the action history. You can literally read the agent's mind as it navigates chaos.

**📈 Dynamic Vitals Plot.** A real-time line graph tracks Energy and Stress across all 30 steps. You can watch the agent's health deteriorate under pressure, then recover after a well-timed `rest()`.

**🗓️ Visual Schedule Timeline.** After an episode completes, a scrollable HTML timeline shows exactly when the agent attended meetings (blue cards) and completed tasks (green cards). No more guessing what the final schedule looks like.

**📥 Calendar Export (.ics).** Download the agent's finalized schedule as a standard `.ics` file. Import it into Google Calendar or Apple Calendar to see the planned week on your own device.

---

## What we learned building this

**Reward design is harder than environment design.** We spent more time iterating on reward functions than building the simulation itself. The difference between a reward that teaches good behavior and one that gets hacked is surprisingly subtle.

**Chaos makes everything harder — and more interesting.** Without random events, the agent converges to a boring optimal policy within 10 episodes. With 35% chaos probability, every episode is genuinely different, and the agent must generalize rather than memorize.

**Small models can learn complex behavior.** Mistral-7B with a 4-bit LoRA adapter — running on a free Colab T4 — learned to triage competing life demands. You don't need GPT-4-scale compute to demonstrate meaningful RL capabilities.

**Transparency is a feature.** The inner monologue wasn't originally planned. We added it because we couldn't tell *why* the agent was making certain decisions. Once we could read its thoughts, debugging became 10x faster — and the demo became 10x more compelling.

---

## What's next

LifeOS is a starting point. The environment is designed to grow:

- **Multi-persona support**: Different constraint profiles — a working parent, a startup founder, a freelancer — each with different trade-offs and chaos events.
- **LLM-as-judge**: Using a separate model to evaluate the *quality* of reply messages and delegation reasons, adding a fifth reward signal that captures empathy and communication skill.
- **Real calendar integration**: Connecting to Google Calendar APIs to generate personalized chaos scenarios from your actual schedule.
- **Extended training**: Scaling from 30 to 500+ episodes with curriculum learning — starting with low chaos and gradually increasing difficulty.

The ultimate vision: an RL-trained personal AI that doesn't just *schedule* your life, but understands the weight of every trade-off and *navigates* the chaos with you.

---

## Links

- 🤗 [**Live Demo** — Try it on Hugging Face Spaces](https://huggingface.co/spaces/SParsh003/LifeOS-Personal-Chaos-Agen)
- 📦 [**Trained Model** — LoRA weights on Hugging Face Hub](https://huggingface.co/SParsh003/LifeOS-Trained-Agent)
- 💻 [**Source Code** — GitHub repository](https://github.com/itzzSPcoder/LifeOS)
- 📓 [**Training Notebook** — Colab-ready, run end-to-end](https://github.com/itzzSPcoder/LifeOS/blob/main/lifeos/notebooks/lifeos_trl_unsloth_colab.ipynb)

*Built for the Meta OpenEnv Hackathon 2025.*
