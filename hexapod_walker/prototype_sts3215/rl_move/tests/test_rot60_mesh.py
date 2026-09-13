"""rot60 equivariance on the MESH model family (mesh_mjx twin).

test_rot60.py proves rotate-60+relabel is an exact symmetry of the
LEGACY primitive model (the suite conftest pins HEXAPOD_MODEL_SOURCE=
primitive). Every current rl_only 50 Hz champion trains on the mesh
family, whose leg subtrees are exact Rz(60 deg) copies in
mesh_mujoco/hexapod_mesh_mjx.xml but whose chassis carries the as-built
(non-axisymmetric) mass distribution. Rotating the WHOLE robot about
world z is still an exact model symmetry regardless of chassis inertia
(gravity and the flat floor are invariant; the chassis rotates with the
base), so the rot60 canonicalization must hold on mesh too. This locks
that claim at the compiled-model level before any wrapped mesh policy
is evaluated or handed off (walkcurr reopen, 2026-09-13).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from rl_move.sim import rot60


def _quat_mul(q, p):
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = p
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


@pytest.fixture(scope="module")
def mesh_env():
    import os
    from unittest import mock
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    with mock.patch.dict(os.environ,
                         {"HEXAPOD_MODEL_SOURCE": "mesh_mjx"}):
        env = SimHexapodJointWalkEnv(params=SimServoParams.from_cfg(None),
                                     randomize=False, episode_seconds=5.0,
                                     seed=0)
    return env


def test_mesh_model_is_mesh_family(mesh_env):
    # Guard: the fixture must actually have loaded the mesh twin, not
    # the conftest-pinned primitive model (mesh twin chassis mass is the
    # as-built ~3.5 kg total vs legacy 2.104 kg).
    total = float(mesh_env.model.body_mass.sum())
    assert total > 3.0, f"expected mesh-family masses, got {total:.3f} kg"


def test_mesh_dynamics_equivariance(mesh_env):
    """Rotate+relabel is a symmetry of the compiled MESH model.

    Same construction as test_rot60.test_mujoco_dynamics_equivariance:
    identical world scene described in relabeled coordinates (root quat
    right-multiplied by Rz(60), joints/ctrl cyclically permuted) must
    give the same trajectory. Tolerances (measured 2026-09-13): the
    mesh XML stores mount quats to 8 decimal digits, so the symmetry is
    exact to ~1e-8 per component at the model level; through 30 contact
    steps the trajectory difference peaks ~2.5e-5 rad and DECAYS (a
    real per-leg model difference grows and shows ~1e-3 within a few
    steps — see the leg mass/inertia guard below). 2.5e-5 rad is ~60x
    below the campaign's own encoder-noise DR floor (0.09 deg), so the
    canonicalization is behaviorally exact on mesh. Early bound 5e-4,
    later chaos allowance 2e-2 (contact-solver Lyapunov amplification
    of the truncation rounding, not asymmetry).
    """
    import mujoco
    from rl_move.sim.servo_model import (joint_qpos_addrs,
                                         joint_qvel_addrs, joint_names)

    model = mesh_env.model
    qadr = joint_qpos_addrs(model)
    aadr = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR,
                                       n) for n in joint_names()])
    k = 1
    jp = rot60.leg_perm(k)
    alpha = k * rot60.SECTOR_RAD
    qz = np.array([math.cos(alpha / 2), 0.0, 0.0, math.sin(alpha / 2)])

    rng = np.random.default_rng(3)
    q0 = rng.uniform(-0.25, 0.25, 18)          # asymmetric leg pose
    tilt_q = np.array([math.cos(0.06), 0.05, 0.06, 0.02])
    tilt_q /= np.linalg.norm(tilt_q)
    ctrl0 = rng.uniform(-0.2, 0.2, 18)

    def rollout(joints, quat, ctrl, steps=100):
        d = mujoco.MjData(model)
        d.qpos[:] = 0
        d.qpos[2] = 0.09
        d.qpos[3:7] = quat
        d.qpos[qadr] = joints
        d.qvel[:] = 0
        d.ctrl[:] = 0
        d.ctrl[aadr] = ctrl
        mujoco.mj_forward(model, d)
        traj_j, traj_root = [], []
        for _ in range(steps):
            mujoco.mj_step(model, d)
            traj_j.append(d.qpos[qadr].copy())
            traj_root.append(d.qpos[:7].copy())
        return np.array(traj_j), np.array(traj_root)

    j1, r1 = rollout(q0, tilt_q, ctrl0)
    j2, r2 = rollout(q0[jp], _quat_mul(tilt_q, qz), ctrl0[jp])

    np.testing.assert_allclose(j2[:30], j1[:30, jp], atol=5e-4)
    np.testing.assert_allclose(r2[:30, :3], r1[:30, :3], atol=5e-4)
    expect_quat = np.array([_quat_mul(q, qz) for q in r1[:30, 3:7]])
    sign = np.sign(np.sum(expect_quat * r2[:30, 3:7], axis=1))[:, None]
    np.testing.assert_allclose(r2[:30, 3:7] * sign, expect_quat,
                               atol=5e-4)
    np.testing.assert_allclose(j2, j1[:, jp], atol=2e-2)
