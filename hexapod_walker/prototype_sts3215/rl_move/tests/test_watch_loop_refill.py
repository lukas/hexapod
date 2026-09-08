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
                   sleep_hook=None, reaper=None, capacity=None, after_spawn=None,
                   run_states=None, processed=(), verdict_reader=None):
    """Exercise the dispatch wiring, with all external I/O replaced."""
    calls = []
    monkeypatch.setattr(watch, "log", lambda message: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr(watch, "spawned_cycles_last_24h", lambda: [])
    monkeypatch.setattr(watch, "daily_cycle_cap", lambda: cap)
    monkeypatch.setattr(watch, "load_processed", lambda: set(processed))
    monkeypatch.setattr(watch, "reap_cycles",
                        reaper or (lambda *_: (list(active), 0, 0)))
    monkeypatch.setattr(watch, "ledger_verdicted", verdict_reader or (lambda: set()))
    monkeypatch.setattr(watch, "runs_by_state",
                        lambda: run_states if run_states is not None
                        else ({"cw-scratch-running"}, set()))
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
    monkeypatch.setattr(watch, "log", lambda message: None)
    monkeypatch.setattr(watch, "_prestage_fired", set())
    watch.prestage_finished("cw-idem-test")
    watch.prestage_finished("cw-idem-test")
    # 1st call runs the full prestage worker; 2nd only refreshes the
    # W&B cache (never re-runs pod evals / checkpoint pull).
    assert started == ["worker", "_refresh"]


@pytest.fixture
def fast_finish_ledger(tmp_path, monkeypatch):
    """The real short deferred-run shape written by cmd_checkup."""
    entry = {
        "run": "cw-fast-deferred", "pod": "train-1", "status": "FINISHED",
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "extra_args": ["--defer-final-artifacts"],
        "checkups": [{"verdict": "FINISHED_BEFORE_CHECKUP"}],
    }
    path = tmp_path / "experiments.json"
    path.write_text(json.dumps([entry]))
    monkeypatch.setattr(watch, "HERE", tmp_path)
    monkeypatch.setattr(watch, "LEDGER", path)
    monkeypatch.setattr(watch, "PAUSE", tmp_path / "PAUSE")
    monkeypatch.setattr(watch, "log", lambda message: None)
    monkeypatch.setattr(watch, "load_processed", lambda: set())
    monkeypatch.setattr(watch, "_prestage_fired", set())
    return entry, path


def test_checkup_completion_is_not_a_scientific_verdict(fast_finish_ledger):
    entry, path = fast_finish_ledger
    rows = []
    for i, verdict in enumerate((None, "", "None", "  ", "clean gait", "CANARY FAIL")):
        rows.append({**entry, "run": f"cw-{i}", "verdict": verdict})
    rows += [
        {"run": "cw-legacy", "status": "FINISHED"},
        {"run": "cw-infra-failed", "status": "FAILED"},
        {**entry, "run": "cw-old-checkup", "checkups": [
            {"verdict": "FINISHED_BEFORE_CHECKUP"}, {"verdict": "HEALTHY"}]},
        # Latest-row selection must retain its original relaunch behavior.
        {"run": "cw-relaunched", "status": "FAILED", "verdict": "old failure"},
        {**entry, "run": "cw-relaunched"},
    ]
    path.write_text(json.dumps(rows))
    assert watch.ledger_verdicted() == {
        "cw-4", "cw-5", "cw-legacy", "cw-infra-failed", "cw-old-checkup"}


def _handoff_polls(monkeypatch, path, polls, dispatch):
    """Run actual worker iterations, replacing only time and remote I/O."""
    index, probes = [0], []
    path.write_text(json.dumps([polls[0][0]]))
    monkeypatch.setattr(watch, "prestage_finished", dispatch)

    def remote_read(args, **kwargs):
        probes.append(args)
        response = polls[index[0]][1]
        if isinstance(response, BaseException):
            raise response
        return SimpleNamespace(
            returncode=1 if response is None else 0,
            stdout=json.dumps(response) if not isinstance(response, str) else response)

    def next_poll(seconds):
        assert seconds == 120
        index[0] += 1
        if index[0] == len(polls):
            raise _StopLoop
        path.write_text(json.dumps([polls[index[0]][0]]))

    monkeypatch.setattr(watch.subprocess, "run", remote_read)
    monkeypatch.setattr(watch.time, "sleep", next_poll)
    with pytest.raises(_StopLoop):
        watch.handoff_watch_worker()
    return probes


@pytest.mark.parametrize("finalizer_phase", ["artifacts_pending", "evaluated", "failed"])
def test_running_to_finished_between_handoff_polls_fires_once(
        fast_finish_ledger, monkeypatch, finalizer_phase):
    entry, path = fast_finish_ledger
    threads = []
    monkeypatch.setattr(
        watch.threading, "Thread",
        lambda *a, **k: SimpleNamespace(
            start=lambda: threads.append(k["target"].__name__)))
    prestage = watch.prestage_finished
    polls = [
        ({**entry, "status": "RUNNING", "checkups": []},
         {"phase": "training", "jobs": {"periodic_eval": {"status": "done"}}}),
        # The checkup completes before the next 120s handoff poll.
        (entry, {"phase": finalizer_phase, "jobs": {"final_video": {"status": "pending"}}}),
        (entry, {"phase": finalizer_phase}),
    ]
    probes = _handoff_polls(monkeypatch, path, polls, prestage)
    assert len(probes) == 2  # periodic completion is not training completion
    assert probes[-1][-1].endswith(
        "/artifact_handoff/cw-fast-deferred/state.json")
    assert threads == ["worker"]
    # The later W&B-finished main-loop event must reuse the existing prestage.
    prestage(entry["run"])
    assert threads == ["worker", "_refresh"]
    assert entry["run"] not in watch.ledger_verdicted()


@pytest.mark.parametrize("blocked", ["processed", "verdict", "missing-pod", "old", "legacy"])
def test_handoff_preserves_handled_and_verdict_exclusions(
        fast_finish_ledger, monkeypatch, blocked):
    entry, path = fast_finish_ledger
    if blocked == "processed":
        monkeypatch.setattr(watch, "load_processed", lambda: {entry["run"]})
    elif blocked == "verdict":
        entry["verdict"] = "CANARY PASS"
        entry["status"] = "RUNNING"  # explicit verdict wins over either status
    elif blocked == "missing-pod":
        entry.pop("pod")
    elif blocked == "old":
        entry["created"] = "2020-01-01T00:00:00+00:00"
    elif blocked == "legacy":
        entry["checkups"] = []

    calls = []
    probes = _handoff_polls(
        monkeypatch, path, [(entry, {"phase": "evaluated"})], calls.append)
    assert calls == []
    assert probes == []


@pytest.mark.parametrize("unready", [
    None, "{unreadable JSON",
    watch.subprocess.TimeoutExpired("handoff-state", 60),
    {"phase": "training", "jobs": {"periodic_video": {"status": "done"}}},
])
def test_handoff_retries_missing_or_pending_training_state(
        fast_finish_ledger, monkeypatch, unready):
    entry, path = fast_finish_ledger
    calls = []
    probes = _handoff_polls(monkeypatch, path, [
        (entry, unready),
        (entry, {"phase": "artifacts_pending"}),
        (entry, {"phase": "evaluated"}),
    ], calls.append)
    assert calls == [entry["run"]]
    assert len(probes) == 2


@pytest.mark.parametrize(
    "wandb_finished,synced,blocked,expected_prestage,expected_cycles",
    [(False, False, None, 0, 0),  # CPU finalizer still owns W&B
     (True, False, None, 1, 0),   # finalizer done, independent gate not ready
     (True, True, None, 1, 1),
     (True, True, "processed", 0, 0),
     (True, True, "in-flight", 0, 0),
     (True, True, "verdict", 0, 0)],
)
def test_fast_finish_triage_waits_for_core_gate_and_preserves_owners(
        fast_finish_ledger, tmp_path, monkeypatch,
        wandb_finished, synced, blocked, expected_prestage, expected_cycles):
    entry, path = fast_finish_ledger
    run = entry["run"]
    if blocked == "verdict":
        entry["verdict"] = "PASS - scientifically reviewed"
        path.write_text(json.dumps([entry]))
    sentinel = tmp_path / "core.synced"
    if synced:
        sentinel.touch()
    prestaged = []
    monkeypatch.setattr(watch, "prestage_sentinel", lambda _: sentinel)
    monkeypatch.setattr(watch, "prestage_finished", prestaged.append)
    monkeypatch.setattr(watch, "mark_triage", lambda *a, **k: None)
    monkeypatch.setattr(watch, "try_auto_continue", lambda _: None)
    monkeypatch.setattr(watch, "_prestage_spawn_wait", lambda _: 3600)
    monkeypatch.setattr(watch, "check_pending_evals", lambda: ([], 0))
    active = [{"label": run, "runs": {run}}] if blocked == "in-flight" else []
    calls = _one_iteration(
        monkeypatch, tmp_path, active=active,
        run_states=(set(), {run}) if wandb_finished else ({run}, set()),
        processed={run} if blocked == "processed" else set(),
        verdict_reader=watch.ledger_verdicted)
    assert len(prestaged) == expected_prestage
    assert len(calls) == expected_cycles
    if calls:
        assert calls[0][0][0] == {run}
