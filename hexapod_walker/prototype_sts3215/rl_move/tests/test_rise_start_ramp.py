"""goal.rise_start_ramp_steps — RISE start-distribution RAMP
(walkcurr flat-start rise track, 2026-09-14).

Background: `cw-stance50hz-rlonly-curlslewgate-{mod,strict}-s1-
canary2m` (both CANARY FAIL - MECHANISM this cycle) closed the ENTIRE
cap-based action-gating family on the flat-start rise over_current
gap: 9 height-magnitude arms + 2 joint-rate doses, all null, because
suppressing the action space cannot fix WHICH SEQUENCE the policy
moves in (CURRENT_TRUTHS.md 2026-09-14 ~06:4x). The static 35/40/25
flat/partial/crouch reverse-curriculum mix (`goal.rise_flat_frac`/
`goal.rise_partial_frac`) has never varied over training time -- a
true flat start is drawn with equal probability at step 0 and step
100M alike. This block ramps the flat/partial split from a loose,
bridge/crouch-heavy start mix up to the cfg target mix over
`goal.rise_start_ramp_steps` global training steps -- the same plain-
ramp / env_method idiom `reward.term_penalty_ramp_steps` already uses.

Contract under test:
  - default OFF (`goal.rise_start_ramp_steps` unset/0): rise_flat_frac/
    rise_partial_frac equal the legacy cfg defaults (0.35/0.40)
    unconditionally, no new state changes behavior.
  - ON: at construction, rise_flat_frac/rise_partial_frac equal the
    configured LOOSE start values, not the target.
  - `set_rise_start_frac(0.0)` reproduces the loose start exactly;
    `set_rise_start_frac(1.0)` reproduces the cfg target exactly;
    `set_rise_start_frac(0.5)` is the exact midpoint.
  - frac is clamped to [0, 1].
  - calling `set_rise_start_frac` while unarmed (ramp_steps<=0) raises
    RuntimeError -- a silent no-op broadcast is never a hidden failure
    mode.
  - `SimHexapodGoalEnv.apply_rise_start_frac` forwards to the goal
    generator (the VecEnv env_method wiring).
  - out-of-range start fractions (flat_start + partial_start > 1) at
    construction raise ValueError.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import GoalGenerator, SimHexapodGoalEnv


def test_default_off_bit_exact_mix():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    assert gen.rise_start_ramp_steps == 0
    assert gen.rise_flat_frac == pytest.approx(0.35)
    assert gen.rise_partial_frac == pytest.approx(0.40)


def test_armed_starts_at_loose_mix():
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_start_ramp_steps"] = 1_000_000
    gen = GoalGenerator(cfg)
    assert gen.rise_start_ramp_steps == 1_000_000
    # Defaults: loose start = all bridge/crouch (0% flat, 60% partial).
    assert gen.rise_flat_frac == pytest.approx(0.0)
    assert gen.rise_partial_frac == pytest.approx(0.60)
    # Target is stashed from the legacy cfg values, unchanged.
    assert gen._rise_flat_frac_target == pytest.approx(0.35)
    assert gen._rise_partial_frac_target == pytest.approx(0.40)


def test_set_rise_start_frac_endpoints_and_midpoint():
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_start_ramp_steps"] = 1_000_000
    cfg["goal"]["rise_start_flat_frac_start"] = 0.1
    cfg["goal"]["rise_start_partial_frac_start"] = 0.5
    cfg["goal"]["rise_flat_frac"] = 0.3
    cfg["goal"]["rise_partial_frac"] = 0.4
    gen = GoalGenerator(cfg)

    r0 = gen.set_rise_start_frac(0.0)
    assert r0["flat_frac"] == pytest.approx(0.1)
    assert r0["partial_frac"] == pytest.approx(0.5)

    r1 = gen.set_rise_start_frac(1.0)
    assert r1["flat_frac"] == pytest.approx(0.3)
    assert r1["partial_frac"] == pytest.approx(0.4)

    rh = gen.set_rise_start_frac(0.5)
    assert rh["flat_frac"] == pytest.approx(0.2)
    assert rh["partial_frac"] == pytest.approx(0.45)

    # Clamped outside [0, 1].
    r_lo = gen.set_rise_start_frac(-3.0)
    assert r_lo["frac"] == 0.0
    r_hi = gen.set_rise_start_frac(5.0)
    assert r_hi["frac"] == 1.0


def test_unarmed_raises():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    with pytest.raises(RuntimeError):
        gen.set_rise_start_frac(0.5)


def test_bad_start_fracs_raise():
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_start_ramp_steps"] = 1_000_000
    cfg["goal"]["rise_start_flat_frac_start"] = 0.7
    cfg["goal"]["rise_start_partial_frac_start"] = 0.6
    with pytest.raises(ValueError):
        GoalGenerator(cfg)


def test_env_apply_rise_start_frac_forwards():
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_start_ramp_steps"] = 500_000
    cfg["goal"]["rise_start_flat_frac_start"] = 0.0
    cfg["goal"]["rise_start_partial_frac_start"] = 0.6
    env = SimHexapodGoalEnv(cfg=cfg, seed=0)
    try:
        assert env._goal_gen.rise_flat_frac == pytest.approx(0.0)
        out = env.apply_rise_start_frac(1.0)
        assert out["flat_frac"] == pytest.approx(0.35)
        assert env._goal_gen.rise_flat_frac == pytest.approx(0.35)
    finally:
        env.close()
