"""A dozen fast tests for the decisions; the runner and CLI are exercised live."""
import dataclasses
import json

import pytest

from hexapod_lab2 import loop, planner, robot, runner
from hexapod_lab2.store import Store

GOOD_FB = {"ok": True, "live": 18, "roll_deg": 1.0, "pitch_deg": -2.0,
           "joints": [{"temp_c": 31.0}] * 18}


def test_health_passes_on_healthy_feedback():
    assert robot.assess(dict(GOOD_FB), elapsed_s=0.2, budget_s=10) == GOOD_FB


@pytest.mark.parametrize("patch, exc, text", [
    ({"live": 17}, robot.RobotNotReady, "17/18"),
    ({"ok": False}, robot.RobotNotReady, "not ok"),
    ({"joints": [{"temp_c": 61.0}] * 18}, robot.RobotNotReady, "61 C"),
    ({"pitch_deg": 40.0}, robot.RobotNotReady, "tilt"),
])
def test_health_refuses_bad_robot(patch, exc, text):
    with pytest.raises(exc, match=text):
        robot.assess({**GOOD_FB, **patch}, elapsed_s=0.2, budget_s=10)


def test_health_read_over_ten_seconds_counts_as_unreachable():
    with pytest.raises(robot.RobotUnreachable, match="budget 10 s"):
        robot.assess(dict(GOOD_FB), elapsed_s=10.4, budget_s=10)


def test_runner_command_uses_checkout_python_and_vision(settings):
    cmd = runner.command(settings, "steps_air_v1")
    assert cmd[0] == str(settings.checkout / ".venv" / "bin" / "python")
    assert "--go" in cmd and "--capture-vision" in cmd and "--force" not in cmd
    assert cmd[cmd.index("--vision-url") + 1] == settings.vision_url
    assert cmd[cmd.index("--vision-frame-url") + 1] == settings.vision_frame_url


def test_runner_passes_force_for_whole_body_protocols_unless_disabled(settings):
    assert "--force" in runner.command(settings, "champion_stand_ground_v1")
    gated = dataclasses.replace(settings, allow_force=False)
    assert "--force" not in runner.command(gated, "champion_stand_ground_v1")


def test_validate_plans_checks_disk_and_force_gate(settings):
    settings = dataclasses.replace(settings, allow_force=False)
    plans = planner.validate_plans(settings, [
        {"title": "L0 steps", "why": "Baseline. Cheap.", "kind": "existing", "protocol": "steps_air_v1"},
        {"title": "missing", "why": "Not on disk.", "kind": "existing", "protocol": "l9_nothing_v1"},
        {"title": "stand", "why": "Whole body.", "kind": "existing",
         "protocol": "champion_stand_ground_v1", "force": True},
        {"title": "build", "why": "New leg.", "kind": "needs_code", "build_spec": "Remap steps_air_v1 to leg 3."},
        {"title": "junk", "why": "", "kind": "existing", "protocol": "steps_air_v1"},
    ])
    kinds = [(p["title"], p["kind"]) for p in plans]
    assert kinds == [("L0 steps", "existing"), ("missing", "needs_code"), ("build", "needs_code")]
    assert plans[1]["build_spec"].startswith("Create sysid/protocols/l9_nothing_v1.json")


def test_store_queue_order_and_consecutive_failures(store):
    a = store.add_plan(title="a", why="w", kind="existing", protocol="p", build_spec=None)
    b = store.add_plan(title="b", why="w", kind="needs_code", protocol=None, build_spec="spec")
    assert store.next_runnable()["id"] == a
    assert [p["id"] for p in store.building_plans()] == [b]
    for status in ("ok", "failed", "unreachable", "failed"):
        rid = store.start_run(a)
        store.finish_run(rid, status=status, exit_code=1, run_dir=None, summary=None, log_tail="")
    assert store.consecutive_failed_runs() == 2  # unreachable does not count
    store.mark_built(b, "p2")
    assert store.plan(b)["kind"] == "existing" and store.plan(b)["status"] == "queued"


def test_stop_reasons(settings, store):
    c = loop.Counters()
    assert loop.stop_reason(settings, store, c) is None
    c.unreachable = 2
    assert "unreachable" in loop.stop_reason(settings, store, c)
    c.unreachable = 0
    store.add_spend("planner", 41.0)
    assert "cap $40" in loop.stop_reason(settings, store, c)


