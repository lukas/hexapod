"""Regression coverage for partial fleet idleness and durable eval dispatch."""

import datetime
import importlib.util
import json
import pathlib
import sys
from types import SimpleNamespace

import pytest


_ORCH_DIR = pathlib.Path(__file__).resolve().parents[1] / "orchestrator"
if str(_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCH_DIR))
_spec = importlib.util.spec_from_file_location(
    "watch_loop_refill_tests", _ORCH_DIR / "watch_loop.py")
watch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(watch)


def _capacity(free=5, backlog=0):
    return {"slots_total": 12, "slots_ready": 11, "slots_free": free,
            "free_pods": [f"hexapod-mjx-train-{i}" for i in range(free)],
            "backlog_count": backlog}


def _active(label):
    return {"label": label, "runs": {"cw-unrelated-finished-run"}}


def test_partial_idle_can_refill_alongside_unrelated_triage():
    active = [_active("cw-unrelated-finished-run")]
    assert not watch.has_refill_owner(active)
    assert watch.partial_refill_trigger(_capacity(), active)


@pytest.mark.parametrize("label", ["partial-refill", "operator-kick", "evalready"])
def test_active_refill_owner_prevents_duplicate_cycle(label):
    active = [_active(label)]
    assert watch.has_refill_owner(active)
    assert watch.partial_refill_trigger(_capacity(), active) is None


def test_nonempty_backlog_belongs_to_mechanical_drain():
    assert watch.partial_refill_trigger(_capacity(backlog=3), []) is None


def test_full_or_unreadable_capacity_does_not_invent_idle_work():
    assert watch.partial_refill_trigger(_capacity(free=0), []) is None
    assert watch.partial_refill_trigger(None, []) is None


@pytest.fixture
def registry(tmp_path, monkeypatch):
    path = tmp_path / "pending_evals.json"
    now = datetime.datetime.now(datetime.timezone.utc)
    ready = {"pod": "train-0", "file": "/eval/ready.json", "label": "yaw",
             "added": now.isoformat()}
    waiting = {"pod": "train-1", "file": "/eval/waiting.json", "label": "walk",
               "added": now.isoformat()}
    path.write_text(json.dumps([ready, waiting]))
    monkeypatch.setattr(watch, "PENDING_EVALS", path)
    monkeypatch.setattr(watch, "log", lambda message: None)
    monkeypatch.setattr(
        watch.subprocess, "run",
        lambda args, **kwargs: SimpleNamespace(
            returncode=0 if args[-1] == ready["file"] else 1))
    return path, ready, waiting


def test_ready_evaluation_remains_durable_until_acknowledged(registry):
    path, ready, waiting = registry
    assert watch.check_pending_evals() == ([ready], 1)
    assert json.loads(path.read_text()) == [ready, waiting]
    # A dispatch blocked by concurrency/daily limits must be retried later.
    assert watch.check_pending_evals() == ([ready], 1)
    watch.acknowledge_pending_evals([ready])
    assert json.loads(path.read_text()) == [waiting]
    assert watch.check_pending_evals() == ([], 1)


def test_ack_preserves_new_registration_of_same_named_evaluation(registry):
    path, ready, waiting = registry
    watch.check_pending_evals()
    new = {**ready, "added": "2099-01-01T00:00:00+00:00"}
    path.write_text(json.dumps([ready, waiting, new]))
    watch.acknowledge_pending_evals([ready])
    assert json.loads(path.read_text()) == [waiting, new]


class _StopLoop(BaseException):
    pass


