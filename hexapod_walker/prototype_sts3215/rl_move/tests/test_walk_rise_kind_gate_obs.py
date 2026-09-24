"""Tests for the rise start-kind GATE one-hot (obs.rise_start_kind_gate,
see rl_move/sim/walk_task.py::rise_start_kind_gate_onehot).

DISTINCT from the already-closed obs.rise_start_kind_sense (removed
2026-09-24 ~19:1x): that channel fed the identical flat/bridge/crouch
label as extra INPUT to one shared trunk (measurably useless). This one
exists purely to drive gru_policy.RiseKindGruActorCriticPolicy's hard
expert-selection gate -- appended immediately BEFORE the existing
obs.mode_onehot tail (walk_task.py) so the gate can read both at a
fixed negative offset regardless of task-specific vel/phase width
upstream. Default OFF, bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.config import load_config
from rl_move.sim.walk_task import (
    MODE_ONEHOT_ORDER, N_MODE_OBS, N_RISE_KIND_OBS, RISE_START_KIND_LABELS,
    SimHexapodJointWalkEnv, rise_start_kind_gate_onehot,
)

ALL_MODES = ("hold", "lean", "track", "unload", "raise",
             "rise", "lower", "walk", "quad")


def test_labels_and_width():
    assert RISE_START_KIND_LABELS == ("flat", "bridge", "crouch")
    assert N_RISE_KIND_OBS == 3


def test_onehot_lookup():
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("rise", "flat"), [1.0, 0.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("rise", "bridge"), [0.0, 1.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("rise", "crouch"), [0.0, 0.0, 1.0])


def test_onehot_zero_on_non_rise_mode_even_with_a_label():
    # A "flat"-shaped label on a non-rise mode string must never light
    # (the mode-family gate, not the label, decides eligibility).
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("walk", "flat"), [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("hold", "bridge"), [0.0, 0.0, 0.0])


def test_onehot_zero_on_unmatched_rise_start_kind():
    # Exotic rise starts (bank, plant, ...) never in the 3-way label
    # set -- all-zero (the RiseKindGru gate falls back to stance/core_b
    # for these, see gru_policy._gate5's known_rise subtraction).
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("rise", "bank"), [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_gate_onehot("rise", None), [0.0, 0.0, 0.0])


def _make_env(mode: str | None = None, *, gate: bool = True, seed: int = 0):
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    obs_cfg["mode_onehot"] = 1.0
    if gate:
        obs_cfg["rise_start_kind_gate"] = 1.0
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    if mode is not None:
        g = env._goal_gen
        for m in ALL_MODES:
            if hasattr(g, f"p_{m}"):
                setattr(g, f"p_{m}", 0.0)
        setattr(g, f"p_{mode}", 1.0)
    return env


def test_default_off_width_unchanged():
    on = _make_env("walk", gate=False)
    obs_on_off, _ = on.reset(seed=0)
    off = _make_env("walk", gate=False)
    # gate defaults off regardless of mode_onehot=1 -- same width as
    # mode_onehot alone.
    obs_off, _ = off.reset(seed=0)
    assert obs_on_off.shape == obs_off.shape


def test_gate_on_width_plus_three():
    base = _make_env("walk", gate=False)
    obs_base, _ = base.reset(seed=0)
    gated = _make_env("walk", gate=True)
    obs_gated, _ = gated.reset(seed=0)
    assert obs_gated.shape[0] == obs_base.shape[0] + N_RISE_KIND_OBS
    # Prefix identical; the 3 new cols sit immediately BEFORE the
    # existing 6-wide mode one-hot tail.
    np.testing.assert_allclose(
        obs_gated[:-(N_RISE_KIND_OBS + N_MODE_OBS)],
        obs_base[:-N_MODE_OBS])
    np.testing.assert_array_equal(
        obs_gated[-N_MODE_OBS:], obs_base[-N_MODE_OBS:])


@pytest.mark.parametrize("kind,expect", [
    ("flat", [1.0, 0.0, 0.0]),
    ("bridge", [0.0, 1.0, 0.0]),
    ("crouch", [0.0, 0.0, 1.0]),
])
def test_rise_tick_carries_real_start_kind(kind, expect):
    env = _make_env("rise", gate=True, seed=3)
    env._goal_gen.force_rise_start = kind
    obs, info = env.reset(seed=1001)
    assert info["goal_mode"] == "rise"
    tail_kind = obs[-(N_RISE_KIND_OBS + N_MODE_OBS):-N_MODE_OBS]
    np.testing.assert_array_equal(tail_kind, expect)
    want_mode = np.zeros(N_MODE_OBS)
    want_mode[MODE_ONEHOT_ORDER.index("rise")] = 1.0
    np.testing.assert_array_equal(obs[-N_MODE_OBS:], want_mode)
    # Constant across the episode (curriculum metadata, not a
    # measurement).
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(5):
        obs, _, term, trunc, _ = env.step(a)
        np.testing.assert_array_equal(
            obs[-(N_RISE_KIND_OBS + N_MODE_OBS):-N_MODE_OBS], expect)
        if term or trunc:
            break


@pytest.mark.parametrize("mode,fam", [
    ("hold", "hold"), ("lower", "lower"), ("walk", "walk"),
    ("quad", "quad"),
])
def test_non_rise_modes_have_zero_kind_gate(mode, fam):
    env = _make_env(mode, gate=True, seed=5)
    obs, info = env.reset(seed=0)
    assert info["goal_mode"] == mode
    tail_kind = obs[-(N_RISE_KIND_OBS + N_MODE_OBS):-N_MODE_OBS]
    np.testing.assert_array_equal(tail_kind, [0.0, 0.0, 0.0])
    want_mode = np.zeros(N_MODE_OBS)
    want_mode[MODE_ONEHOT_ORDER.index(fam)] = 1.0
    np.testing.assert_array_equal(obs[-N_MODE_OBS:], want_mode)