def test_loop_stops_after_three_failed_runs(settings, store, monkeypatch):
    for i in range(4):
        store.add_plan(title=f"p{i}", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="failed", exit_code=1, run_dir=None, summary=None, log_tail="boom", motion_s=1.0))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.5})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=6)
    assert len([r for r in store.runs() if r["status"] == "failed"]) == 3
    assert store.last_stop()["text"] == "3 failed runs in a row"
    assert settings.pause_file.read_text().startswith("stopped: 3 failed runs")


def test_loop_runs_then_plans_and_records_learning(settings, store, monkeypatch):
    store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={"frames": 10}, log_tail="", motion_s=5.0))
    calls = []

    def fake_plan(s, st, last, last_run_id=None):
        calls.append(last["status"] if last else None)
        if last_run_id:
            st.add_learning("leg moved 5 deg", run_id=last_run_id)
        return {"ok": True, "added": 0, "cost_usd": 0.4}
    monkeypatch.setattr(planner, "plan", fake_plan)
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=6)
    assert calls[0] == "ok"
    assert store.last_stop()["text"].startswith("planner returned nothing 2 times")
    run = store.runs()[0]
    assert run["status"] == "ok" and store.learning_for_run(run["id"]) == "leg moved 5 deg"


def test_loop_honours_pause_file(settings, store):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.pause_file.write_text("x")
    slept = []
    reason = loop.main_loop(settings, store, log=lambda m: None, sleep=slept.append, max_iterations=2)
    assert reason == "iteration limit" and len(slept) == 2 and not store.runs()


def test_unreachable_robot_requeues_plan_and_stops_after_two(settings, store, monkeypatch):
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)

    def down(url, budget):
        raise robot.RobotUnreachable("connection refused")
    monkeypatch.setattr(robot, "health", down)
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=4)
    assert store.last_stop()["text"] == "robot unreachable 2 times in a row"
    assert store.plan(pid)["status"] == "queued"


def test_planner_prompt_is_small_and_names_protocols(settings, store):
    store.add_learning("Leg 5 knee hysteresis 3.1 deg at 1.5 A.")
    text = planner.build_prompt(settings, store, None)
    assert len(text) < 20_000
    assert "steps_air_v1" in text and "champion_stand_ground_v1 [traj]" in text
    assert "WHOLE-BODY" not in text
    assert "STEP BACK FIRST" in text and "Leg 5 knee hysteresis" in text
    assert "--force for them automatically" in text
    gated = planner.build_prompt(dataclasses.replace(settings, allow_force=False), store, None)
    assert "cannot run in this loop" in gated


def test_import_hand_run_experiment(settings, store, tmp_path):
    folder = tmp_path / "hex2_trial"
    folder.mkdir()
    (folder / "clip.mp4").write_bytes(b"video")
    (folder / "telemetry.csv").write_text("t,cur\n0,1\n")
    rid = store.import_run(robot="hexapod2", title="Hex2 tripod shuffle", why="See if it stands.",
                           found="It stood for 40 s then tipped left.", source_dir=folder,
                           runs_dir=settings.runs_dir)
    run = store.run(rid)
    assert run["status"] == "ok" and run["robot"] == "hexapod2"
    assert store.run_files(rid) == ["clip.mp4", "telemetry.csv"]
    assert store.learning_for_run(rid).startswith("[hexapod2] It stood")
    assert store.runs(robot="hexapod2")[0]["id"] == rid and store.runs(robot="hexapod1") == []
    assert store.next_runnable() is None  # imported plans never enter the robot-1 queue
    assert store.robots() == ["hexapod2"]


def test_http_import_then_upload_file(settings, store):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hexapod_lab2.web import build_router
    app = FastAPI()
    app.include_router(build_router(lambda: None, lambda: None, settings=settings))
    c = TestClient(app)
    r = c.post("/v2/api/import", json={"title": "Hex2 stand", "why": "Level?", "found": "Level for 30 s.",
                                       "robot": "hexapod2"})
    assert r.status_code == 201, r.text
    rid = r.json()["run_id"]
    up = c.put(f"/v2/api/runs/{rid}/files/clip.mp4", content=b"\x00" * 5000)
    assert up.status_code == 201 and up.json()["bytes"] == 5000
    assert c.put(f"/v2/api/runs/{rid}/files/../evil", content=b"x").status_code in (400, 404, 201)
    assert Store(settings.db_path).run_files(rid) == ["clip.mp4"]
    assert c.get(f"/v2/runs/{rid}/clip.mp4").status_code == 200
    page = c.get("/v2/?robot=hexapod2").text
    assert "Hex2 stand" in page and "clip.mp4" in page
    assert c.put("/v2/api/runs/nope/files/a.txt", content=b"x").status_code == 404


