"""The zero-pose double check: encoders x camera, and what the loop does with each answer."""
import dataclasses
import json
import subprocess

from hexapod_lab2 import loop, planner, robot, runner, zero_check
from tests_lab2.test_lab2 import GOOD_FB

ZERO_FB = {"ok": True, "live": 18, "roll_deg": 0.3, "pitch_deg": 3.0, "joints": [{"deg": 0.5, "temp_c": 31.0} for _ in range(18)]}


def _fb(**off):
    fb = json.loads(json.dumps(ZERO_FB))
    for j, d in off.items():
        fb["joints"][int(j)]["deg"] = d
    return fb


def _cam(off=(), error=None):
    legs = {str(l): {"azimuth_deg": -19.6 + (25.0 if l in off else 1.0), "expected_deg": -19.6,
                     "residual_deg": 25.0 if l in off else 1.0, "verdict": "off" if l in off else "ok"} for l in range(6)}
    doc = {"ok": not off and not error, "off": list(off), "unseen": [], "error": error, "legs": {} if error else legs,
           "summary": "x", "frame": "/tmp/zero_check_cam2.jpg"}
    return lambda settings, out_dir, **k: doc


def test_encoders_gate():
    assert zero_check.encoders(_fb())["at_zero"]
    e = zero_check.encoders(_fb(**{"4": 20.0}))
    assert not e["at_zero"] and e["worst_joint"] == 4 and e["worst_deg"] == 20.0
    assert not zero_check.encoders(GOOD_FB)["known"]          # no deg fields
    assert not zero_check.encoders(None)["known"]


def test_double_check_verdicts(settings, monkeypatch):
    quiet = lambda m: None  # noqa: E731
    assert zero_check.double_check(settings, _fb(**{"7": 30.0}), None, log=quiet)["verdict"] == "not_at_zero"
    assert zero_check.double_check(settings, GOOD_FB, None, log=quiet)["verdict"] == "blind"
    monkeypatch.setattr(zero_check, "camera", _cam())
    assert zero_check.double_check(settings, _fb(), None, log=quiet)["verdict"] == "agree"
    monkeypatch.setattr(zero_check, "camera", _cam(off=(2,)))
    r = zero_check.double_check(settings, _fb(), None, log=quiet)
    assert r["verdict"] == "camera_disagrees" and r["legs_off"] == [2] and "leg 2" in r["text"] and r["frame"]
    monkeypatch.setattr(zero_check, "camera", _cam(error="top camera 2 gave no frame"))
    assert zero_check.double_check(settings, _fb(), None, log=quiet)["verdict"] == "blind"


def test_camera_runs_the_tracker_cli_and_parses_its_last_line(settings, tmp_path):
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, cwd=kw.get("cwd"), timeout=kw.get("timeout"))
        return subprocess.CompletedProcess(cmd, 0, stdout="lid 11 L4 knee: note\n" + json.dumps({"ok": True, "legs": {"0": {}}}) + "\n", stderr="")
    doc = zero_check._real_camera(settings, tmp_path, run=run)
    assert doc["ok"] is True
    assert seen["cmd"][:3] == ["uv", "run", "hexapod-zero-check"] and "--json" in seen["cmd"] and str(tmp_path) in seen["cmd"]
    assert seen["cmd"][seen["cmd"].index("--camera-url") + 1] == "http://127.0.0.1:9"
    assert seen["timeout"] == settings.zero_check_budget_s and seen["cwd"] == str(settings.tracker_checkout)

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    assert "longer than" in zero_check._real_camera(settings, tmp_path, run=slow)["error"]

    def garbage(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 3, stdout="", stderr="Traceback ...")
    assert "exit 3" in zero_check._real_camera(settings, tmp_path, run=garbage)["error"]


def _ran_ok(monkeypatch, fb):
    monkeypatch.setattr(robot, "health", lambda url, budget: fb)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={"ok": True}, log_tail="", motion_s=1.0))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})


def test_loop_holds_and_pauses_only_when_encoders_say_zero_and_camera_disagrees(settings, store, monkeypatch):
    _ran_ok(monkeypatch, _fb())
    monkeypatch.setattr(zero_check, "camera", _cam(off=(2,)))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    run = loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert run["status"] == "held"
    assert store.plan(pid)["status"] == "queued"
    assert "leg" in settings.pause_file.read_text()
    kinds = {e["kind"] for e in store.events(10)}
    assert {"zero_check", "needs_hand"} <= kinds
    assert json.loads(run["summary_json"])["zero_check"]["legs_off"] == [2]


def test_loop_runs_when_camera_agrees_and_records_the_check(settings, store, monkeypatch):
    _ran_ok(monkeypatch, _fb())
    monkeypatch.setattr(zero_check, "camera", _cam())
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    run = loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert run["status"] == "ok"
    assert json.loads(run["summary_json"])["zero_check"]["verdict"] == "agree"
    assert not settings.pause_file.exists()


def test_loop_runs_blind_when_the_camera_cannot_measure(settings, store, monkeypatch):
    _ran_ok(monkeypatch, _fb())     # conftest's camera says "no camera in tests"
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    run = loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert run["status"] == "ok" and json.loads(run["summary_json"])["zero_check"]["verdict"] == "blind"


def test_walk_protocols_and_switched_off_skip_the_check(settings, store, monkeypatch):
    calls = []
    monkeypatch.setattr(zero_check, "camera", lambda *a, **k: calls.append(1) or {"ok": True, "legs": {"0": {}}, "off": []})
    _ran_ok(monkeypatch, _fb())
    (settings.protocols_dir / "walk_t_v1.json").write_text(json.dumps(
        {"name": "walk_t_v1", "walk_protocol": 1, "legs": [{"name": "f", "vx_mm_s": 30, "seconds": 2}]}))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="walk_t_v1", build_spec=None)
    assert loop.run_once(settings, store, store.plan(pid), log=lambda m: None)["status"] == "ok"
    assert calls == []
    off = dataclasses.replace(settings, zero_check=False)
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    run = loop.run_once(off, store, store.plan(pid), log=lambda m: None)
    assert run["status"] == "ok" and calls == [] and "zero_check" not in json.loads(run["summary_json"])
