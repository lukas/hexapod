"""Fast, mechanics-only tests for web_session_drivecapture.py's pure
helpers. No server, no MuJoCo, no network -- <1s total. See
RESEARCH_RULES "Tests".
"""
from rl_move.sim.web_session_drivecapture import (
    drive_cmd_rejected,
    fell_during_session,
    policy_identity_ok,
)
from rl_move.sim.drive_video import human_drive_phases, _script


def test_policy_identity_ok_accepts_a_real_matching_checkpoint():
    info = {"source": "/x/rl_move/sim/policies/champion_v1.zip",
           "obs_dim": 72, "act_dim": 18, "hidden": [256, 256, 128],
           "activation": "ELU"}
    ok, reason = policy_identity_ok(info, "champion_v1")
    assert ok is True
    assert "ELU" in reason and "256" in reason


def test_policy_identity_ok_rejects_the_scripted_fallback():
    info = {"source": "tripod_highstep_demo_gait", "obs_dim": 72,
           "act_dim": 18, "hidden": [], "activation": "scripted"}
    ok, reason = policy_identity_ok(info, "champion_v1")
    assert ok is False
    assert "scripted" in reason


def test_policy_identity_ok_rejects_a_name_mismatch():
    info = {"source": "/x/rl_move/sim/policies/other_policy.zip",
           "hidden": [256, 256, 128], "activation": "ELU"}
    ok, reason = policy_identity_ok(info, "champion_v1")
    assert ok is False
    assert "champion_v1" in reason


def test_policy_identity_ok_rejects_missing_hidden_sizes():
    info = {"source": "/x/champion_v1.zip", "hidden": [], "activation": "ELU"}
    ok, reason = policy_identity_ok(info, "champion_v1")
    assert ok is False
    assert "hidden" in reason


def test_policy_identity_ok_rejects_non_dict_info():
    ok, reason = policy_identity_ok(None, "champion_v1")
    assert ok is False


def test_fell_during_session_detects_the_down_suffix():
    assert fell_during_session("fell over; DOWN") is True
    assert fell_during_session("drive session active") is False
    assert fell_during_session("") is False
    assert fell_during_session(None) is False


def test_drive_cmd_rejected_catches_the_silent_too_low_regression():
    # This is the exact status string the champion's real session showed
    # (2026-09-10 first capture): drive/cmd kept returning ok=True/
    # active=True while silently refusing to re-engage the walk gait.
    assert drive_cmd_rejected("too low to walk - stand first") is True
    assert drive_cmd_rejected("stand first before driving") is True
    assert drive_cmd_rejected("robot is down - reset or recover first") is True
    assert drive_cmd_rejected("drive session active") is False
    assert drive_cmd_rejected("") is False
    assert drive_cmd_rejected(None) is False


def test_human_drive_phases_matches_the_inline_script_bit_exactly():
    # human_drive_phases() is the extracted single source of truth for
    # _script("human", ...) -- confirm the refactor changed nothing.
    speed = 0.07
    phases = human_drive_phases(speed)
    labels = [p[4] for p in phases]
    assert labels == ["forward", "crab-right", "diag-left", "reverse",
                      "stop", "restart", "final-stop"]
    vx, vy, wz, script_labels = _script(
        "human", seconds=26.0, dt=0.02, speed=speed, blend_s=0.5)
    # every phase's label must appear verbatim in the rendered script
    for label in labels:
        assert label in script_labels
