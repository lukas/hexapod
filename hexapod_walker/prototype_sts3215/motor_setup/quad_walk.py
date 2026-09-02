"""LEGACY NAME — canonical module is ``hexapod_core.quad_walk`` (moved
2026-08-29). Stub for historical bare imports (bench demos, tests); new
code imports ``hexapod_core.quad_walk``."""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from hexapod_core.quad_walk import *  # noqa: E402,F401,F403
