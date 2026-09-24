"""goal.lower_start_bank_delay_steps — LOWER-BANK REPLAY-BUFFER HARD
CUTOFF (walkcurr entrybank020 SAC regression, ramp follow-up,
2026-09-24).

Background: `cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-
drramp-entrybank020-acq1` (both FAIL) transferred the fixed-frac
`goal.lower_start_bank_frac` + `goal.bank_qvel_restore` mechanism onto
the rl_only SAC lower role and regressed composed-session survival
dramatically. A follow-up GRADUAL ramp of the same frac
(`goal.lower_start_bank_frac_ramp_steps`, closed+removed 2026-09-24
~19:2x) only partially helped one seed (s0 PARTIAL) and did nothing for
the other (s1 FAIL) -- the STATUS entry's own diagnosis: any nonzero
bank-draw probability from step 0 already lets SAC's off-policy replay
buffer accumulate some hard bank-qvel transitions before the actor has
learned the plain lower task, and a ramp still does exactly that (just
fewer of them). This implements that same entry's own named "next
untried lever": a HARD cutoff instead of a probability ramp. Bank draws
are pinned at EXACTLY ZERO for `goal.lower_start_bank_delay_steps`
global training steps (the replay buffer holds ZERO bank-origin
transitions during the delay, not merely few), then the gate opens and
`lower_start_bank_frac` jumps DIRECTLY to the configured target in one
step (no further ramping).

Contract under test:
  - default OFF (`goal.lower_start_bank_delay_steps` unset/0):
    lower_start_bank_frac equals the legacy cfg value unconditionally,
    no new state, no new rng draws.
  - ON: at construction, lower_start_bank_frac is pinned at 0.0 (gate
    closed) regardless of the configured target.
  - `set_lower_start_bank_gate_open(True)` jumps DIRECTLY to the cfg
    target (no intermediate values); `set_lower_start_bank_gate_open
    (False)` returns to exactly 0.0.
  - calling `set_lower_start_bank_gate_open` while unarmed
    (delay_steps<=0) raises RuntimeError -- a silent no-op broadcast is
    never a hidden failure mode.
  - `SimHexapodGoalEnv.apply_lower_start_bank_gate` forwards to the
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
    assert gen.lower_start_bank_delay_steps == 0
    assert gen.lower_start_bank_gate_open is True
    assert gen.lower_start_bank_frac == pytest.approx(0.0)


def test_default_off_preserves_configured_frac():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_delay_steps == 0
    assert gen.lower_start_bank_gate_open is True
    assert gen.lower_start_bank_frac == pytest.approx(0.20)


def test_armed_starts_gate_closed_at_zero():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_delay_steps"] = 1_000_000
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_delay_steps == 1_000_000
    assert gen.lower_start_bank_gate_open is False
    assert gen.lower_start_bank_frac == pytest.approx(0.0)
    assert gen._lower_start_bank_frac_target == pytest.approx(0.20)


def test_gate_open_jumps_directly_to_target():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_delay_steps"] = 1_000_000
    gen = GoalGenerator(cfg)

    out = gen.set_lower_start_bank_gate_open(True)
    assert out["open"] is True
    assert out["lower_start_bank_frac"] == pytest.approx(0.20)
    assert gen.lower_start_bank_frac == pytest.approx(0.20)
    # No intermediate value is ever produced by this mechanism.
    assert gen.lower_start_bank_frac in (
        pytest.approx(0.0), pytest.approx(0.20))


def test_gate_close_returns_to_zero():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_delay_steps"] = 1_000_000
    gen = GoalGenerator(cfg)
    gen.set_lower_start_bank_gate_open(True)
    assert gen.lower_start_bank_frac == pytest.approx(0.20)

    out = gen.set_lower_start_bank_gate_open(False)
    assert out["open"] is False
    assert out["lower_start_bank_frac"] == pytest.approx(0.0)
    assert gen.lower_start_bank_frac == pytest.approx(0.0)


def test_unarmed_raises():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    with pytest.raises(RuntimeError):
        gen.set_lower_start_bank_gate_open(True)


def test_armed_zero_target_frac_is_a_noop_either_way():
    # Delay armed but the cfg target frac itself is 0.0 (no bank
    # configured/used) -- opening the gate should still work mechanics-
    # wise and just produce 0.0 either way.
    cfg = load_config()
    cfg["goal"]["lower_start_bank_delay_steps"] = 500_000
    gen = GoalGenerator(cfg)
    assert gen.lower_start_bank_frac == pytest.approx(0.0)
    out = gen.set_lower_start_bank_gate_open(True)
    assert out["lower_start_bank_frac"] == pytest.approx(0.0)


def test_env_apply_lower_start_bank_gate_forwards():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.20
    cfg["goal"]["lower_start_bank_delay_steps"] = 500_000
    env = SimHexapodGoalEnv(cfg=cfg, seed=0)
    try:
        assert env._goal_gen.lower_start_bank_frac == pytest.approx(0.0)
        out = env.apply_lower_start_bank_gate(True)
        assert out["lower_start_bank_frac"] == pytest.approx(0.20)
        assert env._goal_gen.lower_start_bank_frac == pytest.approx(0.20)
        out2 = env.apply_lower_start_bank_gate(False)
        assert out2["lower_start_bank_frac"] == pytest.approx(0.0)
        assert env._goal_gen.lower_start_bank_frac == pytest.approx(0.0)
    finally:
        env.close()


def test_default_off_no_new_attribute_surprise():
    # Bit-exact-off contract: the target-tracking attribute exists
    # (harmless bookkeeping) but gate state/frac are untouched from
    # legacy behavior when the delay is not configured.
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_start_bank_frac"] = 0.0
    gen = GoalGenerator(cfg)
    assert gen._lower_start_bank_frac_target == pytest.approx(0.0)
    assert gen.lower_start_bank_gate_open is True
