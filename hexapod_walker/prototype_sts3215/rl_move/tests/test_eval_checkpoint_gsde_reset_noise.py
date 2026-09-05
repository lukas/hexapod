"""``run_episode`` resamples the gSDE exploration matrix once per
episode (2026-09-05, walkcurr sde-s3-c1b triage): SB3's own
``model.predict()`` never calls ``policy.reset_noise()`` -- only the
training-time rollout collector does -- so a loaded gSDE checkpoint's
"stochastic" eval pass silently reused ONE frozen noise draw for every
episode in any goal mode without its own init randomization (confirmed
by hand: `cw-walkscratch-easy0905-sde-s3-c1b`'s `walk_sto_0..5.mp4` are
all one MD5). Additive fix in `eval_checkpoint._maybe_reset_gsde_noise`:
called at the top of every `run_episode`, resamples for `use_sde=True`
models (direct or through a `Rot60Policy`-style `.model` wrapper),
no-ops (bit-exact) for everything else -- the overwhelming majority of
checkpoints, non-gSDE by default.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("mujoco")

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.eval_checkpoint import (  # noqa: E402
    _maybe_reset_gsde_noise,
    run_episode,
)
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402

N_ACT = 18


class _Policy:
    def __init__(self):
        self.reset_noise_calls = 0

    def reset_noise(self, n_envs: int = 1) -> None:
        self.reset_noise_calls += 1


class _Model:
    """Bare stand-in for a loaded SB3 PPO model."""

    def __init__(self, use_sde: bool):
        self.use_sde = use_sde
        self.policy = _Policy()

    def predict(self, obs, deterministic: bool = True):
        return np.zeros(N_ACT), None


class _WrapperModel:
    """Stand-in for Rot60Policy: no `use_sde` of its own, proxies to
    an inner `.model`."""

    def __init__(self, inner):
        self.model = inner

    def predict(self, obs, deterministic: bool = True):
        return self.model.predict(obs, deterministic=deterministic)


def _walk_env():
    cfg = load_config()
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=2.0,
                                 randomize=False, dr_scale=0.0)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    if hasattr(gen, "p_walk"):
        gen.p_walk = 1.0
    return env


def test_non_sde_model_never_calls_reset_noise():
    """Bit-exact-off: the default (`use_sde=False`) path never touches
    `reset_noise` -- covers the overwhelming majority of checkpoints."""
    model = _Model(use_sde=False)
    env = _walk_env()
    run_episode(env, model, deterministic=True, video=False, annotate=None)
    assert model.policy.reset_noise_calls == 0


def test_sde_model_resamples_noise_every_episode():
    """A gSDE checkpoint gets one fresh `reset_noise()` draw per
    `run_episode` call -- the fix that stops repeated "stochastic"
    episodes from being bit-identical replays of one frozen matrix."""
    model = _Model(use_sde=True)
    env = _walk_env()
    run_episode(env, model, deterministic=False, video=False, annotate=None)
    assert model.policy.reset_noise_calls == 1
    env2 = _walk_env()
    run_episode(env2, model, deterministic=False, video=False, annotate=None)
    assert model.policy.reset_noise_calls == 2


def test_wrapped_sde_model_resamples_through_inner_model():
    """A `Rot60Policy`-style wrapper (no `use_sde` of its own, an
    inner `.model`) still gets its inner gSDE noise resampled."""
    inner = _Model(use_sde=True)
    wrapper = _WrapperModel(inner)
    env = _walk_env()
    run_episode(env, wrapper, deterministic=False, video=False, annotate=None)
    assert inner.policy.reset_noise_calls == 1


def test_helper_is_a_noop_for_a_plain_object_with_no_use_sde_or_model():
    class _Bare:
        def predict(self, obs, deterministic=True):
            return np.zeros(N_ACT), None
    # Must not raise even with neither `use_sde` nor `.model`.
    _maybe_reset_gsde_noise(_Bare())
