"""Bound administrative work after a successful, sealed hardware handoff."""

import hashlib
from pathlib import Path
import re
from typing import Any, Dict, Optional


class SealedHandoffComplete(RuntimeError):
    """Raised by the supervisor only after it has reaped the entire agent group."""

    def __init__(self, receipt: Dict[str, Any]):
        super().__init__("Completed hardware handoff exceeded its exit grace")
        self.receipt = receipt


class HandoffExitWatch:
    def __init__(self, experiment_id: str, grace_seconds: float):
        self.experiment_id = experiment_id
        self.grace_seconds = max(1.0, grace_seconds)
        self.first_seen: Optional[float] = None
        self.digest: Optional[str] = None

    def observe(self, experiment: Dict[str, Any], now: float, *, blocked: bool = False) -> Optional[Dict[str, Any]]:
        # Failed/cancelled runs must retain their agent's actual stop disposition.
        digest = experiment.get("evidence_manifest_sha256")
        if (blocked or experiment.get("id") != self.experiment_id
                or experiment.get("status") != "succeeded"
                or not experiment.get("evidence_sealed_at")
                or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            self.first_seen = None
            self.digest = None
            return None
        if self.first_seen is None or digest != self.digest:
            self.first_seen, self.digest = now, digest
        if now - self.first_seen < self.grace_seconds:
            return None
        return {
            "experiment_id": self.experiment_id,
            "experiment_status": "succeeded",
            "evidence_manifest_sha256": digest,
            "evidence_sealed_at": experiment["evidence_sealed_at"],
            "exit_grace_seconds": self.grace_seconds,
        }


def verify_handoff_manifest(receipt: Dict[str, Any], data_dir: Path) -> None:
    path = data_dir / "experiments" / receipt["experiment_id"] / "manifest.json"
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Completed handoff manifest is missing or is a symlink")
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["evidence_manifest_sha256"]:
        raise RuntimeError("Completed handoff manifest does not match its sealed digest")
