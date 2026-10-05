"""safety.max_current_ramp_steps — trainer-driven current-margin ramp.

2026-10-05, walkcurr lower-role L2+L5 terminal-support over_current
habit (see SafetyLayer.__init__ for the full mechanism/why): every
reward-pricing (k_current_hot/k_load_even/k_stance_count), observation
(obs.current_sense), trajectory (lower_ramp_s/lower_hold_only_frac/
term-bank), action-space (lower_hold_action_ema_alpha) and
architecture (recurrent SAC) lever against this exact failure is
closed. Per the terminal-support forensics
(lowerrole_terminal_support_forensics_2026-10-02), the converged 2-leg
stance's per-leg force magnitudes are IDENTICAL in passing vs
over_current-failing episodes -- the trip is fine-grained per-tick
control-noise/dwell variance around a narrow safety margin, not a bad
stance choice. This mechanism anneals the over-current TERMINATION
threshold itself from a wide training-start value down to the real
hardware limit, trainer-driven, mirroring env.dr_stage_ramp_steps'
construction exactly (cfg-armed, default OFF = bit-exact legacy).

Contract under test:
  - default (keys absent/0) is bit-exact OFF: max_current stays
    max_current_a forever, apply raises;
  - ARMED env sits at the wide max_current_ramp_a start until broadcast;
  - frac interpolates linearly from ramp_a (frac 0) to max_current_a
    (frac 1), clamped outside [0, 1];
  - a ramp that does not start wider than the target raises at
    construction (SafetyLayer and the env both);
  - the live threshold actually changes what check_servo_health trips
    on (termination-behavior verification, not just stored state).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.robot_state import RobotState, N_JOINTS
from rl_move.safety import SafetyLayer
from rl_move.sim.servo_model import SimServoParams

ARM = {("safety", "max_current_ramp_a"): 5.0,
       ("safety", "max_current_ramp_steps"): 1_000_000}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=True, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def _state_with_current(j: int, amps: float) -> RobotState:
    cur = np.zeros(N_JOINTS, dtype=float)
    cur[j] = amps
    return RobotState(
        timestamp=0.0,
        joint_position=np.zeros(N_JOINTS, dtype=float),
        joint_velocity=np.zeros(N_JOINTS, dtype=float),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3, dtype=float),
        imu_accel=np.zeros(3, dtype=float),
        commanded_position=np.zeros(N_JOINTS, dtype=float),
        servo_current=cur)


def test_default_off_bit_exact_and_apply_raises():
    env = _env()
    assert env.safety.max_current == pytest.approx(2.5)
    assert env.safety._max_current_ramp_steps <= 0
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_current_margin_frac(0.5)
    env.close()


def test_armed_unbroadcast_sits_at_wide_start():
    env = _env(ARM)
    assert env.safety.max_current == pytest.approx(5.0)
    env.close()


def test_frac_interpolates_and_clamps():
    env = _env(ARM)
    env.apply_current_margin_frac(0.0)
    assert env.safety.max_current == pytest.approx(5.0)
    env.apply_current_margin_frac(0.5)
    assert env.safety.max_current == pytest.approx(3.75)
    env.apply_current_margin_frac(1.0)
    assert env.safety.max_current == pytest.approx(2.5)
    # Overshoot clamps both directions.
    env.apply_current_margin_frac(2.0)
    assert env.safety.max_current == pytest.approx(2.5)
    env.apply_current_margin_frac(-1.0)
    assert env.safety.max_current == pytest.approx(5.0)
    env.close()


def test_ramp_a_must_exceed_target():
    with pytest.raises(ValueError, match="max_current_ramp_a"):
        _env({("safety", "max_current_ramp_a"): 2.0,
              ("safety", "max_current_ramp_steps"): 1_000_000})
    with pytest.raises(ValueError, match="max_current_ramp_a"):
        SafetyLayer(_cfg({("safety", "max_current_ramp_a"): 2.5,
                          ("safety", "max_current_ramp_steps"): 100}))


def test_margin_actually_changes_trip_behavior():
    """The live threshold must change what check_servo_health trips
    on, not just the stored attribute."""
    safety = SafetyLayer(_cfg(ARM))
    safety.set_health_sample_hz(50.0)
    safety._over_current_trip_ticks = 1  # trip on the first over-tick
    j = 2
    state = _state_with_current(j, 4.0)   # between 2.5A and 5.0A
    safety.set_current_margin_frac(0.0)   # wide: 5.0A, 4.0A does NOT trip
    status = safety.check_servo_health(state)
    assert status is None or status.terminate is False
    safety._over_current_ticks = 0
    safety.set_current_margin_frac(1.0)   # narrow: 2.5A, 4.0A DOES trip
    status = safety.check_servo_health(state)
    assert status is not None and status.terminate is True
    assert status.reason == "over_current"
