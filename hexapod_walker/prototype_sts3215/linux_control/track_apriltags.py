#!/usr/bin/env python3
"""Compatibility CLI for the extracted ``hexapod-tracker`` package."""


from hexapod_tracker.track import *
from hexapod_tracker.track import (
    _camera_order_after,
    _parse_camera_cycle,
    _resize_for_processing,
    _safe_pose_assessment,
    main,
)


if __name__ == "__main__":
    raise SystemExit(main())
