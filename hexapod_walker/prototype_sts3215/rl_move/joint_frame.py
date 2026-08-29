"""LEGACY NAME — canonical module is ``hexapod_core.joint_frame`` (moved
2026-08-29). Stub so existing ``rl_move.joint_frame`` imports (deployed
rl_policy weights metadata helpers, sim bridges, tests) keep resolving to
the ONE canonical copy. New code imports ``hexapod_core.joint_frame``."""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from hexapod_core.joint_frame import *  # noqa: E402,F401,F403
from hexapod_core.joint_frame import _ALIASES, _as_joint_array  # noqa: E402,F401
