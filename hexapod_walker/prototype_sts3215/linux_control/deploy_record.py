#!/usr/bin/env python3
"""What is running on this robot, and who put it there.

Anyone may deploy -- that is deliberate. What was missing is the ability for
another process to find out *which* deploy is currently live and when it
landed, without shelling into the board or trusting a workstation-local
``~/.hexapod/deploy.log`` that only its own author can see.

``stage_deploy_tree`` writes ``deploy_record.json`` into the staged tree, so
the receipt ships with the code it describes. On boot the robot appends any
record it has not seen before to ``logs/deploys.jsonl``, giving an ordered
on-robot history. Both are served by ``GET /api/deploy`` and
``GET /api/deploys``.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any

_HERE = Path(__file__).resolve().parent
RECORD_PATH = _HERE / "deploy_record.json"
DEFAULT_LOG_DIR = _HERE / "logs"

_lock = threading.Lock()
_registered: dict[str, Any] | None = None


def _log_dir() -> Path:
    return Path(os.environ.get("HEXAPOD_LOG_DIR", str(DEFAULT_LOG_DIR)))


def _history_path() -> Path:
    return _log_dir() / "deploys.jsonl"


def read_record(path: Path | None = None) -> dict[str, Any] | None:
    """The receipt that shipped with the currently installed tree."""
    target = path or RECORD_PATH
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def history(limit: int = 50) -> list[dict[str, Any]]:
    try:
        lines = _history_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-max(1, min(int(limit or 50), 500)):]:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


def register_current(path: Path | None = None) -> dict[str, Any] | None:
    """Append the installed record to the history the first time it is seen.

    Idempotent on ``deploy_id``: a service restart that does not change the
    installed tree must not invent a new deploy.
    """
    global _registered
    record = read_record(path)
    if record is None:
        return None
    deploy_id = str(record.get("deploy_id") or "")
    with _lock:
        if _registered is not None and _registered.get("deploy_id") == deploy_id:
            return _registered
        seen = {str(item.get("deploy_id") or "") for item in history(limit=500)}
        if deploy_id and deploy_id not in seen:
            entry = dict(record)
            entry["activated_at"] = datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z")
            try:
                directory = _log_dir()
                directory.mkdir(parents=True, exist_ok=True)
                with _history_path().open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")
            except OSError:
                # A read-only or full filesystem must not stop the robot
                # server from starting; /api/deploy still reports the record.
                pass
            record = entry
        _registered = record
    return record


def current() -> dict[str, Any]:
    record = _registered or read_record()
    return {
        "ok": True,
        "deployed": record is not None,
        "record": record,
        "history_count": len(history(limit=500)),
    }
