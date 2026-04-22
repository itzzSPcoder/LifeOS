# LifeOS (Terminal-First)

LifeOS is a terminal-first reinforcement-learning simulation environment for real-life chaos scenarios.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m lifeos.cli --setup
python -m lifeos.cli --list-scenarios
python -m lifeos.cli --scenario student_week --agent heuristic
python -m lifeos.cli --scenario student_week --agent ppo
python -m lifeos.cli --scenario student_week --compare
python -m lifeos.cli --scenario student_week --train --episodes 50
python -m lifeos.cli --demo
```

## Run API

```bash
uvicorn lifeos.api.main:app --reload --port 8000
```

## Runtime Modes

### 1) Container-based (Docker)

All env services run as independent containers:

- `echo_env`
- `coding_env`
- `chess_env`
- `carla_env`
- `julia_env`

Start them:

```bash
docker compose --profile envs up -d echo_env coding_env chess_env carla_env julia_env
```

Check container health (including Julia runtime availability for `julia_env`):

```bash
docker compose ps
```

Health checks:

```bash
curl http://localhost:8101/health
curl http://localhost:8102/health
curl http://localhost:8103/health
curl http://localhost:8104/health
curl http://localhost:8105/health
```

### 2) Process-based (UV)

Lightweight local mode without containers:

```bash
uv sync
uv run uvicorn lifeos.api.main:app --reload --port 8000
uv run python -m lifeos.cli --scenario student_week --agent heuristic
```

### 3) Hybrid (Container + Process)

`coding_env` and `julia_env` run as containers, but execute snippets in internal subprocesses.

Python execution via `coding_env`:

```bash
curl -X POST http://localhost:8102/exec/python \
	-H "Content-Type: application/json" \
	-d '{"code":"print(2 + 2)","timeout_seconds":5}'
```

Julia execution via `julia_env`:

```bash
curl -X POST http://localhost:8105/exec/julia \
	-H "Content-Type: application/json" \
	-d '{"code":"println(2 + 2)","timeout_seconds":5}'
```

## Docker

Build image:

```bash
docker compose build
```

Optionally pin a Julia version at build time:

```bash
docker compose build --build-arg JULIA_VERSION=1.10.4
```

Create local env file for keys:

```bash
copy .env.example .env
```

Then edit `.env` and set values:

```bash
HF_API_TOKEN=your_hf_token
LIFEOS_HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
WANDB_API_KEY=your_wandb_key
```

Start API (with persistent DB and outputs):

```bash
docker compose up -d lifeos-api
```

Run CLI commands inside container:

```bash
docker compose run --rm lifeos-cli python -m lifeos.cli --setup
docker compose run --rm lifeos-cli python -m lifeos.cli --list-scenarios
docker compose run --rm lifeos-cli python -m lifeos.cli --scenario student_week --agent heuristic
docker compose run --rm lifeos-cli python -m lifeos.cli --scenario student_week --agent ppo
docker compose run --rm lifeos-cli python -m lifeos.cli --scenario student_week --compare
docker compose run --rm lifeos-cli python -m lifeos.cli --scenario student_week --train --episodes 50
```

Stop services:

```bash
docker compose down
```

## Real TRL + Unsloth Training (Colab)

Use this when you want actual LLM fine-tuning instead of local simulation.

```bash
pip install -r requirements-colab.txt
python -m lifeos.training.train_trl_unsloth --scenario student_week --episodes 30
```

Colab notebook:

- lifeos/notebooks/lifeos_trl_unsloth_colab.ipynb

Optional push to Hub:

```bash
python -m lifeos.training.train_trl_unsloth --scenario student_week --episodes 50 --push-to-hub --hub-model-id <username>/lifeos-ppo-v1
```

## HuggingFace Integration

PPO mode can call HuggingFace Inference API when these are set:

- `HF_API_TOKEN`
- `LIFEOS_HF_MODEL` (example: `mistralai/Mistral-7B-Instruct-v0.3`)

For training + model upload you may also need:

- `HF_API_TOKEN` (write access for push)
- `WANDB_API_KEY` (optional experiment tracking)

Without these keys, `ppo` mode safely falls back to heuristic logic.

## Secure Token Handling

- Do not paste secret tokens in chat.
- Keep tokens only in local `.env` or terminal environment variables.
- `.env` is ignored in git by default via `.gitignore`.

Windows PowerShell (temporary for current shell):

```powershell
$env:HF_API_TOKEN="your_hf_token"
$env:LIFEOS_HF_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
$env:WANDB_API_KEY="your_wandb_key"
```

Windows cmd (temporary for current shell):

```cmd
set HF_API_TOKEN=your_hf_token
set LIFEOS_HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
set WANDB_API_KEY=your_wandb_key
```

Validate tokens safely (without printing secrets):

```bash
python -m lifeos.scripts.check_tokens
```
