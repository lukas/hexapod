"""JSON bench helpers for the web UI: status, wiggle, demos.

Thin dispatcher since the 2026-08-29 component-boundaries split: the route
groups live in ``linux_control/api/`` as mixins and are composed here.
``from api.common import *`` keeps the legacy module surface intact
(REGISTRY_CANDIDATES, AIR_DEMO_NAMES, the _BusQualityTracker family, ...),
so ``import bench_api`` consumers and tests see the same names as before.

Uses the same Feetech bus as ``DriveController`` (shared lock).
"""
from __future__ import annotations

from api.common import *  # noqa: F401,F403
from api.core import CoreApi
from api.demos import DemosApi
from api.zero import ZeroApi
from api.calibrate import CalibrateApi
from api.rl import RlApi
from api.standup import StandupApi
from api.measure import MeasureApi


class BenchAPI(CoreApi, DemosApi, ZeroApi, CalibrateApi, RlApi, StandupApi, MeasureApi):
    """Bench JSON API — the union of the route-group mixins in api/."""
