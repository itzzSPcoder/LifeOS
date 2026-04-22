import json
from pathlib import Path
from typing import Any

from lifeos.constants import SCENARIOS_DIR


def list_scenario_files() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("*.json"))


def list_scenarios() -> list[dict[str, Any]]:
    scenarios = []
    for file_path in list_scenario_files():
        scenarios.append(load_scenario(file_path.stem))
    return scenarios


def load_scenario(name: str) -> dict[str, Any]:
    file_path = SCENARIOS_DIR / f"{name}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario '{name}' not found at {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)
