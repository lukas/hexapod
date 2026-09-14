"""The per-run camera session: spawn, wait for state, feed the readers, stop; no cameras, no daemon."""
from __future__ import annotations

import dataclasses
import json
import subprocess
import threading
from pathlib import Path

import pytest

from hexapod_lab2 import camera_session, eyes, loop, recovery, runner, walk, zero_check

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"


def _state(seq: int, *, px=(640.0, 360.0), x=100.0, y=50.0, yaw=12.0):
    corners = [[px[0] - 10, px[1] - 10], [px[0] + 10, px[1] - 10], [px[0] + 10, px[1] + 10], [px[0] - 10, px[1] + 10]]
    return {
        "schema_version": 1, "seq": seq, "generated_at_unix_s": 1000.0 + seq, "roles": {"top": 0},
        "cameras": [{"index": 0, "role": "top", "state": "streaming", "width": 1280, "height": 720,
                     "detect_width": 3840, "detect_height": 2160, "detect_seq": seq, "duplicate_ids": [],
                     "frame_age_s": 0.05, "captured_unix": 1000.0 + seq, "tags": {"0": corners}}],
        "poses": {"markers": {"0": {"status": "tracked", "position_mm": {"x": x, "y": y}, "rotation_degrees": {"yaw": yaw},
                                    "camera_indices": [0],
                                    "observations": [{"camera_index": 0, "position_mm": {"x": x, "y": y},
                                                      "rotation_degrees": {"yaw": yaw}}]}}},
        "performance": {"frame_sequence": seq},
    }


class FakeSessionProcess:
    """Stands in for `uv run hexapod-cameras session`: writes the files the real one writes."""

    def __init__(self, cmd, cwd=None, stdin=None, stdout=None, stderr=None, delay_states: int = 0, exit_early: bool = False):
        self.cmd, self.cwd = cmd, cwd
        self.out = Path(cmd[cmd.index("--out") + 1])
        self.stdin = _Pipe()
        self.returncode = None
        self.terminated = False
        self.polls = 0
        self.delay_states, self.exit_early = delay_states, exit_early
        self.out.mkdir(parents=True, exist_ok=True)
        if not exit_early and delay_states == 0:
            self.write_state(1)

    def write_state(self, seq: int) -> None:
        (self.out / "state.json").write_text(json.dumps(_state(seq)))
        (self.out / "latest_top.jpg").write_bytes(JPEG + bytes([seq]))

    def poll(self):
        self.polls += 1
        if self.exit_early:
            self.returncode = 2
        elif self.delay_states and self.polls >= self.delay_states:
            self.write_state(1)
        return self.returncode

    def wait(self, timeout=None):
        assert (self.out / "STOP").exists() and self.stdin.closed, "the session must be told to stop via STOP + stdin"
        (self.out / "top.mp4").write_bytes(b"real video")
        self.returncode = 0
        return 0

    def terminate(self):
        self.terminated = True


class _Pipe:
    closed = False

    def close(self):
        self.closed = True


def _session(settings, tmp_path, **kw):
    on = dataclasses.replace(settings, camera_session=True, camera_start_budget_s=5.0)
    made = {}

    def popen(cmd, **popen_kw):
        made["proc"] = FakeSessionProcess(cmd, **popen_kw, **kw)
        return made["proc"]

    clock = {"t": 0.0}
    cam = camera_session.CameraSession(on, tmp_path / "run", popen=popen, clock=lambda: clock["t"],
                                       sleep=lambda s: clock.__setitem__("t", clock["t"] + s), log=lambda m: None)
    return cam, made, on