def test_restart_releases_builds_the_dead_thread_left_behind(settings, store, monkeypatch):
    pid = store.add_plan(title="b", why="w", kind="needs_code", protocol=None, build_spec="spec")
    store.set_plan_status(pid, "building", "builder running")
    started = []
    monkeypatch.setattr("hexapod_lab2.loop.BuilderThread.maybe_start", lambda self: started.append(1) or None)
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=1)
    assert store.plan(pid)["status_note"] == "builder interrupted by restart"
    assert "1 interrupted build(s) requeued" in store.events(1)[0]["text"]


def test_restart_after_a_stop_gets_fresh_strikes(settings, store, monkeypatch):
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    for _ in range(3):
        rid = store.start_run(pid)
        store.finish_run(rid, status="failed", exit_code=1, run_dir=None, summary=None, log_tail="")
    store.add_event("stop", "3 failed runs in a row")
    # A real restart comes minutes later; the fixture runs land in the same second.
    store.con.execute("UPDATE runs SET started_at='2026-01-01T00:00:00+00:00'")
    store.con.commit()
    assert store.consecutive_failed_runs() == 3
    store.set_plan_status(pid, "queued")
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=1.0))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=2)
    assert not settings.pause_file.exists()
    assert store.runs()[0]["status"] == "ok"


def test_builds_are_capped_and_prompt_flags_an_idle_robot(settings, store, monkeypatch):
    for i in range(3):
        store.add_plan(title=f"b{i}", why="w", kind="needs_code", protocol=None, build_spec="spec")
    text = planner.build_prompt(settings, store, None)
    assert "3 code jobs are already pending" in text and "robot is idle" in text
    from hexapod_lab2 import claude_cli
    monkeypatch.setattr(claude_cli, "oneshot", lambda *a, **k: claude_cli.CliResult(True, {
        "learned": "", "plans": [
            {"title": "another build", "why": "w.", "kind": "needs_code", "build_spec": "x"},
            {"title": "run this", "why": "w.", "kind": "existing", "protocol": "steps_air_v1"},
        ]}, 0.1, "", ""))
    report = planner.plan(settings, store, None)
    assert report["added"] == 1
    assert store.next_runnable()["protocol"] == "steps_air_v1"
    assert len(store.building_plans()) == 3


def test_waiting_on_builder_still_plans_once(settings, store, monkeypatch):
    store.add_plan(title="b", why="w", kind="needs_code", protocol=None, build_spec="spec")
    monkeypatch.setattr("hexapod_lab2.loop.BuilderThread.maybe_start", lambda self: None)
    monkeypatch.setattr("hexapod_lab2.loop.BuilderThread.busy", lambda self: True)
    calls = []
    monkeypatch.setattr(planner, "plan", lambda *a, **k: calls.append(1) or {"ok": True, "added": 0, "cost_usd": 0.0})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=5)
    assert len(calls) == 1


def test_stand_protocols_are_flagged_rejected_and_skipped(settings, store, monkeypatch):
    assert runner.protocol_needs_stand(settings, "steps_air_L5_v1")
    assert not runner.protocol_needs_stand(settings, "champion_stand_ground_v1")  # "stand pose" is not a stand
    text = planner.build_prompt(settings, store, None)
    assert "steps_air_L5_v1 [NEEDS STAND: not runnable]" in text and "PHYSICAL SETUP" in text
    plans = planner.validate_plans(settings, [
        {"title": "air", "why": "w.", "kind": "existing", "protocol": "steps_air_L5_v1"},
        {"title": "floor", "why": "w.", "kind": "existing", "protocol": "steps_air_v1"},
    ])
    assert [p["protocol"] for p in plans] == ["steps_air_v1"]
    pid = store.add_plan(title="air", why="w", kind="existing", protocol="steps_air_L5_v1", build_spec=None)
    ran = []
    monkeypatch.setattr(loop, "run_once", lambda *a, **k: ran.append(1))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=2)
    assert not ran and store.plan(pid)["status"] == "skipped"


