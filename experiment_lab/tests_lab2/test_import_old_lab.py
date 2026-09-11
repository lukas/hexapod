import json
import sqlite3

from hexapod_lab2.import_old_lab import import_all


def make_old(tmp_path):
    old = tmp_path / "old"
    (old / "experiments" / "e1").mkdir(parents=True)
    (old / "experiments" / "e1" / "clip.mp4").write_bytes(b"video")
    (old / "experiments" / "e1" / "telemetry.jsonl").write_bytes(b"x" * 100)
    (old / "experiments" / "e1" / "raw.csv.gz").write_bytes(b"x" * 100)
    (old / "experiments" / "e1" / "notes" / "REPORT.md").parent.mkdir()
    (old / "experiments" / "e1" / "notes" / "REPORT.md").write_text("report")
    con = sqlite3.connect(old / "lab.sqlite3")
    con.executescript("""
        CREATE TABLE experiments(id TEXT, name TEXT, description TEXT, status TEXT, created_at TEXT,
            started_at TEXT, finished_at TEXT, error TEXT, parameters_json TEXT);
        CREATE TABLE experiment_learnings(sequence INTEGER, experiment_id TEXT, text TEXT, created_at TEXT);
        INSERT INTO experiments VALUES('e1','L4 shear','measure L4','succeeded','2026-09-05T01:00:00Z',
            '2026-09-05T01:02:00Z','2026-09-05T01:20:00Z',NULL,'{"protocol":"sysid/protocols/l4_shear_v1.json"}');
        INSERT INTO experiments VALUES('e2','Bad run','tried','failed','2026-09-06T01:00:00Z',
            '2026-09-06T01:02:00Z','2026-09-06T01:03:00Z','runner exited 2',NULL);
        INSERT INTO experiments VALUES('e3','Cancelled','never ran','cancelled','2026-09-07T01:00:00Z',NULL,NULL,NULL,NULL);
        INSERT INTO experiment_learnings VALUES(1,'e1','first draft','2026-09-05T01:25:00Z');
        INSERT INTO experiment_learnings VALUES(2,'e1','L4 loop width 2.1 deg.','2026-09-05T01:30:00Z');
    """)
    con.commit(); con.close()
    return old


def test_import_is_dated_filtered_and_idempotent(settings, store, tmp_path):
    old = make_old(tmp_path)
    dry = import_all(settings, old, dry_run=True, log=None)
    assert dry["imported"] == 2 and dry["bytes"] == len(b"video") + len(b"report")
    stats = import_all(settings, old, log=None)
    assert stats["imported"] == 2 and stats["skipped"] == 0
    runs = store.runs(limit=10)
    assert [r["status"] for r in runs] == ["failed", "ok"]
    ok = runs[1]
    assert ok["started_at"] == "2026-09-05T01:02:00Z" and ok["protocol"] == "l4_shear_v1"
    summary = json.loads(ok["summary_json"])
    assert summary["old_lab"] is True and summary["old_id"] == "e1" and summary["files"] == 2
    files = store.run_files(ok["id"])
    assert "clip.mp4" in files and "notes" in files and "telemetry.jsonl" not in files
    assert store.learning_for_run(ok["id"]) == "[old-lab] L4 loop width 2.1 deg."
    assert store.learnings(limit=1)[0]["created_at"] == "2026-09-05T01:20:00Z"
    assert runs[0]["log_tail"] == "runner exited 2" and store.learning_for_run(runs[0]["id"]) is None
    assert store.consecutive_failed_runs() == 0
    again = import_all(settings, old, log=None)
    assert again["imported"] == 0 and again["skipped"] == 2
    assert store.run_joined("e1")["id"] == ok["id"]
