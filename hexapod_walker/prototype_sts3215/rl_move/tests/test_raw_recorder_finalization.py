"""Recording failure checks with synthetic files; no camera or robot access."""
from __future__ import annotations

import csv
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from rl_move.scripts import run_scripted_gait_suite as survey


def _finished_recorder(tmp_path, frames=3):
    recorder = survey.RawRecorder(
        tmp_path / "camera.mp4", tmp_path / "timestamps.csv", 0,
    )
    recorder.frames = frames
    recorder.thread = Mock(ident=1)
    recorder.thread.is_alive.return_value = False
    with recorder.timestamps.open("w", newline="") as handle:
        rows = csv.writer(handle)
        rows.writerow(["frame", "elapsed_s"])
        rows.writerows((index, index / 30) for index in range(frames))
    return recorder


def _write_video(path, frames=3):
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (32, 32),
    )
    assert writer.isOpened(), "test requires the MP4 writer used by RawRecorder"
    try:
        for index in range(frames):
            writer.write(np.full((32, 32, 3), index * 30, dtype=np.uint8))
    finally:
        writer.release()


def test_closed_video_and_timestamps_validate(tmp_path):
    recorder = _finished_recorder(tmp_path)
    _write_video(recorder.output)

    recorder.stop()

    assert recorder.error is None


@pytest.mark.parametrize("failure", ["missing", "unreadable", "dropped", "timestamps"])
def test_stop_reports_incomplete_recording(tmp_path, failure):
    recorder = _finished_recorder(tmp_path)
    if failure == "unreadable":
        recorder.output.write_bytes(b"not a finalized MP4")
    elif failure in {"dropped", "timestamps"}:
        _write_video(recorder.output, frames=2 if failure == "dropped" else 3)
        if failure == "timestamps":
            recorder.timestamps.write_text("frame,elapsed_s\n0,0\n")

    recorder.stop()

    assert recorder.error is not None
    assert "recording is incomplete" in recorder.error
    if failure == "dropped":
        assert "contains 2.0 frames; expected 3" in recorder.error


def test_stop_reports_undecodable_last_frame(tmp_path, monkeypatch):
    recorder = _finished_recorder(tmp_path)
    recorder.output.write_bytes(b"plausible metadata, missing last packet")
    video = Mock()
    video.get.return_value = recorder.frames
    video.read.side_effect = [(True, np.zeros((32, 32, 3))), (False, None)]
    monkeypatch.setattr(survey.cv2, "VideoCapture", lambda *_: video)

    recorder.stop()

    assert "last video frame cannot be decoded" in recorder.error
    video.release.assert_called_once()


def test_stop_does_not_claim_success_while_writer_is_running(tmp_path):
    recorder = _finished_recorder(tmp_path)
    recorder.thread.is_alive.return_value = True

    recorder.stop()

    assert "did not finish" in recorder.error


def test_stop_before_start_records_failure_without_joining(tmp_path):
    recorder = survey.RawRecorder(tmp_path / "video.mp4", tmp_path / "times.csv", 0)

    recorder.stop()

    assert "did not start" in recorder.error


def test_writer_release_failure_is_reported_and_camera_is_released(tmp_path, monkeypatch):
    recorder = survey.RawRecorder(tmp_path / "video.mp4", tmp_path / "times.csv", 0)
    capture = Mock()
    capture.read.return_value = (True, np.zeros((32, 32, 3), dtype=np.uint8))
    writer = Mock()
    writer.write.side_effect = lambda *_: recorder.stop_event.set()
    writer.release.side_effect = OSError("disk full during finalization")
    monkeypatch.setattr(survey, "StableAVFoundationYuvCapture", lambda *_a, **_k: capture)
    monkeypatch.setattr(survey.cv2, "VideoWriter", lambda *_a, **_k: writer)

    recorder._run()

    assert recorder.error == "could not close video writer: disk full during finalization"
    capture.release.assert_called_once()
    assert len(recorder.timestamps.read_text().splitlines()) == 2
