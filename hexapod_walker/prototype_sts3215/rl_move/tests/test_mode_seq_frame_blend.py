"""goal.mode_seq_frame_blend_s (09-02, standwalk duration-mismatch
DIG-IN follow-up): does the observation-only q_nom blend fix the
confirmed switch-tick shock without silently changing anything else?

Background (STATUS.md 2026-09-02, `debug_seq_switch_obs_jump.py`
instrumented proof): a family-changing mode_seq switch (rise="belly"
-> walk="plant") installs the new canonical q_nom in one tick while
the robot's ACTUAL joints haven't moved -- build_obs's `q_rel =
(joint_position - q_nom)/q_scale` term jumps ~215-220deg L2 (up to
~89deg on one joint) EVERY time, and every surveyed episode's action
output saturates (clipped near max magnitude) on that exact tick and
stays saturated for seconds, pushing current toward the safety cap.
`goal.mode_seq_frame_blend_s` (default 0.0 = off) linearly blends
JUST the q_nom build_obs reads (not the reward/anchor/IK-facing
`self._q_nom`, which keeps behaving exactly as before) from the
pre-switch to the post-switch canonical frame over that many seconds,
so the policy's raw input moves continuously instead of teleporting.

These tests lock:
1. default off (0.0) is bit-exact identical to no blend at all;
2. a same-family switch (walk->lower, both "plant") never arms a
   blend (nothing to blend, frames are identical) regardless of the
   cfg value;
3. a family-changing switch WITH the feature on installs a blend that
   starts at the pre-switch q_rel and ends at the exact same q_rel a
   legacy (blend=0) run reaches, moving smoothly in between -- the
   discontinuity this feature exists to remove is gone, and the
   POST-window state is identical to legacy (no permanent drift);
4. `self._q_nom` itself (the reward/anchor/IK-facing value) is
   UNCHANGED by the blend at every tick, on or off -- this feature
   touches the policy's observation only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "linux_control"))
sys.path.insert(0, str(ROOT / "linux_control" / "urt2_setup"))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.mjx_host import SNAP_ATTRS  # noqa: E402
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402


def _make_env(seed: int, episode_seconds: float, plan: str,
              blend_s: float | None = None,
              seg_s=(6.0, 8.0)) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["mode_seq"] = 1.0
    g["mode_seq_segment_s_min"], g["mode_seq_segment_s_max"] = seg_s
    g["mode_seq_forced_plan"] = plan
    if blend_s is not None:
        g["mode_seq_frame_blend_s"] = blend_s
    cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    return SimHexapodJointWalkEnv(cfg, seed=seed,
                                  episode_seconds=episode_seconds)


def _run(env, n_steps, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    n = env.action_space.shape[0]
    obs_hist, q_nom_hist = [], []
    for _ in range(n_steps):
        a = rng.uniform(-0.05, 0.05, n)
        obs, r, term, trunc, info = env.step(a)
        obs_hist.append(obs.copy())
        q_nom_hist.append(env._q_nom.copy())
        if term or trunc:
            break
    return obs_hist, q_nom_hist


def test_attr_registered_for_pool_restore():
    assert "_frame_blend" in SNAP_ATTRS


def test_default_off_is_bit_exact():
    plan = "rise:6,walk:6"
    a = _make_env(0, 15.0, plan)                       # no key at all
    b = _make_env(0, 15.0, plan, blend_s=0.0)           # explicit 0.0
    oa0, _ = a.reset()
    ob0, _ = b.reset()
    np.testing.assert_array_equal(oa0, ob0)
    oa, _ = _run(a, 900)
    ob, _ = _run(b, 900)
    assert len(oa) == len(ob)
    for x, y in zip(oa, ob):
        np.testing.assert_array_equal(x, y)


def test_same_family_switch_never_arms_blend():
    env = _make_env(0, 15.0, "walk:6,lower:6", blend_s=2.0)
    env.reset()
    _run(env, 900)
    assert env._frame_blend is None


def test_family_switch_blend_matches_legacy_endpoints():
    plan = "rise:6,walk:6"
    legacy = _make_env(0, 15.0, plan, blend_s=0.0)
    blended = _make_env(0, 15.0, plan, blend_s=0.5)
    legacy.reset()
    blended.reset()
    dt = legacy.dt
    switch_tick = round(6.0 / dt)
    n_blend_ticks = round(0.5 / dt)

    def q_rel_for_obs(env):
        return (env._state.joint_position - env._q_nom_for_obs())

    legacy_steps, blended_steps = [], []
    rng_l = np.random.default_rng(1)
    rng_b = np.random.default_rng(1)
    n_act = legacy.action_space.shape[0]
    for i in range(switch_tick + n_blend_ticks + 20):
        a = rng_l.uniform(-0.03, 0.03, n_act)
        legacy.step(a)
        legacy_steps.append(q_rel_for_obs(legacy).copy())
    for i in range(switch_tick + n_blend_ticks + 20):
        a = rng_b.uniform(-0.03, 0.03, n_act)
        blended.step(a)
        blended_steps.append(q_rel_for_obs(blended).copy())

    # Right AT the switch tick (0-indexed step count == switch_tick-1
    # after that many .step() calls) the legacy run already shows the
    # full jump; the blended run must NOT have jumped yet (its q_rel
    # is still close to its own pre-switch value).
    pre_switch_q_rel = legacy_steps[switch_tick - 2]
    legacy_jump = np.linalg.norm(
        legacy_steps[switch_tick - 1] - pre_switch_q_rel)
    blended_at_switch = np.linalg.norm(
        blended_steps[switch_tick - 1] - pre_switch_q_rel)
    assert legacy_jump > 1.0   # legacy: instant, large (radians)
    assert blended_at_switch < 0.05 * legacy_jump   # blended: ~0 yet

    # Well AFTER the blend window, both runs converge to the SAME
    # post-switch q_rel (same actions, same physics — only the
    # observation's transient path differs, never the destination).
    tail_legacy = legacy_steps[-1]
    tail_blended = blended_steps[-1]
    np.testing.assert_allclose(tail_legacy, tail_blended, atol=1e-6)


def test_q_nom_itself_unaffected_by_blend():
    """The reward/anchor/IK-facing self._q_nom must teleport exactly
    as before regardless of the obs-only blend -- only build_obs's
    input path changes."""
    plan = "rise:6,walk:6"
    for blend_s in (0.0, 0.5, 2.0):
        legacy = _make_env(0, 15.0, plan, blend_s=0.0)
        cand = _make_env(0, 15.0, plan, blend_s=blend_s)
        legacy.reset()
        cand.reset()
        rng_l = np.random.default_rng(2)
        rng_c = np.random.default_rng(2)
        n_act = legacy.action_space.shape[0]
        for _ in range(900):
            legacy.step(rng_l.uniform(-0.03, 0.03, n_act))
            cand.step(rng_c.uniform(-0.03, 0.03, n_act))
            np.testing.assert_array_equal(legacy._q_nom, cand._q_nom)