def test_session_starts_in_the_tracker_checkout_waits_for_state_and_stops_cleanly(settings, tmp_path):
    cam, made, on = _session(settings, tmp_path)
    assert cam.start() and cam.ready
    proc = made["proc"]
    assert proc.cmd[:4] == ["uv", "run", "hexapod-cameras", "session"] and "--roles" in proc.cmd and proc.cwd == str(on.tracker_checkout)
    assert cam.camera_dir == tmp_path / "run" / "camera" and cam.state()["seq"] == 1
    assert cam.latest() == JPEG + b"\x01" and cam.latest_path().name == "latest_top.jpg"
    cam.stop()
    assert proc.returncode == 0 and cam.video_path().name == "top.mp4" and cam.proc is None
    (cam.dir / "top.mov").write_bytes(b"native video")
    assert cam.video_path().name == "top.mov"
    assert cam.video_path("side") is None
    (cam.dir / "side.mov").write_bytes(b"side video")
    assert cam.video_path("side").name == "side.mov"


def test_session_reports_a_child_that_dies_or_never_writes(settings, tmp_path):
    cam, made, _ = _session(settings, tmp_path, exit_early=True)
    assert not cam.start() and "exited 2" in cam.reason and cam.camera_dir is None
    cam2, made2, _ = _session(settings, tmp_path / "b", delay_states=10_000)
    assert not cam2.start() and "no camera state" in cam2.reason


def test_session_off_in_settings_does_nothing(settings, tmp_path):
    cam = camera_session.CameraSession(settings, tmp_path, popen=lambda *a, **k: (_ for _ in ()).throw(AssertionError("spawned")))
    assert not cam.start() and "disabled" in cam.reason and cam.camera_dir is None


def test_walk_session_reads_detections_and_poses_from_the_directory(settings, tmp_path):
    d = tmp_path / "camera"
    d.mkdir()
    d.joinpath("state.json").write_text(json.dumps(_state(3, px=(320.0, 180.0), x=-40.0, y=75.0, yaw=-30.0)))
    calls = []
    s = walk.Session(settings, tmp_path, get=lambda url: calls.append(url), camera_dir=d)
    frac = s.pixel()
    assert frac == (0.25, 0.25) and s.fit_source == "tag0" and s.seen_camera == 0
    p = s.pose("leg")
    assert p.tracked and p.x == -40.0 and p.y == 75.0 and p.yaw == -30.0 and s.camera_index == 0
    assert calls == []                                              # never touched the HTTP server
    d.joinpath("state.json").unlink()
    assert s.pixel() is None                                        # no state yet: not visible, not an error


def test_runner_command_points_run_hw_at_the_session_directory(settings, tmp_path):
    cmd = runner.command(settings, "steps_air_v1", vision_dir=tmp_path / "camera")
    assert "--capture-vision" in cmd and cmd[cmd.index("--vision-dir") + 1] == str(tmp_path / "camera")
    assert "--vision-url" not in cmd and "--vision-frame-url" not in cmd
    legacy = runner.command(settings, "steps_air_v1")
    assert "--vision-url" in legacy and "--vision-dir" not in legacy


def test_zero_check_argv_uses_the_directory_and_the_top_role(settings, tmp_path):
    seen = {}

    def run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"ok": True, "legs": {}}), stderr="")

    zero_check._real_camera(settings, None, run=run, camera_dir=tmp_path / "camera")
    cmd = seen["cmd"]
    assert cmd[cmd.index("--camera-dir") + 1] == str(tmp_path / "camera") and cmd[cmd.index("--top-camera") + 1] == "top"
    assert "--camera-url" not in cmd


def test_wide_capture_copies_new_stills_from_the_session_file(tmp_path):
    src = tmp_path / "latest_top.jpg"
    src.write_bytes(JPEG)
    cap = eyes.WideCapture("http://127.0.0.1:9/none.jpg", tmp_path / "wide", hz=50.0, frame_file=src)
    with cap:
        threading.Event().wait(0.08)
        import os
        src.write_bytes(JPEG + b"2")
        os.utime(src, (2_000_000_000, 2_000_000_000))
        threading.Event().wait(0.08)
    frames = sorted((tmp_path / "wide").glob("*.jpg"))
    assert len(frames) == 2                                         # one per distinct file version, not one per tick
    assert frames[1].read_bytes().endswith(b"2")


