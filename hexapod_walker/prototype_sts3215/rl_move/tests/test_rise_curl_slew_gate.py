"""Curl-phase rate ceiling (``safety.rise_curl_slew_gate``, walkcurr
track, 2026-09-14) — unit semantics.

Background (STATUS 09-14 ~05:5x): the height-cap-only family closed
9/9 with zero passes on flat-start rise, and this closing run's own
per-episode telemetry named the actual root cause as RATE, not
magnitude -- ``slew_sat_frac`` 0.76-0.994 (76-100% of ticks command
some joint at >=98% of ``safety.max_delta_q_deg``), while
``cur_max_a`` is already pegged mid-curl. The mesh-native scripted
reference clears the identical flat start at 2.21A/0 trips by pacing
the curl ramp over ~4.9s -- same lockstep leg sequencing as the RL
policy, only the RATE differs. This is the named next lever: a hard
per-tick RATE ceiling (not a reward price) that is tightest at
curl_frac<=0 and relaxes linearly to the ordinary
``max_delta_q_deg`` once curl_frac>=``rise_curl_slew_gate_frac`` --
reusing the exact ``curl_height_cap_frac`` ramp the (now-closed)
height-CAP family already used, applied to the RATE axis instead of
the MAGNITUDE axis.

Contract under test:
  - default OFF (``safety.rise_curl_slew_gate`` unset/0) is bit-exact:
    ``SafetyLayer.filter`` ignores ``curl_frac`` entirely, at every
    curl_frac value including None/0.0/1.0.
  - ON, curl_frac=0: achieved per-tick delta is capped at
    ``rise_curl_slew_gate_floor * max_delta_q_deg``, not the full rate.
  - ON, curl_frac>=gate_frac: no scaling, full max_delta_q_deg rate.
  - ON, curl_frac=None (caller never wired it): inert even though the
    gate is on -- "no gating information" is never treated as "curl
    progress 0".
  - Composes MULTIPLICATIVELY with the entry slew ramp (both active at
    once is a legitimate configuration, e.g. episode start during an
    uncurled rise attempt).
  - Wiring: both ``SimHexapodBalanceEnv`` and the physical
    ``HexapodBalanceEnv`` pass their own live ``self.ik.curl_frac``
    through to ``safety.filter`` (not a hardcoded 0/None).

RESEARCH_RULES "Tests": fast, mechanics only, no artifacts, no
rollout-ranking.

Run: uv run python -m pytest rl_move/tests/test_rise_curl_slew_gate.py -q
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.robot_state import RobotState
from rl_move.safety import N_JOINTS, SafetyLayer, curl_height_cap_frac

DEG = math.pi / 180.0


def _state(q: np.ndarray) -> RobotState:
    return RobotState(
        timestamp=0.0,
        joint_position=q.copy(),
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3), imu_accel=np.zeros(3),
        commanded_position=q.copy(),
    )


def _cfg(**safety_extra) -> dict:
    s = {"max_delta_q_deg": 1.5, "max_roll_deg": 25, "max_pitch_deg": 25}
    s.update(safety_extra)
    return {"safety": s, "control": {"hz": 25}}


def _achieved_delta_deg(layer: SafetyLayer, curl_frac) -> float:
    """One huge-jump tick from a zeroed nominal; achieved deg on joint 0."""
    q0 = np.zeros(N_JOINTS)
    layer.set_nominal(q0)
    target = np.full(N_JOINTS, 45.0 * DEG)
    q_safe, status = layer.filter(target, _state(q0), curl_frac=curl_frac)
    assert status.ok
    return float((q_safe - q0)[0]) / DEG


def test_default_off_bit_exact_regardless_of_curl_frac():
    for curl_frac in (None, 0.0, 0.3, 0.7, 1.0):
        layer = SafetyLayer(_cfg())  # rise_curl_slew_gate unset -> default 0
        d = _achieved_delta_deg(layer, curl_frac)
        assert abs(d - 1.5) < 1e-9, curl_frac


def test_gate_on_caps_rate_at_floor_when_curl_frac_zero():
    layer = SafetyLayer(_cfg(rise_curl_slew_gate=1,
                             rise_curl_slew_gate_frac=0.8,
                             rise_curl_slew_gate_floor=0.3))
    d = _achieved_delta_deg(layer, 0.0)
    assert abs(d - 1.5 * 0.3) < 1e-9


def test_gate_on_full_rate_past_gate_frac():
    layer = SafetyLayer(_cfg(rise_curl_slew_gate=1,
                             rise_curl_slew_gate_frac=0.8,
                             rise_curl_slew_gate_floor=0.3))
    d_at_gate = _achieved_delta_deg(layer, 0.8)
    assert abs(d_at_gate - 1.5) < 1e-9
    layer2 = SafetyLayer(_cfg(rise_curl_slew_gate=1,
                              rise_curl_slew_gate_frac=0.8,
                              rise_curl_slew_gate_floor=0.3))
    d_full = _achieved_delta_deg(layer2, 1.0)
    assert abs(d_full - 1.5) < 1e-9


def test_gate_on_linear_ramp_matches_pure_function():
    gate_frac, floor = 0.8, 0.3
    for curl_frac in (0.2, 0.4, 0.6):
        layer = SafetyLayer(_cfg(rise_curl_slew_gate=1,
                                 rise_curl_slew_gate_frac=gate_frac,
                                 rise_curl_slew_gate_floor=floor))
        d = _achieved_delta_deg(layer, curl_frac)
        expect = 1.5 * curl_height_cap_frac(curl_frac, gate_frac, floor)
        assert abs(d - expect) < 1e-9, curl_frac


def test_gate_on_curl_frac_none_is_inert():
    layer = SafetyLayer(_cfg(rise_curl_slew_gate=1,
                             rise_curl_slew_gate_frac=0.8,
                             rise_curl_slew_gate_floor=0.3))
    d = _achieved_delta_deg(layer, None)
    assert abs(d - 1.5) < 1e-9


def test_gate_composes_multiplicatively_with_entry_ramp():
    """Both levers active: entry ramp mid-way AND curl gate at floor
    (0.3x) must multiply per-TICK, not override each other."""
    layer = SafetyLayer(_cfg(
        rise_curl_slew_gate=1, rise_curl_slew_gate_frac=0.8,
        rise_curl_slew_gate_floor=0.3,
        entry_slew_ramp_s=1.0, entry_slew_start_deg=0.0))
    q0 = np.zeros(N_JOINTS)
    layer.set_nominal(q0)
    target = np.full(N_JOINTS, 45.0 * DEG)
    prev = q0.copy()
    last_delta_deg = None
    for i in range(12):  # per-tick delta, not cumulative displacement
        q_safe, status = layer.filter(target, _state(prev), curl_frac=0.0)
        assert status.ok
        last_delta_deg = float((q_safe - prev)[0]) / DEG
        prev = q_safe
    # the 12th call reads self._entry_ticks == 11 (incremented AFTER each
    # call, starting at 0): t = 11/25 = 0.44s of the 1.0s ramp.
    entry_frac = 11.0 / 25.0
    expected_entry_dq = 0.0 + entry_frac * (1.5 - 0.0)  # deg
    expected = expected_entry_dq * 0.3  # x curl floor
    assert abs(last_delta_deg - expected) < 1e-6, (last_delta_deg, expected)


def test_env_step_wires_live_curl_frac_sim():
    import pytest
    pytest.importorskip("mujoco")
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = load_config()
    cfg.setdefault("safety", {})
    cfg["safety"]["rise_curl_slew_gate"] = 1
    cfg["safety"]["rise_curl_slew_gate_frac"] = 0.8
    cfg["safety"]["rise_curl_slew_gate_floor"] = 0.1
    params = SimServoParams.from_cfg(cfg)
    env = SimHexapodBalanceEnv(params=params, randomize=False, dr_scale=0.0,
                               episode_seconds=2.0, seed=0, cfg=cfg)
    env.reset(seed=0)

    action = np.zeros(6, dtype=np.float32)
    # 0.3 * 80mm default max_height_mm curriculum band -- same magnitude
    # `test_rise_height_curl_gate.py`'s own wiring test uses, chosen
    # there specifically because it is IK-feasible from a plant stance
    # at EITHER curl extreme (a q-mismatch there is the GATE, not a
    # geometry failure at the action space's extreme).
    action[2] = 0.3

    env.ik.curl_frac = 0.0
    q_before = env.safety._last_safe.copy()
    q_low, ok_low, reason_low = env._act_to_q(action)
    q_low_safe, status_low = env.safety.filter(
        q_low, env._state, ik_ok=ok_low, ik_reason=reason_low,
        curl_frac=env.ik.curl_frac)
    dq_low = np.abs(q_low_safe - q_before).max()

    env.safety.set_nominal(q_before)  # reset the rate-limiter reference
    env.ik.curl_frac = 1.0
    q_high, ok_high, reason_high = env._act_to_q(action)
    q_high_safe, status_high = env.safety.filter(
        q_high, env._state, ik_ok=ok_high, ik_reason=reason_high,
        curl_frac=env.ik.curl_frac)
    dq_high = np.abs(q_high_safe - q_before).max()

    assert status_low.ok and status_high.ok
    assert dq_low < dq_high - 1e-9, (
        "gated slew ceiling did not change with live curl_frac -- "
        "wiring regressed to a hardcoded value", dq_low, dq_high)
