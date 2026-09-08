#!/usr/bin/env python3
"""Compatibility CLI for the extracted ``hexapod-tracker`` package."""


from hexapod_tracker.telemetry_video import *
from hexapod_tracker.telemetry_video import main


if __name__ == "__main__":
    raise SystemExit(main())
