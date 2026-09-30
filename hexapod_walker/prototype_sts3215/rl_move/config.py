"""Load ``config.yaml`` with light defaults."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = _HERE / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG
    text = p.read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text) or {}
    except ImportError:
        # Minimal fallback if PyYAML missing on the board.
        data = _tiny_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {p}")
    # HEXAPOD_CONTROL_HZ override (2026-08-25, leg-sacrifice-fingerprint
    # DIG-IN): mirrors the existing HEXAPOD_MODEL_SOURCE pattern
    # (servo_model.resolve_model_source) for the SAME reason. config.yaml's
    # `control.hz` default flipped 25 -> 100 on 2026-08-24
    # (fb_20260824T174619_c49b7e); the now-retired pre-v2 reward-pricing
    # bank called this function with NO
    # override anywhere, so every fixed-magnitude threshold in that bank
    # (charges/bonuses accumulate per TICK, and 100 Hz banks 4x more ticks
    # per wall-clock second than the 25 Hz dynamics they were measured
    # against) went stale silently: a full-bank run found **54 newly-failing
    # tests** (was 1 known-red as of 08-22) the same day this override was
    # added. Unset (the default everywhere except the pinned test suite) is
    # a no-op — bit-exact, whatever config.yaml says. Only
    # `tests/conftest.py` sets this, exactly like `HEXAPOD_MODEL_SOURCE`.
    hz = os.environ.get("HEXAPOD_CONTROL_HZ", "").strip()
    if hz:
        data.setdefault("control", {})["hz"] = float(hz) if "." in hz \
            else int(hz)
    # HEXAPOD_SAFETY_MAX_DELTA_Q_DEG override (2026-09-30, primitive-family
    # calibrated-suite regression DIG-IN): mirrors the SAME HEXAPOD_
    # MODEL_SOURCE/HEXAPOD_CONTROL_HZ pattern for the SAME class of bug.
    # config.yaml's `safety.max_delta_q_deg` default flipped 0.375 -> 1.76
    # on 2026-09-27 (commit 867835836, "we should open it up for faster
    # movement" -- a real hardware-bus-speed change, correct for the mesh
    # family it targets). The calibrated PRIMITIVE-family test suite
    # (`tests/conftest.py`) builds fresh envs with `load_config()` and no
    # trained-artifact stamp to pin against, so it silently inherited the
    # new, much larger per-tick rate cap; root-caused via `git bisect` +
    # cross-model-family replay to a concrete mechanism (not conjecture):
    # a ZERO-action tick is a rate-limited move TOWARD a fixed commanded
    # pose, and the wider cap now snaps the PRIMITIVE model's start pose
    # there fast enough to trip its tilt/fall detector inside the opening
    # 1s zero-command hold -- 100% reproducible
    # (`test_phase_contact_reward_pays_agreement` terminates at tick 28 of
    # 300 with `HEXAPOD_MODEL_SOURCE=primitive`, never with mesh/default).
    # Unset (everywhere except the pinned test suite) is a no-op -- bit-
    # exact, whatever config.yaml says; this does not touch the new mesh/
    # hardware default. Only `tests/conftest.py` sets this.
    max_dq = os.environ.get("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", "").strip()
    if max_dq:
        data.setdefault("safety", {})["max_delta_q_deg"] = float(max_dq)
    return data


def _tiny_yaml(text: str) -> dict[str, Any]:
    """Parse our indented key: value config without PyYAML."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, rest = line.strip().partition(":")
        key = key.strip()
        val = rest.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce(val)
    return root


def _coerce(s: str) -> Any:
    if s in ("null", "Null", "NULL", "~"):
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        return s.strip("'\"")


def cfg_get(cfg: dict, *keys, default=None):
    cur: Any = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
