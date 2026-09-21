"""Cap- and weight-independent body-smoothness metrics in the eval
report (smoothrew re-dose, 2026-09-20).

WHY: the smoothness-reward run (cw-walk50hz-smoothrew-s0) was NOGO
partly because the eval had no trustworthy smoothness number. The only
jerk proxy, ``cmd_jerk_p95_deg_s2``, is the 2nd difference of the
POST-SafetyLayer *command*, so once the policy drives the slew limiter
it pins at exactly ``2*max_delta_q_deg/dt^2`` -- a saturation image of
the cap that is identical across episodes and just scales with the cap
on a lifted-cap run, so it can never show a real jerk change. And
``reward_gyro`` is a WEIGHTED term (=0 when ``k_gyro`` = 0), so it is
not comparable across runs.

The two additive fields tested here read the sim GROUND TRUTH instead:

- ``body_gyro_rms_dps`` (+ per-axis): RMS of the chassis body angular
  rate (MuJoCo ``chassis_gyro``, bias/noise-free), the true-rock
  measure -- responds to a rocking body, not to the reward weight.
- ``meas_jerk_p95_deg_s2`` / ``meas_jerk_rms_deg_s2``: 2nd difference of
  the MEASURED joint positions, bounded by physics/servo dynamics, so
  it does NOT pin at the cap ceiling the way ``cmd_jerk`` does.

Lower ``body_gyro_rms_dps`` + lower ``meas_jerk_*`` = smoother.
"""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.sim.eval_checkpoint import _body_smoothness_fields

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.eval_checkpoint import run_episode
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

N_ACT = 18


# ---------------------------------------------------------------------------
# Pure-function units (no sim): the metric maths, per-axis split, guards.
# ---------------------------------------------------------------------------

def test_body_gyro_rms_units_and_axis_split():
    """Constant 1 rad/s about the roll axis for n ticks -> roll RMS =
    degrees(1) = 57.30 dps, pitch/yaw = 0, and the combined magnitude
    equals the roll axis (only one axis moving)."""
    n = 200
    gyro_sq_sum = np.array([1.0, 0.0, 0.0]) * n   # sum of (rad/s)^2
    q_hist = []                                   # no measured-q this case
    f = _body_smoothness_fields(gyro_sq_sum, n, q_hist, dt=0.01)
    assert f["body_gyro_rms_roll_dps"] == 57.3
    assert f["body_gyro_rms_pitch_dps"] == 0.0
    assert f["body_gyro_rms_yaw_dps"] == 0.0
    assert f["body_gyro_rms_dps"] == 57.3
    # no measured-q -> no jerk keys (partial availability is fine)
    assert "meas_jerk_p95_deg_s2" not in f


def test_meas_jerk_formula_from_measured_q():
    """A joint whose measured position has a CONSTANT 2nd difference of
    0.5 deg/tick^2 must report meas_jerk = 0.5/dt^2 (both p95 and rms,
    since the 2nd difference is constant)."""
    dt = 0.01
    b_deg = 0.5
    n = 60
    q_hist = []
    for t in range(n):
        q = np.zeros(N_ACT)
        q[0] = np.radians(0.5 * b_deg * t * t)   # q'' = b_deg (deg)
        q_hist.append(q)
    f = _body_smoothness_fields(np.zeros(3), 0, q_hist, dt=dt)
    expect = b_deg / (dt * dt)
    assert f["meas_jerk_p95_deg_s2"] == pytest.approx(expect, rel=1e-3)
    assert f["meas_jerk_rms_deg_s2"] == pytest.approx(expect, rel=1e-3)
    # no gyro this case
    assert "body_gyro_rms_dps" not in f


def test_body_smoothness_empty_when_nothing_available():
    """No gyro samples and fewer than 3 measured-q rows -> {} so the
    report stays byte-identical in shape (additive-only contract)."""
    assert _body_smoothness_fields(np.zeros(3), 0, [], dt=0.01) == {}
    assert _body_smoothness_fields(
        np.zeros(3), 0, [np.zeros(N_ACT), np.zeros(N_ACT)], dt=0.01) == {}


# ---------------------------------------------------------------------------
# Integration: the metrics land in the ep dict and behave physically.
# ---------------------------------------------------------------------------

class _ZeroModel:
    """Hold the plant pose (zero offset)."""

    def predict(self, obs, deterministic=True):
        return np.zeros(N_ACT), None


