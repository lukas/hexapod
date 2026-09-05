import math

import numpy as np
import pytest

from rl_move.deployed_policy import (
    WALK_OBS_DIMS,
    phase_clock_runs,
    policy_mode_onehot,
    supports_mode_command,
    supports_yaw_command,
    walk_observation_tail,
)
from rl_move.np_policy import MODE_ONEHOT_ORDER
from rl_move.sim.walk_task import mode_onehot


@pytest.mark.parametrize("obs_dim", WALK_OBS_DIMS)
def test_walk_tail_width_and_prefix(obs_dim):
    tail = walk_observation_tail(
        obs_dim, 0.06, -0.03, math.pi / 2, 0.2, mode="walk")
    assert tail.shape == (obs_dim - 68,)
    np.testing.assert_allclose(tail[:4], [0.4, -0.2, 0.4, -0.2])
    if obs_dim in (74, 75, 81, 93):
        np.testing.assert_allclose(tail[4:6], [1.0, 0.0], atol=1e-7)


def test_obs75_is_phase_then_yaw():
    tail = walk_observation_tail(75, 0.0, 0.0, math.pi, -0.25)
    np.testing.assert_allclose(tail, [0, 0, 0, 0, 0, -1, -0.5],
                               atol=1e-7)


@pytest.mark.parametrize("mode", MODE_ONEHOT_ORDER)
def test_obs81_mode_tail_matches_simulator(mode):
    tail = walk_observation_tail(81, 0.08, 0.0, 0.0, 0.1, mode=mode)
    np.testing.assert_array_equal(tail[-6:], mode_onehot(mode))
    np.testing.assert_array_equal(policy_mode_onehot(mode), mode_onehot(mode))


def test_obs93_keeps_yaw_before_all_healthy_fault_tail():
    tail = walk_observation_tail(93, 0.0, 0.0, 0.0, 0.25)
    assert tail[6] == pytest.approx(0.5)
    np.testing.assert_array_equal(tail[7:], np.ones(18))


def test_capability_and_phase_gates():
    assert not supports_yaw_command(74)
    assert supports_yaw_command(75)
    assert supports_yaw_command(81)
    assert supports_mode_command(81)
    assert not supports_mode_command(75)
    assert phase_clock_runs(75, 0.08, 0.0)
    assert not phase_clock_runs(75, 0.0, 0.0, 0.2)
    assert phase_clock_runs(
        75, 0.0, 0.0, 0.2, phase_run_on_yaw=True)
    assert not phase_clock_runs(72, 0.08, 0.0)


def test_unknown_mode_and_bad_fault_vector_fail_closed():
    with pytest.raises(ValueError, match="unsupported deployed policy mode"):
        walk_observation_tail(81, 0, 0, 0, mode="getup")
    with pytest.raises(ValueError, match="fault_health"):
        walk_observation_tail(93, 0, 0, 0, fault_health=[1.0] * 17)
