import copy
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from hexapod_lab.db import Store


def test_store_keeps_sqlite_database_private(tmp_path):
    path = tmp_path / "lab.sqlite3"
    Store(path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_physical_claim_waits_for_analysis_and_codex_safety_pause(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    completed = store.create(
        {"name": "needs review", "duration_seconds": 1}, "test"
    )
    store.finish(completed["id"], "succeeded")
    store.seal_evidence(completed["id"], "a" * 64)
    next_run = store.create(
        {"name": "physical next", "duration_seconds": 1}, "test"
    )

    assert store.claim_next(require_codex_clear=True) is None
    assert store.get(next_run["id"])["status"] == "queued"

    analysis = store.claim_codex_job(
        "analysis", "reviewer", lease_seconds=60
    )
    assert analysis is not None
    store.finish_codex_job(
        analysis["id"],
        "reviewer",
        "succeeded",
        lease_token=analysis["lease_token"],
    )
    claimed = store.claim_next(require_codex_clear=True)
    assert claimed and claimed["id"] == next_run["id"]

    store.finish(next_run["id"], "succeeded")
    store.seal_evidence(next_run["id"], "b" * 64)
    next_analysis = store.claim_codex_job(
        "analysis", "reviewer", lease_seconds=60
    )
    assert next_analysis is not None
    store.finish_codex_job(
        next_analysis["id"],
        "reviewer",
        "succeeded",
        lease_token=next_analysis["lease_token"],
    )
    paused_run = store.create(
        {"name": "paused physical", "duration_seconds": 1}, "test"
    )
    store.pause_codex_queue(analysis["id"], "inspection required")
    assert store.claim_next(require_codex_clear=True) is None
    assert store.get(paused_run["id"])["status"] == "queued"


def terminal_with_evidence(store: Store, *, name: str = "complete"):
    experiment = store.create(
        {"name": name, "duration_seconds": 1, "parameters": {}},
        "test",
    )
    store.finish(experiment["id"], "succeeded")
    store.seal_evidence(experiment["id"], "a" * 64)
    jobs = store.codex_jobs_for_experiment(experiment["id"])
    analysis = next(job for job in jobs if job["kind"] == "analysis")
    advance = next(job for job in jobs if job["kind"] == "advance")
    return experiment, analysis, advance


def test_running_analysis_blocks_only_its_dependent_advance(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _, analysis, dependent = terminal_with_evidence(store)
    claimed_analysis = store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    )
    assert claimed_analysis["id"] == analysis["id"]

    independent = store.enqueue_advance(
        "independent-queue-reconcile", "queue_reconcile"
    )
    claimed_independent = store.claim_codex_job(
        "advance", "advance-worker", lease_seconds=60
    )
    assert claimed_independent["id"] == independent["id"]
    assert store.get_codex_job(dependent["id"])["status"] == "queued"
    store.finish_codex_job(
        independent["id"],
        "advance-worker",
        "succeeded",
        lease_token=claimed_independent["lease_token"],
    )
    assert store.claim_codex_job(
        "advance", "other-advance-worker", lease_seconds=60
    ) is None

    store.finish_codex_job(
        analysis["id"],
        "analysis-worker",
        "succeeded",
        lease_token=claimed_analysis["lease_token"],
    )
    claimed_dependent = store.claim_codex_job(
        "advance", "other-advance-worker", lease_seconds=60
    )
    assert claimed_dependent["id"] == dependent["id"]


def test_store_restart_backfills_legacy_terminal_experiments_without_codex_jobs(
    tmp_path,
):
    path = tmp_path / "lab.sqlite3"
    store = Store(path)
    sealed, _, _ = terminal_with_evidence(store, name="legacy sealed")
    unsealed = store.create(
        {"name": "legacy unsealed", "duration_seconds": 1, "parameters": {}},
        "test",
    )
    store.finish(unsealed["id"], "failed", "legacy failure")

    # Model a database written before the completion outbox existed while
    # retaining the terminal experiment and (for one row) its evidence seal.
    with store.connect() as con:
        con.execute(
            "DELETE FROM codex_jobs WHERE experiment_id IN (?,?) AND kind='advance'",
            (sealed["id"], unsealed["id"]),
        )
        con.execute(
            "DELETE FROM codex_jobs WHERE experiment_id IN (?,?) AND kind='analysis'",
            (sealed["id"], unsealed["id"]),
        )
    assert store.codex_jobs_for_experiment(sealed["id"]) == []
    assert store.codex_jobs_for_experiment(unsealed["id"]) == []

    restarted = Store(path)
    sealed_jobs = restarted.codex_jobs_for_experiment(sealed["id"])
    assert {job["kind"] for job in sealed_jobs} == {"analysis", "advance"}
    assert {job["status"] for job in sealed_jobs} == {"queued"}
    assert {job["evidence_manifest_sha256"] for job in sealed_jobs} == {
        store.get(sealed["id"])["evidence_manifest_sha256"]
    }
    unsealed_jobs = restarted.codex_jobs_for_experiment(unsealed["id"])
    assert {job["kind"] for job in unsealed_jobs} == {"analysis", "advance"}
    assert {job["status"] for job in unsealed_jobs} == {"awaiting_evidence"}

    # Deterministic dedupe keys make repeated startups a no-op.
    Store(path)
    assert len(restarted.codex_jobs_for_experiment(sealed["id"])) == 2
    assert len(restarted.codex_jobs_for_experiment(unsealed["id"])) == 2


def proposal(name: str = "bounded repeat"):
    return {
        "recommendation_key": "bounded-repeat",
        "rationale": "Separate repeatability from the observed effect.",
        "spec": {
            "name": name,
            "description": "Repeat the same bounded measurement.",
            "duration_seconds": 1.0,
            "parameters": {
                "robot_motion": False,
                "stop_conditions": ["tip", "hot motor"],
            },
            "execution_mode": "external_guarded",
        },
    }


def rejected_followup_fixture(
    tmp_path, *, safety_disposition="clear", execution_mode="external_guarded"
):
    store = Store(tmp_path / "lab.sqlite3")
    source, analysis, _ = terminal_with_evidence(store)
    rejected = proposal("readiness-only repeat")
    rejected["recommendation_key"] = "readiness-only-repeat"
    rejected["rejection_reason"] = "legacy policy treated readiness as rejection"
    rejected["spec"]["execution_mode"] = execution_mode
    result = {
        "safety_disposition": safety_disposition,
        "recommended_experiments": [rejected],
        "followup_receipts": {
            "accepted": [],
            "rejected": [{
                "proposal_index": 0,
                "disposition": "rejected",
                "disposition_reason": rejected["rejection_reason"],
                "child_experiment_id": None,
            }],
            "root_experiment_id": source["id"],
        },
    }
    claimed = store.claim_codex_job("analysis", "reviewer", lease_seconds=60)
    assert claimed["id"] == analysis["id"]
    store.finish_codex_job(
        analysis["id"],
        "reviewer",
        "succeeded",
        result=result,
        lease_token=claimed["lease_token"],
    )
    receipts = store.apply_analysis_followups(
        analysis["id"], source["id"], [rejected], max_depth=4, max_per_root=20
    )
    assert receipts["rejected"][0]["child_experiment_id"] is None
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM codex_followup_proposals "
            "WHERE analysis_job_id=? AND proposal_index=0",
            (analysis["id"],),
        ).fetchone()
    return store, source, analysis, rejected, dict(row)


def reconsideration_arguments(analysis, rejected, row, **overrides):
    values = {
        "analysis_job_id": analysis["id"],
        "proposal_index": 0,
        "expected_recommendation_key": rejected["recommendation_key"],
        "expected_proposal_sha256": row["proposal_sha256"],
        "expected_spec_sha256": row["spec_sha256"],
        "expected_original_reason": rejected["rejection_reason"],
        "adaptive_admission": {
            "policy": "known-bounded-runner-v1",
            "analysis_generated": True,
            "ready": False,
            "reason": "runtime compatibility and a trusted executor remain unresolved",
        },
        "max_depth": 4,
        "max_per_root": 20,
        "reconsidered_by": "policy-migration-test",
    }
    values.update(overrides)
    return values


def test_reconsider_rejected_followup_is_audited_atomic_and_idempotent(tmp_path):
    store, source, analysis, rejected, row = rejected_followup_fixture(tmp_path)
    with store.connect() as con:
        original_result_json = con.execute(
            "SELECT result_json FROM codex_jobs WHERE id=?", (analysis["id"],)
        ).fetchone()["result_json"]

    first = store.reconsider_rejected_followup(
        **reconsideration_arguments(analysis, rejected, row)
    )
    assert first["idempotent"] is False
    child = store.get(first["child_experiment_id"])
    assert child["status"] == "waiting_for_operator"
    assert child["execution_mode"] == "external_guarded"
    assert child["parameters"]["_adaptive_admission"]["ready"] is False
    assert child["parameters"]["_automation"]["root_experiment_id"] == source["id"]
    assert child["parameters"]["_automation"]["lineage_depth"] == 1

    with store.connect() as con:
        promoted = con.execute(
            "SELECT disposition,disposition_reason,child_experiment_id "
            "FROM codex_followup_proposals WHERE id=?",
            (row["id"],),
        ).fetchone()
        audit = con.execute(
            "SELECT * FROM codex_followup_reconsiderations WHERE proposal_id=?",
            (row["id"],),
        ).fetchone()
        unchanged_result_json = con.execute(
            "SELECT result_json FROM codex_jobs WHERE id=?", (analysis["id"],)
        ).fetchone()["result_json"]
    assert tuple(promoted) == ("accepted", "", child["id"])
    assert audit["original_disposition_reason"] == rejected["rejection_reason"]
    assert audit["child_experiment_id"] == child["id"]
    assert unchanged_result_json == original_result_json

    replay = store.reconsider_rejected_followup(
        **reconsideration_arguments(analysis, rejected, row)
    )
    assert replay["idempotent"] is True
    assert replay["child_experiment_id"] == child["id"]
    assert len([item for item in store.list() if item["id"] != source["id"]]) == 1

    changed_admission = reconsideration_arguments(analysis, rejected, row)
    changed_admission["adaptive_admission"] = {
        **changed_admission["adaptive_admission"],
        "reason": "a different readiness decision",
    }
    with pytest.raises(ValueError, match="does not match its audit"):
        store.reconsider_rejected_followup(**changed_admission)

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connect() as con:
            con.execute(
                "UPDATE codex_followup_reconsiderations SET reconsidered_by='x' "
                "WHERE proposal_id=?",
                (row["id"],),
            )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connect() as con:
            con.execute(
                "DELETE FROM codex_followup_reconsiderations WHERE proposal_id=?",
                (row["id"],),
            )


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"expected_proposal_sha256": "0" * 64}, "Proposal SHA-256"),
        ({"expected_spec_sha256": "0" * 64}, "Specification SHA-256"),
        ({"expected_original_reason": "different reason"}, "original rejection"),
        ({"max_depth": 0}, "lineage depth"),
        ({"max_per_root": 0}, "already has"),
    ],
)
def test_reconsider_rejected_followup_fails_closed_without_side_effects(
    tmp_path, override, message
):
    store, source, analysis, rejected, row = rejected_followup_fixture(tmp_path)
    with pytest.raises(ValueError, match=message):
        store.reconsider_rejected_followup(
            **reconsideration_arguments(analysis, rejected, row, **override)
        )
    assert [item for item in store.list() if item["id"] != source["id"]] == []
    with store.connect() as con:
        receipt = con.execute(
            "SELECT disposition,child_experiment_id FROM codex_followup_proposals "
            "WHERE id=?",
            (row["id"],),
        ).fetchone()
        audit_count = con.execute(
            "SELECT COUNT(*) FROM codex_followup_reconsiderations"
        ).fetchone()[0]
    assert tuple(receipt) == ("rejected", None)
    assert audit_count == 0


