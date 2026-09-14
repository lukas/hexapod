"""Dynamics-level rise-height cap keyed on live curl progress
(``actions.rise_height_curl_gate``, walkcurr track, 2026-09-14).

Background (RL_LOG/STATUS 09-14 ~04:4x): 7 successive REWARD-SHAPING
levers on the exact same flat-start-rise question (current-headroom-
gate, geometry/score-income gate, two-phase-freeze, curl-pretrain,
current_pretuck x2, rise_decouple x2) all closed FAIL-MECHANISM --
pricing height/current/curl differently never stopped the policy
ATTEMPTING a poor-leverage straight-up push with the feet still
splayed, it only changed what that attempt cost. The gate's own
pre-registered fallback (STATUS "Next", not another reward dose): an
explicit, non-reward-shaping ceiling enforced at the ACTION-MAPPING
level, before the IK solve ever produces a joint target -- the policy
literally cannot command more height than the live curl-in progress
(``FixedFootBodyIK.curl_frac``, the same ratcheted/monotonic/world-FK-
grounded variable already driving the curl action channel) currently
allows, so there is nothing for the policy to "out-earn".

Contract under test:
  - ``curl_height_cap_frac`` (pure function): floor at curl_frac<=0,
    1.0 once curl_frac>=gate_frac, linear ramp between, gate_frac<=0
    degenerates to always-open (no silent floor-lock misconfiguration).
  - default OFF (``actions.rise_height_curl_gate`` unset/0) is
    bit-exact: ``action_to_body_offset`` ignores ``curl_frac`` entirely
    and returns the same offset as calling ``body_offset_from_action``
    directly, at every curl_frac value including 0.0.
  - ON: a requested POSITIVE height above the live cap is clamped down
    to exactly the cap; a request already below the cap passes through
    unchanged; NEGATIVE height (lowering) is never touched regardless
    of curl_frac, at any gate setting.
  - ON, curl_frac already >= gate_frac: no clamp at all (full max_h
    reachable, identical to gate-off).
  - Wiring: ``SimHexapodBalanceEnv._act_to_q`` passes its own live
    ``self.ik.curl_frac`` through (not a hardcoded 0/None) -- verified
    by driving ``self.ik.curl_frac`` directly and checking the reported
    action-mapped joint target changes at a fixed raw action.

RESEARCH_RULES "Tests": fast, mechanics only, no artifacts, no
rollout-ranking.
"""
from __future__ import annotations

import numpy as np

from rl_move.body_ik import BodyOffset, body_offset_from_action
from rl_move.safety import action_to_body_offset, curl_height_cap_frac


ACTIONS_CFG = {
    "max_roll_deg": 3.0, "max_pitch_deg": 3.0,
    "max_height_mm": 80.0, "max_x_mm": 5.0, "max_y_mm": 5.0,
}


def _cfg(**overrides):
    a = dict(ACTIONS_CFG)
    a.update(overrides)
    return {"actions": a}


def test_cap_frac_floor_and_ceiling():
    assert curl_height_cap_frac(0.0, 0.7, 0.15) == 0.15
    assert curl_height_cap_frac(-1.0, 0.7, 0.15) == 0.15  # clamped, no negative progress
    assert curl_height_cap_frac(0.7, 0.7, 0.15) == 1.0
    assert curl_height_cap_frac(5.0, 0.7, 0.15) == 1.0    # clamped, no >1 progress


def test_cap_frac_linear_ramp():
    # Halfway to gate_frac -> halfway from floor to 1.0.
    f = curl_height_cap_frac(0.35, 0.7, 0.15)
    assert abs(f - (0.15 + 0.85 * 0.5)) < 1e-9


def test_cap_frac_degenerate_gate_always_open():
    # gate_frac<=0 must not silently lock height at the floor forever.
    assert curl_height_cap_frac(0.0, 0.0, 0.15) == 1.0
    assert curl_height_cap_frac(0.0, -1.0, 0.15) == 1.0


def test_default_off_bit_exact_regardless_of_curl_frac():
    action = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])  # full +height request
    cfg = _cfg()  # rise_height_curl_gate unset -> default 0
    ref = body_offset_from_action(
        action, max_roll=0.0, max_pitch=0.0, max_h=0.08, max_x=0.0, max_y=0.0)
    for curl_frac in (None, 0.0, 0.3, 0.7, 1.0):
        got = action_to_body_offset(action, cfg, curl_frac=curl_frac)
        assert got.height == ref.height, curl_frac
        assert got == ref, curl_frac


