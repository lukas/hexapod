"""--cfg-set override parsing, shared by the trainers and every sim tool."""
from __future__ import annotations

import json


def parse_cfg_set(specs: list[str] | None) -> dict[str, float]:
    """Parse --cfg-set 'reward.k_current_max=0.05' overrides.

    Values parse as float; '[..]' parses as a JSON list (08-10:
    goal.rise_height_mm is a [lo, hi] range); anything else stays a
    string (cycle 27: goal.walk_park_bank is an npz PATH). Numeric
    behavior unchanged."""
    out = {}
    for part in (specs or []):
        k, _, v = part.partition("=")
        v = v.strip()
        if v.startswith("["):
            out[k.strip()] = json.loads(v)
            continue
        try:
            out[k.strip()] = float(v)
        except ValueError:
            out[k.strip()] = v
    return out


def cfg_range(v, name: str = "") -> list[float]:
    """Coerce a [lo, hi] cfg value; raise on anything ambiguous.

    Accepts a 2-element list/tuple of numbers, or a 'lo,hi' /
    '[lo,hi]' STRING — the rendering a --cfg-set stack degrades to
    when a list value loses its brackets (2026-09-25: a corrupted
    goal.rise_height_mm=79,87 silently became float('79,87'[0]) → a
    bogus ~7 mm rise target and a wrong CANARY verdict). Silent
    mis-parse is never acceptable here: garbage raises."""
    if isinstance(v, str):
        parts = [p.strip() for p in
                 v.strip().lstrip("[").rstrip("]").split(",") if p.strip()]
        if len(parts) != 2:
            raise ValueError(f"cfg range {name}={v!r}: expected 'lo,hi'")
        return [float(parts[0]), float(parts[1])]
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return [float(v[0]), float(v[1])]
    raise ValueError(f"cfg range {name}={v!r}: expected [lo, hi]")


_parse_cfg_set = parse_cfg_set
