"""The vision page's numbers must equal the lab's numbers for the same runs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

import vision_agent_stats as stats

REPO_ROOT = HERE.parents[2]


def _attempt(root: Path, job: str, attempt: int, **meta) -> Path:
    run_dir = root / "codex-runs" / job / f"attempt-{attempt}"
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"job_id": job, "attempt": attempt, **meta}
    path = run_dir / "metadata.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture()
def runs(tmp_path: Path) -> Path:
    _attempt(
        tmp_path, "job-a", 1, kind="vision", provider="claude",
        model="claude-opus-5", returncode=0,
        started_at="2026-09-07T10:00:00+00:00",
        finished_at="2026-09-07T10:00:20+00:00",
        usage={"cost_usd": 0.5, "input_tokens": 1200, "output_tokens": 300,
               "cache_read_tokens": 40000, "cache_write_tokens": 900,
               "turns": 4, "duration_ms": 20000},
    )
    _attempt(
        tmp_path, "job-b", 1, kind="vision", provider="claude",
        model="claude-opus-5", returncode=1,
        started_at="2026-09-07T11:00:00+00:00",
        finished_at="2026-09-07T11:00:05+00:00",
        usage={"cost_usd": 0.25, "input_tokens": 800, "output_tokens": 100,
               "cache_read_tokens": 10000},
    )
    # A different lane's attempt, which must not appear in vision totals.
    _attempt(
        tmp_path, "job-c", 1, kind="analysis", provider="codex",
        model="gpt-5", returncode=0,
        started_at="2026-09-07T12:00:00+00:00",
        usage={"cost_usd": 9.0, "input_tokens": 5, "output_tokens": 5},
    )
    return tmp_path


def test_totals_cover_only_the_vision_role(runs: Path) -> None:
    snapshot = stats.scan_vision_attempts(runs)
    totals = snapshot["totals"]
    assert snapshot["scanned"] == 2
    assert totals["attempts"] == 2
    assert totals["failed"] == 1
    assert totals["input_tokens"] == 2000
    assert totals["output_tokens"] == 400
    assert totals["cost_usd"] == pytest.approx(0.75)
    # The analysis lane's $9 must not leak into the vision page.
    assert totals["cost_usd"] < 1.0


def test_cache_tokens_are_reported(runs: Path) -> None:
    totals = stats.scan_vision_attempts(runs)["totals"]
    assert totals["cache_read_tokens"] == 50000
    assert totals["cache_write_tokens"] == 900


def test_attempts_are_newest_first_and_limited(runs: Path) -> None:
    snapshot = stats.scan_vision_attempts(runs, limit=1)
    assert [item["job_id"] for item in snapshot["attempts"]] == ["job-b"]
    assert snapshot["attempts"][0]["ok"] is False


def test_missing_run_tree_is_empty_not_an_error(tmp_path: Path) -> None:
    snapshot = stats.scan_vision_attempts(tmp_path / "absent")
    assert snapshot["totals"]["attempts"] == 0
    assert snapshot["attempts"] == []


def test_malformed_metadata_is_skipped(runs: Path) -> None:
    broken = runs / "codex-runs" / "job-d" / "attempt-1"
    broken.mkdir(parents=True)
    (broken / "metadata.json").write_text("{not json", encoding="utf-8")
    assert stats.scan_vision_attempts(runs)["scanned"] == 2


def test_snapshot_cache_serves_repeat_reads(runs: Path) -> None:
    view = stats.VisionAgentStats(runs, ttl_seconds=60.0)
    first = view.snapshot()
    _attempt(
        runs, "job-e", 1, kind="vision", model="claude-opus-5", returncode=0,
        started_at="2026-09-07T13:00:00+00:00",
        usage={"cost_usd": 1.0},
    )
    assert view.snapshot()["totals"] == first["totals"]
    assert view.snapshot(force=True)["totals"]["attempts"] == 3

