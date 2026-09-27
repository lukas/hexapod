"""Profile-shape refit knobs (servo_model.SimServoParams 2026-09-26):
``lowpass_tau_ms`` / ``acc_scale`` / ``vel_of_write_speed``.

Default-off must stay bit-exact on both backends (every legacy json and
cfg); the fitted json ``sim_model_profilefit_20260926.json`` must load,
resolve its speed ceiling from bus.write_speed, and produce a first-order
lagged shaft.  See sysid/fit_servo_profile.py for the fit itself.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from rl_move.sim.servo_model import (
    ACC_UNIT_DEG_S2, COUNTS_PER_DEG, DEG2RAD, N_JOINTS, AxisParams,
    ServoProfile, SimServoParams)

FIT_JSON = Path(SimServoParams.load.__globals__["SIM_MODEL_PATH"]).with_name(
    "sim_model_profilefit_20260926.json")
H = 0.002


def _fast_params(**kw) -> SimServoParams:
    """Latency 0, no deadband, effectively unlimited profile so the
    trapezoid target jumps to the goal in one substep."""
    mk = lambda: AxisParams(kp=1.0, kv=0.1, frictionloss=0.0,  # noqa: E731
                            latency_ms=0.0, vel_max_deg_s=1e6,
                            deadband_deg=0.0)
    return SimServoParams(axes={a: mk() for a in ("yaw", "hip", "knee")},
                          **kw)


def _run(params: SimServoParams, goal_deg: float, seconds: float,
         speed_deg_s: float = 1e6, acc_units: float = 1e6) -> np.ndarray:
    prof = ServoProfile(params, np.zeros(N_JOINTS))
    prof.command(np.full(N_JOINTS, goal_deg * DEG2RAD),
                 speed_deg_s=speed_deg_s, acc_units=acc_units)
    out = []
    for _ in range(int(round(seconds / H))):
        out.append(prof.tick(H).copy())
    return np.asarray(out)


def test_legacy_json_carries_no_refit_knobs():
    p = SimServoParams.load()
    assert p.lowpass_tau_ms == 0.0
    assert p.acc_scale == 1.0
    assert p.vel_of_write_speed == 0.0
    for sel in ("air", "loaded"):
        q = SimServoParams.from_cfg({"bus": {"servo_params": sel}})
        assert (q.lowpass_tau_ms, q.acc_scale, q.vel_of_write_speed) == (0.0, 1.0, 0.0)


def test_tau_off_returns_the_profile_target_itself():
    """tau = 0: tick() hands back the trapezoid target array (identity
    path, no low-pass arithmetic), exactly as before the refit."""
    params = SimServoParams.load()
    prof = ServoProfile(params, np.zeros(N_JOINTS))
    rng = np.random.default_rng(1)
    for _ in range(30):
        prof.command(rng.uniform(-0.5, 0.5, N_JOINTS), speed_deg_s=35.0,
                     acc_units=20.0)
        for _ in range(10):
            out = prof.tick(H)
            assert out is prof.target
            assert np.array_equal(out, prof.target)


def test_lowpass_step_is_first_order():
    tau_ms = 100.0
    y = _run(_fast_params(lowpass_tau_ms=tau_ms), 10.0, 0.5)[:, 1] / DEG2RAD
    t = (np.arange(len(y)) + 1) * H
    want = 10.0 * (1.0 - np.exp(-t / (tau_ms / 1000.0)))
    # Euler integration at h=2 ms of a 100 ms lag: < 0.15 deg off the
    # analytic response over the whole step.
    assert np.max(np.abs(y - want)) < 0.15
    k = int(round(tau_ms / 1000.0 / H))
    assert abs(y[k - 1] / 10.0 - (1 - math.exp(-1))) < 0.02


def test_acc_scale_scales_the_ramp():
    """With acc_scale 2 the trapezoid reaches cruise speed in half the
    time: the target after a short ramp is ~2x further along."""
    acc_units = 20.0
    y1 = _run(_fast_params(acc_scale=1.0), 30.0, 0.1, speed_deg_s=1e6,
              acc_units=acc_units)[:, 1] / DEG2RAD
    y2 = _run(_fast_params(acc_scale=2.0), 30.0, 0.1, speed_deg_s=1e6,
              acc_units=acc_units)[:, 1] / DEG2RAD
    # pure accel phase: x = 0.5 a t^2 -> doubling a doubles x.
    assert y2[-1] / y1[-1] == pytest.approx(2.0, rel=0.05)
    a = acc_units * ACC_UNIT_DEG_S2
    assert y1[-1] == pytest.approx(0.5 * a * 0.1 ** 2, rel=0.05)


def test_profilefit_json_loads_and_follows_write_speed():
    assert FIT_JSON.is_file()
    for ws in (400, 2000):
        p = SimServoParams.from_cfg({"bus": {"servo_params": str(FIT_JSON),
                                             "write_speed": ws}})
        assert p.lowpass_tau_ms > 0
        assert p.acc_scale > 1.0
        want = p.vel_of_write_speed * ws / COUNTS_PER_DEG
        assert np.allclose(p.per_joint("vel_max_deg_s"), want)
        assert len(set(p.per_joint("latency_ms"))) == 1  # shared latency
    # the fitted fraction overrides the counts override: same ceiling
    q = SimServoParams.from_cfg({"bus": {"servo_params": str(FIT_JSON),
                                         "write_speed": 2000,
                                         "servo_vel_max_counts_s": "write_speed"}})
    assert np.allclose(q.per_joint("vel_max_deg_s"),
                       q.vel_of_write_speed * 2000 / COUNTS_PER_DEG)


def test_profilefit_staircase_tracks_at_2000_80():
    """The regression the refit exists for: a 20 Hz staircase of 2 deg
    goal steps at write_speed 2000 / acc 80.  The legacy trapezoid
    (decelerate-to-stop at every intermediate goal) crawls at ~1/3 of
    the commanded rate; the fitted model follows it with ~100 ms lag."""
    def staircase(params):
        prof = ServoProfile(params, np.zeros(N_JOINTS))
        cmd = 0.0
        ys = []
        for tick in range(40):           # 2 s at 20 Hz, 40 deg/s ramp
            cmd += 2.0
            prof.command(np.full(N_JOINTS, cmd * DEG2RAD),
                         speed_deg_s=2000 / COUNTS_PER_DEG, acc_units=80)
            for _ in range(int(round(0.05 / H))):
                ys.append(prof.tick(H)[1] / DEG2RAD)
        return np.asarray(ys), cmd
    y_old, cmd = staircase(SimServoParams.load())
    y_new, _ = staircase(SimServoParams.from_cfg(
        {"bus": {"servo_params": str(FIT_JSON), "write_speed": 2000}}))
    # staircase reached 80 deg at 40 deg/s; the fitted model trails it
    # by its ~80 ms effective lag (~3 deg), the legacy trapezoid --
    # decelerating to a stop at every 2 deg step and clamped at the
    # json's 35 deg/s ceiling -- falls several times further behind.
    lag_new, lag_old = cmd - y_new[-1], cmd - y_old[-1]
    assert lag_new < 5.0, lag_new
    assert lag_old > 3.0 * lag_new, (lag_old, lag_new)


@pytest.mark.skipif(pytest.importorskip("jax", reason="jax not installed") is None,
                    reason="jax")
def test_mjx_profile_tick_matches_numpy_with_lowpass():
    import jax
    import jax.numpy as jnp

    from rl_move.sim import mjx_backend as mb

    params = SimServoParams.from_cfg(
        {"bus": {"servo_params": str(FIT_JSON), "write_speed": 400}})
    rng = np.random.default_rng(3)
    q0 = rng.uniform(-0.5, 0.5, N_JOINTS)
    ref = ServoProfile(params, q0)
    lat = params.per_joint("latency_ms") / 1000.0
    dbd = params.per_joint("deadband_deg") * DEG2RAD
    vel = params.per_joint("vel_max_deg_s") * DEG2RAD
    tau = np.full(N_JOINTS, params.lowpass_tau_ms / 1000.0)
    tp = mb.TickParams(latency_s=jnp.asarray(lat, jnp.float32),
                       deadband=jnp.asarray(dbd, jnp.float32),
                       vel_max=jnp.asarray(vel, jnp.float32),
                       imu_off=jnp.zeros(3, jnp.float32),
                       lp_tau_s=jnp.asarray(tau, jnp.float32))
    acc0 = np.full(N_JOINTS, 15.0 * ACC_UNIT_DEG_S2 * DEG2RAD * params.acc_scale)
    st = mb.init_profile_state(jnp, q0, vel, acc0)
    substeps = 10   # 50 Hz control at h = 2 ms
    speed = 400 / COUNTS_PER_DEG

    @jax.jit
    def run_tick(st, cmd):
        st = mb._profile_enqueue(jnp, st, tp, cmd)
        outs = []
        for _ in range(substeps):
            st, y = mb._profile_tick(jnp, st, tp, H)
            outs.append(y)
        return st, jnp.stack(outs)

    worst = 0.0
    for _ in range(40):
        goal = rng.uniform(-0.8, 0.8, N_JOINTS)
        ref.command(goal, speed_deg_s=speed, acc_units=20.0)
        ref_y = np.stack([ref.tick(H).copy() for _ in range(substeps)])
        cmd = mb.Command(q=jnp.asarray(goal, jnp.float32),
                         vel=jnp.full(N_JOINTS, speed * DEG2RAD, jnp.float32),
                         acc=jnp.full(N_JOINTS, 20.0 * ACC_UNIT_DEG_S2 * DEG2RAD
                                      * params.acc_scale, jnp.float32),
                         valid=jnp.bool_(True))
        st, y = run_tick(st, cmd)
        worst = max(worst, float(np.max(np.abs(np.asarray(y) - ref_y))))
    assert worst < 3e-4, f"lowpass profile diverged: {worst:.2e} rad"


def test_mjx_tick_params_default_none_is_legacy():
    jax = pytest.importorskip("jax")
    import jax.numpy as jnp
    from rl_move.sim import mjx_backend as mb
    tp = mb.TickParams(latency_s=jnp.zeros(N_JOINTS), deadband=jnp.zeros(N_JOINTS),
                       vel_max=jnp.ones(N_JOINTS), imu_off=jnp.zeros(3))
    assert tp.lp_tau_s is None
    st = mb.init_profile_state(jnp, np.zeros(N_JOINTS), np.ones(N_JOINTS),
                               np.ones(N_JOINTS))
    st, y = mb._profile_tick(jnp, st, tp, H)
    assert np.array_equal(np.asarray(y), np.asarray(st.target))
    assert np.array_equal(np.asarray(st.y), np.asarray(st.target))
