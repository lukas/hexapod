"""Pure fail-closed camera admission guard for hardware experiment wrappers."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class CameraGuard:
    """Validate required-tag coverage, timestamp progress, and freshness."""

    required_tag_ids: frozenset[int]
    minimum_coverage: float = 0.9
    max_state_age_s: float = 1.5
    last_timestamp: float | int | None = None
    accepted_samples: int = 0
    failure: str | None = None
    ready: threading.Event = field(default_factory=threading.Event)

    def reject(self, reason: str) -> tuple[bool, str]:
        if self.failure is None:
            self.failure = reason
        return False, self.failure

    def observe(self, state: dict, *, now_unix: float) -> tuple[bool, str]:
        if self.failure:
            return False, self.failure
        if not isinstance(state, dict):
            return self.reject("camera state is not an object")
        timestamp = state.get("generated_at_unix_s")
        if timestamp is None:
            timestamp = (state.get("performance") or {}).get("frame_sequence")
        if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
            return self.reject("camera timestamp is missing")
        if self.last_timestamp is not None and timestamp <= self.last_timestamp:
            return self.reject("camera timestamp did not advance")

        age_s = state.get("state_age_s")
        if age_s is None and state.get("generated_at_unix_s") is not None:
            age_s = max(0.0, now_unix - float(state["generated_at_unix_s"]))
        if not isinstance(age_s, (int, float)) or age_s > self.max_state_age_s:
            return self.reject(
                f"camera state stale: {age_s!r}s exceeds "
                f"{self.max_state_age_s:g}s"
            )

        visible = state.get("visible_tag_ids")
        if visible is None:
            visible = (state.get("coverage") or {}).get("visible_tag_ids")
        try:
            visible_ids = {int(value) for value in visible}
        except (TypeError, ValueError):
            return self.reject("camera visible_tag_ids are missing or invalid")
        covered = len(self.required_tag_ids & visible_ids)
        coverage = covered / len(self.required_tag_ids) if self.required_tag_ids else 1.0
        if coverage < self.minimum_coverage:
            return self.reject(
                f"camera required-tag coverage {coverage:.3f} below "
                f"{self.minimum_coverage:.3f}"
            )

        self.last_timestamp = timestamp
        self.accepted_samples += 1
        if self.accepted_samples >= 2:
            self.ready.set()
        return True, "ok"
