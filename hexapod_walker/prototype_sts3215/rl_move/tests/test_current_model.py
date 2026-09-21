"""Servo-current model + preserved over-current stall trip (2026-09-19).

sim_env now DEFAULTS to the validated mechanical-power current model
(``bus.current_model="power"``): per-joint current = iq/18 + k*|torque*qvel|
(iq_bus=0.19 A, k=0.02282 A/W), 0.1 s low-pass. Because a ~345:1
non-backdrivable gearbox holds a static load at ~0 current, this reads ~0
A while HOLDING *and* while STALLING (both are low-speed). To keep the
SafetyLayer over-current stall trip alive, _read_state also publishes a
SEPARATE stall-sensitive ``over_current_signal`` from the legacy torque
proxy min(|torque|*1.2, 3.0); the trip (and trip-proximity reward shaping)
read that. Legacy ``bus.current_model="torque_proxy"`` reproduces the old
behavior bit-exactly (servo_current = the proxy, no separate trip signal).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.robot_state import RobotState, over_current_reading
from rl_move.safety import SafetyLayer
from rl_move.sim.sim_env import SimHexapodBalanceEnv

IQ_BUS = 0.19
IQ_JOINT = IQ_BUS / 18.0
K_POWER = 0.02282


def _mkenv(model):
    cfg = load_config()
    cfg.setdefault("bus", {})["current_model"] = model
    env = SimHexapodBalanceEnv(cfg=cfg, seed=1)
    env.reset()
    return env


def _set_joint(env, j, torque, qvel):
    env.data.qfrc_actuator[env._vadr] = 0.0
    env.data.qvel[env._vadr] = 0.0
    env.data.qfrc_actuator[env._vadr[j]] = torque
    env.data.qvel[env._vadr[j]] = qvel
    env._cur_filt = None
    env._trip_cur_filt = None


def test_power_model_current_value():
    """servo_current tracks mechanical power; trip signal tracks the proxy."""
    env = _mkenv("power")
    j = 2
    _set_joint(env, j, torque=1.0, qvel=3.0)  # 3 W mechanical
    st = env._read_state()
    assert st.servo_current[j] == pytest.approx(IQ_JOINT + K_POWER * 3.0)
    # idle joints read just the bus idle share
    assert st.servo_current[(j + 1) % 18] == pytest.approx(IQ_JOINT)
    # separate stall-sensitive trip signal = legacy proxy
    assert st.over_current_signal is not None
    assert st.over_current_signal[j] == pytest.approx(min(1.0 * 1.2, 3.0))
    # trip-proximity consumers pick the signal
    assert np.allclose(over_current_reading(st), st.over_current_signal)


# Winding/load-stall term shipped in config.yaml by the 2026-09-21
# reality-gap refit (claude/sim-refit): current += K_STALL*relu(|tau|-THR).
K_STALL = 0.042
STALL_THR = 1.2


def test_gravity_hold_below_thr_reads_idle():
    """A gentle gravity-hold (|torque| < STALL_THR, ~0 speed) still reads
    just the bus idle share — the winding term is gated above the free-hold
    torque rail so idle/stance stays ~0.19 A bus and the validated
    scripted-gait fit is untouched."""
    env = _mkenv("power")
    j = 5
    _set_joint(env, j, torque=0.8, qvel=0.0)  # below the STALL_THR rail
    st = env._read_state()
    assert st.servo_current[j] == pytest.approx(IQ_JOINT, abs=1e-6)


def test_stall_current_elevated_by_winding_term_but_trip_still_fires():
    """POST-REFIT: a stall (high torque, ~0 speed) reads ~0 W of mechanical
    power, so the pure power model read ~0 A — the winding/load-stall term
    now lifts the reported current to K_STALL*(|tau|-STALL_THR) above idle so
    the reward SEES stall load, while staying far below the 2.5 A trip. The
    stall trip itself still rides the SEPARATE torque-proxy signal (2.64 A)."""
    env = _mkenv("power")
    j = 5
    _set_joint(env, j, torque=2.2, qvel=0.0)  # rail torque, no motion
    st = env._read_state()
    expected = IQ_JOINT + K_STALL * (2.2 - STALL_THR)
    assert st.servo_current[j] == pytest.approx(expected, abs=1e-6)
    assert expected > IQ_JOINT  # winding term is load-bearing (not ~0)
    assert st.servo_current.max() < 0.5  # nowhere near the 2.5 A trip
    # the SEPARATE stall trip signal is unchanged (legacy proxy, railed)
    assert st.over_current_signal[j] == pytest.approx(min(2.2 * 1.2, 3.0))


def test_winding_term_off_is_bitexact_power_model():
    """current_k_stall_a_per_nm=0 reproduces the pure power model bit-exact
    (holding/stall read ~0 A) — the pre-refit default and any dict-only
    caller that never sets the key."""
    cfg = load_config()
    cfg["bus"]["current_k_stall_a_per_nm"] = 0.0
    env = SimHexapodBalanceEnv(cfg=cfg, seed=1)
    env.reset()
    j = 5
    _set_joint(env, j, torque=2.2, qvel=0.0)
    st = env._read_state()
    assert st.servo_current[j] == pytest.approx(IQ_JOINT, abs=1e-6)


def test_peak_stall_current_is_capped_by_the_torque_rail():
    """PEAK CEILING (2026-09-21 peak-fit review, claude/current-peak-fit).

    The winding/stall term rides |torque|, and the sim's actuator force is
    clamped at ``AxisParams.torque_limit_nm`` (2.2 N·m; servo_model). So the
    MOST per-joint stall current the model can emit is
    ``IQ_JOINT + K_STALL*(rail - STALL_THR)`` — ~0.05 A at the shipped
    k_stall=0.042 (and only ~0.18 A even at a gaitval-breaking 0.23) — below
    the real
    robot's LPF-matched per-joint walk peak (~0.58-0.61 A on hip/knee, run
    b616; a raised-rail probe re-saturates |tau| at 4 N·m, so the real
    footfall torque implies ~4 N·m, ~2x the sim clamp).

    i.e. the current-model MAPPING cannot reproduce the real per-joint current
    PEAK: the sim |tau| rails at about half the real robot's implied footfall
    torque, and cranking K_STALL to reach the peak would break the scripted
    gaitval-gait current (test_stall_term_gaitval_drift_bounded). Matching the
    peak is a dynamics fix (torque_limit_nm / contact load / under-rock), not
    a current coefficient. This pins the ceiling so a future K_STALL crank is
    not mistaken for a peak fix.
    """
    from rl_move.sim.servo_model import SimServoParams
    env = _mkenv("power")
    rail = SimServoParams.from_cfg(env.cfg).axes["hip"].torque_limit_nm
    assert rail == pytest.approx(2.2)
    j = 5
    _set_joint(env, j, torque=rail, qvel=0.0)  # joint pinned at the force clamp
    st = env._read_state()
    ceiling = IQ_JOINT + K_STALL * (rail - STALL_THR)
    assert st.servo_current[j] == pytest.approx(ceiling, abs=1e-6)
    # the mapping ceiling is far below the measured real per-joint LPF peak
    REAL_HIP_KNEE_LPF_PEAK_A = 0.58
    assert ceiling < 0.25
    assert ceiling < 0.5 * REAL_HIP_KNEE_LPF_PEAK_A


def test_stall_term_gaitval_drift_bounded():
    """GUARD (the check the 2026-09-21 refit omitted): the winding term is NOT
    ~0 on the scripted gaitval gaits — their |torque| ALSO rails at 2.2 N·m
    (> thr) — so it DRIFTS the validated scripted-gait bus current. At the
    shipped (k_stall, thr) that drift is small (max ~0.06 A on gait 1 with the
    run_C air params this test reads, ~0.08 A with the current refit params); this
    test bounds it so a future coefficient crank that reaches for the walk peak
    (e.g. k_stall≈0.23 would add ~0.24 A to gait 1) fails loudly instead of
    silently wrecking the gaitval fit. Skips if the /tmp telemetry is gone
    (same policy as test_constants_reproduce_the_fit)."""
    import csv
    import json
    import os

    csv_path = "/tmp/gaitval/run_C/sim_telemetry.csv"
    if not os.path.exists(csv_path):
        pytest.skip("gaitval telemetry artifact absent")
    cfg = load_config()
    k_stall = float(cfg["bus"].get("current_k_stall_a_per_nm", 0.0))
    thr = float(cfg["bus"].get("current_stall_thr_nm", 1.2))
    rows = list(csv.DictReader(open(csv_path)))
    GUARD_A = 0.12  # bus stall-term add budget per gait (on-main ~0.08 max)
    worst = 0.0
    for g in (1, 2, 3, 4, 7, 10):
        sel = [r for r in rows if r["phase"] == f"gait_{g}_forward"]
        if not sel:
            continue
        add = np.mean([
            float(np.sum(k_stall * np.maximum(
                np.abs(np.array(json.loads(r["joint_torque_nm"]))) - thr, 0.0)))
            for r in sel])
        worst = max(worst, add)
    assert worst < GUARD_A, (
        f"stall term adds {worst:.3f} A to a gaitval gait (> {GUARD_A} guard) "
        f"at k_stall={k_stall}, thr={thr} — this breaks the scripted-gait "
        f"current fit; the walk peak is upstream-limited, not a k_stall knob")


def test_legacy_model_bit_exact():
    """torque_proxy reproduces the pre-2026-09-19 estimate and sets NO
    separate trip signal (trip reads servo_current)."""
    env = _mkenv("torque_proxy")
    j = 5
    _set_joint(env, j, torque=2.2, qvel=0.0)
    st = env._read_state()
    torque = env.data.qfrc_actuator[env._vadr]
    expected = np.minimum(np.abs(torque) * 1.2, 3.0)
    assert np.allclose(st.servo_current, expected)
    assert st.over_current_signal is None
    assert np.allclose(over_current_reading(st), st.servo_current)


def _trip_over_current(safety, servo_current, over_current_signal, n):
    """Feed n identical health frames; return the first over_current status."""
    for _ in range(n):
        st = RobotState(
            timestamp=0.0,
            joint_position=np.zeros(18),
            joint_velocity=np.zeros(18),
            imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
            imu_gyro=np.zeros(3), imu_accel=np.zeros(3),
            commanded_position=np.zeros(18),
            servo_current=servo_current,
            over_current_signal=over_current_signal,
        )
        status = safety.check_servo_health(st)
        if status is not None:
            return status
    return None


def test_safety_trip_uses_stall_signal_not_power_current():
    """The FIX: with the power model, servo_current reads ~0 at a stall, so
    a trip keyed on servo_current would NEVER fire — but the separate
    over_current_signal makes it trip exactly as before."""
    cfg = load_config()
    safety = SafetyLayer(cfg)
    n = safety._over_current_trip_ticks + 2
    power_cur = np.full(18, IQ_JOINT)          # ~0.011 A — would never trip
    trip_sig = np.full(18, 2.64)               # railed proxy
    status = _trip_over_current(safety, power_cur, trip_sig, n)
    assert status is not None and status.reason == "over_current"

    # Control: WITHOUT the signal (as a naive power-only change would be),
    # the same low servo_current does NOT trip — i.e. the signal is load-
    # bearing, protection would have been silently disabled.
    safety2 = SafetyLayer(cfg)
    assert _trip_over_current(safety2, power_cur, None, n) is None


def test_safety_trip_falls_back_to_servo_current_on_hardware():
    """over_current_signal=None (hardware / legacy) → trip reads the
    measured servo_current, byte-identical to before."""
    cfg = load_config()
    safety = SafetyLayer(cfg)
    n = safety._over_current_trip_ticks + 2
    hot = np.full(18, 2.64)
    status = _trip_over_current(safety, hot, None, n)
    assert status is not None and status.reason == "over_current"


def test_env_stall_still_trips_under_default_power_model():
    """End-to-end: a sustained stall (rail torque, zero speed) fed through
    the DEFAULT power model's _read_state still fires the over-current trip,
    even though the reported servo_current stays far below the 2.5 A trip."""
    env = _mkenv("power")
    j = 2
    _set_joint(env, j, torque=2.2, qvel=0.0)
    n = env.safety._over_current_trip_ticks + 15  # + low-pass settle margin
    tripped = None
    max_reported = 0.0
    for _ in range(n):
        st = env._read_state()  # physics not advanced: stall persists
        max_reported = max(max_reported, float(np.max(st.servo_current)))
        status = env.safety.check_servo_health(st)
        if status is not None and status.reason == "over_current":
            tripped = status
            break
    assert tripped is not None, "stall did not trip under power model"
    # The reported (power) current never approached the trip — proof the
    # trip rode the separate stall signal, not servo_current.
    assert max_reported < 2.5


def test_constants_reproduce_the_fit():
    """Pin iq_bus=0.19 / k=0.02282 to the validated fit: recompute the
    least-squares k from the experiment telemetry (matches fit_current.py)
    and confirm the model's predicted bus current tracks the real robot's
    walk_summary current_mean_a. Skips if the /tmp artifact is gone."""
    import csv
    import json
    import os

    csv_path = "/tmp/gaitval/run_C/sim_telemetry.csv"
    if not os.path.exists(csv_path):
        pytest.skip("gaitval telemetry artifact absent")
    rows = list(csv.DictReader(open(csv_path)))
    gaits = [1, 2, 3, 4, 7, 10]
    real = {1: 0.34, 2: 0.31, 3: 0.27, 4: 0.20, 7: 0.23, 10: 0.24}
    power_sum, real_vec = [], []
    for g in gaits:
        sel = [r for r in rows if r["phase"] == f"gait_{g}_forward"]
        p = []
        for r in sel:
            tau = np.abs(np.array(json.loads(r["joint_torque_nm"])))
            w = np.abs(np.array(json.loads(r["joint_qvel_rad_s"])))
            p.append(float(np.sum(tau * w)))  # total mechanical power (W)
        power_sum.append(float(np.mean(p)))
        real_vec.append(real[g])
    P = np.array(power_sum)
    R = np.array(real_vec)
    # least-squares k with iq pinned, exactly as fit_current.py
    k_fit = float(np.sum(P * (R - IQ_BUS)) / np.sum(P * P))
    assert k_fit == pytest.approx(K_POWER, abs=5e-5)
    # bus current = iq_bus + k*sum_j|tau_j*w_j| (== sum of the per-joint
    # model); gait 1 should land near the real 0.34 A.
    pred_g1 = IQ_BUS + K_POWER * P[0]
    assert pred_g1 == pytest.approx(real[1], abs=0.05)


def test_env_stall_trips_under_legacy_model():
    env = _mkenv("torque_proxy")
    j = 2
    _set_joint(env, j, torque=2.2, qvel=0.0)
    n = env.safety._over_current_trip_ticks + 15
    tripped = None
    for _ in range(n):
        st = env._read_state()
        status = env.safety.check_servo_health(st)
        if status is not None and status.reason == "over_current":
            tripped = status
            break
    assert tripped is not None
