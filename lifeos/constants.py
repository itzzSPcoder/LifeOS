from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "lifeos" / "data"
SCENARIOS_DIR = PROJECT_ROOT / "lifeos" / "scenarios"
OUTPUTS_DIR = PROJECT_ROOT / "lifeos" / "outputs"

DB_PATH = DATA_DIR / "lifeos.db"

ACTION_SPACE = [
    "schedule",
    "postpone",
    "cancel",
    "message",
    "rest",
    "commute",
    "buy",
    "delegate",
    "prioritize",
    "sleep",
    "focus",
]

MAX_TIMESTEPS = 168
