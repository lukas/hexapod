"""Command-arrow geometry is semantic and never touches physics."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

from rl_move.sim.command_indicator import (  # noqa: E402
    CommandCue,
    command_cue_from_env,
    draw_command_indicator,
    indicator_segments,
)


def _data(yaw_deg: float = 0.0):
    a = np.radians(yaw_deg)
    c, s = np.cos(a), np.sin(a)
    rot = np.array([[c, -s, 0.0],
                    [s, c, 0.0],
                    [0.0, 0.0, 1.0]])
    return SimpleNamespace(
        xpos=np.array([[1.0, 2.0, 0.12]]),
        xmat=np.array([rot.reshape(-1)]),
    )


def test_linear_arrow_rotates_body_command_into_world() -> None:
    segments = indicator_segments(
        _data(yaw_deg=90.0), 0, CommandCue(mode="walk", vx=0.06)
    )

    assert len(segments) == 1
    arrow = segments[0]
    assert arrow.kind == "arrow"
    delta = arrow.end - arrow.start
    assert delta[0] == pytest.approx(0.0, abs=1e-9)
    assert delta[1] > 0.0
    assert delta[2] == pytest.approx(0.0)


@pytest.mark.parametrize(("wz", "expected_sign"), [(0.3, 1), (-0.3, -1)])
def test_turn_arrow_curves_in_commanded_direction(
        wz: float, expected_sign: int) -> None:
    segments = indicator_segments(
        _data(), 0, CommandCue(mode="walk", wz=wz)
    )

    assert len(segments) > 5
    assert segments[-1].kind == "arrow"
    first = segments[0]
    center = np.array([1.0, 2.0])
    radius = first.start[:2] - center
    tangent = first.end[:2] - first.start[:2]
    cross_z = radius[0] * tangent[1] - radius[1] * tangent[0]
    assert np.sign(cross_z) == expected_sign


@pytest.mark.parametrize(("mode", "rises"), [("rise", True),
                                               ("lower", False)])
def test_height_arrow_points_up_or_down(mode: str, rises: bool) -> None:
    segments = indicator_segments(_data(), 0, CommandCue(mode=mode))

    assert len(segments) == 1
    assert bool(segments[0].end[2] > segments[0].start[2]) is rises


def test_combined_walk_and_turn_draws_both_cues() -> None:
    segments = indicator_segments(
        _data(), 0, CommandCue(mode="walk", vx=0.05, vy=-0.02, wz=0.2)
    )

    green = [s for s in segments if s.rgba[1] == pytest.approx(0.95)]
    amber = [s for s in segments if s.rgba[0] == pytest.approx(1.0)]
    assert len(green) == 1
    assert len(amber) > 5


def test_training_trajectory_command_uses_current_step() -> None:
    traj = SimpleNamespace(
        mode="walk",
        vx=np.array([0.0, 0.04, 0.08]),
        vy=np.array([0.0, -0.02, -0.04]),
        wz=np.array([0.0, 0.1, 0.2]),
    )
    env = SimpleNamespace(_goal_traj=traj, _step_i=1)

    assert command_cue_from_env(env) == CommandCue(
        mode="walk", vx=0.04, vy=-0.02, wz=0.1
    )


def test_interactive_height_ramp_derives_rise_and_lower() -> None:
    traj = SimpleNamespace(
        mode="interactive",
        goal=SimpleNamespace(height_ref=0.04),
        _pub=SimpleNamespace(height_ref=0.01),
    )
    env = SimpleNamespace(_goal_traj=traj, _step_i=0)
    assert command_cue_from_env(env).mode == "rise"

    traj.goal.height_ref = -0.02
    assert command_cue_from_env(env).mode == "lower"


def test_mujoco_scene_receives_decorative_geoms() -> None:
    model = mujoco.MjModel.from_xml_string(
        "<mujoco><worldbody><body name='chassis'/></worldbody></mujoco>"
    )
    data = mujoco.MjData(model)
    scene = mujoco.MjvScene(model, maxgeom=40)

    added = draw_command_indicator(
        mujoco,
        scene,
        data,
        1,
        CommandCue(mode="rise", vx=0.05, wz=0.2),
        clear=True,
    )

    assert added > 3
    assert scene.ngeom == added
    assert all(
        scene.geoms[i].category == mujoco.mjtCatBit.mjCAT_DECOR
        for i in range(scene.ngeom)
    )
