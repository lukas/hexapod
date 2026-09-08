#!/usr/bin/env python3
"""Compatibility entry point for the extracted ``hexapod-tracker`` package."""


from hexapod_tracker.camera_server import *
from hexapod_tracker.camera_server import main


if __name__ == "__main__":
    main()