def test_gate_on_clamps_positive_height_at_zero_curl():
    action = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])  # requests full +80mm
    cfg = _cfg(rise_height_curl_gate=1, rise_height_curl_gate_frac=0.7,
               rise_height_curl_gate_floor=0.15)
    got = action_to_body_offset(action, cfg, curl_frac=0.0)
    assert abs(got.height - 0.15 * 0.08) < 1e-9


def test_gate_on_no_clamp_past_gate_frac():
    action = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    cfg = _cfg(rise_height_curl_gate=1, rise_height_curl_gate_frac=0.7,
               rise_height_curl_gate_floor=0.15)
    got = action_to_body_offset(action, cfg, curl_frac=0.7)
    assert abs(got.height - 0.08) < 1e-9
    got_full = action_to_body_offset(action, cfg, curl_frac=1.0)
    assert abs(got_full.height - 0.08) < 1e-9


def test_gate_on_below_cap_passes_through_unchanged():
    # Requesting less height than the current cap allows must not be
    # perturbed (the gate only ever lowers an over-cap request).
    action = np.array([0.0, 0.0, 0.05, 0.0, 0.0, 0.0])  # requests +4mm of 80mm
    cfg = _cfg(rise_height_curl_gate=1, rise_height_curl_gate_frac=0.7,
               rise_height_curl_gate_floor=0.15)
    got = action_to_body_offset(action, cfg, curl_frac=0.0)
    ref = body_offset_from_action(
        action, max_roll=cfg["actions"]["max_roll_deg"], max_pitch=0.0,
        max_h=0.08, max_x=0.0, max_y=0.0)
    # cap at curl_frac=0 is 0.15*80mm=12mm > the 4mm request -> unclamped
    assert abs(got.height - action[2] * 0.08) < 1e-9


def test_gate_never_touches_negative_height():
    action = np.array([0.0, 0.0, -1.0, 0.0, 0.0, 0.0])  # full -height (lower)
    cfg = _cfg(rise_height_curl_gate=1, rise_height_curl_gate_frac=0.7,
               rise_height_curl_gate_floor=0.15)
    for curl_frac in (0.0, 0.3, 1.0):
        got = action_to_body_offset(action, cfg, curl_frac=curl_frac)
        assert abs(got.height - (-0.08)) < 1e-9, curl_frac


def test_gate_curl_frac_none_is_inert_even_when_on():
    # A caller that never plumbs curl_frac (e.g. a solved-offline BC
    # target builder) must not crash or silently gate -- curl_frac=None
    # is treated as "no gating information available", not "0 progress".
    action = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    cfg = _cfg(rise_height_curl_gate=1)
    got = action_to_body_offset(action, cfg, curl_frac=None)
    assert abs(got.height - 0.08) < 1e-9


def test_env_act_to_q_wires_live_curl_frac():
    """``SimHexapodBalanceEnv._act_to_q`` must read ``self.ik.curl_frac``
    LIVE each call (not a stale/hardcoded value) -- flip it directly
    (as the ratchet inside ``FixedFootBodyIK.solve`` would over an
    episode) and confirm the resulting joint target actually differs
    for the identical raw action."""
    import pytest
    pytest.importorskip("mujoco")
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = load_config()
    cfg.setdefault("actions", {})
    cfg["actions"]["rise_height_curl_gate"] = 1
    cfg["actions"]["rise_height_curl_gate_frac"] = 0.7
    cfg["actions"]["rise_height_curl_gate_floor"] = 0.15
    params = SimServoParams.from_cfg(cfg)
    env = SimHexapodBalanceEnv(params=params, randomize=False, dr_scale=0.0,
                               episode_seconds=2.0, seed=0, cfg=cfg)
    env.reset(seed=0)
    action = np.zeros(6, dtype=np.float32)
    # 0.3 * 80mm = 24mm -- well inside the typical rise_height_mm
    # curriculum band (default [30,70]mm), IK-feasible from a plant
    # stance at either cap so any q-mismatch is the GATE, not a
    # geometry failure at the action-space's own extreme.
    action[2] = 0.3

    env.ik.curl_frac = 0.0
    q_low, ok_low, reason_low = env._act_to_q(action)
    env.ik.curl_frac = 1.0
    q_high, ok_high, reason_high = env._act_to_q(action)

    assert ok_low, reason_low
    assert ok_high, reason_high
    assert not np.allclose(q_low, q_high), (
        "gated action mapping did not change with live curl_frac -- "
        "wiring regressed to a hardcoded value")

