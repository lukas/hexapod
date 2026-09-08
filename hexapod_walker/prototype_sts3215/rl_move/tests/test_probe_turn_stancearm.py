"""Feasibility must inspect raw IK, not TripodGait's finite fallback."""
import sys

import pytest

from rl_move.sim import probe_turn_stancearm as probe


CELLS = [(0.08, 0.15), (0.08, -0.15), (0.08, 0.0)]


@pytest.mark.parametrize("fail_at", [1, 17])
def test_raw_ik_failure_cannot_pass_via_finite_gait_fallback(monkeypatch, fail_at):
    # Patch the actual global read by desired_deg, not a similarly named
    # import in another module. TripodGait turns None into its neutral pose.
    module = sys.modules[probe.TripodGait.__module__]
    original = module._leg_ik
    calls = 0

    def fail_once(target):
        nonlocal calls
        calls += 1
        return None if calls == fail_at else original(target)

    monkeypatch.setattr(module, "_leg_ik", fail_once)
    with pytest.raises(SystemExit, match="raw IK failed"):
        probe.feasibility_guard(20.0, 100.0, CELLS)
    assert module._leg_ik is fail_once


@pytest.mark.parametrize("knee,expected_margins", [
    (100.0, [19.613218251838322, 18.24994375209038, 45.268249966008966]),
    (90.0, [23.206057347917458, 19.56827403559784, 55.09423461416756]),
])
def test_real_baseline_and_extended_stance_keep_original_margins(
        knee, expected_margins):
    module = sys.modules[probe.TripodGait.__module__]
    original = module._leg_ik
    result = probe.feasibility_guard(20.0, knee, CELLS)
    assert result["raw_ik_calls"] == 7200
    assert result["raw_ik_failures"] == 0
    assert [result["joint_margins"][axis]["margin_deg"]
            for axis in ("yaw", "hip", "knee")] == pytest.approx(
                expected_margins, rel=0, abs=1e-12)
    assert module._leg_ik is original


def test_raw_ik_function_restored_after_unexpected_error(monkeypatch):
    module = sys.modules[probe.TripodGait.__module__]

    def broken_ik(target):
        raise RuntimeError("unexpected IK error")

    monkeypatch.setattr(module, "_leg_ik", broken_ik)
    with pytest.raises(RuntimeError, match="unexpected IK error"):
        probe.feasibility_guard(20.0, 100.0, CELLS)
    assert module._leg_ik is broken_ik
