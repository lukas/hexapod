"""LEGACY NAME — canonical module is ``hexapod_core.sim_gait_compat``
(moved 2026-08-29). Stub for historical bare imports (test banks, probes);
new code imports ``hexapod_core.sim_gait_compat``."""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from hexapod_core.sim_gait_compat import *  # noqa: E402,F401,F403
