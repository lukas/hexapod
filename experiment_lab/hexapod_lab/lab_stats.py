"""Whole-lab rollup: what has been run, by which backend, at what cost.

Individual attempts already record their own spend in
``codex-runs/<job>/attempt-<n>/metadata.json``. This aggregates those small
files plus the experiment/job tables into one view, so the question "what is
this costing me?" has an answer that does not require reading transcripts.

The scan is bounded and cached: the metadata files are immutable once an
attempt finishes, so a short TTL keeps a busy dashboard from re-walking the
tree on every request.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

CACHE_TTL_SECONDS = 20.0
MAX_ATTEMPTS_SCANNED = 5000

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None
_cache_at = 0.0


def _parse(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _blank() -> Dict[str, Any]:
    return {"attempts": 0, "cost_usd": 0.0, "input_tokens": 0,
            "output_tokens": 0, "failed": 0}


def _add(bucket: Dict[str, Any], meta: Dict[str, Any]) -> None:
    usage = meta.get("usage") or {}
    bucket["attempts"] += 1
    if meta.get("returncode") not in (0, None):
        bucket["failed"] += 1
    for key, source in (("cost_usd", "cost_usd"),
                        ("input_tokens", "input_tokens"),
                        ("output_tokens", "output_tokens")):
        value = usage.get(source)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bucket[key] += value


def scan_attempts(data_dir: Path) -> Dict[str, Any]:
    """Aggregate every recorded attempt under ``codex-runs``."""
    root = data_dir / "codex-runs"
    totals = _blank()
    by_provider: Dict[str, Dict[str, Any]] = {}
    by_role: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}
    recent: List[Dict[str, Any]] = []
    day_cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    last_24h = _blank()
    scanned = 0
    if root.is_dir():
        paths = sorted(root.glob("*/attempt-*/metadata.json"))
        for path in paths[-MAX_ATTEMPTS_SCANNED:]:
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(meta, dict):
                continue
            scanned += 1
            provider = str(meta.get("provider") or "codex")
            role = str(meta.get("kind") or "unknown")
            model = str(meta.get("model") or "unknown")
            _add(totals, meta)
            _add(by_provider.setdefault(provider, _blank()), meta)
            _add(by_role.setdefault(role, _blank()), meta)
            _add(by_model.setdefault(model, _blank()), meta)
            finished = _parse(meta.get("finished_at")) or _parse(meta.get("started_at"))
            if finished and finished >= day_cutoff:
                _add(last_24h, meta)
            recent.append({
                "job_id": meta.get("job_id"),
                "attempt": meta.get("attempt"),
                "kind": role,
                "provider": provider,
                "model": model,
                "returncode": meta.get("returncode"),
                "started_at": meta.get("started_at"),
                "finished_at": meta.get("finished_at"),
                "experiment_id": meta.get("experiment_id"),
                "usage": meta.get("usage") or {},
            })
    recent.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
    return {
        "totals": totals,
        "last_24h": last_24h,
        "by_provider": by_provider,
        "by_role": by_role,
        "by_model": by_model,
        "recent_attempts": recent[:25],
        "attempts_scanned": scanned,
        "scan_truncated": scanned >= MAX_ATTEMPTS_SCANNED,
    }


def collect(store: Any, settings: Any, *, force: bool = False) -> Dict[str, Any]:
    global _cache, _cache_at
    with _lock:
        fresh = _cache is not None and (time.monotonic() - _cache_at) < CACHE_TTL_SECONDS
        if fresh and not force:
            return _cache

    experiments: Dict[str, int] = {}
    jobs: Dict[str, int] = {}
    try:
        with store.connect() as con:
            for row in con.execute(
                "SELECT status, COUNT(*) AS n FROM experiments GROUP BY status"
            ):
                experiments[str(row["status"])] = int(row["n"])
            for row in con.execute(
                "SELECT kind, status, COUNT(*) AS n FROM codex_jobs "
                "GROUP BY kind, status"
            ):
                jobs[f"{row['kind']}:{row['status']}"] = int(row["n"])
    except Exception:
        # A stats view must never be the reason the dashboard fails to render.
        pass

    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
        "agent": {
            "provider": getattr(settings, "agent_provider", "codex"),
            "label": getattr(settings, "agent_label", "Codex"),
            "model": getattr(settings, "agent_model", ""),
            "effort": getattr(settings, "agent_reasoning_effort", ""),
        },
        "experiments": experiments,
        "experiments_total": sum(experiments.values()),
        "jobs": jobs,
        **scan_attempts(Path(settings.data_dir)),
    }
    with _lock:
        _cache = payload
        _cache_at = time.monotonic()
    return payload


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None
