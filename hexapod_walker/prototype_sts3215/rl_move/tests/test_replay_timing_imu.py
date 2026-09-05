import csv
import json

from rl_move.sim.replay_timing_imu import (
    ATTEMPT_PROFILE,
    CURRENT_PROFILE,
    ReplayConfig,
    analyze_recorded_trace,
    build_report,
    run_matrix,
)

FIELDS = [
    "t_s", "phase", "service_ms", "obs_ms", "policy_ms", "safety_ms",
    "write_ms", "read_ms", "lag_ms", "imu_age_ms", "position_age_ms",
    "learned_policy_active",
]


def _rows():
    rows = []
    for tick in range(20):
        stalled = tick >= 8
        rows.append({
            "t_s": f"{tick / 100:.2f}",
            "phase": "walk",
            "service_ms": "13.1" if stalled else "8.5",
            "obs_ms": "0.3",
            "policy_ms": "0.4",
            "safety_ms": "0.6",
            "write_ms": "9.3" if stalled else "4.7",
            "read_ms": "0.0",
            "lag_ms": "3.1" if stalled else "0.0",
            "imu_age_ms": str(12 + 10 * (tick - 8)) if stalled else "2.0",
            "position_age_ms": "1.0",
            "learned_policy_active": "1",
        })
    return rows


def test_recorded_trace_replays_deadline_stop_and_attributes_write_cost():
    cfg = ReplayConfig()
    events = [{
        "event": "debug_end",
        "result": {"error": "drive timing overrun: 12 consecutive ticks "
                            "missed the 100 Hz deadline"},
    }]
    report = analyze_recorded_trace(_rows(), events, cfg)
    assert report["reproduction"]["ok"] is True
    assert report["reproduction"]["max_consecutive_late"] == 12
    assert report["stall_window"]["start_index"] == 8
    assert report["derived_coupled_refresh_cost_ms"] == 4.6


def test_fault_matrix_is_repeatable_and_keeps_freshness_fail_closed():
    cfg = ReplayConfig(duration_s=2.0, repetitions=10)
    recorded = {
        "baseline_service_ms": 8.9,
        "derived_coupled_refresh_cost_ms": 4.6,
    }
    matrix = run_matrix(
        recorded, cfg, imu_delays_ms=[0, 50], failure_counts=[0, 3]
    )
    assert matrix["all_repetitions_deterministic"] is True
    cases = {
        (case["profile"], case["imu_delay_ms"],
         case["consecutive_imu_read_failures"]): case
        for case in matrix["cases"]
    }
    assert cases[(ATTEMPT_PROFILE, 0.0, 3)]["stop_reason"] == (
        "deadline_miss_streak"
    )
    assert cases[(CURRENT_PROFILE, 0.0, 3)]["completed"] is True
    assert cases[(CURRENT_PROFILE, 50.0, 3)]["stop_reason"] == (
        "attitude_freshness"
    )
    assert all(case["repetitions"] == 10 for case in matrix["cases"])


def test_build_report_hashes_inputs_and_preserves_guards(tmp_path):
    trace = tmp_path / "trace.csv"
    with trace.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(_rows())
    debug = tmp_path / "debug.jsonl"
    debug.write_text(json.dumps({
        "event": "debug_end",
        "result": {"error": "drive timing overrun: 12 consecutive ticks "
                            "missed the 100 Hz deadline"},
    }) + "\n")
    report = build_report(
        trace_path=trace,
        debug_path=debug,
        cfg=ReplayConfig(duration_s=2.0, repetitions=2),
        attempt_revision="old",
        candidate_revision="new",
        imu_delays_ms=[0],
        failure_counts=[3],
    )
    assert report["simulation_only"] is True
    assert report["guards"] == {
        "attitude_freshness_ms": 150.0,
        "deadline_late_grace_ms": 2.0,
        "deadline_miss_streak_limit": 12,
        "changed": False,
    }
    assert len(report["sources"]["trace_sha256"]) == 64
    assert len(report["fault_matrix"]["cases"]) == 2
