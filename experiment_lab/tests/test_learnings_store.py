import sqlite3

import pytest

from hexapod_lab.db import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "lab.sqlite3")


def completed(store, status="succeeded"):
    return store.import_result(
        {"name": "Completed experiment", "duration_seconds": 1}, "runner", status
    )["id"]


def test_additive_initialization_preserves_existing_experiment(tmp_path):
    path = tmp_path / "lab.sqlite3"
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE experiments (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
              duration_seconds REAL NOT NULL, parameters_json TEXT NOT NULL,
              status TEXT NOT NULL, submitted_by TEXT NOT NULL, created_at TEXT NOT NULL,
              started_at TEXT, finished_at TEXT, error TEXT,
              cancel_requested INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO experiments(id,name,description,duration_seconds,
              parameters_json,status,submitted_by,created_at)
              VALUES('existing','Legacy experiment','Evidence intact',1,
                     '{}','succeeded','runner','2026-09-05T00:00:00+00:00');
        """)
    migrated = Store(path)
    assert migrated.get("existing")["description"] == "Evidence intact"
    assert migrated.learnings("existing") is None
    note = migrated.record_learnings("existing", "A useful result.", ["summary.md"], "reviewer")
    reopened = Store(path)
    assert reopened.learnings("existing") == note
    assert reopened.get("existing")["name"] == "Legacy experiment"


def test_missing_experiment_has_no_note_and_cannot_record(store):
    assert store.learnings("missing") is None
    with pytest.raises(ValueError, match="Experiment not found"):
        store.record_learnings("missing", "Result", [], "reviewer")
    assert store.learnings("missing") is None


@pytest.mark.parametrize("status", ["queued", "running", "waiting_for_operator"])
def test_nonterminal_experiment_cannot_have_learnings(store, status):
    experiment = store.create({
        "name": "Pending", "duration_seconds": 1,
        "execution_mode": "external_guarded" if status == "waiting_for_operator" else "builtin",
    }, "runner")
    if status == "running":
        store.claim_next()
    before = store.events(experiment["id"])
    with pytest.raises(ValueError, match="completed experiment"):
        store.record_learnings(experiment["id"], "Too early", [], "reviewer")
    assert store.learnings(experiment["id"]) is None
    assert store.events(experiment["id"]) == before


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled"])
def test_terminal_results_accept_stripped_text_and_source_provenance(store, status):
    experiment_id = completed(store, status)
    with pytest.raises(ValueError, match="must not be blank"):
        store.record_learnings(experiment_id, " \n ", [], "reviewer")
    note = store.record_learnings(experiment_id, "  The test revealed a limit.\n", ["summary.md"], "reviewer")
    assert note["text"] == "The test revealed a limit."
    assert note["sources"] == ["summary.md"]
    assert note["created_by"] == "reviewer"
    assert note["created_at"]
    assert isinstance(note["revision"], int)
    assert store.learnings(experiment_id) == note


def test_revisions_append_and_retries_are_idempotent(store):
    experiment_id = completed(store)
    first = store.record_learnings(experiment_id, "First interpretation", [{"path": "summary.md", "line": 2}], "alice")
    retry = store.record_learnings(experiment_id, " First interpretation\n", [{"line": 2, "path": "summary.md"}], "bob")
    assert retry == first
    second = store.record_learnings(experiment_id, "Updated interpretation", ["telemetry.jsonl"], "bob")
    assert second["revision"] > first["revision"]
    assert store.learnings(experiment_id) == second
    with store.connect() as con:
        history = con.execute("SELECT text FROM experiment_learnings ORDER BY sequence").fetchall()
    assert [row["text"] for row in history] == ["First interpretation", "Updated interpretation"]
    events = [event for event in store.events(experiment_id) if event["kind"] == "learnings_updated"]
    assert len(events) == 2
    assert "alice" in events[0]["message"] and str(first["revision"]) in events[0]["message"]
    assert "bob" in events[1]["message"] and str(second["revision"]) in events[1]["message"]
    assert all("interpretation" not in event["message"] for event in events)


@pytest.mark.parametrize("sql", [
    "UPDATE experiment_learnings SET text='changed'",
    "DELETE FROM experiment_learnings",
])
def test_database_rejects_mutation_of_existing_revisions(store, sql):
    experiment_id = completed(store)
    note = store.record_learnings(experiment_id, "Preserved interpretation", [], "reviewer")
    with store.connect() as con, pytest.raises(sqlite3.IntegrityError, match="append-only"):
        con.execute(sql)
    assert store.learnings(experiment_id) == note