def test_jam_pattern_matches_the_trips_we_saw():
    from hexapod_lab2 import recovery
    for line in ["joint 14 overcurrent 2.34 A (limit 0.75, 3 consecutive polls)",
                 "joint 8 tracking error 30 deg > 30", "start pose did not verify: joint 16 off by 3.0 deg",
                 "joint 0 (ID 2) missed 3 consecutive reads", "bus write failed: Write timeout"]:
        assert recovery.looks_like_jam(line), line
    assert not recovery.looks_like_jam("vision admission failed before motion")


def _fake_robot(fail_first_zero):
    """Robot whose safe-zero fails once (still folded) if asked, then succeeds."""
    calls = []
    state = {"knee": 120.0}
    def post(url, body):
        calls.append((url.rsplit("/", 1)[-1], body))
        if url.endswith("/api/zero") and not (fail_first_zero and calls.count(("zero", body)) == 1):
            state["knee"] = 0.0
        return {"ok": True}
    def get(url):
        if url.endswith("/api/rl/state"):
            return {"pose": {"demo": {"running": False, "status": "done · at zero (safe)" if state["knee"] == 0 else "error: joint 14 overcurrent"}}}
        joints = [{"deg": 0.0} for _ in range(18)]; joints[14]["deg"] = state["knee"]
        return {"ok": True, "roll_deg": 0.3, "pitch_deg": 2.9, "joints": joints}
    return calls, post, get


def test_recovery_ladder_stops_at_first_success(settings):
    from hexapod_lab2 import recovery
    calls, post, get = _fake_robot(fail_first_zero=False)
    slept = []
    rep = recovery.recover(settings, log=lambda m: None, post=post, get=get, sleep=slept.append)
    assert rep["ok"] and [c[0] for c in calls] == ["zero"] and slept == []


def test_recovery_ladder_forces_untrap_only_on_rung_two_with_settle(settings):
    from hexapod_lab2 import recovery
    calls, post, get = _fake_robot(fail_first_zero=True)
    slept = []
    rep = recovery.recover(settings, log=lambda m: None, post=post, get=get, sleep=slept.append)
    assert rep["ok"]
    assert calls == [("zero", {"pose": "sit"}), ("untrap", {"force": True}), ("zero", {"pose": "sit"})]
    assert slept == [recovery.SETTLE_S, recovery.SETTLE_S]


def test_failed_recovery_pauses_texts_and_keeps_loop_alive(settings, store, monkeypatch):
    from hexapod_lab2 import alerts, recovery
    store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="failed", exit_code=1, run_dir=None, summary=None,
        log_tail="runner: ok=False error=joint 14 overcurrent 1.10 A (limit 0.75)", motion_s=7.0))
    monkeypatch.setattr(recovery, "recover", lambda s, **k: {"ok": False, "rungs": [{"rung": "zero", "status": "error: joint 14", "ok": False, "seconds": 9.0}], "final": "error: joint 14", "before": {}, "after": {}})
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    sent = []
    monkeypatch.setattr(alerts, "send_messages_text", lambda r, m: sent.append((r, m)))
    monkeypatch.setenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "+15555550100")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    reason = loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=3)
    assert reason == "iteration limit"            # paused, not stopped
    assert settings.pause_file.exists() and "needs a hand" in settings.pause_file.read_text()
    assert len(sent) == 1 and "needs a hand" in sent[0][1] and alerts.DASHBOARD in sent[0][1]
    kinds = [e["kind"] for e in store.events(10)]
    assert "needs_hand" in kinds and "recovery" in kinds and "text" in kinds


def test_texts_are_rate_limited_per_reason(store, monkeypatch):
    from hexapod_lab2 import alerts
    sent = []
    fake = lambda r, m: sent.append(m)
    assert alerts.text(store, "stop", "first", sender=fake, recipient="+15555550100")
    assert not alerts.text(store, "stop", "second", sender=fake, recipient="+15555550100")
    assert alerts.text(store, "needs_hand", "other reason", sender=fake, recipient="+15555550100")
    assert not alerts.text(store, "stop", "no recipient", sender=fake, recipient="")
    assert len(sent) == 2


