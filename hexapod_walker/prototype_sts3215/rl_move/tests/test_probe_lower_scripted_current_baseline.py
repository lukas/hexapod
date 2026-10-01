"""Mechanics-only smoke test for probe_lower_scripted_current_baseline.py
(walkcurr system-ID baseline, 2026-10-01): env construction + a short
open-loop replay must not crash and must report a physically sane,
per-joint-shaped trip-current reading using the SAME signal
(`over_current_reading`) the SafetyLayer trips on -- not a rollout-
ranking bank, no pass/fail on gait quality.
"""
import numpy as np

from hexapod_core.joint_frame import JOINT_NAMES
from rl_move.sim.probe_lower_scripted_current_baseline import (
    TRIP_A,
    replay_open_loop_trip_trace,
)


def test_short_replay_reports_per_joint_bounded_trip_current():
    row = replay_open_loop_trip_trace(depth_mm=25.0, seed=0,
                                      episode_seconds=1.5)
    assert row["steps"] > 0
    pj = row["per_joint_max_a"]
    assert len(pj) == len(JOINT_NAMES) == 18
    assert all(np.isfinite(v) for v in pj)
    assert all(0.0 <= v <= 3.0 + 1e-6 for v in pj)  # torque-proxy hard cap
    dwell = row["per_joint_rail_dwell_frac"]
    assert len(dwell) == 18
    assert all(0.0 <= f <= 1.0 for f in dwell)
    assert row["worst_joint"] in JOINT_NAMES
    assert row["worst_joint_max_a"] == max(pj)
    assert row["any_joint_at_rail"] == (max(pj) >= TRIP_A)


def test_trip_threshold_matches_lowerrole_launch_overrides():
    # 2026-10-01 lineage pin (cw-stance50hz-rlonly-lowerrole-scratch-
    # sac-{s0,s1}-drramp-acq1): safety.max_current_a=2.9, inherited
    # verbatim from probe_lower_achievability.LAUNCH_OVERRIDES so this
    # module can never silently drift off the lineage it diagnoses.
    assert TRIP_A == 2.9
