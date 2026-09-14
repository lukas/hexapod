"""Tests for rl_move.env.start_kind_of and its two wired consumers.

Bug context (2026-09-14, walkcurr flat-start-rise 22nd/last
"batch-composition" lever): the live env info dict's `start_kind` key
was computed as a plain `getattr(traj, "start_kind", None)`, but rise/
lower/hold trajectory objects never set a literal `.start_kind`
attribute (only getup/recover do) -- so the key was silently always
`None`, meaning `goal_mode_batch_split.py`'s rise-start_kind sub-split
never actually formed disjoint flat/bridge/crouch minibatches despite
looking "engaged". `start_kind_of` (rl_move/env.py) is the derivation
`eval_checkpoint.py`'s own `_start_kind()` already used for eval-report
labeling (from `start_at`/`start_curl`), now shared so both the live
env info dict (`sim_env.py`) and the eval report use ONE
implementation. These tests cover the pure function plus a fast
mechanics-only end-to-end check that the live env info dict now
reports real labels (no rollout-ranking, no checkpoint load).
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from rl_move.env import start_kind_of


def test_explicit_start_kind_wins():
    t = SimpleNamespace(start_kind="tangle_60", start_at="zero",
                        start_curl=0.0)
    assert start_kind_of(t) == "tangle_60"


def test_crouch_start_at():
    t = SimpleNamespace(start_at="crouch")
    assert start_kind_of(t) == "crouch"


def test_quadstance_start_at():
    t = SimpleNamespace(start_at="quadstance")
    assert start_kind_of(t) == "quadstance"


def test_rise_bank_start_at_maps_to_post_lower():
    t = SimpleNamespace(start_at="rise_bank")
    assert start_kind_of(t) == "post_lower"


def test_zero_with_curl_is_bridge():
    t = SimpleNamespace(start_at="zero", start_curl=0.4)
    assert start_kind_of(t) == "bridge"


def test_zero_without_curl_is_flat():
    t = SimpleNamespace(start_at="zero", start_curl=0.0)
    assert start_kind_of(t) == "flat"


def test_default_start_at_is_plant():
    t = SimpleNamespace()
    assert start_kind_of(t) == "plant"


def test_missing_start_curl_defaults_to_zero_not_bridge():
    # No start_curl attribute at all (e.g. a getup/recover trajectory
    # that never carries the field) must not be misread as "bridge".
    t = SimpleNamespace(start_at="zero")
    assert start_kind_of(t) == "flat"


def test_eval_checkpoint_start_kind_delegates_to_shared_helper():
    from rl_move.sim.eval_checkpoint import _start_kind
    t = SimpleNamespace(start_at="zero", start_curl=0.6)
    assert _start_kind(t) == start_kind_of(t) == "bridge"


def _rise_only_cfg(**goal_overrides):
    g = {"p_hold": 0.0, "p_lean": 0.0, "p_track": 0.0, "p_unload": 0.0,
         "p_raise": 0.0, "p_rise": 1.0, "p_lower": 0.0}
    g.update(goal_overrides)
    return {"goal": g}


def test_sim_env_info_start_kind_reports_flat_bridge_crouch():
    """End-to-end (real mujoco env, DR=0, one step each) -- confirms
    the FIX: info["start_kind"] now reports the real derived label
    instead of the always-None bug. <2s total (3 tiny envs)."""
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv

    for force, expect in (("flat", "flat"), ("bridge", "bridge"),
                          ("crouch", "crouch")):
        env = SimHexapodJointGoalEnv(randomize=False,
                                     cfg=_rise_only_cfg())
        env._goal_gen.force_rise_start = force
        env.reset()
        a = np.zeros(env.action_space.shape, dtype=np.float32)
        _, _, _, _, info = env.step(a)
        assert info.get("goal_mode") == "rise"
        assert info.get("start_kind") == expect, (force, info)
        env.close()


def test_sim_env_info_start_kind_absent_off_rise():
    """Non-rise modes never carry the key (unchanged contract)."""
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv

    env = SimHexapodJointGoalEnv(
        randomize=False,
        cfg={"goal": {"p_hold": 1.0, "p_lean": 0.0, "p_track": 0.0,
                      "p_unload": 0.0, "p_raise": 0.0, "p_rise": 0.0,
                      "p_lower": 0.0}})
    env.reset()
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    _, _, _, _, info = env.step(a)
    assert info.get("goal_mode") == "hold"
    assert "start_kind" not in info
    env.close()


def test_ease_rise_flat_only_default_off_is_bit_exact():
    """ease.rise_flat_only unset behaves exactly like before this
    cycle's change: no gravity/vel_ceiling mutation at all when
    ease.gravity_scale/vel_ceiling_scale are also left at 1.0."""
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv

    env = SimHexapodJointGoalEnv(randomize=False, cfg=_rise_only_cfg())
    env._goal_gen.force_rise_start = "flat"
    env.reset()
    assert env._ease_g == 1.0 and env._ease_v == 1.0


def test_ease_rise_flat_only_eases_flat_rise_but_not_bridge():
    """The new scoping gate: ease.gravity_scale applies to a
    start_kind='flat' rise episode when ease.rise_flat_only=1, but a
    bridge-start rise episode in the SAME config reverts to nominal
    (1.0) -- the "genuinely new mechanism family" this cycle adds to
    the flat-start-rise lever hunt (dynamics-parameter easing, scoped
    to the exact still-unsolved sub-population, distinct from every
    already-closed cap/reward-pricing/reset-timing/leg-order/batch-
    composition lever)."""
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv

    cfg = _rise_only_cfg()
    cfg["ease"] = {"gravity_scale": 0.6, "rise_flat_only": 1.0}

    env_flat = SimHexapodJointGoalEnv(randomize=False, cfg=cfg)
    env_flat._goal_gen.force_rise_start = "flat"
    env_flat.reset()
    assert env_flat._ease_g == 0.6

    env_bridge = SimHexapodJointGoalEnv(randomize=False, cfg=cfg)
    env_bridge._goal_gen.force_rise_start = "bridge"
    env_bridge.reset()
    assert env_bridge._ease_g == 1.0
