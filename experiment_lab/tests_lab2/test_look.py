"""The one look before the robot moves."""
import json

from hexapod_lab2 import alerts, eyes, loop, planner, robot, runner
from conftest import REAL_READY_TO_MOVE

GOOD_FB = {"ok": True, "live": 18, "roll_deg": 1.0, "pitch_deg": -2.0, "joints": [{"temp_c": 31.0}] * 18}
JPEG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")  # a header is enough; scaling falls back


def answer(text, tokens=(900, 20)):
    return lambda body, key, timeout=None: {"content": [{"type": "text", "text": text}],
                                            "usage": {"input_tokens": tokens[0], "output_tokens": tokens[1]}}


def test_look_needs_key_frame_and_a_yes(settings, monkeypatch):
    ready = lambda **k: REAL_READY_TO_MOVE(settings, **k)  # noqa: E731
    assert ready(fetch=lambda url: JPEG)[0] is False  # no API key: cannot look, so no
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def no_camera(url):
        raise OSError("connection refused")
    ok, saw, _ = ready(fetch=no_camera)
    assert ok is False and "no camera frame" in saw
    seen = {}

    def post(body, key, timeout=None):
        seen["timeout"] = timeout
        seen["images"] = sum(1 for c in body["messages"][0]["content"] if c["type"] == "image")
        seen["question"] = body["messages"][0]["content"][-1]["text"]
        return answer("YES. The hexapod sits level on the mat with all six legs down and nobody nearby.")(body, key)
    ok, saw, cost = ready(fetch=lambda url: JPEG, post=post)
    assert ok is True and saw.startswith("YES") and cost > 0
    assert seen["images"] == 2 and "ready to move" in seen["question"] and seen["timeout"] <= settings.health_budget_s
    assert (settings.data_dir / "look.jpg").read_bytes() == JPEG
    ok, saw, _ = ready(fetch=lambda url: JPEG, post=answer("NO - a person is kneeling over the robot holding its left rear leg."))
    assert ok is False and "kneeling" in saw

    def slow(body, key, timeout=None):
        raise TimeoutError("timed out")
    ok, saw, _ = ready(fetch=lambda url: JPEG, post=slow)
    assert ok is False and "did not answer" in saw


def test_a_no_holds_the_run_pauses_and_texts(settings, store, monkeypatch):
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(eyes, "ready_to_move",
                        lambda s, **k: (False, "NO. Someone's hands are on the robot and one leg is detached.", 0.01))
    moved = []
    monkeypatch.setattr(runner, "run_protocol", lambda *a, **k: moved.append(1))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    sent = []
    monkeypatch.setattr(alerts, "send_messages_text", lambda r, m: sent.append(m))
    monkeypatch.setenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "+15555550100")
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=3)
    assert not moved
    run = store.runs()[0]
    assert run["status"] == "held" and json.loads(run["summary_json"])["look"].startswith("NO")
    assert store.plan(pid)["status"] == "queued"
    assert settings.pause_file.read_text().startswith("paused: not moving, the camera look said: NO")
    assert len(sent) == 1 and "hands are on the robot" in sent[0] and "reply resume" in sent[0]
    assert store.consecutive_failed_runs() == 0
    assert store.spend_last_24h() == 0.02  # two looks: a no gets a second look before the hold
    assert any(e["kind"] == "look" and e["text"].startswith("NOT READY") for e in store.events(5))


def test_look_can_be_switched_off(settings, store, monkeypatch):
    import dataclasses
    settings = dataclasses.replace(settings, look_before_moving=False)
    store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(eyes, "ready_to_move", lambda s, **k: (False, "NO", 0.0))
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary=None, log_tail="", motion_s=1.0))
    monkeypatch.setattr(planner, "plan", lambda *a, **k: {"ok": True, "added": 0, "cost_usd": 0.0})
    loop.main_loop(settings, store, log=lambda m: None, sleep=lambda s: None, max_iterations=2)
    assert store.runs()[0]["status"] == "ok"


def test_one_wobbly_no_gets_a_second_look_before_the_loop_holds(settings, store, monkeypatch):
    from hexapod_lab2 import loop, planner, robot, runner
    from tests_lab2.test_lab2 import GOOD_FB
    answers = iter([(False, "NO legs look bunched", 0.01), (True, "YES flat, legs out", 0.01)])
    monkeypatch.setattr(eyes, "ready_to_move", lambda s, **k: next(answers))
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=2.0))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    naps = []
    run = loop.run_once(settings, store, store.plan(pid), log=lambda m: None, sleep_fn=naps.append)
    assert run["status"] == "ok" and naps == [8.0]
    kinds = [e["text"][:11] for e in store.events(5) if e["kind"] == "look"]
    assert any(k.startswith("second look") for k in kinds)
