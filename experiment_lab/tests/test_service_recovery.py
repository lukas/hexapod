from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import json
import os
from types import SimpleNamespace

import pytest

from hexapod_lab import service_recovery as recovery


BASE = 1788671000.0


def observation(now, **changes):
    result = {
        "observed_at": now, "local_api": {"ok": True}, "public_api": {"ok": True},
        "robot": {"reachable": True, "fresh": True, "idle": True},
        "cameras": {"state": "healthy", "all_failed": False},
        "lab_runtime": {"ready": True, "observed_at": now},
    }
    result.update(changes)
    return result


def failed(now):
    return observation(now, local_api={"ok": False})


def tcc(now, **changes):
    result = {"pid": 844, "uid": os.getuid(), "executable": recovery.TCCD,
              "start_time": "Sat Sep 5 22:59:07 2026", "fd_count": 250,
              "emfile": True, "observed_at": now, "emfile_observed_at": now}
    result.update(changes)
    return result


def manager(tmp_path, **kwargs):
    clock = [BASE]
    actions = []
    defaults = dict(enabled=True, now=lambda: clock[0], executor=lambda *args: actions.append(args),
                    action_guard=lambda: nullcontext(True))
    defaults.update(kwargs)
    instance = recovery.RecoveryManager(tmp_path / "recovery.json", **defaults)
    return instance, clock, actions


def sample(instance, clock, count=3, factory=failed, idle=True):
    for _ in range(count):
        clock[0] += 1
        result = instance.step(factory(clock[0]), idle_verified=idle)
    return result


def test_intent_is_durable_before_execution_and_success_requires_three_new_samples(tmp_path):
    seen = []
    path = tmp_path / "recovery.json"

    def execute(action, _context):
        persisted = json.loads(path.read_text())
        assert persisted["status"] == "attempting"
        assert persisted["attempts"] == 1
        seen.append(action)

    instance, clock, _ = manager(tmp_path, executor=execute)
    state = sample(instance, clock)
    assert seen == ["restart_lab"]
    assert state["status"] == "verifying"
    assert state["verified_at"] is None
    event = state["event_id"]
    assert instance.step(failed(clock[0]), True)["event_id"] == event
    state = sample(instance, clock, count=2, factory=observation)
    assert state["status"] == "verifying"
    state = sample(instance, clock, count=1, factory=observation)
    assert state["status"] == "recovered"
    assert recovery.epoch(state["verified_at"]) > recovery.epoch(state["last_attempt_at"])
    assert len(state["history"]) == 1
    assert "_episode" not in json.loads(path.read_text())


def test_cooldown_two_attempt_budget_survives_unknown_and_manager_restart(tmp_path):
    instance, clock, actions = manager(tmp_path)
    sample(instance, clock)
    sample(instance, clock, count=5)
    assert len(actions) == 1
    clock[0] += 301
    sample(instance, clock, count=1)
    assert len(actions) == 2
    clock[0] += 301
    state = instance.step(observation(clock[0], local_api={"ok": None}), True)
    assert state["status"] == "verifying"
    reloaded = recovery.RecoveryManager(instance.state_path, enabled=True, now=lambda: clock[0],
                                       executor=lambda *args: actions.append(args),
                                       action_guard=lambda: nullcontext(True))
    state = sample(reloaded, clock)
    assert len(actions) == 2
    assert state["reason_code"] == "attempts_exhausted"
    assert state["status"] == "needs_attention"


def test_verification_requires_observations_collected_after_action_completed(tmp_path):
    instance, clock, actions = manager(tmp_path)
    def execute(*args):
        actions.append(args)
        clock[0] += 10
    instance.executor = execute
    sample(instance, clock)
    completed = clock[0]
    state = instance.step(observation(completed - 1), True)
    assert state["status"] == "verifying"
    assert json.loads(instance.state_path.read_text())["_episode"]["healthy_count"] == 0
    assert sample(instance, clock, count=2, factory=observation)["status"] == "verifying"
    assert sample(instance, clock, count=1, factory=observation)["status"] == "recovered"


