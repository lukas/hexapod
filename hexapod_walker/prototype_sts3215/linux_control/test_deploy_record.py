"""The on-robot deploy receipt and its history."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import deploy_record  # noqa: E402


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_LOG_DIR", str(tmp_path))
    deploy_record._registered = None
    yield
    deploy_record._registered = None


def write(path, **overrides):
    record = {
        "schema_version": 1,
        "deploy_id": "abc123-2026-09-08T00:00:00.000Z",
        "deployed_at": "2026-09-08T00:00:00.000Z",
        "deployer": "claude",
        "git_revision": "a" * 40,
        "git_branch": "main",
        "source_dirty": False,
        "staged_tree_sha256": "b" * 64,
    }
    record.update(overrides)
    path.write_text(json.dumps(record))
    return record


def test_registering_appends_history_once_per_deploy(tmp_path):
    path = tmp_path / "deploy_record.json"
    write(path)
    first = deploy_record.register_current(path)
    assert first["deployer"] == "claude"
    assert "activated_at" in first

    # A service restart with the same tree must not invent a second deploy.
    deploy_record._registered = None
    deploy_record.register_current(path)
    assert len(deploy_record.history()) == 1

    deploy_record._registered = None
    write(path, deploy_id="def456-2026-09-08T01:00:00.000Z")
    deploy_record.register_current(path)
    ids = [d["deploy_id"] for d in deploy_record.history()]
    assert ids == [
        "abc123-2026-09-08T00:00:00.000Z",
        "def456-2026-09-08T01:00:00.000Z",
    ]


def test_missing_receipt_reports_not_deployed(tmp_path):
    assert deploy_record.register_current(tmp_path / "absent.json") is None
    state = deploy_record.current()
    assert state["ok"] is True and state["deployed"] is False


def test_unwritable_history_never_blocks_startup(tmp_path, monkeypatch):
    path = tmp_path / "deploy_record.json"
    write(path)
    monkeypatch.setenv("HEXAPOD_LOG_DIR", "/proc/nonexistent/denied")
    record = deploy_record.register_current(path)
    assert record["deployer"] == "claude"


def test_corrupt_history_lines_are_skipped(tmp_path):
    (tmp_path / "deploys.jsonl").write_text(
        '{"deploy_id": "ok"}\nnot json\n{"deploy_id": "ok2"}\n'
    )
    assert [d["deploy_id"] for d in deploy_record.history()] == ["ok", "ok2"]
