"""gait_sweep analysis: IMU metrics, chassis tracking, and the scorecard verdict."""
import gait_sweep


def test_imu_metrics_use_walk_phase_only():
    rows = [{"phase": "stand", "roll_deg": "30", "pitch_deg": "0"},
            {"phase": "walk", "roll_deg": "3", "pitch_deg": "4", "max_cur_a": "0.5"},
            {"phase": "walk", "roll_deg": "-3", "pitch_deg": "0", "max_cur_a": "0.7"}]
    m = gait_sweep.imu_metrics(rows)
    assert m["walk_ticks"] == 2 and m["roll_peak"] == 3.0 and m["roll_rms"] == 3.0
    assert m["pitch_peak"] == 4.0 and m["max_cur_a"] == 0.7


def _vision(tag, xs, t0=100.0):
    return [{"capture_unix": t0 + i, "markers": {tag: {"status": "tracked", "position_mm": {"x": x, "y": 0.0}, "yaw": 10.0 + i},
                                                   "105": {"status": "tracked", "position_mm": {"x": 0, "y": 0}, "yaw": 0}}}
            for i, x in enumerate(xs)]


def test_chassis_track_prefers_the_chassis_tag_and_ignores_floor_tags():
    v = _vision("119", [0, 100, 200, 300, 400])
    c = gait_sweep.chassis_track(v, 100.0, 104.0, {105}, "119")
    assert c["tag"] == "119" and c["chassis"] and c["net_mm"] == 400.0 and c["mm_s"] == 100.0
    assert c["coverage"] == 1.0 and c["heading_chg_deg"] == 4.0


def test_chassis_track_falls_back_to_best_covered_tag_and_reports_coverage():
    v = _vision("18", [0, 50, 100, 150, 200, 250])
    del v[3]["markers"]["18"]; del v[4]["markers"]["18"]; del v[5]["markers"]["18"]  # occluded for the second half
    c = gait_sweep.chassis_track(v, 100.0, 105.0, {105}, "119")
    assert c["tag"] == "18" and not c["chassis"] and c["coverage"] == 0.4


def test_verdict_is_inconclusive_when_walks_were_cut_short():
    rows = [{"active_s": 1.8, "roll_rms": 0.8, "cam": {"mm_s": 50, "heading_chg_deg": 2}},
            {"active_s": 0.6, "roll_rms": 0.9, "cam": {"mm_s": 40, "heading_chg_deg": 1}}]
    v, why = gait_sweep.verdict(rows, 3.0)
    assert v == "inconclusive" and "0 of 2" in why


def test_verdict_grades_full_exposures():
    good = [{"active_s": 5.2, "roll_rms": 1.2, "cam": {"mm_s": 61, "heading_chg_deg": -1}},
            {"active_s": 5.0, "roll_rms": 1.3, "cam": {"mm_s": 28, "heading_chg_deg": -11}}]
    assert gait_sweep.verdict(good, 6.0)[0] == "promising"
    slow = [dict(r, cam={"mm_s": 5, "heading_chg_deg": 0}) for r in good]
    assert gait_sweep.verdict(slow, 6.0)[0] == "poor"
    veering = [dict(r, cam={"mm_s": 38, "heading_chg_deg": 24}) for r in good]
    assert gait_sweep.verdict(veering, 6.0)[0] == "ok"


def test_next_direction_alternates_until_the_robot_has_drifted_then_heads_back():
    nd = gait_sweep.next_direction
    assert nd(1.0, (0, 0), (100, 0), True, 300) == -1.0          # inside the box: alternate
    assert nd(1.0, (0, 0), (400, 0), True, 300) == -1.0          # drifted, last pass took it away: reverse
    assert nd(-1.0, (0, 0), (400, 0), False, 300) == -1.0        # drifted, last pass brought it closer: keep going
    assert nd(1.0, None, None, None, 300) == -1.0                # no camera: plain alternation


def test_inside_box():
    assert gait_sweep.inside_box((0, 0), (-1, 1, -1, 1)) and not gait_sweep.inside_box((2, 0), (-1, 1, -1, 1))
    assert gait_sweep.inside_box(None, (-1, 1, -1, 1)) and gait_sweep.inside_box((5, 5), None)


def test_steer_command_turns_toward_target_and_only_advances_when_aligned():
    cal = {"heading_offset_deg": 0.0, "yaw_sign": 1.0}
    # facing +x (yaw 0), target straight ahead at +x: go forward, no turn
    vx, wz = gait_sweep.steer_command((0, 0), 0.0, (1000, 0), cal)
    assert vx > 0.05 and abs(wz) < 1e-6
    # target behind (-x): facing 180 deg away -> do not advance, turn hard
    vx, wz = gait_sweep.steer_command((0, 0), 0.0, (-1000, 0), cal)
    assert vx == 0.0 and abs(wz) > 0.2
    # target 90 deg to the left (+y): turn, creep
    vx, wz = gait_sweep.steer_command((0, 0), 0.0, (0, 1000), cal)
    assert wz > 0 and vx < 0.02


def test_steer_command_respects_a_flipped_yaw_sign():
    left = gait_sweep.steer_command((0, 0), 0.0, (0, 1000), {"heading_offset_deg": 0.0, "yaw_sign": 1.0})[1]
    right = gait_sweep.steer_command((0, 0), 0.0, (0, 1000), {"heading_offset_deg": 0.0, "yaw_sign": -1.0})[1]
    assert left == -right and left > 0


def test_steer_command_applies_the_heading_offset():
    # chassis tag reads yaw 90 while the body actually walks along floor +x: offset -90
    cal = {"heading_offset_deg": -90.0, "yaw_sign": 1.0}
    vx, wz = gait_sweep.steer_command((0, 0), 90.0, (1000, 0), cal)
    assert vx > 0.05 and abs(wz) < 1e-6


def test_reached():
    assert gait_sweep.reached((0, 0), (100, 100), 180)
    assert not gait_sweep.reached((0, 0), (300, 300), 180)
