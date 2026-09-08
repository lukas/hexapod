"""Keep action-probe kinematics in the deployed robot-absolute contract."""
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

mujoco = pytest.importorskip("mujoco")

from rl_move.sim.probe_action_clip import LegJac, tracking_lag_med_deg


@pytest.mark.parametrize("pose_deg", [(5, 20, 75), (-10, -15, 110), (15, 30, 45)])
def test_foot_jacobian_matches_analytic_absolute_joint_columns(pose_deg):
    """A hip-only logical correction must preserve absolute tibia angle."""
    jac = LegJac(ROOT / "mesh_mujoco" / "hexapod_mesh_mjx.xml")
    q_abs = np.tile(np.deg2rad(pose_deg), 6)
    q_rel = q_abs.copy()
    q_rel[2::3] -= q_rel[1::3]
    actual = jac(q_rel)
    jac._fk(q_rel)
    mujoco.mj_forward(jac.m, jac.d)
    for leg, sid in enumerate(jac.sids):
        jp = np.zeros((3, jac.m.nv))
        jr = np.zeros_like(jp)
        mujoco.mj_jacSite(jac.m, jac.d, jp, jr, sid)
        # Independent analytic reference: dq_rel = [dyaw, dhip,
        # dknee_abs - dhip]. The old probe omitted the subtraction.
        hinge_cols = jp[:, 6 + 3 * leg:9 + 3 * leg]
        expected = hinge_cols.copy()
        expected[:, 1] -= hinge_cols[:, 2]
        np.testing.assert_allclose(actual[leg], expected, atol=1e-8, rtol=1e-6)
        assert np.linalg.norm(expected[:, 1] - hinge_cols[:, 1]) > 0.01


def test_tracking_error_compares_absolute_targets_to_absolute_measurements():
    qpos = np.zeros((3, 25))
    qpos[:, 3] = 1.0
    measured_abs = np.tile(np.deg2rad([5, 25, 90]), (3, 6))
    qpos[:, 7:25] = measured_abs
    qpos[:, 9:25:3] -= measured_abs[:, 1::3]
    # Use the knee columns to ensure the median cannot hide a frame error.
    command = measured_abs.copy()
    command[:, 0::3] += np.deg2rad(2)
    command[:, 1::3] += np.deg2rad(4)
    assert tracking_lag_med_deg(qpos, command) == pytest.approx(2.0)
    assert tracking_lag_med_deg(qpos, measured_abs) == pytest.approx(0.0)
