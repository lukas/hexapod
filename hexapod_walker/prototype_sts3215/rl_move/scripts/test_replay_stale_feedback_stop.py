import json
from pathlib import Path

import pytest

from rl_move.scripts.replay_stale_feedback_stop import replay


def test_replays_sealed_terminal_stop():
    source = Path.home() / "Library/Application Support/Hexapod Lab/data/experiments/6a632f8ba4bc4b14812e27e6f87eaa42"
    if not source.is_dir():
        pytest.skip("sealed Robot Lab source is not installed")
    report, timeline = replay(
        source,
        expected_manifest_sha256="ee01117989adc676d03ee2653ec34dac82e6c11e21fdf40b6e0770ca4d9ba258",
    )
    assert timeline[-1]["terminal"] is True
    assert timeline[-1]["stale_ticks"] == 11
    assert report["sampler_error_classification"]["errors"] == 2
    assert report["sampler_error_classification"]["physical_rejects"] == 0
    assert report["write_due_and_overrun_correlation"]["terminal_was_skip_write_tick"] is True
    assert report["hold_after_loss_timing"]["hold_begin_to_fresh_sample_ms"] > 80
    assert report["contract"]["simulation_only"] is True
    json.dumps(report)
