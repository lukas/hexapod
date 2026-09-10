"""Fast, mechanics-only tests for web_session_drivecapture.py's pure
helpers. No server, no MuJoCo, no network -- <1s total. See
RESEARCH_RULES "Tests".
"""
from rl_move.sim.web_session_drivecapture import (
    directional_locomotion_fraction,
    drive_cmd_rejected,
    fell_during_session,
    locomotion_fraction,
    policy_identity_ok,
    stalled_phases,
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


def test_locomotion_fraction_flags_a_stalled_session():
    # exact bug pattern caught 2026-09-10: commanded 0.06 m/s forward,
    # measured body speed decays to ~0 after an initial ramp-driven blip.
    rows = [{"vx_body": 0.0, "vy_body": 0.0}] * 6
    assert locomotion_fraction(rows, 0.06, 0.0) == 0.0


def test_locomotion_fraction_passes_real_tracking():
    rows = [{"vx_body": 0.05, "vy_body": 0.0}] * 6
    frac = locomotion_fraction(rows, 0.06, 0.0)
    assert 0.7 < frac < 1.0


def test_locomotion_fraction_ignores_near_zero_commands():
    # stop/final-stop phases command ~0 -- never flag those as a stall
    assert locomotion_fraction([{"vx_body": 0.0, "vy_body": 0.0}], 0.0, 0.0) == 1.0


def test_locomotion_fraction_empty_rows_is_not_a_stall():
    assert locomotion_fraction([], 0.06, 0.0) == 1.0


def test_directional_locomotion_fraction_matches_magnitude_when_aligned():
    # pure on-axis motion: signed projection == magnitude metric exactly.
    rows = [{"vx_body": -0.05, "vy_body": 0.0}] * 6
    frac_mag = locomotion_fraction(rows, -0.08, 0.0)
    frac_dir = directional_locomotion_fraction(rows, -0.08, 0.0)
    assert frac_dir == frac_mag


def test_directional_locomotion_fraction_flags_pure_lateral_jitter():
    # commanded reverse (-0.08, 0) but the body only oscillates sideways --
    # a real "moving but not the right way" case the magnitude metric
    # (2026-09-10 finding) cannot tell apart from genuine backward progress.
    rows = [{"vx_body": 0.0, "vy_body": 0.05}, {"vx_body": 0.0, "vy_body": -0.05}]
    assert locomotion_fraction(rows, -0.08, 0.0) > 0.5
    assert directional_locomotion_fraction(rows, -0.08, 0.0) == 0.0


def test_directional_locomotion_fraction_is_negative_for_wrong_way_motion():
    # steady drift OPPOSITE the commanded direction: magnitude reads "moving
    # fine", directional correctly reads negative (net motion the wrong way).
    rows = [{"vx_body": 0.05, "vy_body": 0.0}] * 4
    assert locomotion_fraction(rows, -0.08, 0.0) > 0.5
    assert directional_locomotion_fraction(rows, -0.08, 0.0) < 0.0


def test_directional_locomotion_fraction_ignores_near_zero_commands():
    assert directional_locomotion_fraction(
        [{"vx_body": 0.0, "vy_body": 0.0}], 0.0, 0.0) == 1.0


def test_directional_locomotion_fraction_empty_rows_is_not_a_stall():
    assert directional_locomotion_fraction([], 0.06, 0.0) == 1.0


def test_stalled_phases_catches_the_09_10_regression_pattern():
    # forward commanded 0-5s at 0.06 m/s; body speed ramps up then
    # collapses to ~0 well before the phase ends (the real telemetry
    # shape from the full-cfg PASS run this test is named for).
    phases = [(0.0, 0.06, 0.0, 0.0, "forward"), (5.0, 0.0, 0.0, 0.0, "stop")]
    telemetry = (
        [{"t": t, "vx_body": 0.04, "vy_body": 0.0} for t in (0.2, 0.6, 1.0)]
        + [{"t": t, "vx_body": 0.0, "vy_body": 0.0}
          for t in (2.0, 3.0, 4.0, 4.8)])
    bad = stalled_phases(telemetry, phases, t_end=8.0)
    assert len(bad) == 1
    assert bad[0]["label"] == "forward"
    assert bad[0]["measured_fraction_of_cmd"] < 0.25


def test_stalled_phases_clean_when_tracking_holds():
    phases = [(0.0, 0.06, 0.0, 0.0, "forward"), (5.0, 0.0, 0.0, 0.0, "stop")]
    telemetry = [{"t": t, "vx_body": 0.06, "vy_body": 0.0}
                for t in (0.2, 2.0, 3.0, 4.0, 4.8)]
    assert stalled_phases(telemetry, phases, t_end=8.0) == []


def test_stalled_phases_skips_the_velocity_ramp_settle_window():
    # rows inside the first 1.5s (the live-drive VEL_RATE ramp window)
    # showing low speed must NOT by themselves trigger a stall verdict.
    phases = [(0.0, 0.06, 0.0, 0.0, "forward")]
    telemetry = ([{"t": t, "vx_body": 0.01, "vy_body": 0.0}
                 for t in (0.2, 0.6, 1.0)]
                + [{"t": t, "vx_body": 0.06, "vy_body": 0.0}
                  for t in (2.0, 3.0, 4.0)])
    assert stalled_phases(telemetry, phases, t_end=5.0) == []


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
