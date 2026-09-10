"""Fast, mechanics-only tests for web_session_drivecapture.py's pure
helpers. No server, no MuJoCo, no network -- <1s total. See
RESEARCH_RULES "Tests".
"""
from rl_move.sim.web_session_drivecapture import (
    _row_t,
    directional_locomotion_fraction,
    drive_cmd_rejected,
    fell_during_session,
    locomotion_fraction,
    net_displacement_fraction,
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


def test_net_displacement_fraction_matches_steady_on_axis_motion():
    # yaw stays 0 (no turning), body walks straight along its own +x axis
    # at exactly the commanded speed for 1s -- true displacement equals
    # commanded speed * duration, so the fraction should read ~1.0.
    rows = [{"t": 0.0, "pos_x": 0.0, "pos_y": 0.0, "yaw_deg": 0.0},
           {"t": 1.0, "pos_x": 0.06, "pos_y": 0.0, "yaw_deg": 0.0}]
    frac = net_displacement_fraction(rows, 0.06, 0.0)
    assert abs(frac - 1.0) < 1e-9


def test_net_displacement_fraction_rotates_by_yaw_at_window_start():
    # body yaw is 90deg (facing world +y) but the command is still
    # expressed in the BODY frame as (+0.06, 0) == "forward" -- world
    # displacement should be along world +y, and the metric must rotate
    # it back into the body frame before projecting, still reading ~1.0.
    rows = [{"t": 0.0, "pos_x": 0.0, "pos_y": 0.0, "yaw_deg": 90.0},
           {"t": 1.0, "pos_x": 0.0, "pos_y": 0.06, "yaw_deg": 90.0}]
    frac = net_displacement_fraction(rows, 0.06, 0.0)
    assert abs(frac - 1.0) < 1e-9


def test_net_displacement_fraction_reads_near_zero_for_pure_jitter():
    # oscillating in place: the SAMPLE-MEAN of an aliased velocity signal
    # might read high (the exact failure mode this metric exists to
    # catch), but true net displacement over the window is ~0 regardless
    # of how many oscillations happened in between.
    rows = [{"t": 0.0, "pos_x": 0.0, "pos_y": 0.10, "yaw_deg": 0.0},
           {"t": 1.0, "pos_x": 0.002, "pos_y": 0.09, "yaw_deg": 0.0}]
    frac = net_displacement_fraction(rows, -0.08, 0.0)
    assert abs(frac) < 0.1


def test_net_displacement_fraction_none_when_position_missing():
    # older telemetry (pre-2026-09-10) has no pos_x/pos_y/yaw_deg --
    # must report "no data" (None), not silently read as 0 or 1.
    rows = [{"t": 0.0, "vx_body": 0.05}, {"t": 1.0, "vx_body": 0.05}]
    assert net_displacement_fraction(rows, 0.06, 0.0) is None


def test_net_displacement_fraction_ignores_near_zero_commands():
    assert net_displacement_fraction(
        [{"t": 0.0, "pos_x": 0.0, "pos_y": 0.0, "yaw_deg": 0.0},
         {"t": 1.0, "pos_x": 0.0, "pos_y": 0.0, "yaw_deg": 0.0}],
        0.0, 0.0) is None


def test_net_displacement_fraction_needs_at_least_two_rows():
    assert net_displacement_fraction(
        [{"t": 0.0, "pos_x": 0.0, "pos_y": 0.0, "yaw_deg": 0.0}],
        0.06, 0.0) is None
    assert net_displacement_fraction([], 0.06, 0.0) is None


def test_row_t_prefers_sim_time_over_wall_clock():
    # 2026-09-10 root-cause fix: when the row carries the server's own
    # simulated time (``sim_t_s``), that is the correct time base for
    # phase/window logic, not the HTTP-poll wall clock -- the two can
    # differ substantially when the server steps physics slower than
    # real time (measured ~0.28x on the controller pod).
    assert _row_t({"t": 5.0, "sim_t_s": 1.4}) == 1.4


def test_row_t_falls_back_to_wall_clock_for_older_telemetry():
    assert _row_t({"t": 5.0}) == 5.0


def test_net_displacement_fraction_uses_sim_time_not_wall_clock():
    # Same true motion (0.06m over 1 SIMULATED second == exactly the
    # commanded speed) but wall-clock elapsed is artificially inflated
    # to 3s (as it would be under ~0.33x real-time server throughput).
    # Using wall-clock dt would read the fraction ~3x too LOW; using
    # sim_t_s (the fix) reads the correct ~1.0.
    rows = [{"t": 0.0, "sim_t_s": 0.0, "pos_x": 0.0, "pos_y": 0.0,
            "yaw_deg": 0.0},
           {"t": 3.0, "sim_t_s": 1.0, "pos_x": 0.06, "pos_y": 0.0,
            "yaw_deg": 0.0}]
    frac = net_displacement_fraction(rows, 0.06, 0.0)
    assert abs(frac - 1.0) < 1e-9


def test_stalled_phases_uses_sim_time_to_place_rows_in_the_right_phase():
    # wall-clock ``t`` would put every row in the SECOND phase (all
    # t>=5), but sim_t_s (the true, much-slower-advancing clock) keeps
    # them in the FIRST phase's settle window -- the fix must window on
    # sim_t_s, not wall-clock t, or this reads the wrong phase entirely.
    phases = [(0.0, 0.08, 0.0, 0.0, "forward"),
             (5.0, 0.0, -0.08, 0.0, "crab-right")]
    telemetry = [
        {"t": 6.0, "sim_t_s": 1.6, "vx_body": 0.08, "vy_body": 0.0},
        {"t": 6.2, "sim_t_s": 1.8, "vx_body": 0.08, "vy_body": 0.0},
    ]
    # Rows are inside the "forward" phase's settled window in SIM time
    # (1.5 <= sim_t_s < 5.0) even though wall-clock t (6.0-6.2) already
    # looks like the crab-right phase -- locomotion_fraction on these
    # rows tracks the FORWARD command well, so no stall should fire.
    out = stalled_phases(telemetry, phases, t_end=9.0)
    assert out == []


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
