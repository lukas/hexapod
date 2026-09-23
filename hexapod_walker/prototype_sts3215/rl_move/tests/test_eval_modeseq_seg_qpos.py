"""eval_modeseq.py's --dump-seg-qpos row builder (RESEARCH_RULES
"Tests": fast, mechanics-only, no rollout-ranking).

Root cause this exists: the standwalk track's single-arc Stage-2
milestone passes 12/12 at DR-0 but fails its own-DR half (7/12,
5/12), with falls concentrated in the walk/lower segments even though
each specialist's own isolated per-mode gate is zero-fall at the
identical dr_scale (2026-09-23 ~17:4x entry). The flagged Next step is
a walk/lower analogue of the existing `--dump-rise-qpos` diagnostic:
capture the composed session's real joint/velocity/tilt state at the
walk/lower handoffs and through the randomized walk segment, and
compare it against the exact pose each specialist's own isolated gate
resets from (the same env.reset() call, captured via
`reanchor_to`'s pre-restore snapshot).

This test locks only `seg_state_row` (no checkpoints/MuJoCo): pure
unit conversion (rad->deg, m->mm) and dict shape, so it runs in well
under a second.
"""
from __future__ import annotations

import math

from rl_move.sim.eval_modeseq import seg_state_row


def test_row_shape_and_tag():
    row = seg_state_row(
        tag="walk_entry", ep=3, t_s=0.0,
        q_deg=[1.0, 2.0], qvel=[0.1, 0.2],
        chassis_z_m=0.09, z0=0.08, h_target=0.005,
        imu_roll_rad=0.0, imu_pitch_rad=0.0)
    assert row["seg"] == "walk_entry"
    assert row["ep"] == 3
    assert row["t_s"] == 0.0
    assert row["q_deg"] == [1.0, 2.0]
    assert row["qvel_rad_s"] == [0.1, 0.2]


def test_height_err_mm_is_m_to_mm_over_z0_plus_h_target():
    row = seg_state_row(
        tag="lower_entry", ep=0, t_s=0.0, q_deg=[], qvel=[],
        chassis_z_m=0.150, z0=0.100, h_target=0.020,
        imu_roll_rad=None, imu_pitch_rad=None)
    # (0.150 - (0.100 + 0.020)) * 1000 = 30.0 mm
    assert row["height_err_mm"] == 30.0


def test_height_err_none_when_frame_missing():
    row = seg_state_row(
        tag="walk_mid", ep=0, t_s=5.0, q_deg=[], qvel=[],
        chassis_z_m=0.15, z0=None, h_target=None,
        imu_roll_rad=None, imu_pitch_rad=None)
    assert row["height_err_mm"] is None
    assert row["roll_deg"] is None
    assert row["pitch_deg"] is None


def test_roll_pitch_rad_to_deg():
    row = seg_state_row(
        tag="walk_cold_reset", ep=0, t_s=0.0, q_deg=[], qvel=[],
        chassis_z_m=0.0, z0=None, h_target=None,
        imu_roll_rad=math.pi / 2, imu_pitch_rad=-math.pi / 4)
    assert row["roll_deg"] == 90.0
    assert row["pitch_deg"] == -45.0
