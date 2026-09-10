"""A dozen fast tests for the decisions; the runner and CLI are exercised live."""
import dataclasses

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
    reason = loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None)
    assert reason == "3 failed runs in a row"
    assert len([r for r in store.runs() if r["status"] == "failed"]) == 3
    assert store.last_stop()["text"] == reason


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
    reason = loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None)
    assert calls[0] == "ok"
    assert reason.startswith("planner returned nothing 2 times")
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
    reason = loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None)
    assert reason == "robot unreachable 2 times in a row"
    assert store.plan(pid)["status"] == "queued"


def test_planner_prompt_is_small_and_names_protocols(settings, store):
    store.add_learning("Leg 5 knee hysteresis 3.1 deg at 1.5 A.")
    text = planner.build_prompt(settings, store, None)
    assert len(text) < 20_000
    assert "steps_air_v1" in text and "champion_stand_ground_v1 [WHOLE-BODY]" in text
    assert "STEP BACK FIRST" in text and "Leg 5 knee hysteresis" in text
    assert "--force for them automatically" in text
    gated = planner.build_prompt(dataclasses.replace(settings, allow_force=False), store, None)
    assert "cannot run in this loop" in gated
