"""LEGACY NAME — canonical module is ``hexapod_core.dance_script`` (moved
2026-08-29). Stub for historical bare imports (bench_api, web_drive, sim
web_session); new code imports ``hexapod_core.dance_script``."""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from hexapod_core.dance_script import *  # noqa: E402,F401,F403

if __name__ == "__main__":
    from hexapod_core.dance_script import _cli
    _cli()
