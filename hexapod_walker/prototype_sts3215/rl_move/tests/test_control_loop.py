"""Clock-only cadence mechanics; no simulator, hardware, sleeps or rate gates."""
import pytest

from rl_move.control_loop import CadenceStats


def test_configured_rate_is_not_reported_as_a_measurement():
    stats = CadenceStats(0.01)
    stats.observe(100.0)
    report = stats.summary()
    assert report["target_hz"] == 100.0
    assert report["measured_hz"] is None
    assert report["mean_period_ms"] is None
    assert report["recent_p99_period_ms"] is None


def test_period_includes_logging_and_publication_between_ticks():
    stats = CadenceStats(0.01, grace_s=0.002)
    stats.observe(0.0)
    # Even if timed control work fits in 10 ms, another 10 ms spent
    # logging/publishing before the next start belongs to the real period.
    stats.observe(0.02)
    stats.observe(0.04)
    report = stats.summary()
    assert report["measured_hz"] == 50.0
    assert report["mean_period_ms"] == 20.0
    assert report["max_period_ms"] == 20.0
    assert report["late_intervals"] == 2


def test_percentiles_are_bounded_but_total_rate_retains_long_stalls():
    stats = CadenceStats(0.01, window_size=2)
    for start in (0.0, 0.1, 0.11, 0.12):
        stats.observe(start)
    report = stats.summary()
    assert report["intervals"] == 3
    assert report["measured_hz"] == 25.0
    assert report["max_period_ms"] == 100.0
    assert report["recent_intervals"] == 2
    assert report["recent_p95_period_ms"] == 10.0
    assert report["recent_p99_period_ms"] == 10.0


def test_late_grace_boundary_and_percentile_interpolation():
    stats = CadenceStats(0.01, grace_s=0.002)
    for start in (1.0, 1.012, 1.026):
        stats.observe(start)
    report = stats.summary()
    assert report["late_intervals"] == 1
    assert report["recent_p95_period_ms"] == 13.9
    assert report["recent_p99_period_ms"] == 13.98


def test_invalid_or_nonadvancing_timestamps_do_not_invent_intervals():
    stats = CadenceStats(0.01)
    for start in (2.0, float("nan"), float("inf"), 2.0, 1.0, 2.01):
        stats.observe(start)
    assert stats.summary()["intervals"] == 1
    assert stats.measured_hz == pytest.approx(100.0)


@pytest.mark.parametrize("period", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_period_is_rejected(period):
    with pytest.raises(ValueError):
        CadenceStats(period)


def test_runner_summary_keeps_stage_cost_separate_from_whole_loop_cadence():
    from rl_policy import _TimingStats

    stats = _TimingStats(0.01)
    stats.cadence.observe(0.0)
    stats.add({"service_s": 0.009})
    stats.cadence.observe(0.02)
    stats.add({"service_s": 0.009})
    report = stats.summary()
    assert report["mean_service_ms"] == 9.0
    assert report["cadence"]["measured_hz"] == 50.0
