"""HOLD start-state reverse-curriculum jitter (goal.hold_start_jitter_
frac/_mm, 2026-09-13, DESIGN_NOTE_2026-09-13_rot60_fullgait_stance.md
Mechanism B gate's next lever). Mechanics-only, no rollout/policy.

Contract:
  - default (frac=0) is bit-exact legacy: no extra rng draw, every
    HOLD episode starts at the plant (start_at="plant", crouch_dz=0)
    with height flat at 0;
  - frac=1 always draws a crouch start inside the configured mm band,
    height stays flat 0 (the target is unchanged -- only the START
    pose moves);
  - the crouch_dz draw stays inside actions.max_height_mm even when
    the configured band would otherwise exceed it.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.goal_task import GoalGenerator

DT = 0.01
N_STEPS = 1500


def _gen(frac: float = 0.0, mm=(5.0, 30.0), max_height_mm: float = 88.0):
    cfg = {"goal": {"p_hold": 1.0, "hold_start_jitter_frac": frac,
                    "hold_start_jitter_mm": list(mm)},
          "actions": {"max_height_mm": max_height_mm}}
    return GoalGenerator(cfg)


def test_default_off_is_bit_exact_plant():
    gen = _gen(frac=0.0)
    for seed in range(10):
        rng = np.random.default_rng(seed)
        rng_ref = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="hold")
        assert traj.start_at == "plant"
        assert traj.crouch_dz == 0.0
        assert np.all(traj.height == 0.0)
        # zero extra draw: rng consumption matches a generator with
        # the feature fully absent (rng advances identically).
        gen_off = _gen(frac=0.0)
        traj_ref = gen_off.sample(rng_ref, N_STEPS, DT, force_mode="hold")
        assert rng.random() == rng_ref.random(), (
            "frac=0 must not consume any extra rng draws")


def test_frac_one_always_jitters_inside_band():
    gen = _gen(frac=1.0, mm=(5.0, 30.0))
    for seed in range(40):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="hold")
        assert traj.start_at == "crouch"
        assert 0.0049 <= traj.crouch_dz <= 0.0301, (
            f"seed {seed}: crouch_dz {traj.crouch_dz*1000:.2f}mm "
            "outside the configured 5-30mm band")
        # target (height ref) is untouched: still flat at 0 throughout.
        assert np.all(traj.height == 0.0)


def test_band_clipped_to_max_height_mm():
    gen = _gen(frac=1.0, mm=(5.0, 200.0), max_height_mm=40.0)
    for seed in range(20):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="hold")
        assert traj.crouch_dz <= 0.0400001, (
            f"seed {seed}: crouch_dz {traj.crouch_dz*1000:.2f}mm "
            "exceeded actions.max_height_mm")


def test_partial_frac_only_sometimes_jitters():
    gen = _gen(frac=0.5, mm=(5.0, 30.0))
    kinds = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="hold")
        kinds.append(traj.start_at)
    frac_crouch = kinds.count("crouch") / len(kinds)
    assert 0.35 < frac_crouch < 0.65, (
        f"observed crouch frac {frac_crouch:.2f} far from configured 0.5")
    assert set(kinds) == {"plant", "crouch"}
