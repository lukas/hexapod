"""Process-wide quarantine for a bus whose async reader did not join.

This is host ownership state, not a statement about physical torque. Clearing
it requires that every retained reader has actually stopped and been joined.
"""
from __future__ import annotations

import threading


class AsyncSamplerCleanupError(RuntimeError):
    """The async reader may still own the serial link; do not use that bus."""


_LOCK = threading.RLock()
_QUARANTINES: dict[int, dict] = {}


def quarantine_bus(bus, sampler, detail: str) -> None:
    with _LOCK:
        entry = _QUARANTINES.setdefault(id(bus), {"bus": bus, "readers": {}})
        entry["readers"][id(sampler)] = (sampler, str(detail))


def bus_quarantine_status(bus) -> dict:
    with _LOCK:
        entry = _QUARANTINES.get(id(bus))
        if entry is None or entry["bus"] is not bus:
            return {"bus_quarantined": False, "bus_available": True}
        readers = list(entry["readers"].values())
        return {
            "bus_quarantined": True,
            "bus_available": False,
            "error": "async reader cleanup incomplete; serial bus unavailable",
            "cleanup_details": [detail for _sampler, detail in readers],
            "reader_alive": any(
                bool(getattr(sampler, "_thread", None)
                     and sampler._thread.is_alive()) for sampler, _ in readers),
            "torque_state": "unverified",
        }


def require_bus_available(bus) -> None:
    status = bus_quarantine_status(bus)
    if status["bus_quarantined"]:
        raise AsyncSamplerCleanupError(status["error"])


def clear_bus_quarantine(bus, sampler) -> None:
    """Clear only this reader, after its stop/join has succeeded."""
    with _LOCK:
        thread = getattr(sampler, "_thread", None)
        if thread is not None:
            if thread.is_alive():
                raise AsyncSamplerCleanupError("cannot clear a live async reader")
            thread.join(timeout=0)
        entry = _QUARANTINES.get(id(bus))
        if entry is None or entry["bus"] is not bus:
            return
        entry["readers"].pop(id(sampler), None)
        if not entry["readers"]:
            del _QUARANTINES[id(bus)]


def recover_bus_quarantine(bus) -> dict:
    """Nonblocking recovery: join already-exited readers, never wait on live ones."""
    with _LOCK:
        entry = _QUARANTINES.get(id(bus))
        readers = (list(entry["readers"].values())
                   if entry is not None and entry["bus"] is bus else [])
    for sampler, _detail in readers:
        thread = getattr(sampler, "_thread", None)
        if thread is not None and thread.is_alive():
            continue
        # The worker-local registry is independent; thread death alone never
        # changes this process-wide quarantine without an explicit join.
        if thread is not None:
            thread.join(timeout=0)
        clear_bus_quarantine(bus, sampler)
    return bus_quarantine_status(bus)
