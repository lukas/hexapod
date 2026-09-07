"""Off-robot tests for passive telemetry recording/contact observation."""
from __future__ import annotations

import json
import queue
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

import telemetry_recorder as telemetry_module
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


def _wait_for_marker(recorder: TelemetryRecorder, marker_id: str,
                     timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ack = recorder.status(marker_id=marker_id)["marker_ack"]
        if ack is not None:
            return ack
        time.sleep(0.005)
    raise AssertionError(recorder.status(marker_id=marker_id))


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
        assert started["piggyback_snapshots"] is False
        assert started["communication_capture"] is True
        assert bus.reads == 0 and callable(bus.sink)
        assert not hasattr(bus.sink, "wants_snapshot")

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


def test_raw_bytes_are_uncapped_and_flush_marker_covers_rotated_parts():
    with tempfile.TemporaryDirectory() as temp:
        recorder = TelemetryRecorder(Path(temp), segment_bytes=1024)
        bus = FakeBus()
        recorder.start(bus, max_hz=1)
        chunks = [bytes(range(256)), b"\x00\xffERR\r\n"] * 10
        for chunk in chunks:
            assert bus.sink("serial_rx", {"data": chunk})
        mark = recorder.mark("test-end")
        ack = _wait_for_marker(recorder, mark["marker_id"])
        status = recorder.status()
        assert status["active"] and status["rate_limited"] == 0
        assert len(status["paths"]) > 1
        assert ack["marker_id"] == mark["marker_id"]
        assert ack["seq"] == mark["accepted_sequence"]
        assert ack["written"] == len(chunks) + 1
        assert ack["path"] in ack["paths"]
        assert ack["part"] == ack["paths"].index(ack["path"])
        assert ack["capture_checkpoint"] == {
            "queue_dropped": 0,
            "communication_dropped": 0,
            "uncaptured_bytes": 0,
            "capture_errors": 0,
        }
        records = [json.loads(line) for path in status["paths"]
                   for line in Path(path).read_text().splitlines()]
        wire = [r for r in records if r["record_type"] == "serial_rx"]
        assert [bytes.fromhex(r["data_hex"]) for r in wire] == chunks
        assert all(r["byte_count"] == len(chunk) for r, chunk in zip(wire, chunks))
        assert all("mono_s" in r and "time_unix_ns" in r for r in wire)
        assert records[-1]["marker_id"] == mark["marker_id"]
        marker_part = [json.loads(line) for line in
                       Path(ack["path"]).read_text().splitlines()]
        assert any(row.get("seq") == ack["seq"]
                   and row.get("marker_id") == mark["marker_id"]
                   for row in marker_part)
        assert recorder.stop()["communication_dropped"] == 0


def test_marker_ack_checkpoints_both_loss_boundaries_and_stays_queryable():
    class GatedRecorder(TelemetryRecorder):
        def __init__(self, *args, **kwargs):
            self.writer_gate = threading.Event()
            super().__init__(*args, **kwargs)

        def _writer(self) -> None:
            self.writer_gate.wait(timeout=2.0)
            super()._writer()

    with tempfile.TemporaryDirectory() as temp:
        recorder = GatedRecorder(Path(temp), queue_max=128)
        bus = FakeBus()
        assert recorder.start(bus)["ok"]

        # Fill the paused writer's queue so the two enqueue-side losses are
        # known and occur strictly before either accepted marker.
        for _ in range(recorder.queue_max):
            assert recorder.offer("feedback", {})
        assert not recorder.offer("serial_rx", {"data": b"lost"})
        assert not recorder.offer("feedback", {})
        recorder.writer_gate.set()
        deadline = time.monotonic() + 2.0
        while recorder.status()["queue"]:
            assert time.monotonic() < deadline, recorder.status()
            time.sleep(0.005)

        assert recorder.offer("serial_capture_error", {
            "data": b"", "uncaptured_bytes": 7,
        })
        first = recorder.mark("first")
        assert recorder.offer("serial_capture_error", {
            "data": b"", "uncaptured_bytes": 11,
        })
        second = recorder.mark("second")

        first_ack = _wait_for_marker(recorder, first["marker_id"])
        second_ack = _wait_for_marker(recorder, second["marker_id"])
        assert first_ack["capture_checkpoint"] == {
            "queue_dropped": 2,
            "communication_dropped": 1,
            "uncaptured_bytes": 7,
            "capture_errors": 1,
        }
        assert second_ack["capture_checkpoint"] == {
            "queue_dropped": 2,
            "communication_dropped": 1,
            "uncaptured_bytes": 18,
            "capture_errors": 2,
        }
        assert first_ack["seq"] == first["accepted_sequence"]
        assert second_ack["seq"] == second["accepted_sequence"]
        assert first_ack["written"] < second_ack["written"]
        assert recorder.status()["flushed_marker"] == second["marker_id"]
        assert recorder.status(marker_id=first["marker_id"])[
            "marker_ack"] == first_ack
        recorder.stop()


def test_marker_ack_is_not_published_until_fsync_completes():
    with tempfile.TemporaryDirectory() as temp:
        recorder = TelemetryRecorder(Path(temp), queue_max=128)
        assert recorder.start(FakeBus())["ok"]
        fsync_entered = threading.Event()
        allow_fsync = threading.Event()
        real_fsync = telemetry_module.os.fsync

        def gated_fsync(fd: int) -> None:
            fsync_entered.set()
            if not allow_fsync.wait(timeout=2.0):
                raise TimeoutError("test did not release fsync")
            real_fsync(fd)

        telemetry_module.os.fsync = gated_fsync
        try:
            marker = recorder.mark("durability-boundary")
            assert fsync_entered.wait(timeout=2.0)
            assert recorder.status(marker_id=marker["marker_id"])[
                "marker_ack"] is None
            allow_fsync.set()
            ack = _wait_for_marker(recorder, marker["marker_id"])
            assert ack["seq"] == marker["accepted_sequence"]
        finally:
            allow_fsync.set()
            telemetry_module.os.fsync = real_fsync
            recorder.stop()


def test_concurrent_markers_each_receive_their_own_acknowledgement():
    with tempfile.TemporaryDirectory() as temp:
        recorder = TelemetryRecorder(Path(temp), queue_max=256)
        assert recorder.start(FakeBus())["ok"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            markers = list(pool.map(
                lambda index: recorder.mark(f"concurrent-{index}"),
                range(32),
            ))
        assert all(marker["ok"] for marker in markers)
        acks = [_wait_for_marker(recorder, marker["marker_id"])
                for marker in markers]
        assert {ack["marker_id"] for ack in acks} == {
            marker["marker_id"] for marker in markers
        }
        assert {ack["seq"] for ack in acks} == {
            marker["accepted_sequence"] for marker in markers
        }
        assert len({ack["written"] for ack in acks}) == len(markers)
        recorder.stop()


def test_marker_ack_retention_is_bounded_to_recent_markers():
    with tempfile.TemporaryDirectory() as temp:
        recorder = TelemetryRecorder(
            Path(temp), marker_ack_limit=2, queue_max=128)
        assert recorder.start(FakeBus())["ok"]
        markers = []
        for index in range(3):
            marker = recorder.mark(f"bounded-{index}")
            _wait_for_marker(recorder, marker["marker_id"])
            markers.append(marker)
        assert recorder.status(marker_id=markers[0]["marker_id"])[
            "marker_ack"] is None
        assert recorder.status(marker_id=markers[1]["marker_id"])[
            "marker_ack"] is not None
        assert recorder.status(marker_id=markers[2]["marker_id"])[
            "marker_ack"] is not None
        recorder.stop()


def test_raw_capture_losses_are_counted_separately():
    recorder = TelemetryRecorder()
    recorder._active = True
    recorder._queue = queue.Queue(maxsize=1)
    assert recorder.offer("serial_tx", {"data": b"x"})
    assert not recorder.offer("serial_rx", {"data": b"y"})
    assert recorder.status()["communication_dropped"] == 1
    assert recorder.status()["queue_dropped"] == 1
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
