"""Stand/lower routing: an upright robot must never be sent through safe_zero.

2026-09-10 (hexapod2): after RL or scripted walks one hip routinely rested
26-45 deg from walk-ready while the robot was standing. The old 25/35 deg
per-joint limits classified that as a recovery pose, and safe_zero's first
stage straightened loaded legs outward, dropping the chassis onto its
belly (nine times, on video). These tests pin the new behaviour:
upright-but-off is "standing"; belly-zero and folded-under are not; a
folded-under pose is recognised so the untrap fold runs before safe_zero.

2026-09-11 addendum: the fold shape (hips negative, knees > 90) is ALSO what
a level robot standing tall on vertical tibias looks like after a hand
reposition or an RL hold. Folding that robot dropped it, then safe_zero's
loaded blend lifted and dropped it again (video). ``_stand_route_decision``
now needs tip/untrap evidence before folding and sends a level, tall,
unrecognised stance through the walk-ready glide instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent, HERE.parent / "motor_setup"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from api.demos import DemosApi          # noqa: E402
from api.standup import StandupApi      # noqa: E402
from api.zero import ZeroApi            # noqa: E402


class _Router(DemosApi, StandupApi, ZeroApi):
    """Just the mixins; no bus, no drive."""


def _pose(yaw=0.0, hip=20.0, knee=80.0):
    return [yaw, hip, knee] * 6


def test_walk_ready_is_standing():
    r = _Router()
    v = r._normal_standing_pose(_pose())
    assert v and v["kind"] == "sim_walk_start"


def test_post_walk_stance_with_one_hip_far_off_is_still_standing():
    # The exact shape that used to drop the robot: five legs near walk-ready,
    # one hip 45 deg off, small yaw offsets.
    q = _pose(yaw=3.0, hip=17.0, knee=82.0)
    q[3 * 3 + 1] = -25.0        # L3 hip 45 deg from the 20 deg reference
    v = _Router()._normal_standing_pose(q)
    assert v is not None
    assert v["max_delta_deg"] >= 40.0


def test_belly_zero_is_not_standing():
    assert _Router()._normal_standing_pose(_pose(hip=0.0, knee=0.0)) is None


def test_folded_under_leg_is_not_standing():
    q = _pose()
    q[0 * 3 + 1] = -36.0        # L0 hip swung negative
    q[0 * 3 + 2] = 118.0        # L0 knee folded under the chassis
    assert _Router()._normal_standing_pose(q) is None


def test_tilted_body_is_not_standing():
    assert _Router()._normal_standing_pose(_pose(), tilt_deg=25.0) is None


def test_folded_under_signature():
    tucked = [0.0, -36.0, 118.0, 0.0, -25.0, 106.0, 0.0, -16.0, 85.0,
              0.0, -28.0, 87.0, 0.0, -34.0, 95.0, 0.0, -28.0, 118.0]
    assert ZeroApi._folded_under_signature(tucked)
    assert not ZeroApi._folded_under_signature(_pose())
    assert not ZeroApi._folded_under_signature(_pose(hip=0.0, knee=0.0))


# ---------------------------------------------------------------------------
# _stand_route_decision (pure)
# ---------------------------------------------------------------------------

TUCK = [0.0, -25.0, 115.0] * 6           # 09-11 tuck / high-knee shape
TALL_HIGH_KNEE = [0.0, -10.0, 100.0] * 6
BELLY_ONE_KNEE = _pose(hip=0.0, knee=0.0)
BELLY_ONE_KNEE[4 * 3 + 2] = 55.0


def _route(q, **kw):
    kw.setdefault("tilt_deg", 1.5)
    kw.setdefault("pinned", False)
    kw.setdefault("fold_recent", False)
    return ZeroApi._stand_route_decision(q, **kw)[0]


def test_level_fold_shape_without_evidence_is_a_glide_not_a_fold():
    # The 19:01 case: level, standing tall, joint medians look folded.
    assert _route(TUCK) == "glide"
    assert _route(TALL_HIGH_KNEE) == "glide"


def test_fold_shape_with_tip_evidence_folds():
    assert _route(TUCK, tilt_deg=14.0, pinned=True) == "fold"


def test_fold_shape_after_our_own_untrap_folds():
    assert _route(TUCK, fold_recent=True) == "fold"


def test_fold_shape_without_imu_keeps_legacy_fold():
    assert _route(TUCK, tilt_deg=None) == "fold"


def test_tilted_fold_shape_folds():
    assert _route(TUCK, tilt_deg=16.0) == "fold"


def test_belly_pose_with_one_folded_knee_goes_to_safe_zero():
    assert _route(BELLY_ONE_KNEE) == "safe_zero"
    assert _route(_pose(hip=0.0, knee=0.0)) == "safe_zero"


def test_level_plant_stand_unrecognised_glides():
    # hip 19 / knee 28 is a real (low) stand: feet ~60 mm below the belly
    # plane. If the classifier ever rejects it, it must glide, not blend.
    assert _route(_pose(hip=19.0, knee=28.0)) == "glide"


def test_low_post_walk_crouch_glides_instead_of_dropping():
    # 2026-09-11 20:18:50Z: median foot 53 mm below the hip pivot after the
    # RL-only walk; the old rule routed it to safe_zero (drop) + STEP (10x rise).
    crouch = _pose(hip=19.0, knee=10.0)      # foot z ~ -55 mm
    assert _route(crouch, tilt_deg=3.0) == "glide"
    # Belly-down (feet on the plane) still goes to the planner.
    assert _route(_pose(hip=0.0, knee=7.0)) == "safe_zero"
