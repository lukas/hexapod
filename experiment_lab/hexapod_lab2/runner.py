"""Run one protocol through the existing sysid runner and keep what it wrote."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Settings


@dataclass
class RunResult:
    status: str                 # ok | failed | timeout
    exit_code: Optional[int]
    run_dir: Optional[Path]
    summary: Optional[dict]
    log_tail: str
    motion_s: float


def protocol_path(settings: Settings, name: str) -> Path:
    name = name.removesuffix(".json")
    return settings.protocols_dir / f"{name}.json"


def protocol_exists(settings: Settings, name: str) -> bool:
    return protocol_path(settings, name).is_file()


def _is_whole_body(doc: dict) -> bool:
    # Same test run_hw.py uses to demand --force.
    return any(isinstance(s, dict) and s.get("kind") in ("traj", "rel_traj")
               for s in doc.get("segments") or [])


def protocol_is_whole_body(settings: Settings, name: str) -> bool:
    try:
        return _is_whole_body(json.loads(protocol_path(settings, name).read_text()))
    except (OSError, ValueError):
        return False


def list_protocols(settings: Settings) -> list[dict]:
    out = []
    for p in sorted(settings.protocols_dir.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        out.append({
            "name": p.stem,
            "description": " ".join(str(doc.get("description") or "").split())[:240],
            "whole_body": _is_whole_body(doc),
        })
    return out


def command(settings: Settings, protocol: str, *, force: bool = False) -> list[str]:
    protocol = protocol.removesuffix(".json")
    cmd = [str(settings.python), "-m", "sysid.run_hw",
           "--protocol", f"sysid/protocols/{protocol}.json",
           "--url", settings.robot_url, "--go",
           "--capture-vision", "--capture-frames",
           "--vision-url", settings.vision_url,
           "--vision-frame-url", settings.vision_frame_url]
    if settings.allow_force and (force or protocol_is_whole_body(settings, protocol)):
        cmd.append("--force")
    return cmd


def sync_checkout(settings: Settings) -> str:
    """Fast-forward the runner checkout to origin/main; never rewrite history."""
    try:
        subprocess.run(["git", "-C", str(settings.checkout), "pull", "--ff-only", "-q"],
                       check=True, capture_output=True, text=True, timeout=120)
        return "synced"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return f"pull failed: {getattr(exc, 'stderr', '') or exc}".strip()[:300]


def run_protocol(settings: Settings, protocol: str, run_id: str, *, force: bool = False,
                 log_path: Optional[Path] = None) -> RunResult:
    datasets = settings.prototype_dir / "sysid" / "datasets"
    before = {p.name for p in datasets.glob("*")} if datasets.exists() else set()
    cmd = command(settings, protocol, force=force)
    started = time.monotonic()
    log_path = log_path or (settings.runs_dir / run_id / "runner.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status, code = "ok", None
    with log_path.open("w") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        try:
            proc = subprocess.run(cmd, cwd=settings.prototype_dir, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=settings.run_timeout_s)
            code = proc.returncode
            status = "ok" if code == 0 else "failed"
        except subprocess.TimeoutExpired:
            status, code = "timeout", None
            log.write(f"\n[lab2] killed after {settings.run_timeout_s:.0f} s\n")
    motion_s = time.monotonic() - started
    # Post-run, well inside its minute: keep the runner's dataset next to the log.
    run_dir = log_path.parent
    new_dirs = sorted((p for p in datasets.glob("*") if p.name not in before and p.is_dir()),
                      key=lambda p: p.stat().st_mtime) if datasets.exists() else []
    summary = None
    for src in new_dirs:
        dest = run_dir / src.name
        if not dest.exists():
            shutil.copytree(src, dest)
        rs = dest / "runner_summary.json"
        if rs.exists():
            try:
                summary = json.loads(rs.read_text())
            except ValueError:
                summary = {"unparseable": rs.name}
    tail = log_path.read_text(errors="replace")[-4000:]
    return RunResult(status=status, exit_code=code, run_dir=run_dir, summary=summary,
                     log_tail=tail, motion_s=motion_s)
