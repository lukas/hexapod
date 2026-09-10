#!/usr/bin/env python3
"""Exclusive command lease: one controller owns robot motion at a time.

Several controllers can reach ``:8080`` at once -- Robot Lab's guarded
runner, the Mac hub on :8898, and a browser on whichever laptop is nearby
(see ``command_journal.py``).  The server already refuses a raw ``/cmd J``
while a demo worker is *running*, but nothing protects the window a guarded
experiment holds around its run: between the readiness check and the first
tick, and between ticks of a protocol the worker has not started yet, a
second controller can command a stand or a lower and the guarded run
inherits a pose nobody planned.  That gap is what the L5/L2 belly-rest
plans record as ``foreign_controller_command_observed``.

A lease closes it.  While one is held, motion-commanding POSTs that do not
carry the lease token are refused with HTTP 409 and journalled, so the
refusal is auditable rather than silent.

Deliberately NOT gated, ever:

- the abort path -- ``/api/rl/stop``, ``/api/standup/stop``,
  ``/api/safe_zero`` and the ``/cmd`` limp words.  A safety stop must work
  from any controller, including one that has lost its token.
- bus recovery and every read-only GET.
- releasing a lease (a stuck lease must be clearable), though only the
  holder's token releases it before its TTL.

The lease is advisory-but-enforced state in the web process: it does not
survive a restart, which is the honest behaviour -- a restarted server has
no running guarded protocol to protect.  TTLs bound a crashed holder.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import secrets
import threading
import time
from typing import Any, Callable

# Motion-commanding POSTs.  Mirrors web_drive.BUS_REQUIRED_POST minus the
# abort paths below; kept here so the policy is testable without importing
# the HTTP server.
GATED_POST = frozenset({
    "/api/tft/ready",
    "/api/tft/recover",
    "/api/tft/selftest",
    "/api/wiggle",
    "/api/pose",
    "/api/demo",
    "/api/demo/speed",
    "/api/zero",
    "/api/set_zero",
    "/api/touchdown_zero/straight",
    "/api/untrap",
    "/api/calibrate",
    "/api/rl/find_plant",
    "/api/rl/capture_plant",
    "/api/rl/stand",
    "/api/rl/lower",
    "/api/rl/walk",
    "/api/rl/set_stance",
    "/api/rl/drive/start",
    "/api/rl/drive/cmd",
    "/api/standup",
    "/api/sysid/run",
    "/api/rl/probe_dynamics",
    "/api/setup/scan",
    "/api/setup/assign",
    "/api/setup/wiggle",
    "/cal",
    "/cal_tuck",
})

# Never gated: the remote abort path and bus recovery must answer any
# controller, and the lease endpoints must stay reachable.
ALWAYS_ALLOWED_POST = frozenset({
    "/api/rl/stop",
    "/api/standup/stop",
    "/api/safe_zero",
    "/api/bus/recover",
    "/api/command-lease/acquire",
    "/api/command-lease/release",
})

# ``/cmd`` is a single path carrying an open-ended command language. These
# words limp the robot and are part of the abort path.
CMD_ABORT_WORDS = frozenset({"X", "DISARM", "RELAX", "HOLD", "STOP"})

TOKEN_HEADER = "X-Hexapod-Command-Lease"
OWNER_HEADER = "X-Hexapod-Controller"
BODY_TOKEN_KEYS = ("command_lease", "command_lease_token", "lease_token")

MAX_TTL_S = float(os.environ.get("HEXAPOD_COMMAND_LEASE_MAX_TTL_S", "1800"))
DEFAULT_TTL_S = 600.0

_lock = threading.Lock()
_state: dict[str, Any] | None = None
_refusals: list[dict[str, Any]] = []
MAX_REFUSALS = 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def _public(entry: dict[str, Any], now: float) -> dict[str, Any]:
    """The lease without its secret token."""
    return {
        "held": True,
        "owner": entry["owner"],
        "reason": entry["reason"],
        "acquired_at": entry["acquired_at"],
        "expires_at": entry["expires_at"],
        "ttl_s": entry["ttl_s"],
        "expires_in_s": round(entry["deadline"] - now, 1),
    }


def _expired(entry: dict[str, Any] | None, now: float) -> bool:
    return entry is None or now >= entry["deadline"]


def reset() -> None:
    """Drop all lease state (tests, and a deliberate operator clear)."""
    global _state
    with _lock:
        _state = None
        _refusals.clear()


def acquire(owner: str, *, ttl_s: float = DEFAULT_TTL_S, reason: str = "",
            token: str = "",
            clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Take (or refresh) the lease.

    A held, unexpired lease belonging to someone else refuses. Passing the
    current token refreshes the deadline, so a long run extends its own
    lease without a release/acquire gap.
    """
    global _state
    owner = str(owner or "").strip()[:64]
    if not owner:
        return {"ok": False, "code": "owner_required",
                "error": "acquire needs a non-empty owner"}
    try:
        ttl = float(ttl_s)
    except (TypeError, ValueError):
        return {"ok": False, "code": "bad_ttl", "error": "ttl_s must be a number"}
    if not (0.0 < ttl <= MAX_TTL_S):
        return {"ok": False, "code": "bad_ttl",
                "error": f"ttl_s must be in (0, {MAX_TTL_S}]"}
    now = clock()
    with _lock:
        current = _state
        if not _expired(current, now):
            same_holder = bool(token) and secrets.compare_digest(
                str(token), current["token"])
            if not same_holder:
                return {"ok": False, "code": "command_lease_held",
                        "error": "another controller holds the command lease",
                        "lease": _public(current, now)}
            new_token = current["token"]
            acquired_at = current["acquired_at"]
        else:
            new_token = secrets.token_hex(16)
            acquired_at = _now_iso()
        entry = {
            "token": new_token,
            "owner": owner,
            "reason": str(reason or "")[:300],
            "ttl_s": round(ttl, 1),
            "acquired_at": acquired_at,
            "expires_at": _now_iso(),   # replaced below for readability
            "deadline": now + ttl,
        }
        # expires_at is wall-clock for humans; deadline is the monotonic gate.
        entry["expires_at"] = datetime.fromtimestamp(
            time.time() + ttl, timezone.utc).isoformat(
                timespec="milliseconds").replace("+00:00", "Z")
        _state = entry
        return {"ok": True, "token": new_token, "lease": _public(entry, now)}


