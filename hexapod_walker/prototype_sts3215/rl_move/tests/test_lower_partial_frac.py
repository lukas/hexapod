"""LOWER mid-descent reverse-curriculum (goal.lower_partial_frac/
_min_frac/_max_frac, 2026-09-13, lowerheavy-s0/s1 FAIL-MECHANISM
follow-up: both seeds parked lower's end height ~-6mm above plant
despite lower=0.6 exposure and fresh std -- a learned-habit wall, not
a reachability limit). Mechanics-only, no rollout/policy.

Contract:
  - default (frac=0) is legacy: every non-belly LOWER episode starts
    at the plant (start_at="plant", crouch_dz=0) and ramps height
    0 -> target exactly as before;
  - frac=1 always starts crouched at a fraction (in
    [min_frac, max_frac]) of THAT EPISODE's own target depth, with
    the height ref at reset matching the crouch depth exactly (no
    tracking-error jump), then ramping the remaining distance to the
    same target;
  - the belly-start branch (lower_belly_start_frac) is untouched by
    this lever.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.goal_task import GoalGenerator

DT = 0.01
N_STEPS = 2000


def _gen(frac: float = 0.0):
    cfg = {"goal": {"p_lower": 1.0, "lower_partial_frac": frac}}
    return GoalGenerator(cfg)


def test_default_off_is_legacy_plant_start():
    gen = _gen(frac=0.0)
    for seed in range(30):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "plant"
        assert traj.crouch_dz == 0.0
        assert traj.height[0] == 0.0
        assert traj.height[-1] < 0.0, "lower target must be below plant"


def test_frac_one_always_crouches_inside_band_no_jump():
    gen = _gen(frac=1.0)
    for seed in range(60):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "crouch"
        target = traj.height[-1]
        assert target < 0.0
        depth = -target
        assert 0.29 * depth <= traj.crouch_dz <= 0.81 * depth, (
            f"seed {seed}: crouch_dz {traj.crouch_dz*1000:.2f}mm "
            f"outside the configured 0.3-0.8x{depth*1000:.1f}mm band")
        # no tracking-error jump: ref at reset matches the crouch depth
        assert abs(traj.height[0] - (-traj.crouch_dz)) < 1e-9
        # still descends further from the partial start to the target
        assert traj.height[0] > traj.height[-1]


def test_partial_frac_only_sometimes_crouches():
    gen = _gen(frac=0.5)
    kinds = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        kinds.append(traj.start_at)
    frac_crouch = kinds.count("crouch") / len(kinds)
    assert 0.35 < frac_crouch < 0.65, (
        f"observed crouch frac {frac_crouch:.2f} far from configured 0.5")
    assert set(kinds) == {"plant", "crouch"}


def test_belly_start_untouched_by_partial_lever():
    cfg = {"goal": {"p_lower": 1.0, "lower_belly_start_frac": 1.0,
                    "lower_partial_frac": 1.0}}
    gen = GoalGenerator(cfg)
    for seed in range(10):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "zero"
        assert np.all(traj.height == 0.0)
