"""Pure fail-closed camera admission guard for hardware experiment wrappers."""
from __future__ import annotations

import math
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
        def finite(value) -> bool:
            return (isinstance(value, (int, float))
                    and not isinstance(value, bool) and math.isfinite(value))

        if (not finite(self.max_state_age_s) or self.max_state_age_s <= 0
                or not finite(self.minimum_coverage)
                or not 0 < self.minimum_coverage <= 1 or not finite(now_unix)):
            return self.reject("camera freshness or coverage bounds are invalid")
        performance = state.get("performance") or {}
        if not isinstance(performance, dict):
            return self.reject("camera performance metadata is invalid")
        generated = state.get("generated_at_unix_s")
        if generated is not None and (
                not finite(generated) or generated - now_unix > 0.25):
            return self.reject("camera generation timestamp is invalid or in the future")
        # A fresh wrapper document must not hide a frozen source frame.
        timestamp = performance.get("frame_sequence")
        if timestamp is None:
            timestamp = generated
        if not finite(timestamp):
            return self.reject("camera timestamp is missing")
        if self.last_timestamp is not None and timestamp <= self.last_timestamp:
            return self.reject("camera timestamp did not advance")

        age_s = state.get("state_age_s")
        if age_s is None and generated is not None:
            age_s = now_unix - generated
        if (not finite(age_s) or age_s < -0.25
                or age_s > self.max_state_age_s):
            return self.reject(
                f"camera state stale: {age_s!r}s exceeds "
                f"{self.max_state_age_s:g}s"
            )

        visible = state.get("visible_tag_ids")
        if visible is None:
            coverage = state.get("coverage") or {}
            if not isinstance(coverage, dict):
                return self.reject("camera coverage metadata is invalid")
            visible = coverage.get("visible_tag_ids")
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