def test_preflight_cannot_start_repair_using_observations_that_expired(tmp_path):
    instance, clock, actions = manager(tmp_path)
    class Executor:
        def preflight(self, *_):
            clock[0] += 31
        def __call__(self, *args):
            actions.append(args)
    instance.executor = Executor()
    state = sample(instance, clock)
    assert state["reason_code"] == "observations_stale"
    assert not actions and state["attempts"] == 0


@pytest.mark.parametrize("options,idle,reason", [
    ({"enabled": False}, True, "disabled"),
    ({}, False, "hardware_active_or_unobserved"),
    ({"action_guard": None}, True, "hardware_active_or_unobserved"),
])
def test_disabled_busy_and_missing_atomic_guard_are_inert(tmp_path, options, idle, reason):
    instance, clock, actions = manager(tmp_path, **options)
    state = sample(instance, clock, idle=idle)
    assert not actions
    assert state["reason_code"] == reason
    assert state["attempts"] == 0


@pytest.mark.parametrize("state", ["paused", "in_use", "unknown", "disconnected", "unavailable"])
def test_camera_ownership_and_missing_devices_never_restart_lab(tmp_path, state):
    instance, clock, actions = manager(tmp_path)
    sample(instance, clock, factory=lambda now: observation(now, cameras={"state": state, "all_failed": True}))
    assert not actions


def test_actual_permission_denial_and_unknown_robot_require_manual_attention(tmp_path):
    instance, clock, actions = manager(tmp_path)
    state = sample(instance, clock, factory=lambda now: observation(now, cameras={"state": "permission_denied", "all_failed": True}))
    assert state["issue_code"] == "camera_permission_denied"
    assert state["status"] == "needs_attention"
    state = sample(instance, clock, factory=lambda now: observation(now, robot={"reachable": False, "fresh": False}))
    assert state["issue_code"] == "robot_controller_unavailable"
    assert state["status"] == "needs_attention"
    assert not actions


def test_tcc_requires_matching_fresh_independent_evidence(tmp_path):
    instance, clock, actions = manager(tmp_path)
    for invalid in ({"emfile": False}, {"fd_count": 239}, {"emfile_observed_at": BASE - 100},
                    {"uid": -1}, {"pid": 1}, {"executable": "/wrong/tccd"}, {"start_time": ""}):
        sample(instance, clock, factory=lambda now: observation(now, tcc=tcc(now, **invalid)))
    assert not actions
    state = sample(instance, clock, factory=lambda now: observation(now, tcc=tcc(now)))
    assert state["action"] == "restart_user_tccd"
    assert len(actions) == 1
    assert instance.requires_privacy_probe()
    assert recovery.RecoveryManager(instance.state_path).requires_privacy_probe()
    sample(instance, clock, factory=lambda now: observation(now, tcc=tcc(now, fd_count=8)))
    assert json.loads(instance.state_path.read_text())["status"] != "recovered"
    state = sample(instance, clock, factory=lambda now: observation(now, tcc=tcc(now, pid=900, fd_count=8)))
    assert state["status"] == "recovered"
    assert not instance.requires_privacy_probe()


def test_runtime_preflight_failure_never_consumes_action_budget(tmp_path):
    class Executor:
        def preflight(self, *_args):
            raise ImportError("private details")

        def __call__(self, *_args):
            pytest.fail("must not restart after failed dependency import")

    instance, clock, _ = manager(tmp_path, executor=Executor())
    state = sample(instance, clock)
    assert state["reason_code"] == "runtime_preflight_failed"
    assert state["attempts"] == 0
    assert state["last_error"] == "ImportError"


def test_action_failure_retains_budget_and_does_not_publish_exception_text(tmp_path):
    def execute(*_args):
        raise RuntimeError("secret token must not appear")

    instance, clock, _ = manager(tmp_path, executor=execute)
    state = sample(instance, clock)
    assert state["reason_code"] == "action_failed"
    assert state["attempts"] == 1
    assert "secret token" not in instance.state_path.read_text()


def test_atomic_guard_and_singleton_lock_span_executor(tmp_path):
    reserved = []

    @contextmanager
    def guard():
        reserved.append(True)
        try:
            yield True
        finally:
            reserved.clear()

    instance, clock, _ = manager(tmp_path, action_guard=guard)
    other = recovery.RecoveryManager(instance.state_path, enabled=True, now=lambda: clock[0],
                                     executor=lambda *_: pytest.fail("singleton lock bypassed"),
                                     action_guard=guard)

    def execute(*_args):
        assert reserved
        assert other.step(failed(clock[0]), True)["status"] == "attempting"

    instance.executor = execute
    sample(instance, clock)
    assert not reserved