@pytest.mark.parametrize("video_suffix", ["mp4", "mov"])
def test_ready_to_move_reads_the_session_still_and_see_run_links_the_real_video(settings, store, tmp_path, monkeypatch, video_suffix):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    still = tmp_path / "latest_top.jpg"
    still.write_bytes(JPEG)
    monkeypatch.setattr(eyes, "_scaled_jpeg", lambda *a, **k: b"jpg")
    seen = {}

    def post(body, api_key, timeout):
        seen["images"] = sum(1 for c in body["messages"][0]["content"] if c["type"] == "image")
        return {"content": [{"type": "text", "text": "YES fine"}], "usage": {}}

    ok, text, _ = eyes.real_ready_to_move(settings, post=post, fetch=lambda url: (_ for _ in ()).throw(OSError("no server")),
                                          frame_file=still)
    assert ok and seen["images"] == 2 and (settings.data_dir / "look.jpg").read_bytes() == JPEG
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    rid = store.start_run(pid)
    run_dir = settings.runs_dir / rid
    (run_dir / "wide").mkdir(parents=True)
    for i in range(3):
        (run_dir / "wide" / f"{i:05d}.jpg").write_bytes(JPEG)
    (run_dir / "camera").mkdir()
    (run_dir / "camera" / "top.mp4").write_bytes(b"real video")
    (run_dir / "camera" / f"top.{video_suffix}").write_bytes(b"real video")
    store.finish_run(rid, status="ok", exit_code=0, run_dir=str(run_dir), summary={}, log_tail="")
    monkeypatch.setattr(eyes, "describe", lambda *a, **k: ("moved a bit", 0.001))
    monkeypatch.setattr(eyes, "make_video", lambda *a, **k: (_ for _ in ()).throw(AssertionError("stitched jpegs instead of using the recording")))
    eyes.see_run(settings, store, rid, "ctx", log=lambda m: None)
    assert json.loads(store.run(rid)["summary_json"])["video"] == f"camera/top.{video_suffix}"


def test_recovery_recorder_takes_stills_from_the_session(tmp_path):
    still = tmp_path / "latest_top.jpg"
    still.write_bytes(JPEG)
    rec = recovery.Recorder(tmp_path / "rec", "http://127.0.0.1:9/x.jpg", get=lambda url: {"ok": True},
                            fetch=lambda url: (_ for _ in ()).throw(OSError("no server")), frame_file=still)
    rec.snapshot("http://robot", "00_before")
    assert (tmp_path / "rec" / "00_before.jpg").read_bytes() == JPEG


def test_loop_gives_every_reader_the_run_session_and_stops_it_afterwards(settings, store, tmp_path, monkeypatch):
    on = dataclasses.replace(settings, camera_session=True, camera_start_budget_s=5.0)
    made = {}
    monkeypatch.setattr(camera_session.subprocess, "Popen", lambda cmd, **kw: made.setdefault("proc", FakeSessionProcess(cmd, **kw)))
    got = {}

    def fake_ready(settings_, **kw):
        got["frame_file"] = kw.get("frame_file")
        return True, "YES", 0.0

    def fake_run(settings_, protocol, run_id, **kw):
        got["camera_dir"] = kw.get("camera_dir")
        return runner.RunResult(status="ok", exit_code=0, run_dir=settings_.runs_dir / run_id, summary={}, log_tail="", motion_s=1.0)

    monkeypatch.setattr(eyes, "ready_to_move", fake_ready)
    monkeypatch.setattr(runner, "run_protocol", fake_run)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(eyes, "see_run", lambda *a, **k: "")
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    row = loop.run_once(on, store, store.plan(pid), log=lambda m: None)
    assert row["status"] == "ok"
    run_dir = on.runs_dir / row["id"]
    assert got["camera_dir"] == run_dir / "camera" and got["frame_file"] == run_dir / "camera" / "latest_top.jpg"
    proc = made["proc"]
    assert proc.returncode == 0 and (run_dir / "camera" / "STOP").exists()      # stopped after the run
    assert any(e["kind"] == "camera" and "session on top" in e["text"] for e in store.events(10))
