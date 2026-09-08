"""Whole-lab cost and activity rollup."""
import json

from hexapod_lab import lab_stats
from hexapod_lab.db import Store

from test_agent_providers import configured


def attempt(data_dir, job, n, **meta):
    run = data_dir / "codex-runs" / job / f"attempt-{n}"
    run.mkdir(parents=True, exist_ok=True)
    payload = {"job_id": job, "attempt": n, "kind": "analysis",
               "provider": "claude", "model": "claude-opus-5", "returncode": 0}
    payload.update(meta)
    (run / "metadata.json").write_text(json.dumps(payload))
    return run


def test_costs_roll_up_by_backend_lane_and_model(tmp_path):
    settings = configured(tmp_path, agent_provider="claude")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    attempt(settings.data_dir, "j1", 1, usage={"cost_usd": 1.5, "output_tokens": 10})
    attempt(settings.data_dir, "j2", 1, kind="advance",
            usage={"cost_usd": 0.5, "output_tokens": 4})
    attempt(settings.data_dir, "j3", 1, provider="codex", model="gpt-5.6-sol",
            returncode=1)
    lab_stats.invalidate()
    data = lab_stats.collect(Store(settings.data_dir / "lab.sqlite3"), settings)

    assert data["totals"]["attempts"] == 3
    assert data["totals"]["cost_usd"] == 2.0
    assert data["totals"]["failed"] == 1
    assert data["by_provider"]["claude"]["cost_usd"] == 2.0
    assert data["by_provider"]["codex"]["attempts"] == 1
    assert data["by_role"]["advance"]["cost_usd"] == 0.5
    assert data["agent"]["label"] == "Claude"


def test_attempts_without_usage_do_not_break_the_rollup(tmp_path):
    """Runs predating cost reporting must count, contributing zero spend."""
    settings = configured(tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    attempt(settings.data_dir, "old", 1)
    (settings.data_dir / "codex-runs" / "broken").mkdir(parents=True)
    (settings.data_dir / "codex-runs" / "broken" / "attempt-1").mkdir()
    (settings.data_dir / "codex-runs" / "broken" / "attempt-1"
     / "metadata.json").write_text("{not json")
    lab_stats.invalidate()
    data = lab_stats.collect(Store(settings.data_dir / "lab.sqlite3"), settings)
    assert data["totals"]["attempts"] == 1
    assert data["totals"]["cost_usd"] == 0.0


def test_missing_run_tree_yields_an_empty_but_valid_rollup(tmp_path):
    settings = configured(tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    lab_stats.invalidate()
    data = lab_stats.collect(Store(settings.data_dir / "lab.sqlite3"), settings)
    assert data["ok"] is True and data["totals"]["attempts"] == 0


def test_operator_pause_latches_and_is_idempotent(tmp_path):
    """A second click must not stack latches one resume would not clear."""
    settings = configured(tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir / "lab.sqlite3")

    first = store.pause_codex_queue_for_operator("watching spend", created_by="alice")
    assert first["paused"] is True and first["already_paused"] is False
    assert first["source_job_id"] is None

    second = store.pause_codex_queue_for_operator("again", created_by="alice")
    assert second["already_paused"] is True
    assert second["sequence"] == first["sequence"]

    assert store.codex_queue_control()["paused"] is True
    store.resume_codex_queue("inspected", created_by="alice")
    assert store.codex_queue_control()["paused"] is False

    third = store.pause_codex_queue_for_operator("second pause", created_by="alice")
    assert third["already_paused"] is False
    assert third["sequence"] > first["sequence"]


def test_operator_pause_requires_a_reason(tmp_path):
    import pytest

    settings = configured(tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir / "lab.sqlite3")
    with pytest.raises(ValueError):
        store.pause_codex_queue_for_operator("   ", created_by="alice")