def _one_iteration(monkeypatch, tmp_path, *, active=(), cap=99, fail_spawn=False,
                   sleep_hook=None, reaper=None, capacity=None, after_spawn=None):
    """Exercise the dispatch wiring, with all external I/O replaced."""
    calls = []
    monkeypatch.setattr(watch, "log", lambda message: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr(watch, "spawned_cycles_last_24h", lambda: [])
    monkeypatch.setattr(watch, "daily_cycle_cap", lambda: cap)
    monkeypatch.setattr(watch, "load_processed", lambda: set())
    monkeypatch.setattr(watch, "reap_cycles",
                        reaper or (lambda *_: (list(active), 0, 0)))
    monkeypatch.setattr(watch, "ledger_verdicted", lambda: set())
    monkeypatch.setattr(watch, "runs_by_state", lambda: ({"cw-scratch-running"}, set()))
    monkeypatch.setattr(watch, "maybe_autorestart_on_new_code", lambda: False)
    monkeypatch.setattr(watch, "pending_mcp_kicks", lambda: [])
    monkeypatch.setattr(watch, "META_HOUR_UTC", 99)
    monkeypatch.setattr(watch, "partial_idle_capacity", lambda: capacity)
    for name in ("WORKED", "PAUSE", "KICK", "FINDINGS"):
        monkeypatch.setattr(watch, name, tmp_path / name)
    monkeypatch.setattr(watch.threading, "Thread",
                        lambda **_: SimpleNamespace(start=lambda: None))

    def stop(*args, **kwargs):
        if sleep_hook:
            return sleep_hook()
        raise _StopLoop

    def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        if fail_spawn:
            raise RuntimeError("simulated process startup failure")
        if after_spawn:
            after_spawn()
        return {"label": kwargs.get("label_override", "evalready"),
                "runs": set()}

    monkeypatch.setattr(watch, "sleep_poll", stop)
    monkeypatch.setattr(watch.time, "sleep", stop)
    monkeypatch.setattr(watch, "spawn_cycle", spawn)
    with pytest.raises(_StopLoop):
        watch.main()
    return calls


def test_ready_eval_dispatches_while_scratch_training_continues(
        registry, tmp_path, monkeypatch):
    path, ready, waiting = registry
    calls = _one_iteration(monkeypatch, tmp_path)
    assert len(calls) == 1
    assert "yaw" in calls[0][1]["trigger_text"]
    assert json.loads(path.read_text()) == [waiting]


@pytest.mark.parametrize("blocked", ["daily-cap", "cycle-cap", "spawn-failure"])
def test_ready_eval_not_lost_when_dispatch_cannot_complete(
        registry, tmp_path, monkeypatch, blocked):
    path, ready, waiting = registry
    active = ([_active(f"cw-triage-{i}") for i in range(watch.MAX_CONCURRENT_CYCLES)]
              if blocked == "cycle-cap" else [])
    calls = _one_iteration(
        monkeypatch, tmp_path, active=active,
        cap=0 if blocked == "daily-cap" else 99,
        fail_spawn=blocked == "spawn-failure")
    assert len(calls) == (1 if blocked == "spawn-failure" else 0)
    assert json.loads(path.read_text()) == [ready, waiting]


def test_partial_idle_main_loop_obeys_grace_owner_and_no_work_backoff(
        tmp_path, monkeypatch):
    """One continuing trainer must neither mask spare slots nor reset backoff."""
    start = 100_000.0
    clock = [start]
    spawned_at = []
    poll = watch.POLL_S
    grace = watch.PARTIAL_IDLE_GRACE_S
    owner_leaves_at = start + grace + 3 * poll
    second_due_at = owner_leaves_at + 2 * grace
    monkeypatch.setattr(watch.time, "time", lambda: clock[0])
    monkeypatch.setattr(watch, "check_pending_evals", lambda: ([], 0))

    def reap(active, processed):
        if not active:
            active = [_active("cw-unrelated-finished-run")]
        # The first refill owner stays active for several polls. It then
        # exits without executing work; that should retain doubled backoff.
        if clock[0] >= owner_leaves_at:
            active = [c for c in active if c["label"] != "partial-refill"]
        return active, 0, 0

    def sleep():
        if clock[0] >= second_due_at:
            raise _StopLoop
        clock[0] += poll

    calls = _one_iteration(
        monkeypatch, tmp_path, reaper=reap, sleep_hook=sleep,
        capacity=_capacity(), after_spawn=lambda: spawned_at.append(clock[0]))

    assert spawned_at == [start + grace, second_due_at]
    assert [kwargs["label_override"] for _, kwargs in calls] == [
        "partial-refill", "partial-refill"]
    # Both passes preserve the running scratch arm and receive the current
    # unrelated triage owner, rather than replacing or duplicating either.
    for args, _ in calls:
        assert args[1] == {"cw-scratch-running"}
        assert "cw-unrelated-finished-run" in args[3]


def test_ledger_verdicted_counts_full_verdict_vocabulary(tmp_path, monkeypatch):
    """Meta 09-07: 1225 verdicted runs carried statuses outside
    FINISHED/FAILED (PASS, CANARY FAIL - MECHANISM, ...); a watcher
    restart could re-spawn triage for all of them."""
    ledger = [
        {"run": "cw-a", "status": "CANARY FAIL - MECHANISM",
         "verdict": "refuted"},
        {"run": "cw-b", "status": "PASS", "verdict": "clean gait"},
        {"run": "cw-c", "status": "FINISHED"},           # legacy terminal
        {"run": "cw-d", "status": "RUNNING"},            # live, no verdict
        {"run": "cw-e", "status": "RUNNING", "verdict": "None"},  # stringified None
        # relaunch after a verdicted attempt: latest entry wins
        {"run": "cw-a", "status": "RUNNING"},
    ]
    (tmp_path / "experiments.json").write_text(json.dumps(ledger))
    monkeypatch.setattr(watch, "HERE", tmp_path)
    got = watch.ledger_verdicted()
    assert got == {"cw-b", "cw-c"}


def test_prestage_finished_is_idempotent(monkeypatch):
    """Early handoff-watch fire + later W&B-finish fire must not
    double-run pod evals."""
    started = []
    monkeypatch.setattr(
        watch.threading, "Thread",
        lambda *a, **k: SimpleNamespace(
            start=lambda: started.append(k["target"].__name__)))
    watch._prestage_fired.discard("cw-idem-test")
    watch.prestage_finished("cw-idem-test")
    watch.prestage_finished("cw-idem-test")
    # 1st call runs the full prestage worker; 2nd only refreshes the
    # W&B cache (never re-runs pod evals / checkpoint pull).
    assert started == ["worker", "_refresh"]
