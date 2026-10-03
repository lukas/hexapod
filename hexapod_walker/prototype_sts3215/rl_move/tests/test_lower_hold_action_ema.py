"""actions.lower_hold_action_ema_alpha (2026-10-03, walkcurr lower-role
terminal-support forensics item 1g's architecture-redesign escalation).

Background: `lowerrole_terminal_support_forensics_2026-10-02/SUMMARY.md`
found the champion lower-role checkpoint's terminal (post-ramp HOLD)
per-leg support forces are NEARLY IDENTICAL in passing vs over_current-
failing episodes, and attributed the trip to fine-grained per-tick
control-noise/dwell variance around a narrow safety margin -- not to
which stance the policy picks. All 3 reward-term levers on this exact
failure are closed and that item's own gate text names the next lever
as structural ("a different observation/action parameterization for
the hold phase"), not another reward dose. This is that lever: an EMA
filter on the policy's OWN previously-applied action (no external/
scripted reference anywhere -- rl_only-clean), engaged only once a
`lower`-mode episode's height ref reaches its final target (the
post-ramp hold, every start-kind converges there with no new state).

Contract under test (mechanics only, no rollout/policy, no artifacts):
  - default (key absent) is bit-exact: applied action == raw action
    every tick, ramp and hold alike;
  - explicit alpha=0.0 is identical to the key being absent;
  - alpha>0, RAMP ticks (height ref not yet at the final target):
    untouched -- applied action == raw action;
  - alpha>0, HOLD ticks (height ref already at the final target):
    applied action == alpha*prev_applied + (1-alpha)*raw, exactly;
  - a `rise`-mode episode with alpha>0 set is completely unaffected
    (gate is `lower`-mode only) even once ITS height ref is flat at
    its own final (nonzero, positive) target.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _force_mode(env, mode: str) -> None:
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == mode else 0.0)


def _lower_env(seed: int, alpha: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg["goal"]["lower_ramp_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 4
    # NOTE: goal.lower_hold_s is NOT a configurable key (GoalGenerator
    # hardcodes 1.0s regardless of cfg) -- the entry-hold runs ~100
    # ticks at dt=0.01 before the (shortened) ramp even begins.
    if alpha is not None:
        cfg.setdefault("actions", {})["lower_hold_action_ema_alpha"] = alpha
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    _force_mode(env, "lower")
    env.debug_pipeline_record = True
    return env


def _rise_env(seed: int, alpha: float) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [60, 60]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 4
    cfg.setdefault("actions", {})["lower_hold_action_ema_alpha"] = alpha
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    _force_mode(env, "rise")
    env.debug_pipeline_record = True
    return env


def _oscillating_action(shape, i: int) -> np.ndarray:
    """A deliberately high-action-rate signal (full-swing square wave)
    so an EMA filter's effect is unmistakable tick to tick."""
    sign = 1.0 if (i % 2 == 0) else -1.0
    return np.full(shape, sign, dtype=np.float32)


def _run(env, n_steps):
    env.reset()
    shape = env.action_space.shape
    applied = []
    height_ref_mm = []
    for i in range(n_steps):
        action = _oscillating_action(shape, i)
        _, _, term, trunc, info = env.step(action)
        applied.append(np.asarray(env._dbg_applied_action, dtype=float)
                       .copy())
        height_ref_mm.append(float(info.get("height_ref_mm", 0.0)))
        if term or trunc:
            break
    env.close()
    return applied, height_ref_mm, shape


def _is_hold_tick(h_mm, target_mm, tol=1e-2):
    return abs(h_mm - target_mm) < tol


def test_default_absent_key_is_bit_exact_no_smoothing():
    env = _lower_env(seed=3, alpha=None)
    applied, _, shape = _run(env, 250)
    for i, a in enumerate(applied):
        expect = _oscillating_action(shape, i)
        assert np.allclose(a, expect, atol=1e-6)


def test_explicit_alpha_zero_matches_absent_key():
    env_absent = _lower_env(seed=3, alpha=None)
    applied_absent, _, shape_a = _run(env_absent, 250)
    env_zero = _lower_env(seed=3, alpha=0.0)
    applied_zero, _, shape_z = _run(env_zero, 250)
    assert len(applied_absent) == len(applied_zero)
    for a, b in zip(applied_absent, applied_zero):
        assert np.allclose(a, b, atol=1e-9)


def test_alpha_positive_ramp_ticks_untouched():
    env = _lower_env(seed=3, alpha=0.7)
    applied, height_ref_mm, shape = _run(env, 250)
    target_mm = height_ref_mm[-1]
    ramp_ticks = [i for i, h in enumerate(height_ref_mm)
                 if not _is_hold_tick(h, target_mm)]
    assert len(ramp_ticks) > 5, "need some genuine pre-hold ramp ticks"
    for i in ramp_ticks:
        expect = _oscillating_action(shape, i)
        assert np.allclose(applied[i], expect, atol=1e-6)


def test_alpha_positive_hold_ticks_are_ema_blended():
    alpha = 0.7
    env = _lower_env(seed=3, alpha=alpha)
    applied, height_ref_mm, shape = _run(env, 250)
    target_mm = height_ref_mm[-1]
    hold_ticks = [i for i, h in enumerate(height_ref_mm)
                 if _is_hold_tick(h, target_mm)]
    assert len(hold_ticks) > 10, "need a real hold window to test"
    # The info dict's height_ref_mm is read AFTER _step_i advances
    # (_step_finish), one tick later than the PRE-increment goal
    # lookup the gate itself reads inside _step_begin (same timing
    # the existing walk_residual_gate reference lookup uses) -- so the
    # very first tick whose REPORTED height_ref_mm reaches the target
    # is still gated on the prior (ramp) goal and is legitimately
    # unsmoothed. Verify blending from the second reported-hold tick
    # on, where gate and report agree.
    hold_ticks = hold_ticks[1:]
    assert len(hold_ticks) > 10, "need a real settled hold window"
    prev_applied = applied[hold_ticks[0] - 1]
    mismatches = 0
    for i in hold_ticks:
        raw = _oscillating_action(shape, i)
        expect = alpha * prev_applied + (1.0 - alpha) * raw
        if not np.allclose(applied[i], expect, atol=1e-5):
            mismatches += 1
        prev_applied = applied[i]
    assert mismatches == 0
    # And the smoothed signal must actually DIFFER from the raw
    # oscillating action during the hold (else the filter is a no-op).
    raw_hold = [_oscillating_action(shape, i) for i in hold_ticks]
    assert any(not np.allclose(applied[i], raw_hold[k], atol=1e-3)
              for k, i in enumerate(hold_ticks))


def test_rise_mode_untouched_even_once_flat_at_target():
    env = _rise_env(seed=3, alpha=0.7)
    applied, height_ref_mm, shape = _run(env, 120)
    target_mm = height_ref_mm[-1]
    flat_ticks = [i for i, h in enumerate(height_ref_mm)
                 if _is_hold_tick(h, target_mm)]
    assert len(flat_ticks) > 10, "need a real flat/hold window to test"
    for i in flat_ticks:
        expect = _oscillating_action(shape, i)
        assert np.allclose(applied[i], expect, atol=1e-6)


