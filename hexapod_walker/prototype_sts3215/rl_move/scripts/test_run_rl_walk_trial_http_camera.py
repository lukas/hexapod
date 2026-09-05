"""Focused tests for the timestamped HTTP camera recorder."""

from __future__ import annotations

import numpy as np
import pytest

from rl_move.scripts import run_rl_walk_trial as trial


@pytest.mark.parametrize("capture", [None, "nan", "97.0", "101.0"])
def test_http_camera_requires_fresh_source_capture_time(
    tmp_path, monkeypatch, capture
) -> None:
    class _Response:
        headers = {} if capture is None else {"X-Capture-Unix-S": capture}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b"unused because timestamp is rejected first"

    monkeypatch.setattr(trial.time, "time", lambda: 100.0)
    monkeypatch.setattr(
        trial.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _Response(),
    )
    recorder = trial.HttpFrameRecorder(
        tmp_path / "out.mp4",
        tmp_path / "ts.csv",
        "http://fake/frame.jpg",
    )

    with pytest.raises(RuntimeError, match="capture timestamp|lacks X-Capture"):
        recorder._read_frame()


def test_http_camera_preserves_capture_time_instead_of_receipt(
    tmp_path, monkeypatch
) -> None:
    class _Response:
        headers = {"X-Capture-Unix-S": "99.5"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b"jpeg"

    monkeypatch.setattr(trial.time, "time", lambda: 100.0)
    monkeypatch.setattr(
        trial.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _Response(),
    )
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    monkeypatch.setattr(trial.cv2, "imdecode", lambda *args: frame)
    recorder = trial.HttpFrameRecorder(
        tmp_path / "out.mp4",
        tmp_path / "ts.csv",
        "http://fake/frame.jpg",
    )

    _, captured = recorder._read_frame()

    assert captured == 99.5
