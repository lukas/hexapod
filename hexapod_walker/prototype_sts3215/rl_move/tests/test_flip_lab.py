from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

mujoco = pytest.importorskip("mujoco")

from rl_move.sim.flip_lab import (  # noqa: E402
    FlipCandidate,
    FlipLab,
    RockCandidate,
    candidate_from_unit,
    opposite_side,
    rock_candidate_from_unit,
    side_leg_sets,
)


def test_side_leg_sets_are_complements():
    assert side_leg_sets("left") == ((0, 1, 2), (3, 4, 5))
    assert side_leg_sets("right") == ((3, 4, 5), (0, 1, 2))
    with pytest.raises(ValueError):
        side_leg_sets("up")


def test_candidate_from_unit_clips_to_bounds():
    c = candidate_from_unit([-1.0] * 10, side="right")
    assert c.side == "right"
    assert c.tuck_hip_deg == -80.0
    assert c.kick_knee_deg == -20.0
    assert c.windup_s == 0.7
    c2 = candidate_from_unit([2.0] * 10, assist_torque_nm=3.0)
    assert c2.tuck_hip_deg == -25.0
    assert c2.kick_knee_deg == 75.0
    assert c2.assist_torque_nm == 3.0


def test_rock_candidate_from_unit_clips_and_rounds_cycles():
    c = rock_candidate_from_unit([2.0] * 12, side="right")
    assert c.side == "right"
    assert c.tuck_knee_deg == 150.0
    assert c.raise_s == 2.5
    assert c.cycles == 8
    assert opposite_side("right") == "left"


def test_flip_lab_evaluates_short_primitive_rollout():
    lab = FlipLab(source="primitive", servo_params="", seed=0)
    metrics = lab.evaluate_candidate(
        FlipCandidate(windup_s=0.02, kick_s=0.02, coast_s=0.02, hold_s=0.02),
        settle_s=0.0,
        total_s=0.08)
    assert math.isfinite(metrics.score)
    assert -1.0 <= metrics.min_up_z <= 1.0
    assert metrics.seconds == 0.08
    assert metrics.realistic
    assert not metrics.realistic_flipped
    assert metrics.realism_violations == []


def test_flip_lab_evaluates_short_rock_rollout():
    lab = FlipLab(source="primitive", servo_params="", seed=0)
    metrics = lab.evaluate_rock_candidate(
        RockCandidate(raise_s=0.0, half_s=0.02, cycles=1, hold_s=0.02),
        settle_s=0.0,
        total_s=0.08)
    assert math.isfinite(metrics.score)
    assert metrics.roll_gain_deg >= 0.0


def test_rock_start_pose_can_start_from_side_program():
    cand = RockCandidate(
        side="left",
        tuck_yaw_deg=8.0,
        tuck_hip_deg=-70.0,
        tuck_knee_deg=140.0,
        lever_yaw_deg=-12.0,
        lever_hip_deg=18.0,
        lever_knee_deg=58.0,
    )
    plant_lab = FlipLab(source="primitive", servo_params="", seed=0,
                        start_pose="plant")
    rock_lab = FlipLab(source="primitive", servo_params="", seed=0,
                       start_pose="rock")
    assert np.allclose(plant_lab.rock_start_pose(cand), plant_lab.plant_q)
    assert not np.allclose(rock_lab.rock_start_pose(cand), rock_lab.plant_q)


def test_side_z_tracks_signed_roll_direction():
    lab = FlipLab(source="primitive", servo_params="", seed=0)
    lab._place(lab.plant_q, roll_deg=90.0)
    assert lab._side_z() > 0.9
    lab._place(lab.plant_q, roll_deg=-90.0)
    assert lab._side_z() < -0.9


def test_impulse_sweep_reports_ordered_rows():
    lab = FlipLab(source="primitive", servo_params="", seed=1)
    rows = lab.impulse_sweep([0.0, 0.5], total_s=0.05, pulse_s=0.03,
                             settle_s=0.0)
    assert [r["torque_nm"] for r in rows] == [0.0, 0.5]
    assert all(np.isfinite(r["max_tilt_deg"]) for r in rows)
    assert all("within_limits" in r for r in rows)