def test_corrupt_state_and_stale_observations_fail_closed(tmp_path):
    instance, clock, actions = manager(tmp_path)
    result = instance.step(failed(BASE - 31), True)
    assert result["reason_code"] == "observations_stale"
    instance.state_path.write_text("not json")
    with pytest.raises(ValueError):
        instance.step(failed(clock[0]), True)
    assert not actions


def test_tunnel_restart_requires_local_health(tmp_path):
    instance, clock, actions = manager(tmp_path)
    state = sample(instance, clock, factory=lambda now: observation(now, public_api={"ok": False}))
    assert state["action"] == "restart_camera_tunnel"
    assert actions[0][0] == "restart_camera_tunnel"


def test_executor_rejects_changed_tcc_identity_before_signals(monkeypatch):
    executor = recovery.MacRecoveryExecutor(idle_guard=lambda: True)
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    monkeypatch.setattr(recovery.time, "time", lambda: BASE)
    monkeypatch.setattr(executor, "_identity", lambda _pid: None)
    monkeypatch.setattr(recovery.os, "kill", lambda *_args: pytest.fail("identity changed"))
    with pytest.raises(RuntimeError, match="identity_changed"):
        executor("restart_user_tccd", {"tcc": tcc(BASE)})


def test_executor_confirmed_tcc_chain_checks_guards_and_restarts_lab(monkeypatch):
    calls = []
    executor = recovery.MacRecoveryExecutor(idle_guard=lambda: calls.append("guard") or True)
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    monkeypatch.setattr(recovery.time, "time", lambda: BASE)
    evidence = tcc(BASE)
    identity = {key: evidence[key] for key in ("pid", "uid", "start_time", "executable")}
    monkeypatch.setattr(executor, "_identity", lambda _pid: identity if "TERM" not in calls else None)
    monkeypatch.setattr(executor, "_replacement", lambda _pid: calls.append("replacement_verified") or True)
    monkeypatch.setattr(executor, "_fd_count", lambda _pid: 250)
    monkeypatch.setattr(executor, "_run", lambda argv, **_kwargs: calls.append(argv))
    monkeypatch.setattr(recovery.os, "kill", lambda pid, sig: calls.append("TERM"))
    executor("restart_user_tccd", {"tcc": evidence})
    assert calls == ["guard", "TERM", "replacement_verified", "guard",
                     ["/bin/launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.lbiewald.hexapod-lab"]]


def test_executor_refuses_evidence_expired_during_idle_guard(monkeypatch):
    clock = [BASE]

    def guard():
        clock[0] += 31
        return True

    executor = recovery.MacRecoveryExecutor(idle_guard=guard)
    evidence = tcc(BASE)
    identity = {key: evidence[key] for key in ("pid", "uid", "start_time", "executable")}
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    monkeypatch.setattr(recovery.time, "time", lambda: clock[0])
    monkeypatch.setattr(executor, "_identity", lambda _pid: identity)
    monkeypatch.setattr(recovery.os, "kill", lambda *_: pytest.fail("expired evidence must not signal"))
    with pytest.raises(RuntimeError, match="evidence_expired"):
        executor("restart_user_tccd", {"tcc": evidence})


def test_executor_refuses_pressure_that_already_recovered(monkeypatch):
    executor = recovery.MacRecoveryExecutor(idle_guard=lambda: True)
    evidence = tcc(BASE)
    identity = {key: evidence[key] for key in ("pid", "uid", "start_time", "executable")}
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    monkeypatch.setattr(recovery.time, "time", lambda: BASE)
    monkeypatch.setattr(executor, "_identity", lambda _pid: identity)
    monkeypatch.setattr(executor, "_fd_count", lambda _pid: 8)
    monkeypatch.setattr(recovery.os, "kill", lambda *_: pytest.fail("healthy tccd must not be signaled"))
    with pytest.raises(RuntimeError, match="no_longer_confirmed"):
        executor("restart_user_tccd", {"tcc": evidence})
