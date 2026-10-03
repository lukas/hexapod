"""goal.lower_hold_only_frac (2026-10-02, walkcurr lower-role terminal-
support forensics item 1's first named-but-unbuilt lever): HOLD-PHASE-
ONLY curriculum -- with probability f a (non-belly) lower episode skips
the descent ramp entirely and starts ALREADY at the full target depth,
height ref flat at target for the whole episode, giving concentrated
practice on exactly the sustained post-ramp HOLD sub-skill the
forensics doc found converges to a fixed, universal 2-leg (L2+L5)
high-current prop. Mechanics-only, no rollout/policy -- mirrors
test_lower_partial_frac.py's contract shape.

Contract:
  - default (frac=0) is legacy: unaffected by this key's presence at
    all (it is read via getattr with a 0.0 default, so an absent key
    behaves identically to frac=0);
  - frac=1 always starts crouched AT the full target depth (no
    intermediate ramp segment: height ref is flat at target from tick
    0), with the crouch depth exactly matching -target (no
    tracking-error jump);
  - mutually exclusive with lower_partial_frac/lower_start_bank (this
    episode's branch is decided first);
  - the belly-start branch (lower_belly_start_frac) is untouched.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.goal_task import GoalGenerator

DT = 0.01
N_STEPS = 2000


def _gen(frac: float = 0.0, **extra):
    goal = {"p_lower": 1.0, "lower_hold_only_frac": frac}
    goal.update(extra)
    return GoalGenerator({"goal": goal})


def test_default_off_is_legacy_ramp_then_hold():
    gen = _gen(frac=0.0)
    for seed in range(30):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "plant"
        assert traj.crouch_dz == 0.0
        assert traj.height[0] == 0.0
        assert traj.height[-1] < 0.0


def test_absent_key_matches_frac_zero():
    """A lineage that never sets the key at all (plain getattr default)
    must behave identically to an explicit frac=0.0 -- same contract as
    every other optional GoalGenerator curriculum knob."""
    gen_absent = GoalGenerator({"goal": {"p_lower": 1.0}})
    gen_zero = _gen(frac=0.0)
    for seed in range(20):
        t_a = gen_absent.sample(np.random.default_rng(seed), N_STEPS, DT,
                                force_mode="lower")
        t_b = gen_zero.sample(np.random.default_rng(seed), N_STEPS, DT,
                              force_mode="lower")
        assert t_a.start_at == t_b.start_at
        assert np.array_equal(t_a.height, t_b.height)


def test_frac_one_starts_flat_at_full_target_depth():
    gen = _gen(frac=1.0)
    for seed in range(60):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "crouch"
        target = traj.height[-1]
        assert target < 0.0
        # flat height ref at target for the WHOLE episode -- no ramp
        assert np.all(traj.height == target)
        assert abs(traj.crouch_dz - (-target)) < 1e-9


def test_partial_frac_only_sometimes_hold_only():
    gen = _gen(frac=0.5)
    kinds = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        # hold-only episodes are flat; ramped episodes descend
        kinds.append(bool(np.all(traj.height == traj.height[-1])))
    frac_hold_only = sum(kinds) / len(kinds)
    assert 0.35 < frac_hold_only < 0.65, (
        f"observed hold-only frac {frac_hold_only:.2f} far from 0.5")


def test_belly_start_untouched_by_hold_only_lever():
    gen = _gen(frac=1.0, lower_belly_start_frac=1.0)
    for seed in range(10):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "zero"
        assert np.all(traj.height == 0.0)


def test_mutually_exclusive_with_lower_partial():
    """When both fracs are 1.0, hold_only wins (decided first) -- the
    episode starts at FULL depth flat, not a partial-depth ramp."""
    gen = _gen(frac=1.0, lower_partial_frac=1.0)
    for seed in range(20):
        rng = np.random.default_rng(seed)
        traj = gen.sample(rng, N_STEPS, DT, force_mode="lower")
        assert traj.start_at == "crouch"
        assert np.all(traj.height == traj.height[-1]), (
            "hold_only must win over lower_partial when both fire")
