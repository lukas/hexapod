"""The camera-server-backed frame source used instead of opening a device."""
import json

import importlib.util

import pytest

from hexapod_lab.vision_service_capture import VisionServiceCapture


STATUS = {
    "cameras": [
        {"index": 1, "requested_stable_id": "0xAAA", "device_name": "12MP AF Camera"},
        {"index": 2, "requested_stable_id": "0xBBB", "device_name": "12MP AF Camera"},
        {"index": 3, "requested_stable_id": "0xCCC", "device_name": "Arducam OV9281"},
    ]
}


# read() decodes JPEG with cv2. The lab service always has it; a bare test
# environment may not, and a missing decoder is not a finding about this code.
requires_cv2 = pytest.mark.skipif(
    importlib.util.find_spec("cv2") is None,
    reason="opencv is not installed in this environment",
)


def _capture(monkeypatch, *, headers=None, jpeg=b"", status=STATUS, **kwargs):
    calls = []

    def fake_get(self, path, timeout=None):
        calls.append(path)
        if path.startswith("/status.json"):
            return json.dumps(status).encode(), {}
        return jpeg, dict(headers or {})

    monkeypatch.setattr(VisionServiceCapture, "_get", fake_get)
    capture = VisionServiceCapture("http://host:8766/", **kwargs)
    return capture, calls


def test_resolves_the_slot_from_the_server_not_from_configuration(monkeypatch):
    # Slots are assigned at the server's startup, so a stored number goes
    # stale when the rig is re-cabled.
    capture, _calls = _capture(monkeypatch, stable_id="0xBBB")
    assert capture._resolve_slot() == 2


def test_refuses_a_stable_id_the_server_is_not_serving(monkeypatch):
    capture, _calls = _capture(monkeypatch, stable_id="0xZZZ")
    with pytest.raises(ValueError, match="not serving 0xZZZ"):
        capture._resolve_slot()


def test_refuses_an_ambiguous_device_name(monkeypatch):
    # Two cameras report "12MP AF Camera"; guessing would silently record the
    # wrong camera's frames against an experiment.
    capture, _calls = _capture(monkeypatch, device_name="12MP AF Camera")
    with pytest.raises(ValueError, match="configure a device_uid"):
        capture._resolve_slot()


def test_resolves_an_unambiguous_device_name(monkeypatch):
    capture, _calls = _capture(monkeypatch, device_name="Arducam OV9281")
    assert capture._resolve_slot() == 3


@requires_cv2
def test_read_reports_a_stale_frame_rather_than_returning_it(monkeypatch):
    capture, _calls = _capture(
        monkeypatch, stable_id="0xCCC",
        headers={"X-Frame-Age-Seconds": "9.5"}, jpeg=b"ignored",
    )
    ok, image = capture.read()
    assert ok is False and image is None
    assert "stalled" in capture.last_error


@requires_cv2
def test_read_forgets_the_slot_after_a_failure(monkeypatch):
    # A server restart renumbers slots, so a cached slot would quietly return
    # a different camera's frames.
    capture, _calls = _capture(monkeypatch, stable_id="0xZZZ")
    ok, _image = capture.read()
    assert ok is False
    assert capture._slot is None
    assert "unreachable" in capture.last_error


@requires_cv2
def test_read_decodes_a_frame_and_keeps_the_servers_capture_stamp(monkeypatch):
    import cv2
    import numpy as np

    frame = np.full((48, 64, 3), 90, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    capture, calls = _capture(
        monkeypatch, stable_id="0xCCC", jpeg=encoded.tobytes(),
        headers={
            "X-Frame-Age-Seconds": "0.05",
            "X-Frame-Captured-Unix": "1788990168.586884",
            "X-Frame-Sequence": "156",
        },
    )
    ok, image = capture.read()
    assert ok is True
    assert image.shape == (48, 64, 3)
    # The server's stamp is used verbatim rather than re-derived here, so
    # vision lines up with robot telemetry on one clock.
    assert capture.captured_unix == 1788990168.586884
    assert capture.frame_sequence == 156
    assert capture.capture_image_size_px == (64, 48)
    assert any(path.startswith("/preview/3.jpg") for path in calls)


def test_release_holds_nothing():
    capture = VisionServiceCapture("http://host:8766", stable_id="0xCCC")
    capture._slot = 3
    capture.release()
    assert capture._slot is None
