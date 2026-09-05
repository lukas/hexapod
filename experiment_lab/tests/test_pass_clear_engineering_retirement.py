import hashlib
import json

import pytest

from hexapod_lab.db import Store
from hexapod_lab.engineering_lane import EngineeringJobStore


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _finished_analysis(store, *, verdict="pass", safety_disposition="clear"):
    experiment = store.create(
        {"name": "measured gait", "duration_seconds": 1, "parameters": {}},
        "test",
    )
    store.finish(experiment["id"], "succeeded")
    store.seal_evidence(experiment["id"], "a" * 64)
    analysis = store.claim_codex_job("analysis", "analyzer", lease_seconds=60)
    assert analysis is not None
    result = {
        "schema_version": 1,
        "experiment_id": experiment["id"],
        "evidence_manifest_sha256": "a" * 64,
        "verdict": verdict,
        "safety_disposition": safety_disposition,
        "what_we_learned": "The measured gait result is conclusive.",
        "sources": ["summary.md"],
        "findings": ["The bounded run produced a usable result."],
        "recommended_experiments": [],
    }
    store.finish_codex_job(
        analysis["id"],
        "analyzer",
        "succeeded",
        result=result,
        lease_token=analysis["lease_token"],
    )
    return experiment, analysis


def _rewrite_job_source_analysis(store, job, *, verdict, safety_disposition):
    source = dict(job["source_context"])
    source["analysis"] = {
        **source["analysis"],
        "verdict": verdict,
        "safety_disposition": safety_disposition,
    }
    encoded = _canonical(source)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET source_context_json=?,"
            "source_context_sha256=? WHERE id=?",
            (encoded, digest, job["id"]),
        )


def test_pass_clear_analysis_does_not_create_engineering_work(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _finished_analysis(store)
    engineering = EngineeringJobStore(store)

    assert engineering.reconcile() == 0
    assert engineering.reconcile() == 0
    assert engineering.list_jobs() == []
    assert engineering.claim("engineer", lease_seconds=60) is None


@pytest.mark.parametrize(
    ("verdict", "safety_disposition"),
    [("fail", "clear"), ("pass", "needs_inspection")],
)
def test_non_pass_or_non_clear_analysis_keeps_engineering_work(
    tmp_path, verdict, safety_disposition
):
    store = Store(tmp_path / "lab.sqlite3")
    _experiment, analysis = _finished_analysis(
        store,
        verdict=verdict,
        safety_disposition=safety_disposition,
    )
    engineering = EngineeringJobStore(store)

    assert engineering.reconcile() == 1
    job = engineering.claim("engineer", lease_seconds=60)
    assert job is not None
    assert job["source_analysis_job_id"] == analysis["id"]


@pytest.mark.parametrize("status", ["queued", "retry"])
def test_reconcile_retires_existing_pass_clear_analysis_work(tmp_path, status):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, _analysis = _finished_analysis(store, verdict="inconclusive")
    engineering = EngineeringJobStore(store)
    assert engineering.reconcile() == 1
    job = engineering.list_jobs()[0]
    _rewrite_job_source_analysis(
        store,
        job,
        verdict="pass",
        safety_disposition="clear",
    )
    prior = {"retry_receipt": {"attempt": 1, "error": "old transient"}}
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET status=?,result_json=?,error=? "
            "WHERE id=?",
            (
                status,
                _canonical(prior) if status == "retry" else None,
                "old transient" if status == "retry" else None,
                job["id"],
            ),
        )

    assert engineering.reconcile() == 1
    retired = engineering.list_jobs()[0]
    assert retired["status"] == "succeeded"
    assert retired["result"]["outcome"] == "no_change"
    assert retired["result"]["physical_motion_started"] is False
    assert retired["result"]["robot_contacted"] is False
    assert retired["result"]["network_used"] is False
    if status == "retry":
        assert retired["result"]["previous_receipt"] == prior
    else:
        assert "previous_receipt" not in retired["result"]
    assert engineering.claim("engineer", lease_seconds=60) is None
    assert any(
        event["kind"] == "engineering_analysis_retired"
        for event in store.events(experiment["id"])
    )


def test_reconcile_never_retires_running_pass_clear_analysis_work(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    _finished_analysis(store, verdict="inconclusive")
    engineering = EngineeringJobStore(store)
    assert engineering.reconcile() == 1
    running = engineering.claim("engineer", lease_seconds=60)
    assert running is not None
    _rewrite_job_source_analysis(
        store,
        running,
        verdict="pass",
        safety_disposition="clear",
    )

    assert engineering.reconcile() == 0
    current = engineering.list_jobs()[0]
    assert current["status"] == "running"
    assert not any(
        event["kind"] == "engineering_analysis_retired"
        for event in store.events(current["experiment_id"])
    )


def test_reconcile_never_retires_queue_handoff(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "bounded walk",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = next(job for job in store.list_codex_jobs() if job["kind"] == "advance")
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(advance, guarded)
    source = dict(handoff["source_context"])
    source["analysis"] = {"verdict": "pass", "safety_disposition": "clear"}
    encoded = _canonical(source)
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET source_context_json=?,"
            "source_context_sha256=? WHERE id=?",
            (
                encoded,
                hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                handoff["id"],
            ),
        )

    assert engineering.reconcile() == 0
    current = engineering.list_jobs()[0]
    assert current["id"] == handoff["id"]
    assert current["status"] == "queued"
