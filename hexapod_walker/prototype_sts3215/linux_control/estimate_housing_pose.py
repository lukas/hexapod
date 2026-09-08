#!/usr/bin/env python3
"""Compatibility CLI for the extracted ``hexapod-tracker`` package."""


from hexapod_tracker.estimate_housing_pose import *
from hexapod_tracker.estimate_housing_pose import main


if __name__ == "__main__":
    raise SystemExit(main())
