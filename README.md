---
title: LifeOS - Personal Chaos Agent
emoji: 🧠
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 6.13.0
app_file: web_app.py
pinned: false
tags:
- openenv
- rl
- llm-training
- personalized-tasks
- reinforcement-learning
- life-simulation
license: mit
---

# LifeOS — Teaching LLMs to Handle Real-Life Chaos

> An OpenEnv-compliant RL environment for training LLMs to manage cascading personal life conflicts.

## The Problem

LLMs excel at structured reasoning tasks — coding, math, Q&A — but fail spectacularly when confronted with the messy, cascading conflicts of real personal life. Consider a student who must simultaneously handle a moved-up assignment deadline, an angry friend's message, a surprise expense, and declining energy — all while deciding *which thing to sacrifice*. No existing RL environment models this uniquely human challenge where every decision has downstream social, temporal, and energy consequences.

## The Environment

LifeOS simulates a chaotic student week as an RL training environment. The agent receives a rich observation and must choose structured actions each step.

```
                    ┌─────────────────────────────────────────┐
                    │            OBSERVATION                  │
                    │  📅 Calendar (conflicts, deadlines)     │
                    │  📬 Inbox (pending messages)            │
                    │  ⚡ Energy: 72/100  😰 Stress: 35/100  │
                    │  💰 Budget: ₹3500   🤝 Relationship: 0.65│
                    │  🌪️ Chaos: "Assignment moved up 2 days!"│
                    └──────────────┬──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │           LLM AGENT              │
                    │  Chooses structured action:       │
                    │  reply_message | prioritize_task  │
                    │  reschedule_event | delegate_task │
                    │  decline_event | rest             │
                    └──────────────┬───────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────────────┐
                    │       4 INDEPENDENT REWARD SIGNALS       │
                    │  ✅ Task Completion    ✅ Social Coherence│
                    │  ✅ Energy Sustain.    ✅ Format Compliance│
                    │  🛡️ Anti-hack: timeout, loop detection   │
                    └──────────────────────────────────────────┘
```

An episode ends after 30 time steps or on burnout (energy = 0).

## Reward Design

| Reward Function | What It Measures | Range |
|---|---|---|
| **Task Completion** | Deadlines met/missed, unnecessary delegation | -1.0 to +1.0 per task |
| **Social Coherence** | Message reply timeliness, reschedule reasons | -0.8 to +0.5 per msg |
| **Energy Sustainability** | Energy above 40, proactive rest, burnout | -1.5 to +0.4 per step |
| **Format Compliance** | Valid action schema, anti-hack detection | -1.0 to +0.1 per step |

Anti-hacking safeguards: 30s step timeout (-2.0), action loop detection (-0.5), protected state access (-1.0), locked chaos queue.

## Results

![Reward curves showing composite and per-function reward improvement over 50 training episodes](lifeos/outputs/reward_curves.png)

> Composite reward improved from **-2.8** (heuristic baseline) to **+1.4** (trained agent) over 50 episodes.

### Before/After: Same Chaos Scenario

| | Heuristic Agent | Trained Agent |
|---|---|---|
| **Step 1** (deadline in 8 steps) | `rest()` — wasted a step | `prioritize_task(t2, urgency=5)` — tackles closest deadline |
| **Step 4** (angry message) | Ignores message | `reply_message(msg4, tone=apologetic)` — replies within 1 step |
| **Step 8** (energy=25) | `prioritize_task` — ignores energy | `rest()` — proactive recovery before burnout |
| **Final** | 3 tasks done, 4 missed, burnout | 6 tasks done, 1 missed, energy=38 |

## Why It Matters

Personal task management under cascading constraints is a **capability gap** in current LLMs. LifeOS provides the first structured RL environment targeting this — useful for:
- **Personal AI assistants** that need to triage competing demands
- **RL research** on multi-signal reward shaping with social consequences
- **Evaluation benchmarks** for LLM planning under real-world uncertainty

## OpenEnv Compliance

LifeOS is fully compliant with the [OpenEnv](https://github.com/meta-pytorch/OpenEnv) standard:
- ✅ `openenv.yaml` manifest with action/observation/reward schema
- ✅ Gym-style API: `reset()`, `step(action)`, `state` property
- ✅ FastAPI server (`lifeos/envs/server.py`) — runs on port 8200
- ✅ Typed HTTP client (`lifeos/envs/client.py`) — no server imports
- ✅ Dockerfile for HuggingFace Spaces deployment

## Quick Start

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Run the CLI (existing terminal-first interface)
```bash
python -m lifeos.cli --setup
python -m lifeos.cli --list-scenarios
python -m lifeos.cli --scenario student_week --agent heuristic
python -m lifeos.cli --tui
```

### Run the OpenEnv Server
```bash
uvicorn lifeos.envs.server:app --host 0.0.0.0 --port 8200
```

### Run GRPO Training (local simulation)
```bash
python -m lifeos.training.train_grpo --episodes 50
```

### Run the Gradio Space Demo
```bash
python spaces/app.py
```

### Run the API
```bash
uvicorn lifeos.api.main:app --reload --port 8000
```

## Project Structure

```
lifeos/
├── envs/                    # OpenEnv-compliant environment
│   ├── student_week_openenv.py  # Environment class
│   ├── server.py            # FastAPI server
│   └── client.py            # HTTP client
├── rewards/                 # Independent reward functions
│   ├── task_completion_reward.py
│   ├── social_coherence_reward.py
│   ├── energy_sustainability_reward.py
│   └── format_compliance_reward.py
├── training/
│   ├── train_grpo.py        # GRPO training script
│   └── train_trl_unsloth.py # TRL + Unsloth (Colab)
├── cli/                     # Terminal-first interface
├── api/                     # Existing REST API
├── scenarios/               # 12 JSON scenario files
└── agents/                  # Heuristic & PPO agents
spaces/
├── app.py                   # Gradio demo for judges
└── README.md                # HF Space card
openenv.yaml                 # OpenEnv manifest
Dockerfile.openenv           # HF Spaces deployment
```

## Links

- 🤗 HuggingFace Space: [LifeOS — Personal Chaos Agent](https://huggingface.co/spaces/SParsh003/LifeOS-Personal-Chaos-Agen)
- 📝 Mini-blog: [docs/hf_blog.md](docs/hf_blog.md)
- 🎥 Demo: Try the interactive demo on the HuggingFace Space above

---

**Theme:** Personalized Tasks (#3.2)  
**Stack:** Python, FastAPI, TRL, Unsloth, Gradio, OpenEnv  
**License:** MIT