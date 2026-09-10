"""Stand/lower routing: an upright robot must never be sent through safe_zero.

2026-09-10 (hexapod2): after RL or scripted walks one hip routinely rested
26-45 deg from walk-ready while the robot was standing. The old 25/35 deg
per-joint limits classified that as a recovery pose, and safe_zero's first
stage straightened loaded legs outward, dropping the chassis onto its
belly (nine times, on video). These tests pin the new behaviour:
upright-but-off is "standing"; belly-zero and folded-under are not; a
folded-under pose is recognised so the untrap fold runs before safe_zero.
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
