import numpy as np

from rl_move.sim.drive_video import _script
from rl_move.sim.play_core import _PlayTraj


def test_existing_drive_scripts_keep_zero_wz() -> None:
    for name in ("square", "human", "sweep"):
        vx, vy, wz, labels = _script(
            name, seconds=6.0, dt=0.02, speed=0.08, blend_s=0.5)
        assert vx.shape == vy.shape == wz.shape
        assert len(labels) == len(vx)
        assert np.allclose(wz, 0.0)


def test_human_turn_script_commands_both_yaw_directions() -> None:
    vx, vy, wz, labels = _script(
        "human_turn", seconds=28.0, dt=0.02, speed=0.08, blend_s=0.5,
        wz_max=0.3)
    assert vx.shape == vy.shape == wz.shape
    assert len(labels) == len(vx)
    assert np.max(wz) > 0.29
    assert np.min(wz) < -0.29
    assert "turn-left" in labels
    assert "turn-right" in labels


def test_play_traj_publishes_ramped_wz_ref() -> None:
    traj = _PlayTraj(dt=0.1)
    traj.reset_published()
    traj.wz = 0.3

    goal1 = traj.at(1)
    goal2 = traj.at(20)

    assert 0.0 < goal1.wz_ref < 0.3
    assert np.isclose(goal2.wz_ref, 0.3)
