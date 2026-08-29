"""LEGACY NAME — canonical module is ``hexapod_core.tripod_gait`` (moved
2026-08-29). This stub keeps historical bare ``import tripod_gait`` sites
(test banks, probes, pod pipeline scripts, on-board tools) resolving to
the ONE canonical copy. New code imports ``hexapod_core.tripod_gait``."""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from hexapod_core.tripod_gait import *  # noqa: E402,F401,F403
from hexapod_core.tripod_gait import (  # noqa: E402,F401  (private/importer-used)
    _clip, _leg_ik, _plant_hip_knee_deg,
)
