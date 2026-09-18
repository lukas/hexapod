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
