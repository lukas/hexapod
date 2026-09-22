"""The sit-down mode in standup_modes.json must stay inside hexapod2's mechanical box and end at zero."""
import json
from pathlib import Path

from hexapod_core.joint_frame import joint_index

MODES = Path(__file__).with_name("standup_modes.json")


def _lower():
    return json.loads(MODES.read_text())["modes"]["lower"]


def test_lower_mode_is_down_only_and_inside_the_mechanical_box():
    m = _lower()
    assert m["down_only"] is True
    hips = [f["q_deg"][joint_index(l, "hip")] for f in m["keyframes"] for l in range(6)]
    knees = [f["q_deg"][joint_index(l, "knee")] for f in m["keyframes"] for l in range(6)]
    yaws = [f["q_deg"][joint_index(l, "yaw")] for f in m["keyframes"] for l in range(6)]
    assert min(hips) >= -40.0, "femur meets hexapod2's top chassis near -55; the old sit went to -78"
    assert max(knees) <= 110.0, "knee stop ~140 / fold cap 135; the old sit went to 146"
    assert max(abs(y) for y in yaws) < 1e-6
    assert m["keyframes"][0]["q_deg"][joint_index(0, "hip")] == 20.0      # starts at the STEP stance
    assert m["keyframes"][0]["q_deg"][joint_index(0, "knee")] == 80.0
    assert all(abs(v) < 1e-6 for v in m["keyframes"][-1]["q_deg"])          # ends at zero (lab _down: knees < 20)
    assert 6.0 <= m["total_s"] <= 20.0


def test_lower_descent_is_slow_and_monotonic():
    m = _lower()
    hips0 = [f["q_deg"][joint_index(0, "hip")] for f in m["keyframes"] if "descent" in f.get("phase", "")]
    assert len(hips0) >= 4
    assert all(b < a for a, b in zip(hips0, hips0[1:])), "the body comes down step by step"
    assert all(f["s"] >= 0.5 for f in m["keyframes"] if "descent" in f.get("phase", ""))
