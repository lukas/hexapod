"""SAC checkpoint detection + auto-loading (2026-08-29).

The walkcurr fallback-ladder SAC probe (train_ppo_mjx --algo sac)
saves stock SB3 SAC zips under the same ppo_goal_<run>.zip naming as
every other checkpoint. Every eval/video/harness path loads through
gru_policy.load_checkpoint_auto, so that function must return the
right algorithm class for SAC, PPO, and recurrent checkpoints alike.
CPU-only, no MuJoCo/MJX dependency: uses tiny dummy Box envs.
"""

import numpy as np
import gymnasium as gym
import pytest


class _TinyBoxEnv(gym.Env):
    """Minimal continuous env: 4-dim obs, 2-dim action."""

    observation_space = gym.spaces.Box(-1.0, 1.0, (4,), np.float32)
    action_space = gym.spaces.Box(-1.0, 1.0, (2,), np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(4, np.float32), {}

    def step(self, action):
        return np.zeros(4, np.float32), 0.0, False, False, {}


@pytest.fixture(scope="module")
def sac_zip(tmp_path_factory):
    from stable_baselines3 import SAC
    path = tmp_path_factory.mktemp("ckpt") / "ppo_goal_sacprobe.zip"
    model = SAC("MlpPolicy", _TinyBoxEnv(), buffer_size=64,
                learning_starts=8, policy_kwargs=dict(net_arch=[8]),
                seed=0, device="cpu")
    model.save(path)
    return path


@pytest.fixture(scope="module")
def ppo_zip(tmp_path_factory):
    from stable_baselines3 import PPO
    path = tmp_path_factory.mktemp("ckpt") / "ppo_goal_ppoprobe.zip"
    model = PPO("MlpPolicy", _TinyBoxEnv(), n_steps=8, batch_size=8,
                policy_kwargs=dict(net_arch=[8]), seed=0, device="cpu")
    model.save(path)
    return path


def test_is_sac_checkpoint_detects_sac(sac_zip, ppo_zip):
    from rl_move.sim.gru_policy import is_sac_checkpoint
    assert is_sac_checkpoint(sac_zip) is True
    assert is_sac_checkpoint(ppo_zip) is False


def test_load_checkpoint_auto_returns_sac(sac_zip):
    from stable_baselines3 import SAC
    from rl_move.sim.gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(sac_zip, device="cpu")
    assert isinstance(model, SAC)
    # The eval harness drives policies through BasePolicy.predict with
    # recurrent-shaped kwargs (_ActFn); SAC must accept them.
    obs = np.zeros(4, np.float32)
    action, state = model.policy.predict(
        obs, state=None, episode_start=np.ones((1,), bool),
        deterministic=True)
    assert action.shape == (2,)


def test_load_checkpoint_auto_ppo_unchanged(ppo_zip):
    from stable_baselines3 import PPO
    from rl_move.sim.gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(ppo_zip, device="cpu")
    assert isinstance(model, PPO)


def test_policy_action_std_none_for_sac(sac_zip):
    """SAC has no static log_std; eval_checkpoint must not crash on it.

    Regression for the 08-29 cw-walkcurr-sac-sv-s1 gate-eval crash:
    eval_checkpoint.evaluate() unconditionally read
    ``model.policy.log_std`` (PPO-only attribute) and raised
    AttributeError on the very first real SAC gate eval.
    """
    from rl_move.sim.gru_policy import load_checkpoint_auto
    from rl_move.sim.eval_checkpoint import policy_action_std
    model = load_checkpoint_auto(sac_zip, device="cpu")
    assert policy_action_std(model) is None


def test_policy_action_std_float_for_ppo(ppo_zip):
    from rl_move.sim.gru_policy import load_checkpoint_auto
    from rl_move.sim.eval_checkpoint import policy_action_std
    model = load_checkpoint_auto(ppo_zip, device="cpu")
    std = policy_action_std(model)
    assert isinstance(std, float) and std > 0