def test_recovery_is_recorded_as_a_run_with_artifacts(settings, store, monkeypatch):
    from hexapod_lab2 import recovery
    calls, post, get = _fake_robot(fail_first_zero=True)
    stills = []
    def fetch(url):
        stills.append(url); return b"jpeg"
    def fake_recover(s, **k):
        return recovery.recover(s, log=lambda m: None, post=post, get=get, sleep=lambda x: None,
                                run_dir=k.get("run_dir"), fetch=fetch)
    plan = {"protocol": "l1_air_radial_shear_hysteresis_control_v1", "robot": "hexapod1"}
    row = loop.record_recovery(settings, store, plan, "joint 14 overcurrent 1.10 A", log=lambda m: None,
                               sleep=lambda x: None, recover=fake_recover)
    assert row["status"] == "ok"
    summary = json.loads(row["summary_json"])
    assert summary["recovery"] and summary["after_protocol"] == plan["protocol"]
    assert [r["rung"] for r in summary["rungs"]] == ["zero", "untrap", "zero"]
    assert summary["before"]["knees_deg"][4] == 120.0 and summary["after"]["knees_deg"][4] == 0.0
    files = store.run_files(row["id"])
    assert "00_before_feedback.json" in files and "00_before.jpg" in files and "03_after_zero.jpg" in files
    assert len(stills) == 4
    plan_row = store.plan(row["plan_id"])
    assert plan_row["title"].startswith("Recovery after") and plan_row["status_note"] == "freed by zero"
    # A recovered jam is an experiment, not a strike.
    rid = store.start_run(plan_row["id"]); store.finish_run(rid, status="failed", exit_code=1, run_dir=None, summary=None, log_tail="")
    assert store.consecutive_failed_runs() == 1


def test_cap_file_overrides_default_and_stop_pauses_with_reply_hint(settings, store, monkeypatch):
    from hexapod_lab2 import alerts, commands
    sent = []
    monkeypatch.setattr(alerts, "send_messages_text", lambda r, m: sent.append(m))
    monkeypatch.setenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "+15555550100")
    store.add_spend("planner", 45.0)
    assert settings.current_cap() == 40.0
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=2,
                   inbox=commands.Inbox(recipient="", db_path=settings.data_dir / "none.db"))
    assert settings.pause_file.read_text().startswith("stopped: spent $45.00")
    assert sent and "raise cap" in sent[0]
    settings.set_cap(100)
    assert settings.current_cap() == 100.0
    assert loop.stop_reason(settings, store, loop.Counters()) is None


def test_text_commands_parse_and_apply(settings, store):
    from hexapod_lab2 import commands
    assert commands.parse("raise cap to 100", 40) == ("cap", 100.0)
    assert commands.parse("Raise cap", 40) == ("cap", 60.0)   # 1.5x, rounded up to $10
    assert commands.parse("cap 80", 40) == ("cap", 80.0)
    assert commands.parse("resume", 40)[0] == "resume"
    assert commands.parse("please pause it", 40)[0] == "pause"
    assert commands.parse("status?", 40)[0] == "status"
    assert commands.parse("hello", 40)[0] == "unknown"
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.pause_file.write_text("stopped: spent $41 in 24 h, cap $40\n")
    replies, resumed = [], []
    commands.apply(settings, store, "raise cap 100", reply=replies.append, on_resume=lambda: resumed.append(1))
    assert settings.current_cap() == 100.0 and not settings.pause_file.exists() and resumed
    assert "resuming" in replies[-1]
    commands.apply(settings, store, "pause", reply=replies.append)
    assert settings.pause_file.exists()
    commands.apply(settings, store, "status", reply=replies.append)
    assert "PAUSED" in replies[-1] and "$100" in replies[-1]
    assert [e["kind"] for e in store.events(3)] == ["command"] * 3


