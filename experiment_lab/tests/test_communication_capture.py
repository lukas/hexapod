import io
import json
from urllib.error import HTTPError, URLError

import hexapod_lab.communication_capture as communication_capture
from hexapod_lab.communication_capture import (
    RobotCommunicationCapture,
    STATUS_NAME,
    TRANSCRIPT_NAME,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload

    def __iter__(self):
        return iter(io.BytesIO(self.payload))


def marker(marker_id, label):
    return {
        "schema_version": 2,
        "record_type": "marker",
        "marker_id": marker_id,
        "label": label,
    }


def marker_ack(marker_id, *, path="/robot/logs/telemetry_part_001.jsonl",
               paths=None, dropped=0, seq=10, written=10):
    return {
        "marker_id": marker_id,
        "path": path,
        "paths": paths or [path],
        "seq": seq,
        "written": written,
        "capture_checkpoint": {
            "queue_dropped": 0,
            "communication_dropped": dropped,
            "uncaptured_bytes": 0,
            "capture_errors": 0,
        },
    }


def recorder(marker_id, *, dropped=0):
    path = "/robot/logs/telemetry_part_001.jsonl"
    return {
        "ok": True,
        "marker_id": marker_id,
        "flushed_marker": marker_id,
        "active": True,
        "communication_capture": True,
        "communication_scope": "host_mcu_serial",
        "communication_rate_limited": False,
        "piggyback_snapshots": False,
        "writer_alive": True,
        "write_error": None,
        "paths": [path],
        "offered": 10,
        "written": 10,
        "queue_dropped": 0,
        "communication_dropped": dropped,
        "uncaptured_bytes": 0,
        "capture_errors": 0,
        "marker_ack": marker_ack(marker_id, dropped=dropped),
    }


def test_marker_bounded_capture_is_attached_with_zero_loss(tmp_path):
    begin = recorder("begin-1")
    end = recorder("end-1")
    rows = [
        {"record_type": "serial_tx", "data_hex": "old"},
        marker("begin-1", "robotlab_run_begin"),
        {"record_type": "serial_tx", "data_hex": "a55a"},
        {"record_type": "serial_rx", "data_hex": "5aa5"},
        marker("end-1", "robotlab_run_end"),
        {"record_type": "serial_tx", "data_hex": "later"},
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([FakeResponse(begin), FakeResponse(end), FakeResponse(log)])
    requested = []

    def open_fake(request, **_):
        requested.append((request.get_method(), request.full_url))
        return next(replies)

    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-1",
        job_id="job-1",
        attempt=1,
        opener=open_fake,
    )
    assert capture.begin()["complete"] is False
    result = capture.finish()

    assert result["complete"] is True
    assert result["loss_deltas"] == {
        "queue_dropped": 0,
        "communication_dropped": 0,
        "uncaptured_bytes": 0,
        "capture_errors": 0,
    }
    captured = [
        json.loads(line)
        for line in (run_dir / TRANSCRIPT_NAME).read_text().splitlines()
    ]
    assert captured == rows[1:5]
    assert json.loads((run_dir / STATUS_NAME).read_text())["complete"] is True
    assert requested == [
        ("POST", "http://robot.test:8080/api/telemetry"),
        ("POST", "http://robot.test:8080/api/telemetry"),
        ("GET", "http://robot.test:8080/api/logs/telemetry_part_001.jsonl"),
    ]
    assert capture.finish() == result


def test_capture_loss_is_explicit_and_invalidates_completeness(tmp_path):
    begin = recorder("begin-2")
    end = recorder("end-2", dropped=3)
    rows = [
        marker("begin-2", "robotlab_run_begin"),
        {"record_type": "serial_rx", "data_hex": "01"},
        marker("end-2", "robotlab_run_end"),
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([FakeResponse(begin), FakeResponse(end), FakeResponse(log)])
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-2",
        job_id="job-2",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    capture.begin()
    result = capture.finish()

    assert result["complete"] is False
    assert result["capture_state"] == "terminal_incomplete"
    assert result["loss_deltas"]["communication_dropped"] == 3
    assert result["transcript"]["bytes"] > 0


def test_lossy_copied_range_stays_terminal_after_resume_without_new_marker(
    tmp_path,
):
    begin = recorder("begin-loss-terminal")
    end = recorder("end-loss-terminal", dropped=1)
    rows = [
        marker("begin-loss-terminal", "robotlab_run_begin"),
        {"record_type": "serial_rx", "data_hex": "01"},
        marker("end-loss-terminal", "robotlab_run_end"),
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([FakeResponse(begin), FakeResponse(end), FakeResponse(log)])
    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-loss-terminal",
        job_id="job-loss-terminal",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    capture.begin()
    first = capture.finish()
    raw_before = (run_dir / TRANSCRIPT_NAME).read_bytes()
    # Old status files did not persist capture_state. Presence of the exact
    # copied range and both acknowledgements must still prevent range growth.
    saved = json.loads((run_dir / STATUS_NAME).read_text())
    saved.pop("capture_state")
    (run_dir / STATUS_NAME).write_text(json.dumps(saved) + "\n")
    resumed = RobotCommunicationCapture.resume(
        run_dir,
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("terminal capture contacted the robot")
        ),
    )
    second = resumed.finish()

    assert first["capture_state"] == "terminal_incomplete"
    assert second["capture_state"] == "terminal_incomplete"
    assert second["complete"] is False
    assert second["end_marker"] == "end-loss-terminal"
    assert (run_dir / TRANSCRIPT_NAME).read_bytes() == raw_before


def test_begin_waits_until_marker_is_flushed_before_snapshot(tmp_path):
    queued = recorder("begin-queued")
    queued["flushed_marker"] = None
    queued.pop("marker_ack")
    flushed = recorder("ignored")
    flushed["marker_id"] = None
    flushed["flushed_marker"] = "begin-queued"
    flushed["marker_ack"] = marker_ack("begin-queued")
    replies = iter([FakeResponse(queued), FakeResponse(flushed)])
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-queued",
        job_id="job-queued",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    result = capture.begin()

    assert result["begin_marker"] == "begin-queued"
    assert result["begin_recorder"]["flushed_marker"] == "begin-queued"


def test_begin_uses_post_counters_so_flush_delay_drops_are_not_hidden(tmp_path):
    begin = recorder("begin-loss")
    begin["flushed_marker"] = None
    begin.pop("marker_ack")
    acknowledged = recorder("ignored", dropped=3)
    acknowledged["marker_id"] = None
    acknowledged["flushed_marker"] = "begin-loss"
    acknowledged["marker_ack"] = marker_ack("begin-loss")
    end = recorder("end-loss", dropped=3)
    rows = [
        marker("begin-loss", "robotlab_run_begin"),
        marker("end-loss", "robotlab_run_end"),
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([
        FakeResponse(begin), FakeResponse(acknowledged),
        FakeResponse(end), FakeResponse(log),
    ])
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-loss",
        job_id="job-loss",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    capture.begin()
    result = capture.finish()

    assert result["complete"] is False
    assert result["loss_deltas"]["communication_dropped"] == 3


def test_later_marker_acknowledges_our_fifo_marker_without_timeout(tmp_path):
    begin = recorder("begin-race")
    begin["flushed_marker"] = None
    begin.pop("marker_ack")
    begin["written"] = 9
    later = recorder("later-marker")
    later["written"] = 11
    later["marker_ack"] = marker_ack("begin-race", written=10)
    replies = iter([FakeResponse(begin), FakeResponse(later)])
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-race",
        job_id="job-race",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    result = capture.begin()

    assert result["begin_marker"] == "begin-race"
    assert result["begin_recorder"]["flushed_marker"] == "begin-race"


def test_capture_spans_rotated_parts_without_copying_old_or_later_rows(tmp_path):
    begin = recorder("begin-rotated")
    begin["paths"] = ["/robot/logs/part-1.jsonl"]
    begin["flushed_marker"] = None
    begin.pop("marker_ack")
    begin_ack = recorder("ignored")
    begin_ack["marker_id"] = None
    begin_ack["flushed_marker"] = "begin-rotated"
    begin_ack["paths"] = [
        "/robot/logs/part-1.jsonl",
        "/robot/logs/part-2.jsonl",
    ]
    begin_ack["marker_ack"] = marker_ack(
        "begin-rotated",
        path="/robot/logs/part-1.jsonl",
        paths=begin_ack["paths"],
    )
    end = recorder("end-rotated")
    end["paths"] = [
        "/robot/logs/part-1.jsonl",
        "/robot/logs/part-2.jsonl",
    ]
    end["marker_ack"] = marker_ack(
        "end-rotated",
        path="/robot/logs/part-2.jsonl",
        paths=end["paths"],
    )
    part_1 = [
        {"record_type": "serial_tx", "data_hex": "old"},
        marker("begin-rotated", "robotlab_run_begin"),
        {"record_type": "serial_tx", "data_hex": "01"},
    ]
    part_2 = [
        {"record_type": "serial_rx", "data_hex": "02"},
        marker("end-rotated", "robotlab_run_end"),
        {"record_type": "serial_rx", "data_hex": "later"},
    ]
    encode = lambda rows: b"".join(
        (json.dumps(row) + "\n").encode() for row in rows
    )
    replies = iter([
        FakeResponse(begin), FakeResponse(begin_ack), FakeResponse(end),
        FakeResponse(encode(part_1)), FakeResponse(encode(part_2)),
    ])
    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-rotated",
        job_id="job-rotated",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    capture.begin()
    result = capture.finish()

    assert result["complete"] is True
    captured = [
        json.loads(line)
        for line in (run_dir / TRANSCRIPT_NAME).read_text().splitlines()
    ]
    assert captured == part_1[1:] + part_2[:2]


def test_recorder_restart_between_markers_is_explicitly_incomplete(tmp_path):
    begin = recorder("begin-restart")
    begin["paths"] = ["/robot/logs/old-session.jsonl"]
    begin["marker_ack"] = marker_ack(
        "begin-restart",
        path=begin["paths"][0],
        paths=begin["paths"],
    )
    end = recorder("end-restart")
    end["paths"] = ["/robot/logs/new-session.jsonl"]
    end["marker_ack"] = marker_ack(
        "end-restart",
        path=end["paths"][0],
        paths=end["paths"],
    )
    replies = iter([FakeResponse(begin), FakeResponse(end)])
    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-restart",
        job_id="job-restart",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )

    capture.begin()
    result = capture.finish()

    assert result["complete"] is False
    assert result["capture_state"] == "terminal_incomplete"
    assert "begin recorder part is absent" in result["errors"][0]
    assert not (run_dir / TRANSCRIPT_NAME).exists()
    resumed = RobotCommunicationCapture.resume(
        run_dir,
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("terminal capture contacted the robot")
        ),
    )
    assert resumed.finish() == result


def test_transient_download_retries_the_exact_saved_end_marker(tmp_path):
    begin = recorder("begin-retry")
    first_end = recorder("end-first")
    rows = [
        marker("begin-retry", "robotlab_run_begin"),
        {"record_type": "serial_tx", "data_hex": "01"},
        marker("end-first", "robotlab_run_end"),
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([
        FakeResponse(begin),
        FakeResponse(first_end),
        OSError("temporary download failure"),
        FakeResponse(log),
    ])
    requested = []

    def open_fake(request, **_kwargs):
        requested.append(request.get_method())
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-retry",
        job_id="job-retry",
        attempt=1,
        opener=open_fake,
    )

    capture.begin()
    first = capture.finish()
    resumed = RobotCommunicationCapture.resume(run_dir, opener=open_fake)
    second = resumed.finish()

    assert first["complete"] is False
    assert first["capture_state"] == "retryable"
    assert second["complete"] is True
    assert second["capture_state"] == "terminal_complete"
    assert second["end_marker"] == "end-first"
    assert second["errors"] == []
    assert requested == ["POST", "POST", "GET", "GET"]


def test_unavailable_recorder_is_recorded_without_blocking_attempt(tmp_path):
    def unavailable(*_args, **_kwargs):
        raise OSError("offline")

    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-3",
        job_id="job-3",
        attempt=1,
        opener=unavailable,
    )

    capture.begin()
    result = capture.finish()

    assert result["complete"] is False
    assert result["capture_state"] == "terminal_incomplete"
    assert result["errors"] == ["begin: OSError: offline"]
    assert result["transcript"] is None
    assert (tmp_path / "attempt-1" / STATUS_NAME).is_file()


