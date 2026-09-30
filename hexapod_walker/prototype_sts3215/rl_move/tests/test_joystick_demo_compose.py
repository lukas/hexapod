"""Pure-function mechanics for joystick_demo_compose.py (walkcurr Next
item 2, 2026-09-30: joystick-driven render of the frozen
walk+turn-hold role composition). No MuJoCo/env/model -- role-switch
routing and offset-clamp math only, per RESEARCH_RULES "Tests"
(mechanics, not measurements; no rollout-ranking).
"""
from __future__ import annotations

import math

import pytest

from rl_move.sim.joystick_demo_compose import (
    TURN_OFFSET_CLAMP_DEG, WZ_EPS, joystick_script, resolve_roles,
)


def test_joystick_script_unknown_name_raises():
    with pytest.raises(ValueError):
        joystick_script("nope")


@pytest.mark.parametrize("name", ["demo1", "turns_only", "smoke"])
def test_joystick_script_segments_have_required_fields(name):
    segs = joystick_script(name)
    assert len(segs) > 0
    for seg in segs:
        assert set(seg) >= {"duration_s", "vx", "vy", "wz", "label"}
        assert seg["duration_s"] > 0.0


def test_resolve_roles_pure_translate_routes_to_walk():
    segs = [{"duration_s": 5.0, "vx": 0.06, "vy": 0.0, "wz": 0.0,
             "label": "fwd"}]
    out = resolve_roles(segs)
    assert len(out) == 1
    assert out[0]["role"] == "walk"
    assert out[0]["speed"] == pytest.approx(0.06)
    assert out[0]["heading_deg"] == pytest.approx(0.0)


def test_resolve_roles_lateral_translate_heading_90():
    segs = [{"duration_s": 5.0, "vx": 0.0, "vy": 0.05, "wz": 0.0,
             "label": "strafe"}]
    out = resolve_roles(segs)
    assert out[0]["role"] == "walk"
    assert out[0]["heading_deg"] == pytest.approx(90.0)


def test_resolve_roles_zero_speed_walk_heading_defaults_zero():
    segs = [{"duration_s": 2.0, "vx": 0.0, "vy": 0.0, "wz": 0.0,
             "label": "stop"}]
    out = resolve_roles(segs)
    assert out[0]["role"] == "walk"
    assert out[0]["speed"] == 0.0
    assert out[0]["heading_deg"] == 0.0


def test_resolve_roles_nonzero_wz_routes_to_turn_and_integrates_offset():
    # small enough offset (wz*dur) to stay under the clamp, so the
    # exact integrated value is checked unclamped.
    wz, dur = 0.05, 4.0  # -> ~11.46 deg, well under the 30deg clamp
    segs = [{"duration_s": dur, "vx": 0.0, "vy": 0.0, "wz": wz,
             "label": "turn"}]
    out = resolve_roles(segs)
    assert out[0]["role"] == "turn"
    expected = math.degrees(wz * dur)
    assert out[0]["offset_deg"] == pytest.approx(expected)
    assert out[0]["clamped"] is False


def test_resolve_roles_turn_offset_clamped_to_band():
    # large wz*dur must clamp to +/- TURN_OFFSET_CLAMP_DEG, sign preserved
    segs = [
        {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": 0.35,
         "label": "turn-left"},
        {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": -0.35,
         "label": "turn-right"},
    ]
    out = resolve_roles(segs)
    assert out[0]["offset_deg"] == pytest.approx(TURN_OFFSET_CLAMP_DEG)
    assert out[0]["clamped"] is True
    assert out[1]["offset_deg"] == pytest.approx(-TURN_OFFSET_CLAMP_DEG)
    assert out[1]["clamped"] is True


def test_resolve_roles_turn_carries_curve_speed_from_vx_vy():
    segs = [{"duration_s": 8.0, "vx": 0.06, "vy": 0.0, "wz": 0.35,
             "label": "curve-left"}]
    out = resolve_roles(segs)
    assert out[0]["role"] == "turn"
    assert out[0]["curve_speed"] == pytest.approx(0.06)


def test_resolve_roles_boundary_wz_at_eps_is_walk_not_turn():
    segs = [{"duration_s": 3.0, "vx": 0.02, "vy": 0.0, "wz": WZ_EPS,
             "label": "edge"}]
    out = resolve_roles(segs)
    assert out[0]["role"] == "walk"


def test_demo1_script_alternates_walk_and_turn_roles():
    out = resolve_roles(joystick_script("demo1"))
    roles = [r["role"] for r in out]
    assert roles == ["walk", "turn", "walk", "turn", "walk", "turn",
                      "walk"]
