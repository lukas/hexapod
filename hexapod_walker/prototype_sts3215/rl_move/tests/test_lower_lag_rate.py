"""LOWER ramp-tracking LAG-RATE charge (reward.k_lower_lag_rate,
walkcurr track, 2026-09-17).

Background (CURRENT_TRUTHS.md 09-17 ~04:1x; STATUS.md same date):
thirteen closed mechanism arms across four classes -- reward-pricing
(score-prog/ratchet-partial/dense-posture/plain-stage-gate, 4),
batch-composition (1), stage-gate frac_min (4), absorbing-state
termination (4) -- all leave `lower` parked at the identical
~28-31mm/0-2-of-12-ok floor. Every one of those levers prices the
accumulated POSITION gap (a one-time ratchet on best depth reached,
a continuous charge on the REMAINING fraction, a termination keyed on
"no improvement for N seconds"). None prices the instantaneous RATE
mismatch against the ramp's own current velocity -- a policy that
never starts moving pays only the same diffuse, quadratic-in-mm
position penalty every other lever already left it able to afford.

`reward.k_lower_lag_rate` adds `reward_lower_lag_rate`: every tick the
ramp reference is actively moving (nonzero tick-to-tick
`goal.height_ref` delta), charge `-k * max(0, |ref_vel| - actual_vel
projected onto the ramp's own direction)` -- i.e. exactly how much
slower than the commanded rate the robot is currently falling behind,
floored at zero (never a bonus for outrunning the ramp). Lower
episodes only (`env._h_target < 0`); RISE/HOLD/TRACK/WALK are
untouched even when the key is on.

Contract under test:
  - default OFF (`reward.k_lower_lag_rate` unset) never exposes
    `reward_lower_lag_rate` -- bit-exact legacy path.
  - ON, frozen policy (zero action) during a lower episode: the charge
    fires (negative) on ticks where the ramp is actively moving, and
    is exactly zero/absent on hold-phase ticks (ramp not yet started,
    `ref_vel == 0`).
  - dose scaling: doubling `k_lower_lag_rate` doubles the lifetime
    charge for the identical frozen rollout (same seed/action) --
    confirms the term is a plain linear price on the measured
    shortfall, not accidentally coupled to any other ratchet/gate.

RESEARCH_RULES "Tests": fast, mechanics + one short wired-env
integration check, no rollout ranking, no artifacts, mesh model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _lower_env(seed: int, k_lag: float = 0.0) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_height_mm"] = [40, 40]
    cfg["goal"]["lower_hold_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 7
    if k_lag:
        cfg.setdefault("reward", {})["k_lower_lag_rate"] = k_lag
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "lower" else 0.0)
    return env


def _run(env, n_steps, action):
    env.reset()
    out = []
    for _ in range(n_steps):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    return out


def test_default_off_never_exposes_the_new_key():
    env = _lower_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 350, action)
    env.close()
    assert not any("reward_lower_lag_rate" in i for i in infos)
    assert any("reward_rise_progress" in i for i in infos), \
        "test setup never entered a lower episode with a real target"


def test_gate_on_frozen_policy_charged_only_while_ramp_moves():
    env = _lower_env(seed=1, k_lag=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 350, action)
    env.close()
    charged = [i for i in infos if "reward_lower_lag_rate" in i]
    assert charged, "k_lower_lag_rate gate never fired"
    # frozen body -> actual_vel ~ 0, so every charged tick is strictly
    # negative (the ramp is by construction moving whenever the key
    # fires -- ref_vel==0 ticks never populate the key at all).
    assert all(i["reward_lower_lag_rate"] < 0.0 for i in charged)
    # hold-phase ticks (before the ramp starts) never carry the key.
    hold_ticks = len(infos) - len(charged)
    assert hold_ticks > 0, \
        "test setup's hold window never produced a pre-ramp tick"


def test_dose_scaling_is_linear_in_k():
    env1 = _lower_env(seed=1, k_lag=1.0)
    action = np.zeros(env1.action_space.shape, dtype=np.float32)
    infos1 = _run(env1, 350, action)
    env1.close()
    env2 = _lower_env(seed=1, k_lag=2.0)
    infos2 = _run(env2, 350, action)
    env2.close()
    total1 = sum(i.get("reward_lower_lag_rate", 0.0) for i in infos1)
    total2 = sum(i.get("reward_lower_lag_rate", 0.0) for i in infos2)
    assert total1 < 0.0
    assert total2 == pytest.approx(2.0 * total1, rel=1e-6)