def test_reconsider_rejected_followup_requires_clear_analysis(tmp_path):
    store, source, analysis, rejected, row = rejected_followup_fixture(
        tmp_path, safety_disposition="needs_inspection"
    )
    with pytest.raises(ValueError, match="did not clear"):
        store.reconsider_rejected_followup(
            **reconsideration_arguments(analysis, rejected, row)
        )
    assert [item for item in store.list() if item["id"] != source["id"]] == []


def test_reconsider_rejected_followup_requires_external_guarded_spec(tmp_path):
    store, source, analysis, rejected, row = rejected_followup_fixture(
        tmp_path, execution_mode="builtin"
    )
    with pytest.raises(ValueError, match="external-guarded"):
        store.reconsider_rejected_followup(
            **reconsideration_arguments(analysis, rejected, row)
        )
    assert [item for item in store.list() if item["id"] != source["id"]] == []


def test_reconsider_rejected_followup_enforces_root_spec_dedupe(tmp_path):
    store, source, analysis, rejected, row = rejected_followup_fixture(tmp_path)
    accepted_duplicate = copy.deepcopy(rejected)
    accepted_duplicate.pop("rejection_reason")
    accepted_duplicate["recommendation_key"] = "already-accepted-same-spec"
    duplicate_receipts = store.apply_analysis_followups(
        analysis["id"],
        source["id"],
        [rejected, accepted_duplicate],
        max_depth=4,
        max_per_root=20,
    )
    existing_child = duplicate_receipts["accepted"][0]["child_experiment_id"]

    with pytest.raises(ValueError, match="Exact experiment specification"):
        store.reconsider_rejected_followup(
            **reconsideration_arguments(analysis, rejected, row)
        )
    children = [item for item in store.list() if item["id"] != source["id"]]
    assert [item["id"] for item in children] == [existing_child]