class _RollRockModel:
    """Sinusoid on the femurs, one body side opposite the other, so the
    chassis rocks in ROLL (action index = 3*leg + axis; legs 0-2 vs
    3-5)."""

    def __init__(self, amp=0.6, hz=1.0, dt=0.01):
        self.amp, self.hz, self.dt, self.t = amp, hz, dt, 0
        self.sign = np.array(
            [1.0 if (i // 3) < 3 else -1.0 for i in range(N_ACT)])

    def predict(self, obs, deterministic=True):
        self.t += 1
        return (self.amp * np.sin(2 * np.pi * self.hz * self.t * self.dt)
                * self.sign), None


class _BangBangModel:
    """Alternate the full offset ±amp every tick so the command always
    slams the slew limiter -> cmd side is cap-saturated."""

    def __init__(self, amp=0.5):
        self.amp, self.k = amp, 0

    def predict(self, obs, deterministic=True):
        self.k += 1
        return (self.amp if self.k % 2 else -self.amp) * np.ones(N_ACT), None


def _hold_env(cap=None):
    cfg = load_config()
    if cap is not None:
        cfg.setdefault("safety", {})["max_delta_q_deg"] = cap
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=6.0,
                                 randomize=False, dr_scale=0.0)
    gen = env._goal_gen
    for m in ("lean", "track", "unload", "raise", "walk", "lower", "rise"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    if hasattr(gen, "p_hold"):
        gen.p_hold = 1.0
    return env


def test_new_metrics_present_in_ep_report():
    ep, _ = run_episode(_hold_env(), _ZeroModel(), deterministic=True,
                        video=False, annotate=None)
    for k in ("body_gyro_rms_dps", "body_gyro_rms_roll_dps",
              "body_gyro_rms_pitch_dps", "body_gyro_rms_yaw_dps",
              "meas_jerk_p95_deg_s2", "meas_jerk_rms_deg_s2"):
        assert k in ep, f"missing {k}"
        assert ep[k] is not None and np.isfinite(ep[k])
    # the existing (cap-side) field is untouched, still present
    assert "cmd_jerk_p95_deg_s2" in ep


def test_body_gyro_rms_responds_to_rocking():
    """A body that rocks in roll reads a much higher body_gyro_rms than a
    body just holding pose from spawn, and the extra energy shows up on
    the ROLL axis -- the whole point of a weight-independent true-rock
    measure. (The hold baseline is not literally zero: it includes the
    spawn -> rise-to-hold settle transient, ~6-7 dps here; the rock
    clears it by >1.8x.)"""
    still, _ = run_episode(_hold_env(), _ZeroModel(), deterministic=True,
                           video=False, annotate=None)
    rock, _ = run_episode(_hold_env(), _RollRockModel(), deterministic=True,
                          video=False, annotate=None)
    assert rock["body_gyro_rms_dps"] > 1.8 * still["body_gyro_rms_dps"]
    # the rock is in roll -> roll axis dominates its own pitch/yaw
    assert rock["body_gyro_rms_roll_dps"] > rock["body_gyro_rms_yaw_dps"]
    assert rock["body_gyro_rms_roll_dps"] > still["body_gyro_rms_roll_dps"]


def test_meas_jerk_not_pinned_at_slew_cap():
    """The bug: cmd_jerk_p95_deg_s2 is a saturation image of the slew cap
    (exactly 2*cap/dt^2 when every tick saturates), so it just scales
    with the cap and cannot show a real jerk change. meas_jerk, read from
    the MEASURED joints, must NOT track the cap that way."""
    env2 = _hold_env(cap=2.0)
    env8 = _hold_env(cap=8.0)
    dt = env2.dt
    e2, _ = run_episode(env2, _BangBangModel(), deterministic=True,
                        video=False, annotate=None)
    e8, _ = run_episode(env8, _BangBangModel(), deterministic=True,
                        video=False, annotate=None)
    # sanity: the command is genuinely cap-saturated in both runs
    assert e2["slew_sat_frac"] > 0.9 and e8["slew_sat_frac"] > 0.9
    # cmd_jerk IS the cap artifact: exactly 2*cap/dt^2, i.e. ratio == 4
    assert e2["cmd_jerk_p95_deg_s2"] == pytest.approx(
        2 * 2.0 / (dt * dt), rel=2e-2)
    assert e8["cmd_jerk_p95_deg_s2"] == pytest.approx(
        2 * 8.0 / (dt * dt), rel=2e-2)
    cmd_ratio = e8["cmd_jerk_p95_deg_s2"] / e2["cmd_jerk_p95_deg_s2"]
    assert cmd_ratio == pytest.approx(4.0, rel=0.1)
    # meas_jerk is measured motion, physically bounded by the servo speed
    # profile: in this fully-saturated regime it sits orders of magnitude
    # below the cap ceiling at BOTH caps (unlike cmd_jerk, which IS the
    # ceiling and scales exactly with it), so it is not the cap-saturation
    # artifact. (At a non-saturating cap the gap narrows -- the point is
    # that meas tracks real motion, not the cap.)
    assert e2["meas_jerk_p95_deg_s2"] < 0.05 * e2["cmd_jerk_p95_deg_s2"]
    assert e8["meas_jerk_p95_deg_s2"] < 0.05 * e8["cmd_jerk_p95_deg_s2"]
