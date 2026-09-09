"""Fast store/lease mechanics; no robot, process, service, or paid-agent calls."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import uuid

import pytest


@pytest.fixture
def lab(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    root = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(root / "experiment_lab"))
    from hexapod_lab.db import Store
    from hexapod_lab.engineering_lane import EngineeringJobStore

    store = Store(tmp_path / "lab.sqlite3")
    engineering = EngineeringJobStore(store)

    def create(parameters=None):
        experiment = store.create({
            "name": "bounded store fixture", "duration_seconds": 1,
            "execution_mode": "external_guarded", "parameters": parameters or {},
        }, "test")
        advance = next(job for job in store.list_codex_jobs()
                       if job["experiment_id"] == experiment["id"])
        return engineering.ensure_queue_handoff(advance, experiment)

    def control(action):
        with store.connect() as con:
            con.execute("INSERT INTO codex_queue_controls(dedupe_key,action,reason,created_by,created_at) "
                        "VALUES(?,?,?,?,?)", (uuid.uuid4().hex, action, "fixture", "test",
                                              datetime.now(timezone.utc).isoformat()))
            return con.execute("SELECT MAX(sequence) FROM codex_queue_controls").fetchone()[0]

    return store, engineering, create, control


def test_hardware_claim_is_paused_without_attempt_or_lease_mutation(lab):
    store, engineering, create, control = lab
    original = create()
    control("pause")
    assert engineering.claim("worker", 60, lane="hardware") is None
    saved = engineering.list_jobs()[0]
    for key in ("status", "attempts", "lease_owner", "lease_token", "lease_expires_at", "claimed_control_sequence"):
        assert saved[key] == original[key]


@pytest.mark.parametrize("lane", ["any", "offline"])
def test_paused_claim_preserves_explicit_offline_lane(lab, lane):
    _, engineering, create, control = lab
    hardware = create()
    offline = create({"simulation_only": True, "robot_motion": False})
    sequence = control("pause")
    claimed = engineering.claim("worker", 60, lane=lane)
    assert claimed["id"] == offline["id"]
    assert claimed["claimed_control_sequence"] == sequence
    assert engineering.execution_revocation_reason(claimed, "worker") is None
    hardware = next(job for job in engineering.list_jobs() if job["id"] == hardware["id"])
    assert hardware["status"] == "queued"
    assert hardware["attempts"] == 0


@pytest.mark.parametrize("parameters", [{}, {"robot_motion": False}, {"simulation_only": True},
                                          {"simulation_only": "true", "robot_motion": False}])
def test_ambiguous_source_stays_hardware_during_pause(lab, parameters):
    _, engineering, create, control = lab
    create(parameters)
    control("pause")
    assert engineering.claim("worker", 60, lane="any") is None


def test_pause_resume_pulse_revokes_persisted_attempt(lab):
    _, engineering, create, control = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    assert claimed["claimed_control_sequence"] == 0
    assert engineering.execution_revocation_reason(claimed, "worker") is None
    control("pause")
    control("resume")
    # Caller-controlled lane/cutoff cannot override the durable attempt.
    forged = {**claimed, "lane": "offline", "claimed_control_sequence": 1000,
              "source_context": {"experiment": {"parameters": {"simulation_only": True, "robot_motion": False}}}}
    assert "paused after" in engineering.execution_revocation_reason(forged, "worker")


def test_new_claim_after_resume_has_current_cutoff(lab):
    _, engineering, create, control = lab
    create()
    control("pause")
    sequence = control("resume")
    claimed = engineering.claim("worker", 60, lane="hardware")
    assert claimed["claimed_control_sequence"] == sequence
    assert engineering.execution_revocation_reason(claimed, "worker") is None
    control("pause")
    assert "queue is paused" in engineering.execution_revocation_reason(claimed, "worker")


@pytest.mark.parametrize("change", ["owner", "token", "expiry", "status", "missing"])
def test_lease_revocation_applies_even_to_offline_attempts(lab, change):
    store, engineering, create, _ = lab
    create({"simulation_only": True, "robot_motion": False})
    claimed = engineering.claim("worker", 60, lane="offline")
    with store.connect() as con:
        if change == "missing":
            con.execute("DELETE FROM codex_engineering_jobs WHERE id=?", (claimed["id"],))
        else:
            field, value = {
                "owner": ("lease_owner", "someone-else"),
                "token": ("lease_token", "other-token"),
                "expiry": ("lease_expires_at", (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()),
                "status": ("status", "blocked"),
            }[change]
            con.execute(f"UPDATE codex_engineering_jobs SET {field}=? WHERE id=?", (value, claimed["id"]))
    assert engineering.execution_revocation_reason(claimed, "worker")


def test_legacy_schema_migration_is_idempotent_and_fails_closed(lab):
    store, engineering, create, _ = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    with store.connect() as con:
        con.execute("ALTER TABLE codex_engineering_jobs DROP COLUMN claimed_control_sequence")
        con.execute("ALTER TABLE codex_engineering_jobs DROP COLUMN claimed_completion_only")
    engineering = type(engineering)(store)
    engineering = type(engineering)(store)
    assert "no recorded queue-control cutoff" in engineering.execution_revocation_reason(claimed, "worker")
    saved = engineering.list_jobs()[0]
    assert saved["status"] == "running"
    assert saved["lease_token"] == claimed["lease_token"]
    assert saved["attempts"] == 1


def test_unstarted_deferral_refunds_only_matching_attempt_and_reclaims_after_resume(lab):
    from hexapod_lab.engineering_lane import EngineeringLaneError
    _, engineering, create, control = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    control("pause")
    deferred = engineering.defer_unstarted(claimed, "worker", "paused before launch")
    assert deferred["status"] == "retry"
    assert deferred["attempts"] == 0
    assert deferred["lease_token"] is None
    assert deferred["claimed_control_sequence"] is None
    assert deferred["result"]["unstarted_defer_receipt"]["child_started"] is False
    assert engineering.claim("worker", 60, lane="hardware") is None
    control("resume")
    new = engineering.claim("worker", 60, lane="hardware")
    assert new["attempts"] == 1
    assert new["lease_token"] != claimed["lease_token"]
    assert engineering.execution_revocation_reason(new, "worker") is None
    with pytest.raises(EngineeringLaneError, match="no longer owned"):
        engineering.defer_unstarted(claimed, "worker", "old token cannot refund new attempt")
    assert engineering.list_jobs()[0]["attempts"] == 1


def test_claim_holds_write_lock_while_reading_pause_control(lab, monkeypatch):
    store, engineering, create, _ = lab
    create()
    original = store.connect
    observed = []
    from contextlib import contextmanager

    @contextmanager
    def checked_connection():
        with original() as con:
            def trace(sql):
                if sql.startswith("SELECT sequence,action FROM codex_queue_controls"):
                    with sqlite3.connect(str(store.path), timeout=0.001) as competing:
                        with pytest.raises(sqlite3.OperationalError, match="locked"):
                            competing.execute("BEGIN IMMEDIATE")
                    observed.append(True)
            con.set_trace_callback(trace)
            yield con
    monkeypatch.setattr(store, "connect", checked_connection)
    assert engineering.claim("worker", 60, lane="hardware") is not None
    assert observed == [True]


def test_park_revoked_keeps_spent_attempt_and_requires_newer_resume(lab):
    store, engineering, create, control = lab
    created = create()
    with store.connect() as con:
        con.execute("UPDATE codex_engineering_jobs SET result_json=? WHERE id=?",
                    (json.dumps({"prior_receipt": {"retained": True}}), created["id"]))
    claimed = engineering.claim("worker", 60, lane="hardware")
    control("pause")
    resumed_before_park = control("resume")
    parked = engineering.park_revoked(claimed, "worker", "pause observed while child ran; child now stopped")
    assert parked["status"] == "blocked"
    assert parked["attempts"] == 1
    assert parked["max_attempts"] == claimed["max_attempts"]
    assert parked["finished_at"]
    assert parked["lease_token"] is None
    saved = parked["result"]
    assert saved["prior_receipt"] == {"retained": True}
    assert saved["blocked_control_sequence"] == resumed_before_park
    assert saved["execution_revocation"]["execution_may_have_started"] is True
    assert "physical_motion_started" not in saved["execution_revocation"]
    assert saved["continuation"]["completion_only"] is True
    assert engineering.claim("worker", 60, lane="hardware") is None
    advance = store.get_codex_job(parked["source_analysis_job_id"])
    target = store.get(parked["experiment_id"])
    unchanged = engineering.ensure_queue_handoff(advance, target)
    assert unchanged["status"] == "blocked"
    control("pause")
    control("resume")
    retry = engineering.ensure_queue_handoff(advance, target)
    assert retry["status"] == "retry"
    reclaimed = engineering.claim("worker", 60, lane="hardware")
    assert reclaimed["attempts"] == 2
    assert reclaimed["continuation"]["completion_only"] is True
    assert reclaimed["claimed_completion_only"] == 1


@pytest.mark.parametrize("column,value", [("status", "cancelled"), ("cancel_requested", 1)])
def test_queue_handoff_cancel_revokes_live_execution_without_trusting_caller(lab, column, value):
    store, engineering, create, _ = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    with store.connect() as con:
        con.execute(f"UPDATE experiments SET {column}=? WHERE id=?", (value, claimed["experiment_id"]))
    forged = {**claimed, "claimed_completion_only": 1, "continuation": {"completion_only": True}}
    assert "cancelled" in engineering.execution_revocation_reason(forged, "worker")


def test_cancel_does_not_revoke_attempt_already_claimed_for_completion_only(lab):
    store, engineering, create, _ = lab
    created = create()
    with store.connect() as con:
        con.execute("UPDATE codex_engineering_jobs SET result_json=? WHERE id=?",
                    (json.dumps({"continuation": {"completion_only": True}}), created["id"]))
    claimed = engineering.claim("worker", 60, lane="hardware")
    with store.connect() as con:
        con.execute("UPDATE experiments SET status='cancelled' WHERE id=?", (claimed["experiment_id"],))
    assert claimed["claimed_completion_only"] == 1
    assert engineering.execution_revocation_reason(claimed, "worker") is None


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled"])
def test_terminal_handoff_at_claim_is_completion_only(lab, status):
    store, engineering, create, _ = lab
    created = create()
    with store.connect() as con:
        con.execute("UPDATE experiments SET status=? WHERE id=?", (status, created["experiment_id"]))
    claimed = engineering.claim("worker", 60, lane="hardware")
    assert claimed["claimed_completion_only"] == 1
    assert claimed["continuation"]["completion_only"] is True
    assert engineering.execution_revocation_reason(claimed, "worker") is None


@pytest.mark.parametrize("status", ["succeeded", "failed"])
def test_normal_terminal_transition_does_not_interrupt_evidence_finalization(lab, status):
    store, engineering, create, _ = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    with store.connect() as con:
        con.execute("UPDATE experiments SET status=? WHERE id=?", (status, claimed["experiment_id"]))
    assert engineering.execution_revocation_reason(claimed, "worker") is None


def test_parking_rejects_stale_owner_without_mutating_job(lab):
    from hexapod_lab.engineering_lane import EngineeringLaneError
    _, engineering, create, _ = lab
    create()
    claimed = engineering.claim("worker", 60, lane="hardware")
    with pytest.raises(EngineeringLaneError, match="no longer owned"):
        engineering.park_revoked(claimed, "other-owner", "cannot park someone else's work")
    saved = engineering.list_jobs()[0]
    assert saved["status"] == "running"
    assert saved["attempts"] == 1
    assert saved["lease_token"] == claimed["lease_token"]