def test_begin_retries_transient_url_error_with_exact_marker_request(
    tmp_path, monkeypatch,
):
    replies = iter([
        URLError(OSError(65, "No route to host")),
        FakeResponse(recorder("begin-after-route")),
    ])
    requested = []
    delays = []

    def open_fake(request, **kwargs):
        requested.append((request, kwargs))
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(communication_capture.time, "sleep", delays.append)
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-route",
        job_id="job-route",
        attempt=2,
        opener=open_fake,
    )

    result = capture.begin()

    assert result["begin_marker"] == "begin-after-route"
    assert result["errors"] == []
    assert delays == [0.05]
    assert len(requested) == 2
    assert [request.get_method() for request, _ in requested] == ["POST", "POST"]
    assert [request.full_url for request, _ in requested] == [
        "http://robot.test:8080/api/telemetry",
        "http://robot.test:8080/api/telemetry",
    ]
    assert requested[0][0].data == requested[1][0].data
    assert json.loads(requested[0][0].data) == {
        "action": "mark",
        "label": "robotlab_run_begin",
        "data": {
            "experiment_id": "experiment-route",
            "job_id": "job-route",
            "attempt": 2,
        },
    }
    assert [kwargs for _, kwargs in requested] == [
        {"timeout": 10.0},
        {"timeout": 10.0},
    ]


