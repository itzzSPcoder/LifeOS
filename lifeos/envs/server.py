"""
LifeOS OpenEnv Server — FastAPI wrapper for the StudentWeekEnv.

Exposes the environment via HTTP endpoints for the OpenEnv standard.
This is separate from the existing lifeos/api/main.py and runs alongside it.

Run:  uvicorn lifeos.envs.server:app --host 0.0.0.0 --port 8200
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from lifeos.envs.student_week_openenv import (
    Action,
    Observation,
    State,
    StudentWeekEnv,
)

app = FastAPI(
    title="LifeOS OpenEnv Server",
    description="OpenEnv-compliant RL environment: The Personal Chaos Agent",
    version="1.0.0",
)

# ── Active environment instances ──
_ENVS: dict[str, StudentWeekEnv] = {}


class CreateEnvRequest(BaseModel):
    scenario_name: str = "student_week"
    max_steps: int = 30
    chaos_probability: float = 0.20


class ResetResponse(BaseModel):
    episode_id: str
    observation: Observation


class StepRequest(BaseModel):
    episode_id: str
    action: Action


class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class StateResponse(BaseModel):
    state: State


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "lifeos-openenv"}


@app.post("/env/create")
def create_env(req: CreateEnvRequest) -> dict[str, str]:
    """Create a new environment instance."""
    env = StudentWeekEnv(
        scenario_name=req.scenario_name,
        max_steps=req.max_steps,
        chaos_probability=req.chaos_probability,
    )
    obs = env.reset()
    ep_id = env.state.episode_id
    _ENVS[ep_id] = env
    return {"episode_id": ep_id, "status": "created"}


@app.post("/env/reset")
def env_reset(episode_id: str = "") -> ResetResponse:
    """Reset an existing environment or create a new one."""
    if episode_id and episode_id in _ENVS:
        env = _ENVS[episode_id]
    else:
        env = StudentWeekEnv()
        _ENVS["__default__"] = env

    obs = env.reset()
    ep_id = env.state.episode_id
    _ENVS[ep_id] = env
    return ResetResponse(episode_id=ep_id, observation=obs)


@app.post("/env/step")
def env_step(req: StepRequest) -> StepResponse:
    """Execute one step in the environment."""
    env = _ENVS.get(req.episode_id)
    if not env:
        raise HTTPException(status_code=404, detail=f"Episode {req.episode_id} not found")

    obs, reward, done, info = env.step(req.action)
    return StepResponse(observation=obs, reward=reward, done=done, info=info)


@app.get("/env/state/{episode_id}")
def env_state(episode_id: str) -> StateResponse:
    """Get the current state of an episode."""
    env = _ENVS.get(episode_id)
    if not env:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")
    return StateResponse(state=env.state)


@app.get("/env/reward_log/{episode_id}")
def env_reward_log(episode_id: str) -> dict[str, Any]:
    """Get the per-step reward log for monitoring/debugging."""
    env = _ENVS.get(episode_id)
    if not env:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")
    return {"episode_id": episode_id, "reward_log": env.reward_log}


@app.delete("/env/{episode_id}")
def env_close(episode_id: str) -> dict[str, str]:
    """Close and clean up an environment instance."""
    if episode_id in _ENVS:
        del _ENVS[episode_id]
        return {"status": "closed", "episode_id": episode_id}
    raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")
