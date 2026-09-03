#!/usr/bin/env python3
"""Compatibility CLI for the extracted ``hexapod-tracker`` package."""

from pathlib import Path
import sys


_TRACKER_SRC = Path(__file__).resolve().parents[2] / "hexapod-tracker" / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from hexapod_tracker.gait_motion import *  # noqa: E402,F403
from hexapod_tracker.gait_motion import _best_floor_homography, main  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit(main())
