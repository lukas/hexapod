"""One-time import of the original Robot Lab's findings into v2.

The original lab (experiment_lab/hexapod_lab, retired 2026-09-11) kept its
experiments in data/lab.sqlite3 and artifacts under data/experiments/<id>/.
Every experiment that actually ran (status succeeded or failed) becomes a v2
plan + run on hexapod1 dated when it happened, with its latest learning
paragraph filed as a v2 learning tagged [old-lab]. Cancelled experiments
measured nothing and are skipped. Bulk telemetry (.gz, .jsonl, .bin) stays in
the old data directory, which is left on disk untouched; everything else
(video, stills, CSV, notes, scripts) is copied next to the run.

    python -m hexapod_lab2.import_old_lab [--old-dir DIR] [--dry-run]

Re-running is safe: runs are keyed on the old experiment id.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .config import Settings, load_settings
from .store import Store

SKIP_SUFFIXES = {".gz", ".jsonl", ".bin"}
STATUS = {"succeeded": "ok", "failed": "failed"}


def old_experiments(old_db: Path) -> list[dict]:
    con = sqlite3.connect(f"file:{old_db}?immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, name, description, status, created_at, started_at, finished_at, error, parameters_json"
        " FROM experiments WHERE status IN ('succeeded','failed') ORDER BY created_at").fetchall()
    out = []
    for r in rows:
        learning = con.execute(
            "SELECT text, created_at FROM experiment_learnings WHERE experiment_id=? ORDER BY sequence DESC LIMIT 1",
            (r["id"],)).fetchone()
        d = dict(r)
        d["learning"] = learning["text"] if learning else ""
        d["learning_at"] = learning["created_at"] if learning else None
        out.append(d)
    con.close()
    return out


def already_imported(store: Store) -> set:
    return {r[0] for r in store.con.execute(
        "SELECT json_extract(summary_json, '$.old_id') FROM runs"
        " WHERE json_extract(summary_json, '$.old_lab') = 1")}


def copy_artifacts(src: Path, dest: Path) -> tuple[list[str], int]:
    names, size = [], 0
    if not src.is_dir():
        return names, size
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.name.startswith(".") or p.suffix.lower() in SKIP_SUFFIXES:
            continue
        rel = p.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(p, target)
        names.append(str(rel))
        size += p.stat().st_size
    return names, size


def protocol_name(parameters_json: Optional[str]) -> Optional[str]:
    try:
        params = json.loads(parameters_json or "{}")
    except ValueError:
        return None
    for key in ("protocol", "protocol_name"):
        v = params.get(key) if isinstance(params, dict) else None
        if isinstance(v, str) and v:
            return Path(v).stem[:80]
    return None


def import_all(settings: Settings, old_dir: Path, *, dry_run: bool = False,
               log: Optional[callable] = print) -> dict:
    store = Store(settings.db_path)
    done = already_imported(store)
    rows = old_experiments(old_dir / "lab.sqlite3")
    stats = {"seen": len(rows), "imported": 0, "skipped": 0, "bytes": 0}
    for r in rows:
        if r["id"] in done:
            stats["skipped"] += 1
            continue
        started = r["started_at"] or r["created_at"]
        finished = r["finished_at"] or started
        found = f"[old-lab] {r['learning'].strip()}" if r["learning"].strip() else ""
        summary = {"old_lab": True, "old_id": r["id"], "old_status": r["status"],
                   "error": (r["error"] or "")[:400] or None}
        if log:
            log(f"{'would import' if dry_run else 'import'} {r['id'][:8]} {r['status']:9} {started[:16]} {r['name'][:60]}")
        if dry_run:
            src = old_dir / "experiments" / r["id"]
            size = sum(p.stat().st_size for p in src.rglob("*")
                       if p.is_file() and p.suffix.lower() not in SKIP_SUFFIXES) if src.is_dir() else 0
            stats["bytes"] += size
            stats["imported"] += 1
            continue
        rid = store.record_historic(
            robot="hexapod1", title=r["name"][:200], why=(r["description"] or "")[:2000],
            found=found, started_at=started, finished_at=finished, status=STATUS[r["status"]],
            run_dir=None, summary=summary, log_tail=(r["error"] or ""),
            protocol=protocol_name(r["parameters_json"]), source="old-lab")
        run_dir = settings.runs_dir / rid
        names, size = copy_artifacts(old_dir / "experiments" / r["id"], run_dir)
        summary["files"] = len(names)
        store.con.execute("UPDATE runs SET run_dir=?, summary_json=? WHERE id=?",
                          (str(run_dir), json.dumps(summary), rid))
        store.con.commit()
        stats["bytes"] += size
        stats["imported"] += 1
    return stats


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old-dir", type=Path,
                    default=Path.home() / "Library" / "Application Support" / "Hexapod Lab" / "data")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(list(argv) if argv is not None else None)
    stats = import_all(load_settings(), a.old_dir, dry_run=a.dry_run)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
