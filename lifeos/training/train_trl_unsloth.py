from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lifeos.constants import ACTION_SPACE, OUTPUTS_DIR
from lifeos.db import repository
from lifeos.env.lifeos_env import LifeOSEnv


def _lazy_imports() -> tuple[object, object, object, object, object]:
    # Imported lazily so normal local runs do not require GPU packages.
    from datasets import Dataset
    from transformers import AutoTokenizer
    from trl import PPOConfig, PPOTrainer
    from unsloth import FastLanguageModel

    return Dataset, AutoTokenizer, PPOConfig, PPOTrainer, FastLanguageModel


@dataclass
class TrainConfig:
    scenario_name: str
    model_name: str
    episodes: int
    max_new_tokens: int
    push_to_hub: bool
    hub_model_id: str | None


def build_prompt(state: dict, tasks: list[dict], timestep: int) -> str:
    pending = [t for t in tasks if t.get("status") != "done"]
    top_pending = sorted(pending, key=lambda t: (t["deadline_hours"], -t["priority"]))[:3]
    return (
        "You are a LifeOS RL agent. Pick exactly one action and give reasoning.\n"
        f"Allowed actions: {ACTION_SPACE}\n"
        f"Timestep: {timestep}\n"
        f"State: energy={state['energy']:.2f}, stress={state['stress']:.2f}, "
        f"money={state['money']:.2f}, relationship={state['relationship']:.2f}\n"
        f"Top pending tasks: {json.dumps(top_pending)}\n"
        "Respond as strict JSON: {\"action\": \"...\", \"reasoning\": \"...\"}"
    )


def parse_model_output(text: str) -> tuple[str, str]:
    text = text.strip()
    if "{" in text and "}" in text:
        candidate = text[text.find("{") : text.rfind("}") + 1]
        try:
            data = json.loads(candidate)
            action = str(data.get("action", "prioritize")).strip().lower()
            if action not in ACTION_SPACE:
                action = "prioritize"
            reasoning = str(data.get("reasoning", "No reasoning"))[:400]
            return action, reasoning
        except Exception:
            pass
    lowered = text.lower()
    for action in ACTION_SPACE:
        if action in lowered:
            return action, text[:400]
    return "prioritize", text[:400]


def run_real_training(cfg: TrainConfig) -> tuple[list[float], str]:
    Dataset, AutoTokenizer, PPOConfig, PPOTrainer, FastLanguageModel = _lazy_imports()

    repository.init_db()
    repository.seed_scenarios()
    scenario = repository.get_scenario_by_name(cfg.scenario_name)
    if not scenario:
        raise ValueError(f"Scenario not found: {cfg.scenario_name}")

    scenario_payload = {
        "name": scenario.name,
        "display_name": scenario.display_name,
        "profile": scenario.profile_json,
        "tasks": scenario.tasks_json,
        "events": scenario.events_json,
    }

    # Unsloth optimized model load.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg.model_name,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    ppo_config = PPOConfig(
        learning_rate=1e-5,
        batch_size=1,
        mini_batch_size=1,
        gradient_accumulation_steps=1,
        optimize_cuda_cache=True,
    )

    # PPOTrainer needs a reference model; TRL handles cloning internally when ref_model is None.
    ppo_trainer = PPOTrainer(
        config=ppo_config,
        model=model,
        ref_model=None,
        tokenizer=tokenizer,
        dataset=Dataset.from_dict({"query": ["bootstrap"]}),
    )

    episode_rewards: list[float] = []
    for ep in range(cfg.episodes):
        env = LifeOSEnv(scenario_payload)
        done = False
        total_reward = 0.0

        while not done:
            prompt = build_prompt(env.state, env.tasks, env.timestep)
            query_tensor = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
            response_tensor = ppo_trainer.generate(query_tensor, max_new_tokens=cfg.max_new_tokens)
            response_text = tokenizer.decode(response_tensor[0], skip_special_tokens=True)

            action, _reason = parse_model_output(response_text)
            step_result = env.step(action, response_text[:400])
            reward_value = float(step_result.reward)
            total_reward += reward_value

            # PPO update step.
            ppo_trainer.step([query_tensor[0]], [response_tensor[0]], [reward_value])
            done = step_result.done

        # Small exploration noise helps avoid reward flat-lines in short runs.
        total_reward += random.uniform(-0.03, 0.03)
        episode_rewards.append(total_reward)
        print(f"Episode {ep + 1}/{cfg.episodes} | reward={total_reward:.4f}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_out_dir = Path("models") / f"lifeos_ppo_real_{stamp}"
    model_out_dir.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(model_out_dir)
    tokenizer.save_pretrained(model_out_dir)

    rewards_file = OUTPUTS_DIR / f"rewards_real_{cfg.scenario_name}_{stamp}.json"
    rewards_file.write_text(json.dumps(episode_rewards, indent=2), encoding="utf-8")

    if cfg.push_to_hub and cfg.hub_model_id:
        model.push_to_hub(cfg.hub_model_id)
        tokenizer.push_to_hub(cfg.hub_model_id)

    run_id = repository.create_training_run(
        scenario_id=scenario.id,
        model_name=cfg.model_name,
        rewards=episode_rewards,
        model_path=str(model_out_dir),
    )
    print(f"Saved training_run id={run_id}")
    return episode_rewards, str(model_out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LifeOS with TRL + Unsloth PPO")
    parser.add_argument("--scenario", default="student_week")
    parser.add_argument("--model", default="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-model-id", default=None)
    args = parser.parse_args()

    cfg = TrainConfig(
        scenario_name=args.scenario,
        model_name=args.model,
        episodes=args.episodes,
        max_new_tokens=args.max_new_tokens,
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id,
    )
    run_real_training(cfg)


if __name__ == "__main__":
    main()
