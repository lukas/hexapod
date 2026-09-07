"""Offline fault injections for the sysid camera admission guard."""
import json
import threading

import pytest

from sysid.camera_guard import CameraGuard
from sysid.run_hw import _capture_vision_sidecar


REQUIRED = frozenset({18, 25, 48, 64})


def _state(timestamp=100.0, tags=(18, 25, 48, 64)):
    return {
        "generated_at_unix_s": timestamp,
        "visible_tag_ids": list(tags),
    }


def test_camera_guard_accepts_two_fresh_advancing_full_coverage_samples():
    guard = CameraGuard(REQUIRED, minimum_coverage=0.9, max_state_age_s=1.5)

    assert guard.observe(_state(100.0), now_unix=100.1) == (True, "ok")
    assert guard.observe(_state(100.2), now_unix=100.3) == (True, "ok")
    assert guard.ready.is_set()
    assert guard.accepted_samples == 2


def test_camera_guard_rejects_stale_timestamp():
    guard = CameraGuard(REQUIRED)
    assert guard.observe(_state(100.0), now_unix=100.1)[0] is True

    ok, error = guard.observe(_state(100.0), now_unix=100.2)

    assert ok is False
    assert "did not advance" in error


def test_camera_guard_rejects_state_age_over_bound():
    guard = CameraGuard(REQUIRED, max_state_age_s=1.5)

    ok, error = guard.observe(_state(100.0), now_unix=101.6)

    assert ok is False
    assert "stale" in error


def test_camera_guard_rejects_coverage_below_point_nine():
    guard = CameraGuard(REQUIRED, minimum_coverage=0.9)

    ok, error = guard.observe(_state(tags=(18, 25, 48)), now_unix=100.1)

    assert ok is False
    assert "coverage 0.750 below 0.900" in error


def test_camera_guard_failure_is_latched():
    guard = CameraGuard(REQUIRED)
    guard.reject("camera stream stale after repeated read failures")

    ok, error = guard.observe(_state(), now_unix=100.1)

    assert ok is False
    assert error == "camera stream stale after repeated read failures"


@pytest.mark.parametrize("field,value", [
    ("generated_at_unix_s", float("nan")),
    ("generated_at_unix_s", float("inf")),
    ("generated_at_unix_s", True),
    ("generated_at_unix_s", 101.0),
    ("state_age_s", float("nan")),
    ("state_age_s", float("inf")),
    ("state_age_s", True),
    ("state_age_s", -1.0),
    ("performance", "malformed"),
])
def test_camera_guard_rejects_invalid_freshness_metadata(field, value):
    state = _state()
    state[field] = value
    guard = CameraGuard(REQUIRED)

    assert guard.observe(state, now_unix=100.1)[0] is False
    assert not guard.ready.is_set()


def test_camera_guard_fresh_wrapper_cannot_hide_frozen_source_frame():
    guard = CameraGuard(REQUIRED)
    first, second = _state(100.0), _state(100.2)
    first["performance"] = second["performance"] = {"frame_sequence": 7}

    assert guard.observe(first, now_unix=100.1)[0] is True
    assert guard.observe(second, now_unix=100.3)[0] is False
    assert guard.failure == "camera timestamp did not advance"


@pytest.mark.parametrize("bound", [float("nan"), float("inf"), -1.0])
def test_camera_guard_rejects_invalid_age_bound(bound):
    guard = CameraGuard(REQUIRED, max_state_age_s=bound)
    assert guard.observe(_state(), now_unix=100.1)[0] is False


def test_capture_worker_binds_stale_timestamp_to_abort(monkeypatch, tmp_path):
    first = _state(100.0)
    first["state_age_s"] = 0.0
    second = _state(100.0)
    second["state_age_s"] = 0.0
    states = iter([first, second])

    class _Response:
        def __init__(self, state):
            self.payload = json.dumps(state).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.payload

    monkeypatch.setattr(
        "sysid.run_hw.urllib.request.urlopen",
        lambda *args, **kwargs: _Response(next(states)),
    )
    guard = CameraGuard(REQUIRED, max_state_age_s=1000.0)
    summary = {}
    aborts = []

    _capture_vision_sidecar(
        "http://camera.invalid/state",
        tmp_path,
        threading.Event(),
        hz=30.0,
        save_frames=False,
        frame_url=None,
        summary=summary,
        guard=guard,
        on_guard_failure=aborts.append,
    )

    assert aborts == ["camera timestamp did not advance"]
    assert summary["camera_guard_failed"] == aborts[0]