def test_claim_token_fences_same_owner_after_expiry_and_reclaim(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _, analysis, _ = terminal_with_evidence(store)

    first = store.claim_codex_job("analysis", "shared-owner", lease_seconds=60)
    assert first["id"] == analysis["id"]
    assert first["lease_token"]
    assert "lease_token" not in store.get_codex_job(first["id"])

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET lease_expires_at=? WHERE id=?",
            (expired, first["id"]),
        )
    assert store.recover_expired_codex_jobs() == 1
    second = store.claim_codex_job("analysis", "shared-owner", lease_seconds=60)
    assert second["id"] == first["id"]
    assert second["lease_token"] != first["lease_token"]

    with pytest.raises(ValueError, match="lease"):
        store.finish_codex_job(
            first["id"],
            "shared-owner",
            "succeeded",
            lease_token=first["lease_token"],
        )
    assert store.get_codex_job(first["id"])["status"] == "running"

    finished = store.finish_codex_job(
        second["id"],
        "shared-owner",
        "succeeded",
        lease_token=second["lease_token"],
    )
    assert finished["status"] == "succeeded"
    with store.connect() as con:
        stored = con.execute(
            "SELECT lease_owner,lease_token,lease_expires_at "
            "FROM codex_jobs WHERE id=?",
            (second["id"],),
        ).fetchone()
    assert tuple(stored) == (None, None, None)


