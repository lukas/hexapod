"""Two ways to call the Claude CLI: a restricted one-shot and a tool-using build."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CliResult:
    ok: bool
    output: Optional[Dict[str, Any]]
    cost_usd: float
    error: str
    raw_tail: str


def _parse(raw: str) -> CliResult:
    text = raw.strip()
    start = text.find("{")
    if start < 0:
        return CliResult(False, None, 0.0, "no JSON in CLI output", text[-800:])
    try:
        doc = json.loads(text[start:])
    except ValueError as exc:
        return CliResult(False, None, 0.0, f"bad JSON: {exc}", text[-800:])
    cost = float(doc.get("total_cost_usd") or 0.0)
    out = doc.get("structured_output")
    if doc.get("is_error") or doc.get("subtype") != "success" or not isinstance(out, dict):
        return CliResult(False, None, cost,
                         str(doc.get("result") or doc.get("subtype") or "CLI error")[:400],
                         text[-800:])
    return CliResult(True, out, cost, "", "")


def _env() -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("CLAUDE_CODE_DISABLE_AUTOUPDATER", "1")
    return env


def oneshot(claude_bin: str, prompt: str, schema: dict, *, model: str, max_usd: float,
            timeout_s: float) -> CliResult:
    """Restricted: no tools, structured JSON back, hard wall clock."""
    cmd = [claude_bin, "-p", "--restricted", "--output-format", "json",
           "--json-schema", json.dumps(schema), "--model", model,
           "--max-budget-usd", f"{max_usd:.2f}", "--no-session-persistence"]
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout_s, env=_env())
    except subprocess.TimeoutExpired:
        return CliResult(False, None, 0.0, f"planner exceeded {timeout_s:.0f} s", "")
    except OSError as exc:
        return CliResult(False, None, 0.0, f"cannot start claude: {exc}", "")
    res = _parse(proc.stdout)
    if not res.ok and not res.error:
        res.error = proc.stderr[-400:]
    return res


def build(claude_bin: str, prompt: str, schema: dict, *, workdir: Path, model: str,
          max_usd: float, timeout_s: float, log_path: Path) -> CliResult:
    """Tool-using, confined to one worktree, with a hard wall clock."""
    cmd = [claude_bin, "-p", "--output-format", "json",
           "--json-schema", json.dumps(schema), "--model", model,
           "--permission-mode", "bypassPermissions", "--add-dir", str(workdir),
           "--max-budget-usd", f"{max_usd:.2f}", "--no-session-persistence",
           "--strict-mcp-config"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout_s, cwd=workdir, env=_env())
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or ""))
        return CliResult(False, None, 0.0, f"builder exceeded {timeout_s:.0f} s", "")
    except OSError as exc:
        return CliResult(False, None, 0.0, f"cannot start claude: {exc}", "")
    log_path.write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    res = _parse(proc.stdout)
    if not res.ok and not res.error:
        res.error = proc.stderr[-400:]
    return res
