from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from lifeos.db import repository
from lifeos.env.lifeos_env import LifeOSEnv


app = FastAPI(title="LifeOS API", version="1.0.0")
ACTIVE_ENVS: dict[int, LifeOSEnv] = {}


class StartEpisodeRequest(BaseModel):
    scenario_id: int | None = None
    scenario_name: str | None = None
    agent_type: str = Field(default="heuristic")


class StepRequest(BaseModel):
    action_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


@app.on_event("startup")
def startup() -> None:
    repository.init_db()
    repository.seed_scenarios()


@app.get("/scenarios")
def get_scenarios() -> list[dict[str, Any]]:
    scenarios = repository.get_scenarios()
    return [{"id": s.id, "name": s.name, "display_name": s.display_name} for s in scenarios]


@app.post("/episodes/start")
def start_episode(req: StartEpisodeRequest) -> dict[str, Any]:
    scenario = None
    if req.scenario_id is not None:
        scenario = repository.get_scenario_by_id(req.scenario_id)
    elif req.scenario_name is not None:
        scenario = repository.get_scenario_by_name(req.scenario_name)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    env = LifeOSEnv(
        {
            "name": scenario.name,
            "display_name": scenario.display_name,
            "profile": scenario.profile_json,
            "tasks": scenario.tasks_json,
            "events": scenario.events_json,
        }
    )
    episode = repository.create_episode(scenario.id, req.agent_type)
    ACTIVE_ENVS[episode.id] = env
    obs = env.reset().tolist()
    return {"episode_id": episode.id, "initial_observation": obs, "state": env.state, "tasks": env.tasks}


@app.post("/episodes/{episode_id}/step")
def step_episode(episode_id: int, req: StepRequest) -> dict[str, Any]:
    env = ACTIVE_ENVS.get(episode_id)
    if not env:
        raise HTTPException(status_code=404, detail="Episode not active")

    result = env.step(req.action_type, req.reasoning)
    info = result.info
    repository.append_step(
        episode_id=episode_id,
        timestep=int(info["timestep"]),
        state={**info["state"], "sleep_hours": info["sleep_hours"]},
        tasks_json=env.tasks,
        pending_events_json=info.get("known_events", []),
        action_type=req.action_type,
        reasoning=req.reasoning,
        reward=result.reward,
        triggered_events=info.get("triggered_events", []),
    )
    if result.done:
        productivity = info["completion"]
        wellbeing = max(0.0, 1.0 - info["state"]["stress"])
        trust = info["state"]["relationship"]
        balance = (productivity + wellbeing + trust + info["state"]["energy"]) / 4.0
        repository.finalize_episode(
            episode_id,
            total_reward=env.total_reward,
            productivity=productivity,
            wellbeing=wellbeing,
            trust=trust,
            balance=balance,
        )

    return {
        "observation": result.observation.tolist(),
        "reward": result.reward,
        "done": result.done,
        "info": info,
    }


@app.get("/episodes/{episode_id}")
def get_episode(episode_id: int) -> dict[str, Any]:
    payload = repository.get_episode_payload(episode_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Episode not found")
    return payload


@app.get("/episodes/{episode_id}/compare")
def compare_episode(episode_id: int) -> dict[str, Any]:
    payload = repository.get_episode_payload(episode_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Episode not found")
    scenario_id = payload["episode"]["scenario_id"]
    return repository.get_comparison_for_scenario(scenario_id)


@app.get("/training/{run_id}/rewards")
def get_training_rewards(run_id: int) -> dict[str, Any]:
    rewards = repository.get_training_rewards(run_id)
    if rewards is None:
        raise HTTPException(status_code=404, detail="Training run not found")
    return {"run_id": run_id, "rewards": rewards}


@app.post("/episodes/{episode_id}/reset")
def reset_episode(episode_id: int) -> dict[str, Any]:
    payload = repository.get_episode_payload(episode_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Episode not found")
    scenario_id = payload["episode"]["scenario_id"]
    agent_type = payload["episode"]["agent_type"]
    scenario = repository.get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario missing")

    env = LifeOSEnv(
        {
            "name": scenario.name,
            "display_name": scenario.display_name,
            "profile": scenario.profile_json,
            "tasks": scenario.tasks_json,
            "events": scenario.events_json,
        }
    )
    new_episode = repository.create_episode(scenario_id=scenario_id, agent_type=agent_type)
    ACTIVE_ENVS[new_episode.id] = env
    return {"episode_id": new_episode.id, "state": env.state, "observation": env._observation().tolist()}
