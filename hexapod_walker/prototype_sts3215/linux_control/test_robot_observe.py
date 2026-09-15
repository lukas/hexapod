"""Fast, offline evidence-integrity tests for the read-only observer."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import robot_observe as observe
from hexapod_core.joint_frame import N_JOINTS


class Clock:
    def __init__(self):
        self.elapsed = 0.0

    def time(self):
        return 1000.0 + self.elapsed

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        assert seconds >= 0
        self.elapsed += seconds


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "sts3215")
    clock = Clock()
    monkeypatch.setattr(observe, "time", clock)

    def block_network(*args, **kwargs):
        raise AssertionError("An observer test attempted unmocked network I/O")

    monkeypatch.setattr(observe.urllib.request, "urlopen", block_network)
    return clock


def feedback(stamp=999.0):
    return {"ok": True, "live": N_JOINTS, "t_unix": stamp, "roll_deg": 1.2, "pitch_deg": -2.3,
            "joints": [{"raw_deg": 12.0, "deg": 24.0, "cur_a": .1,
                        "temp_c": 30, "volt": 11.4, "load_pct": 8.0} for _ in range(N_JOINTS)]}


def supply_feedback(monkeypatch, payloads):
    pending = iter(payloads)
    calls = []

    def get_json(base, path):
        assert path == "/api/feedback"
        calls.append((base, path))
        return next(pending)

    monkeypatch.setattr(observe, "get_json", get_json)
    return calls


@pytest.mark.parametrize("missing_joint", [None, 6])
def test_observer_accepts_current_public_feedback_contract_without_raw_angles(
        monkeypatch, offline, missing_joint):
    from linux_control.api.rl import RlApi
    from linux_control.api import rl

    monkeypatch.setattr(rl, "time", offline)
    readings = {
        j: {"deg": 24.0, "current_a": .1, "temp_c": 30, "load_pct": 8.0, "volt": 11.4}
        for j in range(N_JOINTS) if j != missing_joint}
    bus = SimpleNamespace(read_all_feedback=lambda: readings,
                          read_imu=lambda **kwargs: {"ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0})
    api = SimpleNamespace(drive=SimpleNamespace(dry_run=False, bus=bus),
                          _bus_admission_error=lambda: None)
    payload = RlApi.rl_feedback(api)
    assert "raw_deg" not in payload["joints"][0]
    monkeypatch.setattr(observe, "get_bytes", lambda *args: json.dumps(payload).encode())
    row = observe.read_feedback("http://offline")
    assert row["summary"]["fresh"]
    assert row["summary"]["complete"] is (missing_joint is None)
    assert row["summary"]["raw_positions_available"] is False
    assert row["summary"]["max_abs_logical_deg"] == 24.0
    assert "raw_deg" not in row["feedback"]["joints"][0]


@pytest.mark.parametrize("stamps,expected", [
    ([999.0] * 6, False),
    ([999.0, 999.0, 999.1, 999.1, 999.2], True),
    ([999.2, 999.3, 999.1, 999.2, 999.3], False),
    ([999.0, 999.1, 997.0, 999.2, 999.3], False),
    ([999.0, 999.1, 999.2], True),
])
def test_three_scan_collection_requires_distinct_fresh_monotonic_evidence(monkeypatch, stamps, expected):
    calls = supply_feedback(monkeypatch, [feedback(stamp) for stamp in stamps])
    result = observe.collect_feedback("http://offline", attempts=len(stamps), interval=.05)
    assert result["three_fresh_complete_samples"] is expected
    assert len(result["attempts"]) == len(calls)
    if expected:
        accepted = [row["summary"]["t_unix"] for row in result["samples"]]
        assert len(accepted) == len(set(accepted)) == 3
        assert accepted == sorted(accepted)
    else:
        assert len(result["samples"]) < 3


@pytest.mark.parametrize("fault", ["missing_joint", "missing_stamp", "missing_field", "request_failure"])
def test_incomplete_read_breaks_a_partial_run_without_erasing_attempt_evidence(monkeypatch, fault):
    bad = feedback(999.2)
    if fault == "missing_joint":
        bad["joints"].pop()
        bad["live"] = N_JOINTS - 1
    elif fault == "missing_stamp":
        bad.pop("t_unix")
    elif fault == "missing_field":
        bad["joints"][6].pop("deg")
    else:
        bad = {"ok": False, "error": "offline read failed"}
    supply_feedback(monkeypatch, [feedback(999), feedback(999.1), bad,
                                  feedback(999.3), feedback(999.4)])
    result = observe.collect_feedback("http://offline", attempts=5, interval=.05)
    assert not result["three_fresh_complete_samples"]
    assert len(result["attempts"]) == 5
    assert result["attempts"][2]["feedback"] == bad
    assert [row["summary"]["t_unix"] for row in result["samples"]] == [999.3, 999.4]


@pytest.mark.parametrize("field,value", [
    ("raw_deg", None), ("raw_deg", float("nan")), ("deg", float("inf")),
    ("cur_a", float("-inf")), ("temp_c", "30"), ("volt", True), ("load_pct", {}),
])
def test_malformed_joint_telemetry_never_becomes_complete(field, value):
    data = feedback()
    data["joints"][7][field] = value
    summary = observe.summarize_feedback(data, 1000)
    assert not summary["complete"]
    assert 7 in summary["invalid_joint_indices"]
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("replace", [
    {"joints": None}, {"joints": [None] * N_JOINTS}, {"live": N_JOINTS - 1}, {"ok": "true"},
    {"roll_deg": float("nan")}, {"pitch_deg": float("inf")},
])
def test_malformed_pose_or_attitude_cannot_be_complete(replace):
    data = {**feedback(), **replace}
    summary = observe.summarize_feedback(data, 1000)
    assert not summary["complete"]
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("stamp", [None, True, "999", float("nan"), float("inf"), 997.9, 1000.6])
def test_missing_nonfinite_old_or_future_timestamp_is_not_fresh(stamp):
    summary = observe.summarize_feedback(feedback(stamp), 1000)
    assert not summary["fresh"]
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("raw", [b"[]", b"{", b'{"t_unix":NaN}', b'{"t_unix":Infinity}',
                                  b'{"joints":[{"cur_a":1e999}]}'])
def test_json_decode_failures_and_nonfinite_numbers_become_serializable_error_evidence(monkeypatch, raw):
    monkeypatch.setattr(observe, "get_bytes", lambda *args: raw)
    result = observe.get_json("http://offline", "/api/feedback")
    assert result["ok"] is False
    assert result["error"]
    json.dumps(result, allow_nan=False)


def install_get_server(monkeypatch, responder):
    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self.payload

    def urlopen(request, timeout):
        calls.append((request.get_method(), request.full_url, request.data, timeout))
        assert request.get_method() == "GET"
        assert request.data is None
        return Response(responder(request.full_url))

    monkeypatch.setattr(observe.urllib.request, "urlopen", urlopen)
    return calls


@pytest.mark.parametrize("failed_camera", [None, 1])
def test_snapshot_preserves_partial_evidence_and_uses_only_gets(tmp_path, monkeypatch, offline, failed_camera):
    jpeg = b"\xff\xd8offline-camera-evidence\xff\xd9"

    def respond(url):
        if url == "http://cameras/snapshot/0.jpg":
            return jpeg
        if url == "http://cameras/snapshot/1.jpg":
            if failed_camera == 1:
                raise OSError("camera one unavailable")
            return jpeg
        if url == "http://robot/api/demo/status":
            return b'{"ok":true,"armed":false,"demo":{"running":false}}'
        assert url == "http://robot/api/feedback"
        return json.dumps(feedback(offline.time())).encode()

    calls = install_get_server(monkeypatch, respond)
    out = tmp_path / "snapshot"
    result = observe.capture_snapshot("http://robot", "http://cameras", out)
    assert result["observations_complete"] is (failed_camera is None)
    assert result["cameras"][0]["ok"]
    assert result["cameras"][1]["ok"] is (failed_camera is None)
    assert (out / "camera0.jpg").read_bytes() == jpeg
    assert (out / "camera1.jpg").exists() is (failed_camera is None)
    assert result["status"]["armed"] is False
    assert result["feedback"]["three_fresh_complete_samples"]
    assert len(result["feedback"]["attempts"]) == 3
    assert json.loads((out / "observation.json").read_text()) == result
    assert {url for _, url, _, _ in calls} == {
        "http://robot/api/feedback", "http://robot/api/demo/status",
        "http://cameras/snapshot/0.jpg", "http://cameras/snapshot/1.jpg"}


@pytest.mark.parametrize("status", [{}, {"armed": False, "demo": None},
                                    {"armed": "false", "demo": {"running": False}},
                                    {"armed": False, "demo": {"running": "false"}}])
def test_incomplete_status_cannot_claim_complete_observations_despite_good_images_and_scans(
        tmp_path, monkeypatch, offline, status):
    def respond(url):
        if url.startswith("http://cameras/snapshot/"):
            return b"\xff\xd8offline image\xff\xd9"
        if url == "http://robot/api/demo/status":
            return json.dumps(status).encode()
        assert url == "http://robot/api/feedback"
        return json.dumps(feedback(offline.time())).encode()

    install_get_server(monkeypatch, respond)
    result = observe.capture_snapshot("http://robot", "http://cameras", tmp_path / "snapshot")
    assert not result["observations_complete"]
    assert all(row["ok"] for row in result["cameras"])
    assert result["feedback"]["three_fresh_complete_samples"]
    assert result["status"] == status


def test_existing_snapshot_directory_and_watch_file_are_never_overwritten_or_read_from_robot(tmp_path, monkeypatch):
    out = tmp_path / "existing"
    out.mkdir()
    sentinel = out / "observation.json"
    sentinel.write_text("original evidence")
    calls = install_get_server(monkeypatch, lambda url: pytest.fail("No HTTP before exclusive output creation"))
    with pytest.raises(FileExistsError):
        observe.capture_snapshot("http://robot", "http://cameras", out)
    with pytest.raises(FileExistsError):
        observe.watch_feedback("http://robot", sentinel, .2, .1)
    assert sentinel.read_text() == "original evidence"
    assert not calls


def test_capture_camera_preserves_existing_image(tmp_path, monkeypatch):
    image = tmp_path / "camera0.jpg"
    image.write_bytes(b"previous evidence")
    monkeypatch.setattr(observe, "get_bytes", lambda *args: b"\xff\xd8new image\xff\xd9")
    result = observe.capture_camera("http://cameras", 0, tmp_path)
    assert not result["ok"]
    assert image.read_bytes() == b"previous evidence"


def test_passive_watch_is_bounded_and_records_errors_without_any_abort_or_torque_calls(tmp_path, monkeypatch, offline):
    def respond(url):
        assert url == "http://robot/api/feedback"
        raise OSError("read unavailable")

    calls = install_get_server(monkeypatch, respond)
    path = tmp_path / "watch.jsonl"
    result = observe.watch_feedback("http://robot", path, seconds=.55, interval=.2)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert result["observer_only"]
    assert result["samples"] == result["invalid_or_stale"] == len(rows) == 3
    assert len(calls) == 3
    assert offline.elapsed == pytest.approx(.55)
    assert all(row["feedback"]["error"] == "read unavailable" for row in rows)


@pytest.mark.parametrize("seconds,interval", [(0, .1), (1801, .1), (float("inf"), .1),
                                               (1, 0), (1, 61), (1, float("nan"))])
def test_watch_rejects_unbounded_or_invalid_limits_without_output_or_io(tmp_path, seconds, interval):
    path = tmp_path / "watch.jsonl"
    with pytest.raises(ValueError):
        observe.watch_feedback("http://robot", path, seconds, interval)
    assert not path.exists()


def test_watch_does_not_start_another_poll_after_an_inflight_read_passes_deadline(tmp_path, monkeypatch, offline):
    def respond(url):
        assert url == "http://robot/api/feedback"
        offline.sleep(.8)
        return json.dumps(feedback(offline.time())).encode()

    calls = install_get_server(monkeypatch, respond)
    result = observe.watch_feedback("http://robot", tmp_path / "watch.jsonl", seconds=.5, interval=.1)
    assert result["samples"] == len(calls) == 1
    assert offline.elapsed == pytest.approx(.8)  # Only the in-flight read can overrun.


def test_offline_trial_summary_requires_no_body_monitor_or_network_and_keeps_raw_logical_distinction(tmp_path):
    trial = {"prediction": "bounded relative test", "command": {"deltas_deg": {"2": -5}},
             "result": {"ok": False, "error": "time limit", "torque_off": True,
                        "joints": {"2": {"before_deg": 18, "target_deg": 13, "reached_deg": 14,
                                         "after_deg": 17, "peak_current_a": .2},
                                   "5": {"peak_current_a": .1}, "8": {"peak_current_a": 0}}},
             "after_feedback": feedback(10)}
    path = tmp_path / "trial.json"
    path.write_text(json.dumps(trial))
    saved = path.read_bytes()
    result = observe.summarize_trial(tmp_path)
    assert result["ok"] is False and result["torque_off"] is True
    assert set(result["joints"]) == {"2", "5"}
    assert result["after_feedback"]["historical"] is True
    assert "fresh" not in result["after_feedback"]
    assert "age_s" not in result["after_feedback"]
    assert result["joint_angles"][2] == {"index": 2, "raw_deg": 12, "logical_deg": 24}
    assert result["max_abs_roll_deg"] is None and result["max_abs_pitch_deg"] is None
    assert path.read_bytes() == saved
    assert not (tmp_path / "body-monitor.json").exists()
