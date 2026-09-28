"""Fast, mechanics-only tests for eval_checkpoint._sacrificed_legs and
its gait_valid_relaxed_hold branch (2026-09-28, walkcurr yaw-offset
canary triage -- see the function's own docstring).

Pure function over hand-built duty/swing arrays -- no sim rollout, no
randomization, no artifacts, no GPU. Per RESEARCH_RULES "Tests": under
5s, mechanics only, no rollout-ranking bank.
"""
from rl_move.sim.eval_checkpoint import _sacrificed_legs


def _duty(*vals):
    assert len(vals) == 6
    return list(vals)


def test_default_flags_parked_unloaded_leg():
    # leg 4 essentially always airborne (duty<0.10) -> sacrificed either way.
    duty = _duty(0.5, 0.5, 0.5, 0.5, 0.05, 0.5)
    swings = [3, 3, 3, 3, 0, 3]
    assert _sacrificed_legs(duty, swings) == [4]
    assert _sacrificed_legs(duty, swings, gait_valid_relaxed_hold=True) == [4]


def test_default_flags_dragged_anchor_but_relaxed_hold_does_not():
    # leg 2 grounded the whole run (duty>0.95) with zero swings: a
    # dragged anchor under the default rule, but a legitimate
    # converged-hold stance under the relaxed rule.
    duty = _duty(0.5, 0.5, 0.98, 0.5, 0.5, 0.5)
    swings = [3, 3, 0, 3, 3, 3]
    assert _sacrificed_legs(duty, swings) == [2]
    assert _sacrificed_legs(duty, swings, gait_valid_relaxed_hold=True) == []


def test_relaxed_hold_still_catches_unloaded_leg_alongside_a_held_stance():
    # a converged hold (legs 0-4 grounded/no-swing) plus one genuinely
    # unloaded leg (5, duty<0.10) -- relaxed mode still flags leg 5.
    duty = _duty(0.97, 0.97, 0.97, 0.97, 0.97, 0.03)
    swings = [0, 0, 0, 0, 0, 0]
    assert _sacrificed_legs(duty, swings) == [0, 1, 2, 3, 4, 5]
    assert _sacrificed_legs(duty, swings, gait_valid_relaxed_hold=True) == [5]


def test_lift_legs_excluded_from_both_modes():
    # quadwalk-style commanded-lifted legs are never counted, in
    # either mode, regardless of their own duty/swing pattern.
    duty = _duty(0.02, 0.5, 0.5, 0.5, 0.5, 0.98)
    swings = [0, 3, 3, 3, 3, 0]
    assert _sacrificed_legs(duty, swings, lift=(0, 5)) == []
    assert _sacrificed_legs(duty, swings, lift=(0, 5),
                             gait_valid_relaxed_hold=True) == []


def test_normal_cycling_gait_is_never_flagged_either_mode():
    duty = _duty(0.55, 0.6, 0.5, 0.58, 0.52, 0.61)
    swings = [4, 4, 4, 4, 4, 4]
    assert _sacrificed_legs(duty, swings) == []
    assert _sacrificed_legs(duty, swings, gait_valid_relaxed_hold=True) == []
