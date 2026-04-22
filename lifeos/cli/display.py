from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


def _bar(value: float, width: int = 10) -> str:
    filled = int(max(0, min(width, round(value * width))))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def show_profile(scenario: dict[str, Any]) -> None:
    profile = scenario["profile"]
    panel = Panel(
        (
            f"[bold]Name:[/bold] {profile['name']}\n"
            f"[bold]Role:[/bold] {profile['role']}\n"
            f"[bold]Stress:[/bold] {profile['stress']:.2f}  [bold]Energy:[/bold] {profile['energy']:.2f}\n"
            f"[bold]Money:[/bold] {profile['money']:.0f}  [bold]Relationship:[/bold] {profile['relationship']:.2f}"
        ),
        title=f"Scenario: {scenario['display_name']}",
    )
    console.print(panel)


def show_scenarios(scenarios: list[dict[str, Any]]) -> None:
    table = Table(title="LifeOS Scenarios")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Display")
    for s in scenarios:
        table.add_row(str(s["id"]), s["name"], s["display_name"])
    console.print(table)


def show_step(timestep: int, action: str, reason: str, reward: float, state: dict[str, Any]) -> None:
    line = (
        f"[T+{timestep:03d}h] action={action:<10} reward={reward:+.3f} | "
        f"stress {_bar(state['stress'])} {state['stress']:.2f} | "
        f"energy {_bar(state['energy'])} {state['energy']:.2f} | "
        f"money {state['money']:.0f} | rel {state['relationship']:.2f}"
    )
    console.print(line)
    console.print(f"  reason: {reason}")


def show_event(event: dict[str, Any]) -> None:
    desc = event.get("description") or event.get("event_type", "event")
    console.print(Panel(f"{desc}\nimpact={event.get('impact', {})}", title="EVENT", style="bold yellow"))


def show_score_card(scores: dict[str, float]) -> None:
    table = Table(title="End of Episode Score Card")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in scores.items():
        table.add_row(key, f"{value:.3f}")
    console.print(table)


def show_comparison(heuristic: dict[str, Any] | None, ppo: dict[str, Any] | None) -> None:
    table = Table(title="Heuristic vs PPO")
    table.add_column("Metric")
    table.add_column("Heuristic")
    table.add_column("PPO")
    metrics = ["total_reward", "productivity", "wellbeing", "trust", "balance"]
    for metric in metrics:
        h = "-" if not heuristic or heuristic.get(metric) is None else f"{heuristic[metric]:.3f}"
        p = "-" if not ppo or ppo.get(metric) is None else f"{ppo[metric]:.3f}"
        table.add_row(metric, h, p)
    console.print(table)
