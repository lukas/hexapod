"""Off-robot tests for passive telemetry recording/contact observation."""
from __future__ import annotations

import json
import queue
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from telemetry_recorder import (
    DEFAULT_MODEL_PATH,
    RollingContactObserver,
    TelemetryRecorder,
)
from rl_move.contact_predictor import LinearContactModel


class FakeBus:
    def __init__(self):
        self.sink = None
        self.reads = 0

    def set_telemetry_sink(self, sink) -> None:
        self.sink = sink

    def read_all_feedback(self):
        self.reads += 1
        raise AssertionError("recorder must not poll the bus")


def _plant_payload(include_command: bool = False) -> dict:
    payload = {
        "position_deg": [0.0, 20.0, 80.0] * 6,
        "speed_deg_s": [0.0] * 18,
        "current_a": [0.1] * 18,
        "load_pct": [2.0] * 18,
        "voltage_v": [12.0] * 18,
        "temperature_c": [30] * 18,
    }
    if include_command:
        payload["command_deg"] = [0.0, 20.0, 80.0] * 6
    return payload


def test_rolling_observer_uses_history_before_declaring_plant():
    observer = RollingContactObserver(DEFAULT_MODEL_PATH)
    assert observer.error is None
    outputs = []
    for sample in range(7):
        outputs.append(observer.update(
            _plant_payload(include_command=(sample == 0)),
            mono_s=10.0 + sample * 0.02,
        ))
    assert outputs[1]["ready_legs"] == 0
    assert outputs[-1]["ready_legs"] == 6
    assert outputs[-1]["planted"] == [True] * 6
    assert all(len(row["features"]) == 5 for row in outputs[-1]["legs"])


def test_online_scorer_matches_evaluated_model_math():
    payload = json.loads(DEFAULT_MODEL_PATH.read_text())
    reference = LinearContactModel.from_dict(payload["model"])
    observer = RollingContactObserver(DEFAULT_MODEL_PATH)
    features = (1.25, -0.5, 7.0, -7.0, 2.5)
    want = float(reference.predict_proba(features)[0])
    assert abs(observer._score(features) - want) < 1e-12


def test_recorder_attaches_without_reading_and_persists_session():
    with tempfile.TemporaryDirectory() as temp:
        bus = FakeBus()
        recorder = TelemetryRecorder(Path(temp), queue_max=256)
        started = recorder.start(bus, label="floor test", max_hz=50)
        assert started["ok"] and started["active"]
        assert started["adds_bus_reads"] is False
        assert started["piggyback_snapshots"] is True
        assert bus.reads == 0 and callable(bus.sink)
        assert bus.sink.wants_snapshot()

        for sample in range(7):
            assert bus.sink("feedback", _plant_payload(
                include_command=(sample == 0)))
            time.sleep(0.01)
        stopped = recorder.stop(timeout=2.0)
        assert stopped["ok"] and not stopped["active"]
        assert stopped["queue_dropped"] == 0
        assert stopped["written"] == 7
        assert bus.sink is None and bus.reads == 0

        path = Path(stopped["path"])
        assert path.is_file()
        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert records[0]["record_type"] == "session"
        assert records[0]["adds_bus_reads"] is False
        feedback = [row for row in records if row["record_type"] == "feedback"]
        assert len(feedback) == 7
        assert feedback[-1]["contact"]["planted"] == [True] * 6
        assert records[-1]["record_type"] == "session_end"
        assert records[-1]["queue_dropped"] == 0


def test_full_queue_drops_immediately_instead_of_waiting():
    recorder = TelemetryRecorder(queue_max=128)
    recorder._active = True
    recorder._minimum_period_ns = 0
    recorder._queue = queue.Queue(maxsize=1)
    assert recorder.offer("marker", {"value": 1})
    for value in range(1000):
        assert not recorder.offer("marker", {"value": value})
    assert recorder._queue_dropped == 1000
    recorder._active = False


def test_high_rate_records_are_capped_but_feedback_is_not():
    recorder = TelemetryRecorder(queue_max=128)
    recorder._active = True
    recorder._minimum_period_ns = 1_000_000_000
    recorder._queue = queue.Queue(maxsize=8)
    assert recorder.offer("step", {})
    assert not recorder.offer("step", {})
    assert recorder.offer("feedback", {})
    assert recorder._rate_limited == 1
    recorder._active = False


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print("OK" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
