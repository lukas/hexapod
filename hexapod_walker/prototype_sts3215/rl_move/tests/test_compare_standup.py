"""Stand-up IK must constrain the physical hinge as well as absolute links."""
import math

import pytest

from rl_move.sim.compare_standup import RealLegFK


@pytest.mark.parametrize('hip,tibia', [(-78, 148), (-100, -100), (40, 200), (20, 80)])
def test_solver_projection_respects_all_three_limits(hip, tibia):
    h, k = RealLegFK.project_angles(math.radians(hip), math.radians(tibia))
    assert RealLegFK.HIP_LO <= h <= RealLegFK.HIP_HI
    assert RealLegFK.KNEE_LO <= k <= RealLegFK.KNEE_HI
    assert RealLegFK.HINGE_LO - 1e-12 <= k - h <= RealLegFK.HINGE_HI + 1e-12


def test_projection_preserves_feasible_pose():
    q = (math.radians(20), math.radians(80))
    assert RealLegFK.project_angles(*q) == q
