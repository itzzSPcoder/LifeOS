from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from lifeos.db.database import SessionLocal, engine
from lifeos.db.models import Action, Base, Episode, Event, Scenario, State, TrainingRun
from lifeos.scenarios.loader import list_scenarios


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_scenarios() -> int:
    loaded = list_scenarios()
    created = 0
    with SessionLocal() as db:
        for scenario in loaded:
            existing = db.scalar(select(Scenario).where(Scenario.name == scenario["name"]))
            if existing:
                existing.display_name = scenario["display_name"]
                existing.profile_json = scenario["profile"]
                existing.tasks_json = scenario["tasks"]
                existing.events_json = scenario["events"]
                continue
            db.add(
                Scenario(
                    name=scenario["name"],
                    display_name=scenario["display_name"],
                    profile_json=scenario["profile"],
                    tasks_json=scenario["tasks"],
                    events_json=scenario["events"],
                )
            )
            created += 1
        db.commit()
    return created


def get_scenarios() -> list[Scenario]:
    with SessionLocal() as db:
        return list(db.scalars(select(Scenario).order_by(Scenario.id)))


def get_scenario_by_name(name: str) -> Scenario | None:
    with SessionLocal() as db:
        return db.scalar(select(Scenario).where(Scenario.name == name))


def get_scenario_by_id(scenario_id: int) -> Scenario | None:
    with SessionLocal() as db:
        return db.get(Scenario, scenario_id)


def create_episode(scenario_id: int, agent_type: str) -> Episode:
    with SessionLocal() as db:
        episode = Episode(scenario_id=scenario_id, agent_type=agent_type)
        db.add(episode)
        db.commit()
        db.refresh(episode)
        return episode


def append_step(
    episode_id: int,
    timestep: int,
    state: dict[str, Any],
    tasks_json: list[dict[str, Any]],
    pending_events_json: list[dict[str, Any]],
    action_type: str,
    reasoning: str,
    reward: float,
    triggered_events: list[dict[str, Any]],
) -> None:
    with SessionLocal() as db:
        state_row = State(
            episode_id=episode_id,
            timestep=timestep,
            energy=float(state["energy"]),
            stress=float(state["stress"]),
            money=float(state["money"]),
            relationship_score=float(state["relationship"]),
            sleep_hours=float(state.get("sleep_hours", 6.0)),
            tasks_json=tasks_json,
            pending_events_json=pending_events_json,
        )
        db.add(state_row)
        db.flush()
        db.add(
            Action(
                episode_id=episode_id,
                state_id=state_row.id,
                action_type=action_type,
                action_params_json={},
                reasoning=reasoning,
                reward=reward,
            )
        )
        for event in triggered_events:
            db.add(
                Event(
                    episode_id=episode_id,
                    timestep=int(event.get("timestep", timestep)),
                    event_type=str(event.get("event_type", "unknown")),
                    impact_json=event.get("impact", {}),
                    is_random=1 if event.get("is_random", False) else 0,
                )
            )
        db.commit()


def finalize_episode(
    episode_id: int,
    total_reward: float,
    productivity: float,
    wellbeing: float,
    trust: float,
    balance: float,
) -> None:
    with SessionLocal() as db:
        episode = db.get(Episode, episode_id)
        if not episode:
            return
        episode.total_reward = total_reward
        episode.productivity_score = productivity
        episode.wellbeing_score = wellbeing
        episode.trust_score = trust
        episode.balance_score = balance
        episode.ended_at = datetime.utcnow()
        db.commit()


def create_training_run(
    scenario_id: int,
    model_name: str,
    rewards: list[float],
    model_path: str | None,
) -> int:
    with SessionLocal() as db:
        run = TrainingRun(
            scenario_id=scenario_id,
            model_name=model_name,
            num_episodes=len(rewards),
            rewards_json=rewards,
            model_path=model_path,
            ended_at=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id


def get_training_rewards(run_id: int) -> list[float] | None:
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if not run:
            return None
        return list(run.rewards_json)


def get_episode_payload(episode_id: int) -> dict[str, Any] | None:
    with SessionLocal() as db:
        episode = db.get(Episode, episode_id)
        if not episode:
            return None
        states = db.scalars(select(State).where(State.episode_id == episode_id).order_by(State.timestep)).all()
        actions = db.scalars(select(Action).where(Action.episode_id == episode_id).order_by(Action.id)).all()
        events = db.scalars(select(Event).where(Event.episode_id == episode_id).order_by(Event.timestep)).all()
        return {
            "episode": {
                "id": episode.id,
                "scenario_id": episode.scenario_id,
                "agent_type": episode.agent_type,
                "total_reward": episode.total_reward,
                "productivity_score": episode.productivity_score,
                "wellbeing_score": episode.wellbeing_score,
                "trust_score": episode.trust_score,
                "balance_score": episode.balance_score,
            },
            "states": [
                {
                    "timestep": s.timestep,
                    "energy": s.energy,
                    "stress": s.stress,
                    "money": s.money,
                    "relationship_score": s.relationship_score,
                    "sleep_hours": s.sleep_hours,
                }
                for s in states
            ],
            "actions": [
                {
                    "action_type": a.action_type,
                    "reasoning": a.reasoning,
                    "reward": a.reward,
                }
                for a in actions
            ],
            "events": [
                {
                    "timestep": e.timestep,
                    "event_type": e.event_type,
                    "impact": e.impact_json,
                    "is_random": bool(e.is_random),
                }
                for e in events
            ],
        }


def get_comparison_for_scenario(scenario_id: int) -> dict[str, Any]:
    with SessionLocal() as db:
        episodes = db.scalars(
            select(Episode)
            .where(Episode.scenario_id == scenario_id, Episode.total_reward.is_not(None))
            .order_by(Episode.id.desc())
        ).all()
        latest_by_agent: dict[str, Episode] = {}
        for ep in episodes:
            if ep.agent_type not in latest_by_agent:
                latest_by_agent[ep.agent_type] = ep
        return {
            "heuristic": _episode_score_payload(latest_by_agent.get("heuristic")),
            "ppo": _episode_score_payload(latest_by_agent.get("ppo")),
        }


def _episode_score_payload(ep: Episode | None) -> dict[str, Any] | None:
    if not ep:
        return None
    return {
        "episode_id": ep.id,
        "total_reward": ep.total_reward,
        "productivity": ep.productivity_score,
        "wellbeing": ep.wellbeing_score,
        "trust": ep.trust_score,
        "balance": ep.balance_score,
    }
