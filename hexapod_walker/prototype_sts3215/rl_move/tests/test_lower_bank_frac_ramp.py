"""goal.lower_start_bank_frac_ramp_steps — LOWER-BANK-FRAC RAMP
(walkcurr entrybank020 SAC regression, 2026-09-24).

Background: `cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-
drramp-entrybank020-acq1` (both FAIL this cycle) transferred the
fixed-frac `goal.lower_start_bank_frac` + `goal.bank_qvel_restore`
mechanism -- already PASSed on both any_means MLP/GRU stand
architectures (CURRENT_TRUTHS.md 2026-09-23 ~21:3x) -- onto the
rl_only SAC lower role. Composed-session survival got dramatically
WORSE (0/12 and 3/12 direct/plant ok, vs a 6/12 and 5/6 baseline;
walkcurr/STATUS.md 2026-09-24 ~16:1x), and the mechanical seed-pruner
independently flagged both seeds regressing mid-run. The fixed-frac
bank draw fills SAC's off-policy replay buffer with hard bank-qvel
states from step 0, before the actor has learned the plain task at
all -- an on-policy PPO curriculum on the sibling architectures never
faced that exact exposure shape. This ramps `lower_start_bank_frac`
from a low/zero ramp-start value up to the cfg target over
`goal.lower_start_bank_frac_ramp_steps` global training steps -- the
same plain-ramp / env_method idiom `goal.rise_start_ramp_steps`
already uses.

Contract under test:
  - default OFF (`goal.lower_start_bank_frac_ramp_steps` unset/0):
    lower_start_bank_frac equals the legacy cfg value unconditionally,
    no new state changes behavior.
  - ON: at construction, lower_start_bank_frac equals the configured
    ramp-start value (default 0.0), not the target.
  - `set_lower_start_bank_frac(0.0)` reproduces the ramp start
    exactly; `set_lower_start_bank_frac(1.0)` reproduces the cfg
    target exactly; `set_lower_start_bank_frac(0.5)` is the exact
    midpoint.
  - frac is clamped to [0, 1].
  - calling `set_lower_start_bank_frac` while unarmed (ramp_steps<=0)
    raises RuntimeError -- a silent no-op broadcast is never a hidden
    failure mode.
  - `SimHexapodGoalEnv.apply_lower_start_bank_frac` forwards to the
    goal generator (the VecEnv env_method wiring).

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import GoalGenerator, SimHexapodGoalEnv


def test_default_off_bit_exact():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_frac_ramp_steps == 0
    assert gen.lower_start_bank_frac == pytest.approx(0.0)


def test_default_off_preserves_configured_frac():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_frac_ramp_steps == 0
    assert gen.lower_start_bank_frac == pytest.approx(0.20)


def test_armed_starts_at_ramp_start_value():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_frac_ramp_steps"] = 1_000_000
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_frac_ramp_steps == 1_000_000
    # Default ramp-start = 0.0 (no bank exposure at step 0).
    assert gen.lower_start_bank_frac == pytest.approx(0.0)
    assert gen._lower_start_bank_frac_target == pytest.approx(0.20)


def test_armed_custom_ramp_start_value():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_frac_ramp_steps"] = 1_000_000
    cfg["goal"]["lower_start_bank_frac_ramp_start"] = 0.05
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_frac == pytest.approx(0.05)


def test_set_lower_start_bank_frac_endpoints_and_midpoint():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_frac_ramp_steps"] = 1_000_000
    cfg["goal"]["lower_start_bank_frac_ramp_start"] = 0.0
    gen = GoalGenerator(cfg)

    r0 = gen.set_lower_start_bank_frac(0.0)
    assert r0["lower_start_bank_frac"] == pytest.approx(0.0)

    r1 = gen.set_lower_start_bank_frac(1.0)
    assert r1["lower_start_bank_frac"] == pytest.approx(0.20)

    rh = gen.set_lower_start_bank_frac(0.5)
    assert rh["lower_start_bank_frac"] == pytest.approx(0.10)

    # Clamped outside [0, 1].
    r_lo = gen.set_lower_start_bank_frac(-3.0)
    assert r_lo["frac"] == 0.0
    r_hi = gen.set_lower_start_bank_frac(5.0)
    assert r_hi["frac"] == 1.0


def test_unarmed_raises():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    with pytest.raises(RuntimeError):
        gen.set_lower_start_bank_frac(0.5)


def test_env_apply_lower_start_bank_frac_forwards():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_frac_ramp_steps"] = 500_000
    env = SimHexapodGoalEnv(cfg=cfg, seed=0)
    try:
        assert env._goal_gen.lower_start_bank_frac == pytest.approx(0.0)
        out = env.apply_lower_start_bank_frac(1.0)
        assert out["lower_start_bank_frac"] == pytest.approx(0.20)
        assert env._goal_gen.lower_start_bank_frac == pytest.approx(0.20)
    finally:
        env.close()