def test_claim_token_legacy_fallback_is_thread_local_to_store_instance(tmp_path):
    path = tmp_path / "lab.sqlite3"
    store = Store(path)
    _, analysis, _ = terminal_with_evidence(store)
    claimed = store.claim_codex_job("analysis", "worker", lease_seconds=60)

    restarted_store = Store(path)
    with pytest.raises(ValueError, match="token"):
        restarted_store.retry_codex_job(
            analysis["id"], "worker", "retry", delay_seconds=0
        )

    retried = store.retry_codex_job(
        analysis["id"], "worker", "retry", delay_seconds=0
    )
    assert retried["status"] == "retry"
    with store.connect() as con:
        assert con.execute(
            "SELECT lease_token FROM codex_jobs WHERE id=?", (claimed["id"],)
        ).fetchone()["lease_token"] is None


@pytest.mark.parametrize(
    "change",
    ["recommendation_key", "rationale", "spec", "rejection_reason"],
)
def test_followup_receipt_conflicts_when_same_index_proposal_changes(
    tmp_path, change
):
    store = Store(tmp_path / "lab.sqlite3")
    source, analysis, _ = terminal_with_evidence(store)
    original = proposal()
    first = store.apply_analysis_followups(
        analysis["id"], source["id"], [original], max_depth=4, max_per_root=20
    )
    child_id = first["accepted"][0]["child_experiment_id"]

    replay = store.apply_analysis_followups(
        analysis["id"], source["id"], [copy.deepcopy(original)],
        max_depth=4, max_per_root=20,
    )
    assert replay["accepted"][0]["child_experiment_id"] == child_id

    changed = copy.deepcopy(original)
    if change == "recommendation_key":
        changed["recommendation_key"] = "different-key"
    elif change == "rationale":
        changed["rationale"] = "A materially different rationale."
    elif change == "spec":
        changed["spec"]["duration_seconds"] = 2.0
    else:
        changed["rejection_reason"] = "New safety rejection"
    with pytest.raises(ValueError, match="existing receipt index"):
        store.apply_analysis_followups(
            analysis["id"], source["id"], [changed],
            max_depth=4, max_per_root=20,
        )

    assert len(
        [item for item in store.list() if item["id"] != source["id"]]
    ) == 1
    with store.connect() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM codex_followup_proposals"
        ).fetchone()[0]
    assert count == 1


