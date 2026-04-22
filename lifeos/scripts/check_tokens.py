from __future__ import annotations

import os
from pathlib import Path

import requests


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value


def check_hf(token: str) -> tuple[bool, str]:
    try:
        resp = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 200:
            payload = resp.json()
            user = payload.get("name") or payload.get("fullname") or "unknown"
            return True, f"HF token OK (user: {user})"
        return False, f"HF token failed ({resp.status_code})"
    except Exception as exc:
        return False, f"HF check error: {exc}"


def check_wandb(key: str) -> tuple[bool, str]:
    try:
        query = {"query": "query Viewer { viewer { id username } }"}
        # Try classic API-key auth first.
        attempts = [
            requests.post(
                "https://api.wandb.ai/graphql",
                json=query,
                auth=("api", key),
                timeout=15,
            ),
            requests.post(
                "https://api.wandb.ai/graphql",
                json=query,
                headers={"Authorization": f"Bearer {key}"},
                timeout=15,
            ),
        ]
        for resp in attempts:
            if resp.status_code != 200:
                continue
            payload = resp.json()
            viewer = payload.get("data", {}).get("viewer")
            if viewer and viewer.get("username"):
                return True, f"W&B key OK (user: {viewer['username']})"
        return False, "W&B key invalid or expired (viewer not found)"
    except Exception as exc:
        return False, f"W&B check error: {exc}"


def main() -> int:
    load_dotenv(Path(".env"))

    hf_token = os.getenv("HF_API_TOKEN", "").strip()
    wandb_key = os.getenv("WANDB_API_KEY", "").strip()

    if not hf_token:
        print("HF token missing in .env (HF_API_TOKEN)")
    else:
        ok, msg = check_hf(hf_token)
        print(msg)

    if not wandb_key:
        print("W&B key missing in .env (WANDB_API_KEY)")
    else:
        ok, msg = check_wandb(wandb_key)
        print(msg)

    if hf_token and wandb_key:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
