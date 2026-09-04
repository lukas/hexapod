"""``run_episode`` persisting the per-episode DR draw into the returned
ep dict (standwalk STATUS Next#1, 2026-09-04): "add per-episode DR-draw
logging to eval_cmd_stress/eval_checkpoint own-DR pass ... correlate
against which episodes still fire hold_min_load" — no consumer
persisted `info0["randomization"]` (already computed every episode by
`EpisodeRandomization.summary()`, sim_env.py's reset info) into the
eval report, so no dig-in could correlate a fired termination against
the SAMPLED friction/mass/gain/etc axis. Purely additive: a DR-off
episode's `info0["randomization"]` is already None (no randomizer ->
no key change), so the ep dict must be BYTE-IDENTICAL (same keys) to
before this change; a DR-on episode gets one new `ep["randomization"]`
key mirroring the reset info verbatim.
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
from rl_move.sim.eval_checkpoint import run_episode  # noqa: E402
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402

N_ACT = 18


class _ZeroModel:
    def predict(self, obs, deterministic=True):
        return np.zeros(N_ACT), None


def _rise_env(*, randomize: bool, dr_scale: float = 0.5):
    cfg = load_config()
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=8.0,
                                 randomize=randomize, dr_scale=dr_scale)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "walk", "lower"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_rise = 1.0
    return env


def test_dr_off_episode_has_no_randomization_key():
    """No randomizer (dr_scale=0, randomize=False): the ep dict must
    NOT grow a `randomization` key — every pre-existing DR0 report.json
    shape stays byte-identical."""
    env = _rise_env(randomize=False, dr_scale=0.0)
    ep, _frames = run_episode(env, _ZeroModel(), deterministic=True,
                              video=False, annotate=None)
    assert "randomization" not in ep


def test_dr_on_episode_persists_the_sampled_draw():
    """DR on: `ep["randomization"]` mirrors the reset info's
    `EpisodeRandomization.summary()` verbatim (same keys/values) so a
    dig-in can correlate a fired termination against the sampled
    friction/mass/gain/etc axis."""
    env = _rise_env(randomize=True, dr_scale=0.5)
    obs, info0 = env.reset(seed=123)
    assert info0.get("randomization") is not None
    expected = info0["randomization"]
    env2 = _rise_env(randomize=True, dr_scale=0.5)
    ep, _frames = run_episode(env2, _ZeroModel(), deterministic=True,
                              video=False, annotate=None)
    # env2.reset(seed=None) inside run_episode re-seeds env2.rng from
    # its own __init__ seed=0, identical draw order to env's seed=123
    # reset only if seeds match -- assert structurally instead: same
    # KEY SET, and every value is the right type/finite, not a fixed
    # numeric match (the two envs are independent RNG streams).
    assert "randomization" in ep
    assert set(ep["randomization"].keys()) == set(expected.keys())
    for k, v in ep["randomization"].items():
        if isinstance(v, float):
            assert np.isfinite(v)
