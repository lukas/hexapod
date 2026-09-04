"""TripodGait.combined_yaw_amplify_scale unit tests (standwalk Next
item 2, candidate (iii), 09-04) -- pure stdlib, no mujoco/env
dependency.

See hexapod_core/tripod_gait.py's __init__ docstring for the full
derivation: unlike ``combined_yaw_arm_scale`` (uniform, all 6 legs),
this dose only touches legs where the vx cross term AMPLIFIES the
true combined tangential foot velocity past that leg's own
pure-omega-only magnitude; the other legs must stay bit-exact.

REFUTED (09-04, same cycle it was built): these tests pin the
MECHANICS (selective per-leg scaling behaves as designed), but
``test_probe_turn_authority.py::
test_yaw_amplify_scale_desaturates_clip_but_REGRESSES_real_wz`` shows
the dose that "works" here (fully de-saturates the commanded-yaw-rate
clip proxy) makes the REAL scripted-teacher body wz WORSE, not
better. Do not wire this into BC-anchor training or spend an RL
canary on it -- kept only as a documented, bit-exact-off negative
result, like the codebase's other refuted dose knobs.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hexapod_core.tripod_gait import TripodGait  # noqa: E402


def _make(amplify_scale=1.0):
    g = TripodGait(vx=0.0, combined_yaw_amplify_scale=amplify_scale)
    g.sync_plant_stance(20.0, 100.0)
    g.reset_phase()
    return g


def test_default_is_bit_exact_identity():
    ref = _make(1.0)
    dosed = TripodGait(vx=0.0)
    dosed.sync_plant_stance(20.0, 100.0)
    dosed.reset_phase()
    ref.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    for t in (0.0, 0.05, 0.1, 0.37, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_pure_turn_and_pure_walk_bit_exact_regardless_of_dose():
    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.0, omega=0.25)
    dosed.set_velocity(vx=0.0, omega=0.25)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-turn"

    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.06, omega=0.0)
    dosed.set_velocity(vx=0.06, omega=0.0)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-walk"


def test_selective_dose_leaves_some_legs_bit_exact_on_combined_tick():
    """The whole point vs. the uniform yaw_arm_scale lever: at least
    one leg (an ATTENUATED one, per the derivation) must be untouched
    on a combined tick, while at least one (an AMPLIFIED one) diverges
    -- a fully uniform lever would diverge on every leg."""
    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_same = saw_diff = False
    for t in (0.05, 0.3, 0.7, 1.5, 2.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        for leg in range(6):
            yaw_i, hip_i, knee_i = 3 * leg, 3 * leg + 1, 3 * leg + 2
            # hip/knee (foot placement/lift) must never move.
            assert abs(a[hip_i] - b[hip_i]) < 1e-9, "hip changed"
            assert abs(a[knee_i] - b[knee_i]) < 1e-9, "knee changed"
            if abs(a[yaw_i] - b[yaw_i]) < 1e-9:
                saw_same = True
            else:
                saw_diff = True
    assert saw_same, "expected >=1 leg untouched (attenuated legs)"
    assert saw_diff, "expected >=1 leg to diverge (amplified legs)"


def test_amplified_legs_shrink_toward_pure_turn_magnitude():
    """A leg whose combined |yaw| exceeds the pure-turn magnitude
    should shrink toward (not away from) that pure-turn magnitude as
    the dose increases -- the mechanism's actual purpose."""
    turn_only = _make(1.0)
    turn_only.set_velocity(vx=0.0, omega=0.25)
    pure_turn_yaw = turn_only.desired_deg(0.3)

    combined_ref = _make(1.0)
    combined_ref.set_velocity(vx=0.08, omega=0.25)
    combined_yaw = combined_ref.desired_deg(0.3)
    # find a leg genuinely amplified past its pure-turn magnitude at
    # this command (per the derivation, e.g. leg 4 / angle 270deg).
    amplified_leg = next(
        i for i in range(6)
        if abs(combined_yaw[3 * i]) > abs(pure_turn_yaw[3 * i]) + 1e-6)

    doses = (1.0, 1.5, 2.0, 3.0)
    yaws = []
    for d in doses:
        g = _make(d)
        g.set_velocity(vx=0.08, omega=0.25)
        yaws.append(g.desired_deg(0.3)[3 * amplified_leg])
    # magnitude should be non-increasing as dose grows (monotone
    # shrink toward the pure-turn reference) for the amplified leg.
    mags = [abs(y) for y in yaws]
    assert mags == sorted(mags, reverse=True), mags
    assert mags[-1] < mags[0]


def test_full_desaturation_at_dose_3_all_six_legs():
    """probe_leg_yaw_rate.py's own zero-training finding, pinned as a
    regression test: at vx=0.08/omega=0.25, dose=3.0 applied only to
    the amplified legs brings the per-tick yaw-command rate of ALL SIX
    legs under the 37.5deg/s (0.375deg @ 100Hz) SafetyLayer clip,
    where the unscaled baseline leaves 3/6 legs over it."""
    from rl_move.sim.probe_leg_yaw_rate import sample, CLIP_DEG_PER_S

    baseline = sample(vx_cmd=0.08, omega_cmd=0.25, seconds=3.0)
    n_over_base = sum(1 for v in baseline.values()
                       if v["max_rate_deg_s"] > CLIP_DEG_PER_S)
    assert n_over_base >= 1, "baseline should reproduce the known 3/6 finding"

    dosed = sample(vx_cmd=0.08, omega_cmd=0.25, seconds=3.0,
                    amplify_scale=3.0)
    n_over_dosed = sum(1 for v in dosed.values()
                        if v["max_rate_deg_s"] > CLIP_DEG_PER_S)
    assert n_over_dosed == 0, dosed