def test_paused_queue_claims_only_pausing_analysis_completion_advance(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _, analysis, expected_advance = terminal_with_evidence(store)
    unrelated = store.enqueue_advance("bootstrap:unrelated", "bootstrap")

    claimed_analysis = store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    )
    store.finish_codex_job(
        claimed_analysis["id"],
        "analysis-worker",
        "succeeded",
        result={"safety_disposition": "needs_inspection"},
    )
    store.pause_codex_queue(analysis["id"], "Analysis requires inspection")

    claimed_advance = store.claim_codex_job(
        "advance", "advance-worker", lease_seconds=60
    )
    assert claimed_advance["id"] == expected_advance["id"]
    assert claimed_advance["depends_on_job_id"] == analysis["id"]
    assert store.claim_codex_job(
        "advance", "second-worker", lease_seconds=60
    ) is None
    assert store.get_codex_job(unrelated["id"])["status"] == "queued"

    store.finish_codex_job(
        claimed_advance["id"], "advance-worker", "blocked"
    )
    store.pause_codex_queue(
        claimed_advance["id"], "Read-only advance confirmed the block"
    )
    assert store.claim_codex_job(
        "advance", "second-worker", lease_seconds=60
    ) is None


def test_resume_acknowledges_pause_supersedes_dependent_advances_once(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _, analysis, dependent = terminal_with_evidence(store)
    claimed_analysis = store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    )
    store.finish_codex_job(
        claimed_analysis["id"], "analysis-worker", "succeeded",
        result={"safety_disposition": "clear"},
    )
    claimed_dependent = store.claim_codex_job(
        "advance", "advance-worker", lease_seconds=60
    )
    assert claimed_dependent["id"] == dependent["id"]
    store.finish_codex_job(
        claimed_dependent["id"], "advance-worker", "blocked",
        error="fixture needs inspection",
    )
    pause = store.pause_codex_queue(
        dependent["id"], "fixture needs inspection"
    )
    extra = store.enqueue_advance(
        "dependent:retry",
        "analysis_followups",
        depends_on_job_id=analysis["id"],
    )
    with store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET status='retry' WHERE id=?", (extra["id"],)
        )
    target = store.create(
        {
            "name": "waiting physical plan",
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
        },
        "test",
    )

    resumed = store.resume_codex_queue(
        "Robot and evidence inspected", created_by="operator"
    )
    assert resumed["resumed"] is True
    assert resumed["source_job_id"] == dependent["id"]
    assert resumed["resumes_control_sequence"] == pause["sequence"]
    assert resumed["superseded_count"] == 2
    assert {job["id"] for job in resumed["superseded_jobs"]} == {
        dependent["id"], extra["id"]
    }
    for job in resumed["superseded_jobs"]:
        assert job["status"] == "succeeded"
        assert job["result"]["action"] == "superseded"
    kick = store.get_codex_job(resumed["advance_job_id"])
    assert kick["status"] == "queued"
    assert kick["trigger_kind"] == "operator_resume"
    assert kick["depends_on_job_id"] is None
    assert kick["experiment_id"] == target["id"]

    replay = store.resume_codex_queue(
        "Duplicate network retry", created_by="operator"
    )
    assert replay["resumed"] is False
    assert replay["sequence"] == resumed["sequence"]
    assert replay["advance_job_id"] == resumed["advance_job_id"]
    with store.connect() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM codex_jobs WHERE trigger_kind='operator_resume'"
        ).fetchone()[0] == 1


