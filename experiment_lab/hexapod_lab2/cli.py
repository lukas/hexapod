"""hexapod-lab2: loop | run <protocol> | plan | add <protocol> "title" "why" | status | pause | resume"""
from __future__ import annotations

import argparse
import json
import sys

from . import loop, planner
from .config import load_settings
from .store import Store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hexapod-lab2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("loop", help="run the lab loop until it stops itself")
    run = sub.add_parser("run", help="run one existing protocol now (health read, run, record; no planner)")
    run.add_argument("protocol")
    run.add_argument("--why", default="operator run")
    run.add_argument("--force", action="store_true")
    sub.add_parser("plan", help="one planner call against the current state")
    add = sub.add_parser("add", help="queue an existing protocol")
    add.add_argument("protocol"); add.add_argument("title"); add.add_argument("why")
    imp = sub.add_parser("import", help="record a hand-run experiment (e.g. on hexapod 2) with its folder of video/telemetry")
    imp.add_argument("folder", nargs="?", default=None, help="folder to copy in whole; optional")
    imp.add_argument("--robot", default="hexapod2")
    imp.add_argument("--title", required=True)
    imp.add_argument("--why", required=True)
    imp.add_argument("--found", default="", help="one paragraph: what it showed. Joins the learnings the planner reads.")
    imp.add_argument("--status", default="ok", choices=["ok", "failed"])
    sub.add_parser("recover", help="run the robot's own recovery ladder now (safe-zero, untrap, safe-zero)")
    at = sub.add_parser("alert-test", help="send one test text to the configured recipient")
    at.add_argument("--message", default="test from Robot Lab v2")
    sub.add_parser("status")
    sub.add_parser("pause"); sub.add_parser("resume")
    args = ap.parse_args(argv)

    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.db_path)

    if args.cmd == "loop":
        reason = loop.main_loop(settings, store, log=lambda m: print(m, flush=True))
        print(f"loop stopped: {reason}")
        return 0
    if args.cmd == "run":
        pid = store.add_plan(title=f"operator: {args.protocol}", why=args.why, kind="existing",
                             protocol=args.protocol, build_spec=None, force=args.force, source="operator")
        row = loop.run_once(settings, store, store.plan(pid), log=lambda m: print(m, flush=True))
        print(json.dumps({k: row[k] for k in ("id", "status", "exit_code", "run_dir")}, indent=1))
        return 0 if row["status"] == "ok" else 1
    if args.cmd == "plan":
        last = store.runs(limit=1)
        print(json.dumps(planner.plan(settings, store, last[0] if last else None,
                                      last_run_id=last[0]["id"] if last else None), indent=1))
        return 0
    if args.cmd == "add":
        print(store.add_plan(title=args.title, why=args.why, kind="existing", protocol=args.protocol,
                             build_spec=None, source="operator"))
        return 0
    if args.cmd == "import":
        from pathlib import Path
        folder = Path(args.folder).expanduser() if args.folder else None
        if folder is not None and not folder.is_dir():
            print(f"not a folder: {folder}"); return 2
        rid = store.import_run(robot=args.robot, title=args.title, why=args.why, found=args.found,
                               source_dir=folder, runs_dir=settings.runs_dir, status=args.status)
        print(json.dumps({"run_id": rid, "files": store.run_files(rid),
                          "url": f"/v2/?robot={args.robot}"}, indent=1))
        return 0
    if args.cmd == "recover":
        from . import recovery
        rep = recovery.recover(settings, log=lambda m: print(m, flush=True))
        store.add_event("recovery", ("recovered (operator): " if rep["ok"] else "FAILED (operator): ")
                        + "; ".join(f"{r['rung']}={r['status'][:60]}" for r in rep["rungs"]))
        print(json.dumps(rep, indent=1)); return 0 if rep["ok"] else 1
    if args.cmd == "alert-test":
        from . import alerts
        sent = alerts.text(store, f"test-{store.events(1)[0]['id'] if store.events(1) else 'first'}", args.message)
        print("sent" if sent else "not sent: " + store.events(1)[0]["text"]); return 0 if sent else 1
    if args.cmd == "status":
        print(json.dumps({"paused": settings.pause_file.exists(), "last_stop": store.last_stop(),
                          "spend_24h_usd": round(store.spend_last_24h(), 2),
                          "queue": [(p["status"], p["title"], p["protocol"]) for p in store.plans(["queued", "building", "running"])],
                          "runs": [(r["started_at"], r["protocol"], r["status"]) for r in store.runs(limit=5)]}, indent=1))
        return 0
    if args.cmd == "pause":
        settings.pause_file.write_text("paused by operator\n"); print("paused"); return 0
    if args.cmd == "resume":
        settings.pause_file.unlink(missing_ok=True); print("resumed"); return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
