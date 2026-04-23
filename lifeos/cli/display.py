from __future__ import annotations

import os
import sys
import time
import threading
from typing import Any

from rich.console import Console

console = Console()

BANNER = """[bold green]
  _      _  __        ____   _____ 
 | |    (_)/ _|      / __ \ / ____|
 | |     _| |_ ___  | |  | | (___  
 | |    | |  _/ _ \ | |  | |\___ \ 
 | |____| | ||  __/ | |__| |____) |
 |______|_|_| \___|  \____/|_____/ 
                                   
[/bold green][dim]v0.1.0-alpha | Kernel: Linux-style[/dim]
"""

def print_banner() -> None:
    console.print(BANNER)

class Spinner:
    def __init__(self, message: str = "Thinking"):
        self.message = message
        self.stop_running = threading.Event()
        self.spin_thread = threading.Thread(target=self.init_spin)

    def init_spin(self) -> None:
        while not self.stop_running.is_set():
            for cursor in '|/-\\':
                sys.stdout.write(f"\r\033[93m[root@lifeos:~#] {self.message}... {cursor}\033[0m")
                sys.stdout.flush()
                time.sleep(0.1)

    def __enter__(self) -> "Spinner":
        self.spin_thread.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        self.stop_running.set()
        self.spin_thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 30) + "\r")
        sys.stdout.flush()

def _bar(value: float, width: int = 10) -> str:
    filled = int(max(0, min(width, round(value * width))))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def show_profile(scenario: dict[str, Any]) -> None:
    profile = scenario["profile"]
    console.print(f"[bold green]root@lifeos:~#[/bold green] cat /etc/lifeos/scenarios/{scenario['name']}.conf")
    console.print(f"NAME={profile['name']}")
    console.print(f"ROLE={profile['role']}")
    console.print(f"INIT_STRESS={profile['stress']:.2f}")
    console.print(f"INIT_ENERGY={profile['energy']:.2f}")
    console.print(f"INIT_MONEY={profile['money']:.0f}")
    console.print(f"INIT_RELATIONSHIP={profile['relationship']:.2f}")
    console.print("")


def show_scenarios(scenarios: list[dict[str, Any]]) -> None:
    console.print("[bold green]root@lifeos:~#[/bold green] ls -l /etc/lifeos/scenarios/")
    console.print(f"{'ID':<4} {'NAME':<20} {'DISPLAY_NAME'}")
    console.print("-" * 50)
    for s in scenarios:
        console.print(f"{s['id']:<4} {s['name']:<20} {s['display_name']}")
    console.print("")


def show_step(timestep: int, action: str, reason: str, reward: float, state: dict[str, Any]) -> None:
    # Use syslog style or dmesg style
    line = (
        f"[[green]{timestep:06d}[/green]] action=[cyan]{action:<10}[/cyan] reward=[bold]{reward:+.3f}[/bold] | "
        f"str:{_bar(state['stress'])} "
        f"nrg:{_bar(state['energy'])} "
        f"mon:{state['money']:>+6.0f} | rel:{state['relationship']:.2f}"
    )
    console.print(line)
    console.print(f"         > {reason}")


def show_event(event: dict[str, Any]) -> None:
    desc = event.get("description") or event.get("event_type", "event")
    console.print(f"[[bold red]KERN_ALERT[/bold red]] {desc}")
    console.print(f"[[bold red]KERN_ALERT[/bold red]] impact: {event.get('impact', {})}")


def show_score_card(scores: dict[str, float]) -> None:
    console.print("\n[bold green]root@lifeos:~#[/bold green] ./bin/eval_episode")
    console.print("[dim]--- EPISODE SCORE CARD ---[/dim]")
    for key, value in scores.items():
        console.print(f"{key:<15} : {value:.3f}")
    console.print("")


def show_comparison(heuristic: dict[str, Any] | None, ppo: dict[str, Any] | None) -> None:
    console.print("\n[bold green]root@lifeos:~#[/bold green] diff heuristic.log ppo.log")
    console.print(f"{'METRIC':<15} | {'HEURISTIC':<10} | {'PPO':<10}")
    console.print("-" * 45)
    metrics = ["total_reward", "productivity", "wellbeing", "trust", "balance"]
    for metric in metrics:
        h = "-" if not heuristic or heuristic.get(metric) is None else f"{heuristic[metric]:.3f}"
        p = "-" if not ppo or ppo.get(metric) is None else f"{ppo[metric]:.3f}"
        console.print(f"{metric:<15} | {h:<10} | {p:<10}")
    console.print("")
