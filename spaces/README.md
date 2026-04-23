---
title: "LifeOS - Personal Chaos Agent"
emoji: 🧠
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: "4.30.0"
app_file: app.py
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

# LifeOS: The Personal Chaos Agent 🧠

An RL environment where an LLM must handle cascading personal life conflicts in real time.

## What is this?

LifeOS is an OpenEnv-compliant reinforcement learning environment that simulates a chaotic student week. The agent must navigate:

- 📅 **Calendar conflicts** (overlapping meetings, social events)
- 📬 **Inbox pressure** (messages requiring timely replies)
- ⚡ **Energy management** (burnout = game over)
- 💰 **Budget constraints** (unexpected expenses, delegation costs)
- 🌪️ **Chaos events** (surprise deadlines, Wi-Fi outages, roommate conflicts)

## Reward Design

Four independent reward signals prevent reward hacking:

| Signal | What it measures |
|--------|-----------------|
| Task Completion | Deadlines met vs missed |
| Social Coherence | Message reply timeliness |
| Energy Sustainability | Avoiding burnout |
| Format Compliance | Valid action schema |

## Try it!

Click **Run Episode** to watch an agent navigate a chaos scenario.
Toggle between **Heuristic** and **Trained Agent** to compare.