def test_resume_creates_dependency_free_empty_queue_check(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    source = store.enqueue_advance("pause-source", "bootstrap")
    claimed = store.claim_codex_job("advance", "worker", lease_seconds=60)
    assert claimed["id"] == source["id"]
    store.finish_codex_job(
        source["id"],
        "worker",
        "blocked",
        error="Inspect an external blocker",
        lease_token=claimed["lease_token"],
    )

    resumed = store.resume_codex_queue(
        "Inspection complete", created_by="operator"
    )
    kick = store.get_codex_job(resumed["advance_job_id"])
    assert kick["depends_on_job_id"] is None
    assert kick["experiment_id"] is None


def test_stale_evidence_fails_outbox_closed_and_latches_pause(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    experiment = store.create(
        {"name": "unsealed terminal run", "duration_seconds": 1}, "test"
    )
    store.finish(experiment["id"], "succeeded")

    failed = store.fail_stale_awaiting_evidence(
        experiment["id"],
        "Final evidence was not sealed before the configured cutoff",
    )
    assert failed["affected_count"] == 2
    assert failed["analysis_dead_count"] == 1
    assert failed["advance_blocked_count"] == 1
    statuses = {job["kind"]: job["status"] for job in failed["jobs"]}
    assert statuses == {"analysis": "dead", "advance": "blocked"}
    analysis = next(job for job in failed["jobs"] if job["kind"] == "analysis")
    assert failed["queue_control"]["paused"] is True
    assert failed["queue_control"]["source_job_id"] == analysis["id"]
    assert store.codex_queue_control()["paused"] is True
    assert any(
        event["kind"] == "codex_evidence_timeout"
        for event in store.events(experiment["id"])
    )

    replay = store.fail_stale_awaiting_evidence(
        experiment["id"], "Same reconciliation pass"
    )
    assert replay["affected_count"] == 0
    assert len(
        [
            event for event in store.events(experiment["id"])
            if event["kind"] == "codex_evidence_timeout"
        ]
    ) == 1


def test_late_evidence_requeues_analysis_and_resume_waits_for_its_success(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    experiment = store.create(
        {"name": "late evidence", "duration_seconds": 1}, "test"
    )
    store.finish(experiment["id"], "succeeded")
    failed = store.fail_stale_awaiting_evidence(
        experiment["id"], "Evidence missed its deadline"
    )
    analysis = next(job for job in failed["jobs"] if job["kind"] == "analysis")
    advance = next(job for job in failed["jobs"] if job["kind"] == "advance")

    sealed = store.seal_evidence(experiment["id"], "b" * 64)
    assert sealed["evidence_manifest_sha256"] == "b" * 64
    repaired = {job["kind"]: job for job in store.codex_jobs_for_experiment(
        experiment["id"]
    )}
    assert repaired["analysis"]["id"] == analysis["id"]
    assert repaired["analysis"]["status"] == "queued"
    assert repaired["analysis"]["result"] is None
    assert repaired["advance"]["id"] == advance["id"]
    assert repaired["advance"]["status"] == "blocked"

    with pytest.raises(ValueError, match="Cannot resume"):
        store.resume_codex_queue("Evidence repaired", created_by="operator")
    assert store.codex_queue_control()["paused"] is True

    claimed = store.claim_codex_job("analysis", "worker", lease_seconds=60)
    assert claimed["id"] == analysis["id"]
    store.finish_codex_job(
        analysis["id"],
        "worker",
        "succeeded",
        result={"safety_disposition": "clear"},
        lease_token=claimed["lease_token"],
    )
    resumed = store.resume_codex_queue(
        "Late evidence was analyzed and the robot was inspected",
        created_by="operator",
    )
    assert resumed["resumed"] is True
    assert store.get_codex_job(resumed["advance_job_id"])["status"] == "queued"


def test_resume_is_noop_without_a_pause(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    resumed = store.resume_codex_queue("No blocker", created_by="operator")
    assert resumed["resumed"] is False
    assert resumed["advance_job_id"] is None
    assert store.list_codex_jobs() == []


def test_advance_terminal_stop_atomically_latches_queue(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    job = store.enqueue_advance("atomic:block", "test")
    claimed = store.claim_codex_job("advance", "worker", lease_seconds=60)
    assert claimed["id"] == job["id"]

    store.finish_codex_job(
        job["id"],
        "worker",
        "blocked",
        error="camera inspection required",
        lease_token=claimed["lease_token"],
    )

    control = store.codex_queue_control()
    assert control["paused"] is True
    assert control["source_job_id"] == job["id"]
    assert "camera" in control["reason"]


def test_expired_advisory_advance_retries_without_latching_queue(tmp_path):
    retry_store = Store(tmp_path / "retry.sqlite3")
    retry_job = retry_store.enqueue_advance(
        "atomic:retry-dead", "test", max_attempts=1
    )
    claimed = retry_store.claim_codex_job("advance", "worker", lease_seconds=60)
    finished = retry_store.retry_codex_job(
        retry_job["id"],
        "worker",
        "prerequisite never became ready",
        delay_seconds=0,
        lease_token=claimed["lease_token"],
    )
    assert finished["status"] == "dead"
    assert retry_store.codex_queue_control()["source_job_id"] == retry_job["id"]

    expiry_store = Store(tmp_path / "expiry.sqlite3")
    expiry_job = expiry_store.enqueue_advance("atomic:expired", "test")
    expiry_store.claim_codex_job("advance", "worker", lease_seconds=60)
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with expiry_store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET lease_expires_at=? WHERE id=?",
            (expired, expiry_job["id"]),
        )
    assert expiry_store.recover_expired_codex_jobs() == 1
    recovered = expiry_store.get_codex_job(expiry_job["id"])
    assert recovered["status"] == "retry"
    assert expiry_store.codex_queue_control()["paused"] is False

    exhausted_store = Store(tmp_path / "expired-max.sqlite3")
    exhausted = exhausted_store.enqueue_advance(
        "queue-drain:waiting-plan", "queue_reconcile", max_attempts=1
    )
    exhausted_store.claim_codex_job("advance", "worker", lease_seconds=60)
    with exhausted_store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET lease_expires_at=? WHERE id=?",
            (expired, exhausted["id"]),
        )
    assert exhausted_store.recover_expired_codex_jobs() == 1
    assert exhausted_store.get_codex_job(exhausted["id"])["status"] == "dead"
    exhausted_control = exhausted_store.codex_queue_control()
    assert exhausted_control["paused"] is True
    assert exhausted_control["source_job_id"] == exhausted["id"]


def test_resume_stays_paused_while_an_advance_claim_is_running(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    queued = store.enqueue_advance("running-advance", "bootstrap")
    running = store.claim_codex_job("advance", "worker", lease_seconds=60)
    assert running["id"] == queued["id"]
    pause = store.pause_codex_queue(running["id"], "Inspect in-flight work")

    with pytest.raises(ValueError, match="job that paused the queue has finished"):
        store.resume_codex_queue(
            "Inspection requested", created_by="operator"
        )
    assert store.codex_queue_control()["sequence"] == pause["sequence"]
    assert store.codex_queue_control()["paused"] is True


def test_preview_schema_migrates_fencing_and_receipt_columns(tmp_path):
    path = tmp_path / "preview.sqlite3"
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE codex_jobs (
              id TEXT PRIMARY KEY, dedupe_key TEXT NOT NULL UNIQUE,
              kind TEXT NOT NULL, trigger_kind TEXT NOT NULL,
              experiment_id TEXT, evidence_manifest_sha256 TEXT,
              status TEXT NOT NULL, depends_on_job_id TEXT,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_attempts INTEGER NOT NULL DEFAULT 5,
              not_before TEXT NOT NULL, lease_owner TEXT,
              lease_expires_at TEXT, created_at TEXT NOT NULL,
              started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL,
              result_json TEXT, error TEXT
            );
            CREATE TABLE codex_followup_proposals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              analysis_job_id TEXT NOT NULL,
              source_experiment_id TEXT NOT NULL,
              root_experiment_id TEXT NOT NULL,
              proposal_index INTEGER NOT NULL,
              recommendation_key TEXT NOT NULL,
              spec_sha256 TEXT NOT NULL, spec_json TEXT NOT NULL,
              rationale TEXT NOT NULL, lineage_depth INTEGER NOT NULL,
              disposition TEXT NOT NULL, disposition_reason TEXT NOT NULL,
              child_experiment_id TEXT, created_at TEXT NOT NULL,
              UNIQUE(analysis_job_id,proposal_index)
            );
            CREATE TABLE codex_queue_controls (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              dedupe_key TEXT NOT NULL UNIQUE,
              action TEXT NOT NULL, source_job_id TEXT,
              reason TEXT NOT NULL, created_by TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        legacy_spec = {"name": "legacy", "duration_seconds": 1}
        con.execute(
            "INSERT INTO codex_followup_proposals("
            "analysis_job_id,source_experiment_id,root_experiment_id,"
            "proposal_index,recommendation_key,spec_sha256,spec_json,rationale,"
            "lineage_depth,disposition,disposition_reason,created_at"
            ") VALUES('analysis','source','source',0,'legacy-key','spec',?,"
            "'legacy rationale',1,'rejected','old limit','2026-01-01')",
            (json.dumps(legacy_spec),),
        )

    store = Store(path)
    with store.connect() as con:
        assert "lease_token" in {
            row["name"] for row in con.execute("PRAGMA table_info(codex_jobs)")
        }
        assert "resumes_control_sequence" in {
            row["name"]
            for row in con.execute("PRAGMA table_info(codex_queue_controls)")
        }
        migrated = con.execute(
            "SELECT proposal_sha256 FROM codex_followup_proposals WHERE id=1"
        ).fetchone()
    assert migrated["proposal_sha256"] == Store._proposal_sha256(
        {
            "recommendation_key": "legacy-key",
            "rationale": "legacy rationale",
            "spec": legacy_spec,
        }
    )
