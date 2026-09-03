"""Compatibility imports for the extracted ``hexapod-tracker`` package."""

from pathlib import Path
import sys


_TRACKER_SRC = Path(__file__).resolve().parents[1] / "hexapod-tracker" / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from hexapod_tracker.apriltag_vision import *  # noqa: E402,F403
from hexapod_tracker.apriltag_vision import (  # noqa: E402
    _TagPoseSolution,
    _scale_tag_corners,
)
