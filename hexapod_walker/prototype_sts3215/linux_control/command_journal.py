#!/usr/bin/env python3
"""Attributed journal of high-level commands sent to the robot.

Several controllers drive this robot: Robot Lab's automation, the Mac hub on
:8898, and a browser on whichever laptop is nearby.  ``events.jsonl`` records
every request, but its in-memory ring is sized for debugging a single session
and GET polling evicts it within seconds -- so after something happens there is
no way to answer "what was commanded, and who commanded it?".

This keeps a separate, much longer ring of *state-changing* commands only,
each tagged with the controller that issued it, plus an append-only
``logs/commands.jsonl`` so the history outlives the ring.

Read it back with ``GET /api/commands``.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterable

_HERE = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = _HERE / "logs"

# The 5 Hz drive heartbeat is a continuation of an already-journalled
# session, not a new decision. Counting it keeps the signal without the noise.
HEARTBEAT_PATHS = frozenset({"/api/rl/drive/cmd"})

# Bodies can carry whole trajectories; keep the shape, drop the bulk.
MAX_BODY_CHARS = 700

_lock = threading.Lock()
_entries: deque = deque(maxlen=int(os.environ.get("HEXAPOD_COMMAND_JOURNAL_MAX", "500")))
_heartbeats: dict[str, Any] = {"count": 0, "last_ts": None, "by_controller": {}}
_seq = 0
_file_failed = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _controller_map() -> dict[str, str]:
    """Optional ``{"192.168.4.23": "lukas-laptop"}`` from the environment."""
    raw = os.environ.get("HEXAPOD_CONTROLLER_MAP", "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def _clean_label(value: str) -> str:
    keep = [c for c in value.strip()[:40] if c.isalnum() or c in "-_. "]
    return "".join(keep).strip()


def identify_controller(peer: str, headers: Any = None) -> dict[str, str]:
    """Attribute a request to a controller.

    Precedence: an explicit header, then a configured peer map, then a
    user-agent hint, then the bare address. ``how`` records which of those
    answered, so a label is never mistaken for stronger evidence than it is.
    """
    header_value = ""
    agent = ""
    if headers is not None:
        try:
            header_value = (headers.get("X-Hexapod-Controller") or "").strip()
            agent = (headers.get("User-Agent") or "").strip()
        except Exception:
            header_value = agent = ""

    if header_value:
        label = _clean_label(header_value)
        if label:
            return {"controller": label, "how": "header", "peer": peer, "agent": agent[:120]}

    mapped = _controller_map().get(peer or "")
    if mapped:
        return {"controller": _clean_label(mapped) or "unknown", "how": "peer_map",
                "peer": peer, "agent": agent[:120]}

    lowered = agent.lower()
    for needle, label in (
        ("hexapod-lab", "robotlab"),
        ("robot-lab", "robotlab"),
        ("hexapod-web", "mac-hub"),
        ("python-urllib", "script"),
        ("curl", "script"),
    ):
        if needle in lowered:
            return {"controller": label, "how": "user_agent", "peer": peer,
                    "agent": agent[:120]}
    if lowered.startswith("mozilla"):
        return {"controller": f"browser@{peer or 'unknown'}", "how": "user_agent",
                "peer": peer, "agent": agent[:120]}

    return {"controller": f"unknown@{peer or 'unknown'}", "how": "peer_only",
            "peer": peer, "agent": agent[:120]}


def _shrink(body: Any) -> Any:
    if body in (None, "", {}, []):
        return None
    if isinstance(body, (dict, list)):
        text = json.dumps(body, sort_keys=True)
        if len(text) <= MAX_BODY_CHARS:
            return body
        return {"_truncated": True, "preview": text[:MAX_BODY_CHARS]}
    return str(body)[:MAX_BODY_CHARS]


def _append_file(entry: dict[str, Any]) -> None:
    global _file_failed
    if _file_failed:
        return
    try:
        directory = Path(os.environ.get("HEXAPOD_LOG_DIR", str(DEFAULT_LOG_DIR)))
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "commands.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except Exception:
        # Never let journalling break a control path; the ring still serves
        # /api/commands and one failure disables only the file mirror.
        _file_failed = True


def record(method: str, path: str, *, body: Any = None, peer: str = "",
           headers: Any = None, code: int | None = None) -> dict[str, Any] | None:
    """Journal one command. Returns the entry, or None if it was a heartbeat."""
    global _seq
    base = path.split("?", 1)[0]
    who = identify_controller(peer, headers)
    if base in HEARTBEAT_PATHS:
        with _lock:
            _heartbeats["count"] += 1
            _heartbeats["last_ts"] = _now()
            counts = _heartbeats["by_controller"]
            counts[who["controller"]] = counts.get(who["controller"], 0) + 1
        return None
    with _lock:
        _seq += 1
        entry = {
            "seq": _seq,
            "ts": _now(),
            "mono": round(time.monotonic(), 3),
            "method": method,
            "path": base,
            "query": path.split("?", 1)[1] if "?" in path else "",
            "controller": who["controller"],
            "attributed_by": who["how"],
            "peer": who["peer"],
            "agent": who["agent"],
            "body": _shrink(body),
            "code": code,
        }
        _entries.append(entry)
    _append_file(entry)
    return entry


def set_result(seq: int, code: int) -> None:
    """Fill in the response code once the handler has produced one."""
    with _lock:
        for entry in reversed(_entries):
            if entry["seq"] == seq:
                entry["code"] = code
                return


def recent(limit: int = 50, since: int = 0,
           controller: str | None = None) -> dict[str, Any]:
    with _lock:
        items: Iterable[dict[str, Any]] = list(_entries)
        heartbeats = json.loads(json.dumps(_heartbeats))
        total = _seq
    if since:
        items = [e for e in items if e["seq"] > since]
    if controller:
        items = [e for e in items if e["controller"] == controller]
    items = list(items)[-max(1, min(int(limit or 50), 500)):]
    controllers: dict[str, int] = {}
    for entry in items:
        controllers[entry["controller"]] = controllers.get(entry["controller"], 0) + 1
    return {
        "ok": True,
        "total_recorded": total,
        "returned": len(items),
        "ring_capacity": _entries.maxlen,
        "controllers": controllers,
        "drive_heartbeats": heartbeats,
        "commands": items,
    }


def reset() -> None:
    """Test hook."""
    global _seq, _file_failed
    with _lock:
        _entries.clear()
        _seq = 0
        _heartbeats.update({"count": 0, "last_ts": None, "by_controller": {}})
        _file_failed = False
