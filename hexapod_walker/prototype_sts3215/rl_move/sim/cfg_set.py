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


_parse_cfg_set = parse_cfg_set