def release(token: str, *,
            clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Release the lease. Only the holder's token releases an active lease."""
    global _state
    now = clock()
    with _lock:
        current = _state
        if _expired(current, now):
            _state = None
            return {"ok": True, "released": False, "held": False,
                    "note": "no active lease"}
        if not token or not secrets.compare_digest(str(token), current["token"]):
            return {"ok": False, "code": "command_lease_held",
                    "error": "release needs the holder's token",
                    "lease": _public(current, now)}
        _state = None
        return {"ok": True, "released": True, "held": False}


def state(*, clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Read the lease (never exposes the token)."""
    now = clock()
    with _lock:
        current = _state
        if _expired(current, now):
            return {"ok": True, "held": False,
                    "recent_refusals": list(_refusals[-10:])}
        return {"ok": True, **_public(current, now),
                "recent_refusals": list(_refusals[-10:])}


def token_from_request(headers: Any = None, body: Any = None) -> str:
    """Pull a lease token from the header or a JSON body field."""
    if headers is not None:
        try:
            value = (headers.get(TOKEN_HEADER) or "").strip()
        except Exception:
            value = ""
        if value:
            return value
    if isinstance(body, dict):
        for key in BODY_TOKEN_KEYS:
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def is_gated(method: str, path: str, *, command_line: str = "") -> bool:
    """Would this request be refused while someone else holds the lease?"""
    if str(method).upper() != "POST":
        return False
    base = str(path).split("?", 1)[0]
    if base in ALWAYS_ALLOWED_POST:
        return False
    if base == "/cmd":
        return str(command_line or "").strip().upper() not in CMD_ABORT_WORDS
    if base.startswith("/api/measure/"):
        return False
    return base in GATED_POST


def check(method: str, path: str, *, token: str = "", command_line: str = "",
          controller: str = "", clock: Callable[[], float] = time.monotonic
          ) -> dict[str, Any] | None:
    """``None`` when the request may proceed, else a 409 refusal payload."""
    if not is_gated(method, path, command_line=command_line):
        return None
    now = clock()
    with _lock:
        current = _state
        if _expired(current, now):
            return None
        if token and secrets.compare_digest(str(token), current["token"]):
            return None
        refusal = {
            "ts": _now_iso(),
            "method": str(method).upper(),
            "path": str(path).split("?", 1)[0],
            "controller": str(controller or "")[:64],
            "lease_owner": current["owner"],
            "had_token": bool(token),
        }
        _refusals.append(refusal)
        del _refusals[:-MAX_REFUSALS]
        payload = {
            "ok": False,
            "code": "command_lease_held",
            "error": (f"{current['owner']} holds the exclusive command lease; "
                      "motion commands from another controller are refused. "
                      "The abort path (/api/rl/stop, /api/safe_zero, /cmd X) "
                      "stays open."),
            "lease": _public(current, now),
            "refused": refusal,
        }
    return payload
