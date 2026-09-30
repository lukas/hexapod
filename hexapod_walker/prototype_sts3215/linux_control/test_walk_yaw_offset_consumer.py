"""rl_policy: the walk_yaw_offset_cmd (obs-74 turn-and-hold) hardware
consumer -- _resolve_yaw_offset_request (request validation) and
YawOffsetTracker (live achieved-rotation integration). See
rl_move/deployed_policy.py's module docstring for the width-74
phase-vs-offset ambiguity this closes, and walkcurr STATUS.md item 3
("linux_control has no consumer for walk_yaw_offset_cmd")."""
from __future__ import annotations

import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

import rl_policy  # noqa: E402

_OFFSET_META = {
    "walk_yaw_offset_cmd": True,
    "obs_dim": 74,
    "walk_yaw_offset_set": [15, 30, 45, 90, -15, -30, -45, -90],
}


def test_non_offset_policy_bit_exact_default_path():
    assert rl_policy._resolve_yaw_offset_request(
        {"obs_dim": 74}, None, None, 0.0, 0.0) == (False, 0.0, None)


def test_non_offset_policy_rejects_yaw_offset_deg():
    cmd, target, err = rl_policy._resolve_yaw_offset_request(
        {"obs_dim": 74}, 30.0, None, 0.0, 0.0)
    assert not cmd and target == 0.0
    assert "no walk_yaw_offset_cmd" in err


def test_offset_policy_defaults_to_hold_current_heading():
    cmd, target, err = rl_policy._resolve_yaw_offset_request(
        _OFFSET_META, None, None, 0.0, 0.0)
    assert err is None
    assert cmd is True
    assert target == pytest.approx(0.0)


def test_offset_policy_accepts_a_trained_offset():
    cmd, target, err = rl_policy._resolve_yaw_offset_request(
        _OFFSET_META, 30.0, None, 0.0, 0.0)
    assert err is None and cmd is True
    assert target == pytest.approx(math.radians(30.0))


def test_offset_policy_rejects_an_untrained_offset():
    _, _, err = rl_policy._resolve_yaw_offset_request(
        _OFFSET_META, 20.0, None, 0.0, 0.0)
    assert "trained offsets" in err


def test_offset_policy_rejects_nonzero_translation():
    _, _, err = rl_policy._resolve_yaw_offset_request(
        _OFFSET_META, 30.0, None, 0.05, 0.0)
    assert "vx and vy must be 0" in err


def test_offset_policy_rejects_turn(): 
    _, _, err = rl_policy._resolve_yaw_offset_request(
        _OFFSET_META, 30.0, "left", 0.0, 0.0)
    assert "turn=" in err


def test_offset_policy_requires_obs74():
    bad_meta = dict(_OFFSET_META, obs_dim=75)
    _, _, err = rl_policy._resolve_yaw_offset_request(
        bad_meta, 30.0, None, 0.0, 0.0)
    assert "!= 74" in err


def test_yaw_offset_tracker_integrates_gyro_and_reports_remaining():
    tracker = rl_policy.YawOffsetTracker(math.radians(30.0))
    dt = 0.02
    for _ in range(int(1.0 / dt)):
        # 30 deg/s about z -> reaches the 30 deg target in exactly 1 s.
        target, remaining = tracker.update(math.radians(30.0), dt)
    assert target == pytest.approx(math.radians(30.0))
    assert remaining == pytest.approx(0.0, abs=1e-6)


def test_yaw_offset_tracker_starts_at_zero_achieved():
    tracker = rl_policy.YawOffsetTracker(math.radians(45.0))
    assert tracker.achieved_rad == 0.0
    target, remaining = tracker.update(0.0, 0.02)
    assert remaining == pytest.approx(target)