def test_begin_records_one_aggregate_error_after_url_retries_are_exhausted(
    tmp_path, monkeypatch,
):
    failures = iter([
        URLError("first route failure"),
        URLError("second route failure"),
        URLError("final route failure"),
    ])
    requests = []
    delays = []

    def unavailable(request, **_kwargs):
        requests.append(request)
        raise next(failures)

    monkeypatch.setattr(communication_capture.time, "sleep", delays.append)
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-route-exhausted",
        job_id="job-route-exhausted",
        attempt=1,
        opener=unavailable,
    )

    result = capture.begin()

    assert len(requests) == 3
    assert delays == [0.05, 0.1]
    assert result["begin_marker"] is None
    assert result["errors"] == [
        "begin: URLError: <urlopen error final route failure> "
        "(after 3 attempts)"
    ]
    assert "first route failure" not in result["errors"][0]
    assert "second route failure" not in result["errors"][0]


def test_begin_does_not_retry_http_error(
    tmp_path, monkeypatch,
):
    requests = []
    delays = []

    def rejected(request, **_kwargs):
        requests.append(request)
        raise HTTPError(request.full_url, 409, "Conflict", None, None)

    monkeypatch.setattr(communication_capture.time, "sleep", delays.append)
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        tmp_path / "attempt-1",
        experiment_id="experiment-rejected",
        job_id="job-rejected",
        attempt=1,
        opener=rejected,
    )

    result = capture.begin()

    assert len(requests) == 1
    assert delays == []
    assert result["errors"] == [
        "begin: HTTPError: HTTP Error 409: Conflict"
    ]