def test_inbox_reads_only_recipient_messages_after_start(tmp_path):
    import sqlite3
    from hexapod_lab2 import commands
    db = tmp_path / "chat.db"
    con = sqlite3.connect(db)
    con.executescript("CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT);"
                      "CREATE TABLE message (ROWID INTEGER PRIMARY KEY, text TEXT, handle_id INTEGER, is_from_me INTEGER, date INTEGER);")
    con.execute("INSERT INTO handle VALUES (1, '+15555550100'), (2, 'other@example.com')")
    now_apple_ns = int((commands.time.time() - commands.APPLE_EPOCH_OFFSET) * 1e9)
    old = now_apple_ns - int(3600e9)
    con.execute("INSERT INTO message VALUES (1, 'old resume', 1, 0, ?)", (old,))
    con.execute("INSERT INTO message VALUES (2, 'raise cap 100', 1, 0, ?)", (now_apple_ns + int(5e9),))
    con.execute("INSERT INTO message VALUES (3, 'status', 2, 0, ?)", (now_apple_ns + int(5e9),))
    con.execute("INSERT INTO message VALUES (4, 'Robot Lab: cap is now', 1, 1, ?)", (now_apple_ns + int(6e9),))
    con.commit(); con.close()
    inbox = commands.Inbox(recipient="+1 (555) 555-0100", db_path=db, started_unix=commands.time.time() - 1)
    assert inbox.poll() == ["raise cap 100"]
    assert inbox.poll() == []
    missing = commands.Inbox(recipient="+15555550100", db_path=tmp_path / "nope.db")
    assert missing.poll() == [] and missing.unavailable


def test_merge_gate_rejects_out_of_scope_oversize_and_self_edits(settings):
    from hexapod_lab2 import engineer
    ok = ["hexapod_walker/prototype_sts3215/linux_control/sysid_runner.py"]
    assert engineer.gate(settings, " 1 file changed, 8 insertions(+), 1 deletion(-)", ok) is None
    assert "outside" in engineer.gate(settings, " 1 file changed, 2 insertions(+)", ["README.md"])
    assert "forbidden" in engineer.gate(settings, " 1 file changed, 2 insertions(+)",
                                        ["hexapod_walker/prototype_sts3215/firmware/bridge.ino"])
    assert "forbidden" in engineer.gate(settings, " 1 file changed, 2 insertions(+)",
                                        ["experiment_lab/hexapod_lab2/loop.py"]) or "outside" in engineer.gate(
        settings, " 1 file changed, 2 insertions(+)", ["experiment_lab/hexapod_lab2/loop.py"])
    assert "changed lines" in engineer.gate(settings, " 3 files changed, 180 insertions(+), 40 deletions(-)", ok)
    assert engineer.gate(settings, "", []) == "no changes on the branch"


def test_frame_sampler_spreads_and_keeps_the_last_four(tmp_path):
    from hexapod_lab2 import eyes
    frames = [tmp_path / f"{i:05d}.jpg" for i in range(100)]
    picked = eyes.sample_frames(frames)
    assert len(picked) == 12
    assert picked[-4:] == frames[-4:]
    assert picked[0] == frames[0] and picked[7] == frames[95]
    assert eyes.sample_frames(frames[:5]) == frames[:5]


def test_wide_capture_records_frames(tmp_path):
    import time
    from hexapod_lab2 import eyes
    grabbed = []
    with eyes.WideCapture("http://x/snap.jpg", tmp_path / "wide", hz=50.0, fetch=lambda u: grabbed.append(u) or b"jpg") as cap:
        time.sleep(0.2)
    assert cap.count >= 3 and len(list((tmp_path / "wide").glob("*.jpg"))) == cap.count


def test_deploy_waits_for_the_gap_between_runs_and_clears_the_flag(settings, store, monkeypatch):
    from hexapod_lab2 import deploy, robot
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.deploy_flag.write_text("lab2/fix-abc: raise GLIDE_TOL\n")
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    rid = store.start_run(pid)
    calls = []
    fake_run = lambda *a, **k: calls.append(k.get("env", {}).get("HEXAPOD_SSH")) or type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    assert deploy.deploy_if_needed(settings, store, log=lambda m: None, run=fake_run)["reason"] == "a run is in progress"
    assert calls == []
    store.finish_run(rid, status="ok", exit_code=0, run_dir=None, summary=None, log_tail="")
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    rep = deploy.deploy_if_needed(settings, store, log=lambda m: None, run=fake_run)
    assert rep["deployed"] and calls == ["arduino@192.168.4.39"] and not settings.deploy_flag.exists()
    assert store.events(1)[0]["kind"] == "deploy"


