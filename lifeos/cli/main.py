from __future__ import annotations

import click

from lifeos.agents import heuristic, ppo_agent
from lifeos.cli import display
from lifeos.constants import OUTPUTS_DIR
from lifeos.db import repository
from lifeos.env.lifeos_env import LifeOSEnv
from lifeos.scenarios.loader import load_scenario
from lifeos.training.train import run_training


def _ensure_setup() -> None:
    repository.init_db()
    repository.seed_scenarios()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _run_episode(scenario_name: str, agent: str, model: str | None = None) -> dict[str, float]:
    _ensure_setup()
    scenario_row = repository.get_scenario_by_name(scenario_name)
    if not scenario_row:
        raise click.ClickException(f"Scenario '{scenario_name}' not found. Run --list-scenarios")

    scenario = {
        "name": scenario_row.name,
        "display_name": scenario_row.display_name,
        "profile": scenario_row.profile_json,
        "tasks": scenario_row.tasks_json,
        "events": scenario_row.events_json,
    }
    display.show_profile(scenario)

    env = LifeOSEnv(scenario)
    episode = repository.create_episode(scenario_id=scenario_row.id, agent_type=agent)
    done = False
    while not done:
        if agent == "heuristic":
            action, reason = heuristic.choose_action(env.state, env.tasks)
        else:
            action, reason = ppo_agent.choose_action(env.state, env.tasks, model=model)

        result = env.step(action, reason)
        info = result.info
        display.show_step(info["timestep"], action, reason, result.reward, info["state"])
        for event in info.get("triggered_events", []):
            display.show_event(event)

        repository.append_step(
            episode_id=episode.id,
            timestep=info["timestep"],
            state={**info["state"], "sleep_hours": info["sleep_hours"]},
            tasks_json=env.tasks,
            pending_events_json=info.get("known_events", []),
            action_type=action,
            reasoning=reason,
            reward=result.reward,
            triggered_events=info.get("triggered_events", []),
        )
        done = result.done

    productivity = info["completion"]
    wellbeing = 1.0 - info["state"]["stress"]
    trust = info["state"]["relationship"]
    balance = (productivity + wellbeing + trust + info["state"]["energy"]) / 4.0
    repository.finalize_episode(
        episode_id=episode.id,
        total_reward=env.total_reward,
        productivity=productivity,
        wellbeing=wellbeing,
        trust=trust,
        balance=balance,
    )
    scores = {
        "total_reward": env.total_reward,
        "productivity": productivity,
        "wellbeing": wellbeing,
        "trust": trust,
        "balance": balance,
    }
    display.show_score_card(scores)
    return scores


@click.command()
@click.option("--setup", is_flag=True, help="Initialize DB and load scenarios")
@click.option("--list-scenarios", is_flag=True, help="List available scenarios")
@click.option("--scenario", type=str, help="Scenario name, e.g., student_week")
@click.option("--agent", type=click.Choice(["heuristic", "ppo"]), help="Agent type")
@click.option("--model", type=str, default=None, help="HF model id or local model path")
@click.option("--compare", is_flag=True, help="Print latest comparison for scenario")
@click.option("--train", is_flag=True, help="Run local training simulation")
@click.option("--episodes", type=int, default=100, show_default=True, help="Training episodes")
@click.option("--demo", is_flag=True, help="Run scripted Rahul demo")
def cli(
    setup: bool,
    list_scenarios: bool,
    scenario: str | None,
    agent: str | None,
    model: str | None,
    compare: bool,
    train: bool,
    episodes: int,
    demo: bool,
) -> None:
    if setup:
        _ensure_setup()
        total = len(repository.get_scenarios())
        click.echo(f"[OK] Environment initialized. Scenarios loaded: {total}")

    if list_scenarios:
        _ensure_setup()
        scenarios = repository.get_scenarios()
        display.show_scenarios(
            [{"id": s.id, "name": s.name, "display_name": s.display_name} for s in scenarios]
        )

    if scenario and not agent and not train and not compare:
        _ensure_setup()
        display.show_profile(load_scenario(scenario))

    if agent:
        if not scenario:
            raise click.ClickException("Provide --scenario with --agent")
        _run_episode(scenario_name=scenario, agent=agent, model=model)

    if compare:
        if not scenario:
            raise click.ClickException("Provide --scenario with --compare")
        _ensure_setup()
        scenario_row = repository.get_scenario_by_name(scenario)
        if not scenario_row:
            raise click.ClickException("Scenario not found")
        comp = repository.get_comparison_for_scenario(scenario_row.id)
        display.show_comparison(comp.get("heuristic"), comp.get("ppo"))

    if train:
        if not scenario:
            raise click.ClickException("Provide --scenario with --train")
        _ensure_setup()
        run_id, rewards_path, plot_path = run_training(scenario_name=scenario, episodes=episodes, model_name=model)
        click.echo(f"Training complete. run_id={run_id}")
        click.echo(f"Rewards JSON: {rewards_path}")
        click.echo(f"Reward Plot: {plot_path}")

    if demo:
        _ensure_setup()
        click.echo("[DEMO] Rahul scenario loaded...")
        _run_episode("rahul_story", "heuristic")
        _run_episode("rahul_story", "ppo", model=model)
        scenario_row = repository.get_scenario_by_name("rahul_story")
        if scenario_row:
            comp = repository.get_comparison_for_scenario(scenario_row.id)
            display.show_comparison(comp.get("heuristic"), comp.get("ppo"))


if __name__ == "__main__":
    cli()
