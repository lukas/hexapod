"""Speed-track teacher gait-geometry doses (2026-09-11) — mechanics only.

Two mechanisms, both default-off/bit-exact:

1. ``TripodGait(period_scale=, lift_scale=, stride_scale=)`` ctor knobs
   (pre-existing) drive the scripted teacher's cycle time, swing apex
   and foot stroke — the speed track's feasibility-sweep axes
   (``probe_teacher_headings --period-scale/--lift-scale/--stride-scale``).
2. ``sim_env._make_walk_bc_gait`` reads
   ``train.bc_anchor_teacher_{period,lift,stride}_scale`` (default 1.0)
   so a discovery arm can anchor to the retuned geometry.

Pure stdlib for the gait half (same pattern as
test_tripod_gait_yaw_arm_scale.py); the cfg-plumb half calls the
unbound method with a stub — no MuJoCo, no env build, well under 5 s.
"""
from __future__ import annotations

from types import SimpleNamespace

from hexapod_core.tripod_gait import TripodGait


def _make(**kw):
    g = TripodGait(vx=0.0, **kw)
    g.sync_plant_stance(20.0, 100.0)
    g.reset_phase()
    return g


def _walk(g, vx=0.08):
    g.set_velocity(vx=vx, vy=0.0, omega=0.0)


def test_defaults_are_bit_exact_identity():
    ref = _make()
    dosed = _make(period_scale=1.0, lift_scale=1.0, stride_scale=1.0)
    _walk(ref)
    _walk(dosed)
    for t in (0.0, 0.05, 0.1, 0.37, 0.6, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_stride_scale_changes_walk_targets_not_stand():
    plain = _make()
    dosed = _make(stride_scale=1.4)
    # standing still (zero command): identical
    for t in (0.05, 0.4):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "stand"
    _walk(plain)
    _walk(dosed)
    diffs = [max(abs(a - b) for a, b in
                 zip(plain.desired_deg(t), dosed.desired_deg(t)))
             for t in (0.1, 0.3, 0.5, 0.7)]
    assert max(diffs) > 0.1, "stride_scale=1.4 must move walk targets"


def test_period_scale_changes_cycle_timing():
    plain = _make()
    dosed = _make(period_scale=1.5)
    _walk(plain)
    _walk(dosed)
    diffs = [max(abs(a - b) for a, b in
                 zip(plain.desired_deg(t), dosed.desired_deg(t)))
             for t in (0.2, 0.4, 0.6)]
    assert max(diffs) > 0.1, "period_scale=1.5 must shift the cycle"


def test_lift_scale_changes_swing_apex():
    plain = _make()
    dosed = _make(lift_scale=1.6)
    _walk(plain)
    _walk(dosed)
    diffs = [max(abs(a - b) for a, b in
                 zip(plain.desired_deg(t), dosed.desired_deg(t)))
             for t in (0.1, 0.2, 0.3, 0.5)]
    assert max(diffs) > 0.1, "lift_scale=1.6 must raise the swing"


def _stub_gait(cfg):
    """Call the real _make_walk_bc_gait against a cfg stub (no env)."""
    from rl_move.sim.sim_env import SimHexapodBalanceEnv
    # the method only touches self.cfg
    holder = SimpleNamespace(cfg=cfg)
    return SimHexapodBalanceEnv._make_walk_bc_gait(holder)


def test_cfg_default_is_identity_teacher():
    g = _stub_gait({})
    assert g.period_scale == 1.0
    assert g.stride_scale == 1.0
    assert g.lift_scale == [1.0] * 6


def test_cfg_doses_reach_the_teacher():
    g = _stub_gait({"train": {
        "bc_anchor_teacher_period_scale": 1.5,
        "bc_anchor_teacher_lift_scale": 1.3,
        "bc_anchor_teacher_stride_scale": 1.4,
    }})
    assert g.period_scale == 1.5
    assert g.stride_scale == 1.4
    assert g.lift_scale == [1.3] * 6
