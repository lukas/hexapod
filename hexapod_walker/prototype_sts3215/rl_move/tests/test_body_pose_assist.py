"""safety.body_pose_assist_* -- kinematic FALL-PROOF body-pose-assist
curriculum (2026-09-27, walkcurr walkyaw turn-in-place: the one
unscoped, structurally-new candidate left in OPERATOR_QUESTIONS
q_20260927T0828Z after every architecture/reward/action-box/RND lever
on the turn-in-place freeze closed).

Unlike every already-closed lever on this freeze (termination-cap
schedules, reward-price schedules), this changes the PHYSICS itself: a
restoring roll/pitch torque about the chassis, applied via xfrc_applied
exactly like the existing dr.walk_push_*/dr.ext_push_* disturbance
torques (opposite purpose -- assist, not disturb), gated/ramped like
reward.drag_stance_allow_ramp_steps (fades OUT over training instead of
tightening IN).

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF (gain 0.0, no ramp) is bit-exact: `_body_pose_assist_
  active` is False, `_body_pose_assist_torque_nm()` returns (0.0, 0.0),
  and `_advance()`'s chassis xfrc row is untouched by this mechanism;
- deadband: an error inside `body_pose_assist_deadband_frac *
  safety.max_roll/max_pitch` produces zero torque on that axis;
- beyond the deadband: torque OPPOSES the error sign and saturates at
  `body_pose_assist_max_nm`;
- the ramp (`safety.body_pose_assist_ramp_steps`) mirrors
  `apply_drag_allow_frac`'s contract exactly: raises when unarmed,
  sits at the TARGET (default 0 = fully unassisted) when armed but
  never broadcast, and linearly interpolates start->target on
  `apply_body_pose_assist_frac(frac)`;
- construction raises when the ramp start is below its target (the
  ramp may only ever FADE OUT the assist, never raise it);
- end-to-end: `_advance()` actually writes a nonzero corrective xfrc
  torque on the chassis when the mechanism is active and the error
  clears the deadband.
"""
import dataclasses
import math

import numpy as np
import pytest


def _walk_env(cfg=None, *, seed: int = 0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg=cfg or {}, randomize=True,
                                  dr_scale=0.0, seed=seed)
    env.reset(seed=seed)
    return env


# ---------------------------------------------------------------- default off

def test_default_off_is_inactive_and_torque_is_zero():
    env = _walk_env()
    try:
        assert env._body_pose_assist_active is False
        assert env._body_pose_assist_torque_nm() == (0.0, 0.0)
    finally:
        env.close()


def test_default_off_advance_leaves_chassis_torque_row_untouched():
    env = _walk_env()
    try:
        env._advance()
        Rp = env.data.xmat[env._chassis_bid].reshape(3, 3)
        expected = Rp[:, 0] * env._walk_push_torque_nm()
        np.testing.assert_allclose(
            env.data.xfrc_applied[env._chassis_bid, 3:6], expected)
    finally:
        env.close()


# -------------------------------------------------------------- pure function

def test_deadband_zeroes_a_small_error():
    cfg = {"safety": {"body_pose_assist_gain_nm_per_rad": 5.0,
                       "body_pose_assist_deadband_frac": 0.5,
                       "body_pose_assist_max_nm": 50.0}}
    env = _walk_env(cfg)
    try:
        assert env._body_pose_assist_active is True
        db_roll = 0.5 * env.safety.max_roll
        env._state = dataclasses.replace(
            env._state,
            imu_roll=env._tilt_ref0[0] + 0.5 * db_roll,   # inside deadband
            imu_pitch=env._tilt_ref0[1])
        roll_nm, pitch_nm = env._body_pose_assist_torque_nm()
        assert roll_nm == 0.0
        assert pitch_nm == 0.0
    finally:
        env.close()


def test_beyond_deadband_restores_and_saturates():
    cfg = {"safety": {"body_pose_assist_gain_nm_per_rad": 1000.0,
                       "body_pose_assist_deadband_frac": 0.1,
                       "body_pose_assist_max_nm": 4.0}}
    env = _walk_env(cfg)
    try:
        env._state = dataclasses.replace(
            env._state,
            imu_roll=env._tilt_ref0[0] + math.radians(30.0),
            imu_pitch=env._tilt_ref0[1] - math.radians(30.0))
        roll_nm, pitch_nm = env._body_pose_assist_torque_nm()
        # Positive roll error -> restoring (negative) torque; negative
        # pitch error -> restoring (positive) torque. Huge gain -> pins
        # the saturation cap.
        assert roll_nm == pytest.approx(-4.0)
        assert pitch_nm == pytest.approx(4.0)
    finally:
        env.close()


# ------------------------------------------------------------------ the ramp

def test_apply_frac_raises_when_ramp_not_armed():
    env = _walk_env({"safety": {"body_pose_assist_gain_nm_per_rad": 3.0}})
    try:
        with pytest.raises(RuntimeError, match="body_pose_assist_ramp"):
            env.apply_body_pose_assist_frac(0.5)
    finally:
        env.close()


def test_ramp_sits_at_target_when_unbroadcast_then_interpolates():
    cfg = {"safety": {"body_pose_assist_ramp_steps": 100,
                       "body_pose_assist_start_gain_nm_per_rad": 10.0,
                       "body_pose_assist_gain_nm_per_rad": 0.0}}
    env = _walk_env(cfg)
    try:
        # Armed-but-unbroadcast: TARGET (0 = fully unassisted), unlike
        # hold_grace/residual_blend's "sits at loose start" convention
        # -- an eval/play path that never broadcasts must see the
        # final, production-safe (unassisted) value.
        assert env._current_body_pose_assist_gain() == 0.0
        out0 = env.apply_body_pose_assist_frac(0.0)
        assert out0["gain_nm_per_rad"] == pytest.approx(10.0)
        out_mid = env.apply_body_pose_assist_frac(0.5)
        assert out_mid["gain_nm_per_rad"] == pytest.approx(5.0)
        out1 = env.apply_body_pose_assist_frac(1.0)
        assert out1["gain_nm_per_rad"] == pytest.approx(0.0)
    finally:
        env.close()


def test_construction_raises_when_start_below_target():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"safety": {"body_pose_assist_ramp_steps": 10,
                       "body_pose_assist_start_gain_nm_per_rad": 1.0,
                       "body_pose_assist_gain_nm_per_rad": 5.0}}
    with pytest.raises(ValueError, match="body_pose_assist_start"):
        SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=0.0, seed=0)


# --------------------------------------------------------------- end-to-end

def test_advance_writes_a_nonzero_restoring_torque_when_active():
    cfg = {"safety": {"body_pose_assist_gain_nm_per_rad": 6.0,
                       "body_pose_assist_deadband_frac": 0.1,
                       "body_pose_assist_max_nm": 50.0}}
    env = _walk_env(cfg)
    try:
        env._state = dataclasses.replace(
            env._state,
            imu_roll=env._tilt_ref0[0] + math.radians(25.0),
            imu_pitch=env._tilt_ref0[1])
        roll_nm, pitch_nm = env._body_pose_assist_torque_nm()
        assert roll_nm != 0.0
        env._advance()
        torque_row = env.data.xfrc_applied[env._chassis_bid, 3:6]
        assert np.linalg.norm(torque_row) > 0.0
    finally:
        env.close()