def test_engineer_success_merges_queues_verify_and_followups(settings, store, monkeypatch):
    from hexapod_lab2 import builder, claude_cli, engineer
    monkeypatch.setattr(engineer, "_prepare_worktree", lambda s, pid, subdir="fix": settings.data_dir / "wt")
    monkeypatch.setattr(engineer, "_cleanup_worktree", lambda s, wt: None)
    monkeypatch.setattr(engineer.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    monkeypatch.setattr(claude_cli, "build", lambda *a, **k: claude_cli.CliResult(True, {
        "fixed": True, "summary": "Raised GLIDE_TOL_DEG 3 -> 8; tests pass.", "verify_protocol": "steps_air_v1",
        "touched_robot_side": True,
        "followups": [{"title": "Make the tolerance a protocol field", "why": "w", "fix_spec": "add start_tol to runner"}]},
        2.5, "", ""))
    monkeypatch.setattr(engineer, "merge_branch", lambda s, b: {"merged": True, "files": [
        "hexapod_walker/prototype_sts3215/linux_control/sysid_runner.py"], "stat": "1 file changed, 8 insertions(+)", "robot_side": True})
    pid = store.add_plan(title="Loosen the 3 deg glide gate", why="w", kind="needs_fix", protocol=None,
                         build_spec="GLIDE_TOL_DEG=3 rejects 3.4 deg droop")
    rep = engineer.fix_plan(settings, store, store.plan(pid))
    assert rep["ok"] and rep["verify"] == "steps_air_v1" and rep["followups"] == 1
    assert settings.deploy_flag.exists()
    plans = store.plans(limit=10)
    assert any(p["title"].startswith("Verify fix") and p["status"] == "queued" for p in plans)
    assert any(p["kind"] == "needs_fix" and p["status"] == "building" and p["source"] == "engineer" for p in plans)
    assert store.plan(pid)["status"] == "done"
    assert store.spend_last_24h() == 2.5


def test_engineer_unmerged_branch_is_left_for_review_and_texted(settings, store, monkeypatch):
    from hexapod_lab2 import alerts, claude_cli, engineer
    monkeypatch.setattr(engineer, "_prepare_worktree", lambda s, pid, subdir="fix": settings.data_dir / "wt")
    monkeypatch.setattr(engineer, "_cleanup_worktree", lambda s, wt: None)
    monkeypatch.setattr(engineer.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    monkeypatch.setattr(claude_cli, "build", lambda *a, **k: claude_cli.CliResult(True, {"fixed": True, "summary": "rewrote everything"}, 9.0, "", ""))
    monkeypatch.setattr(engineer, "merge_branch", lambda s, b: {"merged": False, "reason": "412 changed lines, limit 200"})
    sent = []
    monkeypatch.setattr(alerts, "send_messages_text", lambda r, m: sent.append(m))
    monkeypatch.setenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "+15555550100")
    pid = store.add_plan(title="Big rewrite", why="w", kind="needs_fix", protocol=None, build_spec="x")
    rep = engineer.fix_plan(settings, store, store.plan(pid))
    assert not rep["ok"] and "left on lab2/fix-" in store.plan(pid)["status_note"]
    assert sent and "not merged" in sent[0] and not settings.deploy_flag.exists()


def test_code_slot_prefers_fixes_over_builds(settings, store, monkeypatch):
    from hexapod_lab2 import builder
    b = store.add_plan(title="build", why="w", kind="needs_code", protocol=None, build_spec="x")
    f = store.add_plan(title="fix", why="w", kind="needs_fix", protocol=None, build_spec="y")
    started = []
    class FakeThread:
        def __init__(self, target=None, args=(), name="", daemon=True): started.append((name, args[2]["id"]))
        def start(self): pass
        def is_alive(self): return False
    monkeypatch.setattr(builder.threading, "Thread", FakeThread)
    slot = builder.BuilderThread(settings, store)
    assert slot.maybe_start() == f and started[0][0].startswith("engineer-")


def test_seen_text_reaches_the_planner_digest(settings, store):
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    rid = store.start_run(pid)
    store.finish_run(rid, status="failed", exit_code=1, run_dir=None, summary={"x": 1}, log_tail="joint 14 overcurrent")
    store.update_run_summary(rid, seen="Leg 4 folded under the body from frame 6; chassis propped on the right side.")
    text = planner.build_prompt(settings, store, store.runs(limit=1)[0])
    assert "what the wide camera showed" in text and "Leg 4 folded" in text
    assert "needs_fix" in text and "Do not work around a code blocker" in text
    plans = planner.validate_plans(settings, [{"title": "Loosen gate", "why": "w.", "kind": "needs_fix",
                                               "build_spec": "GLIDE_TOL_DEG 3 -> 8 in sysid_runner.py"}])
    assert plans[0]["kind"] == "needs_fix"
