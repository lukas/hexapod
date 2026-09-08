#!/usr/bin/env python3
"""Compatibility CLI for the extracted ``hexapod-tracker`` package."""

from pathlib import Path
import sys


_TRACKER_SRC = Path(__file__).resolve().parents[1] / "hexapod-tracker" / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from hexapod_tracker.track import *  # noqa: E402,F403
from hexapod_tracker.track import (  # noqa: E402
    _camera_order_after,
    _parse_camera_cycle,
    _resize_for_processing,
    _safe_pose_assessment,
    main,
)


if __name__ == "__main__":
    raise SystemExit(main())
