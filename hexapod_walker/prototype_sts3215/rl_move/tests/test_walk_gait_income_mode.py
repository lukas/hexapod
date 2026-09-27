"""Income-mode repricing of the per-leg gait charges (2026-09-27).

reward.walk_leg_swing_gap_income / reward.walk_leg_duty_ratio_income
flip the corresponding CHARGE into a bounded per-tick income with the
identical slope (term400-acq3 dig-in: a per-tick charge with no
episode cutoff makes early termination an escape hatch no bounded
one-time penalty can price away). Mechanics only, no rollouts.
"""
from types import SimpleNamespace

from rl_move.sim import walk_reward_gates


def _gap_env(charge=0.0, income=0.0, gaps=(0.0,) * 6,
             grace=3.0, cap=4.0):
    return SimpleNamespace(
        cfg={"reward": {
            "walk_leg_swing_gap_charge": charge,
            "walk_leg_swing_gap_income": income,
            "walk_leg_swing_gap_grace_s": grace,
            "walk_leg_swing_gap_cap_s": cap,
        }},
        _swing_gap_s=list(gaps),
    )


def test_swing_gap_income_off_is_bit_exact_charge():
    env = _gap_env(charge=10.0, income=0.0, gaps=[5.0] + [0.0] * 5)
    g, r = walk_reward_gates.leg_swinggap_charge(env, {}, s_ref=1.0)
    assert g == 10.0
    assert r == -10.0 * 2.0  # excess = 5 - 3 grace


def test_swing_gap_income_bounds_and_slope():
    info = {}
    # fresh swing (gap 0, under grace): full income = income * cap
    env = _gap_env(income=10.0)
    g, r = walk_reward_gates.leg_swinggap_charge(env, info, s_ref=1.0)
    assert g == 10.0 and r == 40.0
    # frozen past grace+cap: income floors at exactly 0, never negative
    env = _gap_env(income=10.0, gaps=[20.0] * 6)
    _, r0 = walk_reward_gates.leg_swinggap_charge(env, {}, s_ref=1.0)
    assert r0 == 0.0
    # identical slope to the charge: delta income == delta charge
    r_at = {}
    for gap in (4.0, 5.0):
        inc = _gap_env(income=10.0, gaps=[gap] + [0.0] * 5)
        chg = _gap_env(charge=10.0, gaps=[gap] + [0.0] * 5)
        _, r_at[("i", gap)] = walk_reward_gates.leg_swinggap_charge(
            inc, {}, s_ref=1.0)
        _, r_at[("c", gap)] = walk_reward_gates.leg_swinggap_charge(
            chg, {}, s_ref=1.0)
    assert (r_at[("i", 5.0)] - r_at[("i", 4.0)]
            == r_at[("c", 5.0)] - r_at[("c", 4.0)] == -10.0)


def test_swing_gap_both_gains_zero_inert():
    env = _gap_env()
    info = {}
    g, r = walk_reward_gates.leg_swinggap_charge(env, info, s_ref=1.0)
    assert g == 0.0 and r == 0.0 and info == {}


def _duty_env(charge=0.0, income=0.0, ema=(0.30,) * 6, ticks=1000,
              dt=0.02, target=0.30, grace=3.0):
    return SimpleNamespace(
        cfg={"reward": {
            "walk_leg_duty_ratio_charge": charge,
            "walk_leg_duty_ratio_income": income,
            "walk_leg_duty_ratio_target": target,
            "walk_leg_duty_ratio_grace_s": grace,
        }},
        _legduty_ratio_ema=list(ema),
        _legduty_ratio_ticks=ticks,
        dt=dt,
    )


def test_duty_ratio_income_bounds_grace_and_slope():
    # at-target legs: full income = income * target
    g, floor_, r = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(income=10.0), {}, s_ref=1.0)
    assert g == 10.0 and r == 3.0
    # fully unloaded worst leg (ratio 0): income exactly 0
    _, _, r0 = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(income=10.0, ema=[0.0] + [0.30] * 5), {}, s_ref=1.0)
    assert r0 == 0.0
    # grace not yet filled: no income at all
    _, _, rg = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(income=10.0, ticks=1), {}, s_ref=1.0)
    assert rg == 0.0
    # slope identical to charge mode
    _, _, r_c = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(charge=10.0, ema=[0.10] + [0.30] * 5), {}, s_ref=1.0)
    _, _, r_i = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(income=10.0, ema=[0.10] + [0.30] * 5), {}, s_ref=1.0)
    assert abs((r_i - 3.0) - r_c) < 1e-9


def test_duty_ratio_income_off_is_bit_exact_charge():
    from rl_move.sim.walk_task import walk_legduty_ratio_charge
    ema = [0.02] + [0.30] * 5
    shortfall, _ = walk_legduty_ratio_charge(ema, 0.30)
    assert shortfall > 0.0  # a genuinely starved leg
    _, _, r = walk_reward_gates.leg_duty_ratio_charge(
        _duty_env(charge=10.0, ema=ema), {}, s_ref=1.0)
    assert abs(r - (-10.0 * shortfall)) < 1e-9
