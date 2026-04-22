from lifeos.env.lifeos_env import LifeOSEnv
from lifeos.scenarios.loader import load_scenario


def test_env_runs_full_episode_without_crash() -> None:
    env = LifeOSEnv(load_scenario("student_week"))
    done = False
    safety = 0
    while not done and safety < 200:
        result = env.step("prioritize", "test")
        done = result.done
        safety += 1
    assert done is True
    assert safety <= 168


def test_reward_is_float() -> None:
    env = LifeOSEnv(load_scenario("student_week"))
    result = env.step("rest", "test")
    assert isinstance(result.reward, float)
