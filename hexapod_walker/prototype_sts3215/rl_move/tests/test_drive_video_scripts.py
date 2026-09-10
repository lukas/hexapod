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


def test_play_traj_velocity_blend_finishes_in_a_fixed_duration() -> None:
    # 2026-09-10 fix: the command blend must complete in BLEND_S seconds
    # regardless of magnitude -- the old fixed-RATE ramp took over 2x
    # longer than training's own 1s command-resample blend for a large
    # multi-axis delta (see _PlayTraj docstring / CURRENT_TRUTHS.md).
    dt = 0.02
    traj = _PlayTraj(dt=dt)
    traj.reset_published()
    traj.vx, traj.vy = 0.0566, 0.0566   # diag-left-sized target
    n_full = int(round(_PlayTraj.BLEND_S / dt))
    for step in range(1, n_full + 5):
        traj.at(step)
    assert np.isclose(traj._pvx, 0.0566, atol=1e-6)
    assert np.isclose(traj._pvy, 0.0566, atol=1e-6)

    # Large multi-axis flip (diag-left -> reverse-sized target): must
    # ALSO finish within BLEND_S, not the >2.2s the old rate-limited ramp
    # needed for this exact geometry.
    traj.vx, traj.vy = -0.08, 0.0
    step0 = n_full + 5
    n_half = step0 + int(round(0.5 * _PlayTraj.BLEND_S / dt))
    for step in range(step0 + 1, n_half + 1):
        traj.at(step)
    # halfway through the blend the command must already be moving
    # AWAY from a full stop, not sitting at (0, 0) -- the old rate-
    # limited ramp put BOTH axes at ~0 simultaneously around this point
    # for this exact command pair.
    assert abs(traj._pvx) + abs(traj._pvy) > 0.01
    for step in range(n_half + 1, step0 + n_full + 5):
        traj.at(step)
    assert np.isclose(traj._pvx, -0.08, atol=1e-6)
    assert np.isclose(traj._pvy, 0.0, atol=1e-6)


def test_play_traj_velocity_blend_restarts_from_the_published_value() -> None:
    # A target change mid-blend must restart the blend from wherever the
    # command actually is right now, not from the old target or from 0.
    dt = 0.05
    traj = _PlayTraj(dt=dt)
    traj.reset_published()
    traj.vx = 0.08
    for step in range(1, 6):   # 0.25s of a 1.0s blend: partway there
        traj.at(step)
    assert 0.0 < traj._pvx < 0.08
    mid = traj._pvx
    traj.vx = -0.08            # target flips before the first blend finishes
    goal = traj.at(6)
    # must move from `mid` toward the new target, not jump or reset
    assert goal.vx_ref < mid
