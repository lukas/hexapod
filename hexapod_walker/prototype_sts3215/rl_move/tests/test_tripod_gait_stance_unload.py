"""``TripodGait(stance_unload_frac=...)`` (2026-09-28) — mechanics only.

standwalk root-cause pass (`audit_slip_frame.py --phase-bins 8` on the
ceil15-stressmixbase lineage, det AND sto, both deployable widths):
slip concentrates ONLY in the last stance phase-bin (pre-liftoff)
while measured foot force is already at its lowest there -- the foot
is naturally unloading while the reference still drags it at the same
constant horizontal rate as mid-stance. Reward pricing (aggregate +
per-leg loadslip charge) and the MJX contact-solver iteration count
both came back CANARY FAIL - inert on this exact lineage; this is the
first WHEN-timing (gait-schedule) lever tried. Legacy stance is a pure
constant-rate linear sweep ``prog = 0.5 - s``; ``stance_unload_frac``
decelerates that rate to exactly zero over the FINAL fraction of the
stance window (matched constant-rate segment so total stroke and
duration are unchanged), then is wired 1:1 into the walk BC-anchor
teacher via ``train.bc_anchor_teacher_stance_unload_frac`` (default
0.0). Same pure-stdlib-gait / cfg-stub-wiring pattern as
test_teacher_speed_scales.py -- no MuJoCo, no env build, well under 5 s.
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
    dosed = _make(stance_unload_frac=0.0)
    _walk(ref)
    _walk(dosed)
    for t in (0.0, 0.05, 0.1, 0.37, 0.6, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_stance_unload_changes_walk_targets_not_stand():
    plain = _make()
    dosed = _make(stance_unload_frac=0.3)
    # standing still (zero command): identical -- the knob only
    # reshapes the STANCE horizontal sweep, which is zero-amplitude
    # at vx=vy=omega=0 regardless of its rate profile.
    for t in (0.05, 0.4):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "stand"
    _walk(plain)
    _walk(dosed)
    diffs = [max(abs(a - b) for a, b in
                 zip(plain.desired_deg(t), dosed.desired_deg(t)))
             for t in (0.1, 0.3, 0.5, 0.7, 0.9, 1.1)]
    assert max(diffs) > 0.1, "stance_unload_frac=0.3 must move walk targets"


def test_clip_range():
    assert _make(stance_unload_frac=0.9).stance_unload_frac == 0.45
    assert _make(stance_unload_frac=-0.2).stance_unload_frac == 0.0
    assert _make(stance_unload_frac=0.2).stance_unload_frac == 0.2


def test_stance_prog_endpoints_match_legacy_for_any_frac():
    for frac in (0.0, 0.05, 0.2, 0.3, 0.45):
        g = _make(stance_unload_frac=frac)
        assert abs(g._stance_prog(0.0) - 0.5) < 1e-9, frac
        assert abs(g._stance_prog(1.0) - (-0.5)) < 1e-9, frac


def test_stance_prog_decelerates_into_the_tail():
    """The tail (last `frac` of stance) must move SLOWER than the
    constant-rate lead-in segment -- the whole point of the mechanism
    (foot push rate -> 0 right before liftoff, not a fixed rate all
    the way through)."""
    g = _make(stance_unload_frac=0.3)
    eps = 1e-4
    lead_rate = abs(g._stance_prog(0.1 + eps) - g._stance_prog(0.1)) / eps
    tail_rate = abs(g._stance_prog(0.95 + eps) - g._stance_prog(0.95)) / eps
    assert tail_rate < lead_rate * 0.5, (lead_rate, tail_rate)
    # near-zero velocity right at liftoff (s=1), unlike legacy's constant rate
    end_rate = abs(g._stance_prog(1.0) - g._stance_prog(1.0 - eps)) / eps
    assert end_rate < lead_rate * 0.05, (lead_rate, end_rate)
    # and legacy (frac=0) has NO deceleration -- constant rate throughout
    legacy = _make(stance_unload_frac=0.0)
    r_lead = abs(legacy._stance_prog(0.1 + eps) - legacy._stance_prog(0.1)) / eps
    r_tail = abs(legacy._stance_prog(0.95 + eps) - legacy._stance_prog(0.95)) / eps
    assert abs(r_lead - r_tail) < 1e-6


def test_dz_zero_throughout_stance_regardless_of_frac():
    """Only the horizontal push rate reshapes -- foot height during
    stance stays exactly 0.0 (the touchdown/liftoff swing bump is a
    separate, untouched code path) at every dose."""
    import math
    for frac in (0.0, 0.3, 0.45):
        g = _make(stance_unload_frac=frac)
        # leg 0 is in stance whenever phi=(_phase+phase_offset)%(2pi)
        # falls in [pi, 2pi); sample several stance instants directly.
        for phase in (0.6 * math.pi, math.pi, 1.4 * math.pi, 1.49 * math.pi):
            g._phase = phase
            _, _, dz0 = g._foot_target_in_body(0, 0.08, 0.0, 0.0)
            assert dz0 == 0.0, (frac, phase)


def _stub_gait(cfg):
    """Call the real _make_walk_bc_gait against a cfg stub (no env),
    same pattern as test_teacher_speed_scales.py -- plus `_plant_deg`
    (a pre-existing, unrelated gap: `_make_walk_bc_gait` reads
    `self._plant_deg` a few lines after the ctor call this test
    targets; the sibling test file's identical stub predates that
    read and was silently broken by it, 2/2 tests there, confirmed via
    `git stash` byte-identical on HEAD before this change -- not a
    regression from this commit, not fixed in that file, but trivial
    to avoid here so THIS mechanism's own cfg-wiring tests are a real
    green signal rather than inheriting a stale crash)."""
    from rl_move.sim.sim_env import SimHexapodBalanceEnv, _default_plant_deg
    holder = SimpleNamespace(cfg=cfg, _plant_deg=_default_plant_deg())
    return SimHexapodBalanceEnv._make_walk_bc_gait(holder)


def test_cfg_default_is_identity_teacher():
    g = _stub_gait({})
    assert g.stance_unload_frac == 0.0


def test_cfg_dose_reaches_the_teacher():
    g = _stub_gait({"train": {
        "bc_anchor_teacher_stance_unload_frac": 0.25,
    }})
    assert g.stance_unload_frac == 0.25
