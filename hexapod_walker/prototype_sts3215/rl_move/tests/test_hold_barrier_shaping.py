"""reward.hold_barrier_gain — steepening BARRIER penalty on approach to
the active HOLD-mode termination bound (``sim_env.hold_barrier_penalty``).

2026-09-13, walkcurr track: the ``holdgrace`` gated-tightening-curriculum
canary pair (both seeds) closed the "termination-grace curriculum" lever
named as the next escalation after 5/5 static-cfg-dose hold-from-scratch
levers failed (STATUS.md 09-13 ~17:5x/~18:0x/~18:0x-holdgrace) — the
competence gate itself engaged fine in both seeds (survived_frac cleared
0.4 by ~131k/2M steps) but once the envelope tightened to its validated
15mm/0.5s target both seeds still rode it straight to hold_low_height
every remaining episode (0/6 survived at 2M, fwd med 0.00-0.01m
throughout). Per the 08-21 ruling ("reward is misaligned -> fix the
reward"), this adds a divergent barrier term so the marginal cost of
approaching the cliff rises faster than the existing flat quadratic
reward_height term, instead of another static-dose/curriculum-shape
retry.

Contract under test (mechanics only, no training spend, no mujoco):
  - default (reward.hold_barrier_gain absent/0) is bit-exact OFF: 0.0
    regardless of h_err/bound;
  - no active bound (hold_max_drop_mm<=0) -> 0.0 even with gain>0;
  - monotonically more negative as |h_err| approaches the bound;
  - DIVERGES near the bound: penalty at 99% of the bound is far more
    than 4x the penalty at 50% of the bound (the whole point vs a
    plain quadratic, which would only be ~4x at that ratio);
  - symmetric in the sign of h_err (only |h_err| matters);
  - clamps at the >= bound edge (drop_frac capped at 0.999, finite).
"""
from __future__ import annotations

from rl_move.sim.sim_env import hold_barrier_penalty


def test_default_off_zero_gain():
    assert hold_barrier_penalty(0.010, 15.0, 0.0) == 0.0
    assert hold_barrier_penalty(0.0149, 15.0, 0.0) == 0.0


def test_no_active_bound_is_zero():
    assert hold_barrier_penalty(0.010, 0.0, 5.0) == 0.0
    assert hold_barrier_penalty(0.010, -1.0, 5.0) == 0.0


def test_zero_error_is_zero_penalty():
    assert hold_barrier_penalty(0.0, 15.0, 5.0) == 0.0


def test_monotonic_toward_bound():
    gain = 5.0
    bound_mm = 15.0
    p25 = hold_barrier_penalty(0.25 * bound_mm * 0.001, bound_mm, gain)
    p50 = hold_barrier_penalty(0.50 * bound_mm * 0.001, bound_mm, gain)
    p90 = hold_barrier_penalty(0.90 * bound_mm * 0.001, bound_mm, gain)
    p99 = hold_barrier_penalty(0.99 * bound_mm * 0.001, bound_mm, gain)
    assert 0.0 > p25 > p50 > p90 > p99


def test_diverges_faster_than_quadratic_near_bound():
    gain = 1.0
    bound_mm = 15.0
    p50 = hold_barrier_penalty(0.50 * bound_mm * 0.001, bound_mm, gain)
    p99 = hold_barrier_penalty(0.99 * bound_mm * 0.001, bound_mm, gain)
    # A plain quadratic (-k*x^2) would give p99/p50 == (0.99/0.50)^2
    # ~= 3.92. This barrier's whole point is to blow up far faster than
    # that near the cliff.
    assert abs(p99) / abs(p50) > 20.0


def test_symmetric_in_sign():
    bound_mm = 15.0
    gain = 3.0
    pos = hold_barrier_penalty(0.010, bound_mm, gain)
    neg = hold_barrier_penalty(-0.010, bound_mm, gain)
    assert pos == neg


def test_clamped_finite_at_or_past_bound():
    bound_mm = 15.0
    gain = 2.0
    at_bound = hold_barrier_penalty(bound_mm * 0.001, bound_mm, gain)
    past_bound = hold_barrier_penalty(2.0 * bound_mm * 0.001, bound_mm, gain)
    assert at_bound == past_bound  # both clamp to the same 0.999 cap
    import math
    assert math.isfinite(at_bound)
