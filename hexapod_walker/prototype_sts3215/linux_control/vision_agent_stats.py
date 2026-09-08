"""Vision-agent attempt log and token accounting.

The vision agent records each attempt the same way every other lane does: one
``metadata.json`` under ``<data-dir>/codex-runs/<job>/attempt-<n>/`` carrying
``provider``, ``kind``, ``model``, ``returncode`` and a ``usage`` object.  This
module reads those files and rolls up only the vision role, so the numbers on
the vision page reconcile with the whole-lab totals instead of being a second,
divergent tally.

``experiment_lab/hexapod_lab/lab_stats.py`` is the source of truth for the
bucket shape; ``_parse``, ``_blank`` and ``_add`` below are deliberately
identical to it and ``test_vision_agent_stats.py`` asserts the two agree on the
same fixture.  The duplication is intentional: the vision service runs from the
tracker virtualenv and must not import the lab package.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

#: Role recorded in ``metadata.json`` by the vision lane.
VISION_ROLE = "vision"

CACHE_TTL_SECONDS = 20.0
MAX_ATTEMPTS_SCANNED = 5000
DEFAULT_LOG_LIMIT = 50


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


def _cache_tokens(bucket: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Accumulate the cache counters the lab rollup does not break out.

    Prompt caching dominates this lane's token volume -- the vision agent
    re-reads the same capture configuration on every attempt -- so a page that
    only showed input/output tokens would understate what is being sent.
    """
    usage = meta.get("usage") or {}
    for key in ("cache_read_tokens", "cache_write_tokens"):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            bucket[key] = bucket.get(key, 0) + value


def _attempt_entry(path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
    usage = meta.get("usage") or {}
    started = _parse(meta.get("started_at"))
    finished = _parse(meta.get("finished_at"))
    return {
        "job_id": meta.get("job_id"),
        "attempt": meta.get("attempt"),
        "provider": meta.get("provider") or "codex",
        "model": meta.get("model") or "unknown",
        "returncode": meta.get("returncode"),
        "ok": meta.get("returncode") in (0, None),
        "started_at": started.isoformat() if started else None,
        "finished_at": finished.isoformat() if finished else None,
        "duration_ms": usage.get("duration_ms"),
        "turns": usage.get("turns"),
        "cost_usd": usage.get("cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_tokens"),
        "cache_write_tokens": usage.get("cache_write_tokens"),
        "summary": meta.get("summary") or meta.get("error") or "",
        "run_dir": str(path.parent),
    }


def scan_vision_attempts(
        data_dir: Path,
        *,
        role: str = VISION_ROLE,
        limit: int = DEFAULT_LOG_LIMIT,
) -> Dict[str, Any]:
    """Roll up every recorded attempt for one lane role.

    Returns totals, a 24-hour window, a per-model split and the most recent
    attempts newest-first.  Missing or malformed metadata is skipped rather
    than raised: a half-written attempt directory must not take the page down.
    """
    root = Path(data_dir) / "codex-runs"
    totals = _blank()
    last_24h = _blank()
    by_model: Dict[str, Dict[str, Any]] = {}
    entries: List[Dict[str, Any]] = []
    day_cutoff = datetime.now(timezone.utc) - timedelta(days=1)
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
            if str(meta.get("kind") or "") != role:
                continue
            scanned += 1
            _add(totals, meta)
            _cache_tokens(totals, meta)
            _add(by_model.setdefault(str(meta.get("model") or "unknown"),
                                     _blank()), meta)
            finished = (_parse(meta.get("finished_at"))
                        or _parse(meta.get("started_at")))
            if finished and finished >= day_cutoff:
                _add(last_24h, meta)
                _cache_tokens(last_24h, meta)
            entries.append(_attempt_entry(path, meta))
    entries.sort(key=lambda item: item.get("started_at") or "", reverse=True)
    return {
        "role": role,
        "scanned": scanned,
        "totals": totals,
        "last_24h": last_24h,
        "by_model": by_model,
        "attempts": entries[:max(0, int(limit))],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class VisionAgentStats:
    """Cached view of the vision lane's spend, safe to call per request.

    Attempt metadata is immutable once written, so a short TTL keeps a page
    that polls from re-walking the run tree on every refresh.
    """

    def __init__(self, data_dir: Path,
                 *, ttl_seconds: float = CACHE_TTL_SECONDS) -> None:
        self.data_dir = Path(data_dir)
        self.ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_at = 0.0
        self._cache_limit = 0

    def snapshot(self, *, limit: int = DEFAULT_LOG_LIMIT,
                 force: bool = False) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            fresh = (self._cache is not None
                     and now - self._cache_at < self.ttl_seconds)
            if fresh and not force and self._cache_limit >= limit:
                cached = dict(self._cache or {})
                cached["attempts"] = list(cached.get("attempts", []))[:limit]
                return cached
        # Scan outside the lock: a cold walk of the run tree is slow enough
        # that holding it would serialise every concurrent page refresh.
        scanned = scan_vision_attempts(
            self.data_dir, limit=max(limit, DEFAULT_LOG_LIMIT))
        with self._lock:
            self._cache = scanned
            self._cache_at = time.monotonic()
            self._cache_limit = max(limit, DEFAULT_LOG_LIMIT)
        result = dict(scanned)
        result["attempts"] = list(scanned.get("attempts", []))[:limit]
        return result
