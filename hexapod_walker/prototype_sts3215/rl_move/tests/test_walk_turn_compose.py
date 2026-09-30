"""Pure-function mechanics for eval_walk_turn_compose.py (walkcurr
Next item, 2026-09-30 role-composition tool). No MuJoCo/env/model --
schedule shape and gait-validity array math only, per RESEARCH_RULES
"Tests" (mechanics, not measurements; no rollout-ranking).
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.eval_walk_turn_compose import (
    _duty_swings, forward_schedule,
)


def test_forward_schedule_shape_and_total_time():
    sched = forward_schedule(0.06, 0.0)
    assert len(sched) == 3
    # settle (0 speed), hold (commanded vx/vy), stop (0 speed)
    assert sched[0][1] == 0.0 and sched[0][2] == 0.0
    assert sched[1][1] == 0.06 and sched[1][2] == 0.0
    assert sched[2][1] == 0.0 and sched[2][2] == 0.0
    assert sum(s for s, _, _ in sched) == 8.0  # 1.0 + 6.0 + 1.0


def test_forward_schedule_carries_nonzero_vy_for_off_axis_headings():
    sched = forward_schedule(0.04, -0.04)
    assert sched[1][1:] == (0.04, -0.04)


def test_duty_swings_all_planted_no_swings():
    contact = np.ones((50, 6), dtype=bool)
    duty, swings = _duty_swings(contact)
    assert np.allclose(duty, 1.0)
    assert swings == [0] * 6


def test_duty_swings_one_leg_airborne_whole_window():
    contact = np.ones((50, 6), dtype=bool)
    contact[:, 2] = False
    duty, swings = _duty_swings(contact)
    assert duty[2] == 0.0
    assert all(duty[f] == 1.0 for f in range(6) if f != 2)


def test_duty_swings_counts_touchdown_to_liftoff_transitions():
    # leg 0: planted, lifts once (contact->no-contact = one "swing"
    # start per _sacrificed_legs' own d==-1 convention), replants.
    contact = np.ones((20, 6), dtype=bool)
    contact[8:12, 0] = False
    duty, swings = _duty_swings(contact)
    assert swings[0] == 1
    assert 0.0 < duty[0] < 1.0
    assert all(swings[f] == 0 for f in range(1, 6))