def test_resume_rejects_identity_mismatch_before_contacting_robot(tmp_path):
    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-identity",
        job_id="job-identity",
        attempt=1,
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    capture.begin()

    try:
        RobotCommunicationCapture.resume(
            run_dir,
            expected_experiment_id="different-experiment",
            expected_job_id="job-identity",
            expected_attempt=1,
        )
    except Exception as exc:
        assert "experiment_id mismatched" in str(exc)
    else:
        raise AssertionError("mismatched saved capture identity was accepted")


def test_finish_retries_final_receipt_write_without_new_marker(tmp_path, monkeypatch):
    begin = recorder("begin-receipt")
    end = recorder("end-receipt")
    rows = [
        marker("begin-receipt", "robotlab_run_begin"),
        marker("end-receipt", "robotlab_run_end"),
    ]
    log = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    replies = iter([FakeResponse(begin), FakeResponse(end), FakeResponse(log)])
    run_dir = tmp_path / "attempt-1"
    capture = RobotCommunicationCapture(
        "http://robot.test:8080/api/telemetry",
        run_dir,
        experiment_id="experiment-receipt",
        job_id="job-receipt",
        attempt=1,
        opener=lambda *_args, **_kwargs: next(replies),
    )
    capture.begin()
    original_write = capture._write_status
    failures = 1

    def flaky_write():
        nonlocal failures
        if failures:
            failures -= 1
            raise OSError("temporary receipt failure")
        original_write()

    monkeypatch.setattr(capture, "_write_status", flaky_write)
    try:
        capture.finish()
    except OSError as exc:
        assert "temporary receipt failure" in str(exc)
    else:
        raise AssertionError("injected receipt failure was not raised")

    result = capture.finish()
    assert result["complete"] is True
    assert result["capture_state"] == "terminal_complete"
    assert json.loads((run_dir / STATUS_NAME).read_text())["complete"] is True
    # The reply iterator being exhausted proves the retry emitted no marker.
