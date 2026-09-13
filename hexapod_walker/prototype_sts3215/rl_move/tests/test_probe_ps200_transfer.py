import math
from types import SimpleNamespace

import numpy as np
import pytest

from rl_move.sim.domain_rand import DomainRandomizer, RandRanges
from rl_move.sim.probe_ps200_transfer import (
    Intervention,
    periodic_active,
    periodic_half_sine,
    periodic_phase_s,
)
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def test_periodic_phase_starts_at_requested_gait_phase(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    assert periodic_phase_s(2.49, start_s=2.0, period_s=1.5,
                            phase_s=0.5) is None
    assert periodic_phase_s(2.5, start_s=2.0, period_s=1.5,
                            phase_s=0.5) == pytest.approx(0.0)
    assert periodic_phase_s(4.1, start_s=2.0, period_s=1.5,
                            phase_s=0.5) == pytest.approx(0.1)


def test_periodic_support_window_is_bounded_and_repeats(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    iv = Intervention("drop", mechanism="support_loss", duration_s=0.3,
                      phase_s=0.25, start_s=2.0, period_s=1.5)
    assert not periodic_active(2.24, iv)
    assert periodic_active(2.25, iv)
    assert periodic_active(2.54, iv)
    assert not periodic_active(2.55, iv)
    assert periodic_active(3.75, iv)


def test_periodic_roll_torque_is_smooth_half_sine(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    iv = Intervention("push", mechanism="roll_torque", torque_peak_nm=2.6,
                      duration_s=0.4, start_s=2.0, period_s=1.5)
    assert periodic_half_sine(1.99, iv) == 0.0
    assert periodic_half_sine(2.0, iv) == pytest.approx(0.0)
    assert periodic_half_sine(2.2, iv) == pytest.approx(2.6)
    assert periodic_half_sine(2.4, iv) == 0.0
    assert periodic_half_sine(3.7, iv) == pytest.approx(2.6)
    assert math.isfinite(periodic_half_sine(1000.0, iv))


def test_recurrent_walk_push_range_is_sampled_only_when_enabled(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    off = DomainRandomizer(RandRanges(
        walk_push_prob=1.0, walk_push_nm=(5.0, 5.0),
        walk_push_s=(0.3, 0.3)))
    off_ep = off.sample(np.random.default_rng(4))
    assert off_ep.walk_push_repeat_period_s == 0.0
    assert off_ep.walk_push_start_s == 0.0

    on = DomainRandomizer(RandRanges(
        walk_push_prob=1.0, walk_push_nm=(5.0, 5.0),
        walk_push_s=(0.3, 0.3),
        walk_push_repeat_period_s=(1.5, 1.5),
        walk_push_start_s=(2.375, 2.375)))
    on_ep = on.sample(np.random.default_rng(4))
    assert abs(on_ep.walk_push_peak_nm) == 5.0
    assert on_ep.walk_push_repeat_period_s == 1.5
    assert on_ep.walk_push_start_s == 2.375


def test_sim_walk_push_repeats_without_changing_legacy_shape(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    fake = SimpleNamespace(
        _ep_rand=SimpleNamespace(
            walk_push_peak_nm=5.0, walk_push_dur_s=0.3,
            walk_push_repeat_period_s=1.5, walk_push_start_s=2.375),
        _goal_traj=SimpleNamespace(mode="walk"),
        _step_i=0,
        dt=0.025,
    )
    torque = SimHexapodJointWalkEnv._walk_push_torque_nm
    fake._step_i = round(2.525 / fake.dt)
    assert torque(fake) == pytest.approx(5.0)
    fake._step_i = round(4.025 / fake.dt)
    assert torque(fake) == pytest.approx(5.0)
    fake._step_i = round(3.0 / fake.dt)
    assert torque(fake) == 0.0

    fake._ep_rand.walk_push_repeat_period_s = 0.0
    fake._ep_rand.walk_push_start_s = 0.0
    fake._ep_rand.walk_push_dur_s = 1.5
    fake._step_i = round(0.75 / fake.dt)
    assert torque(fake) == pytest.approx(5.0)
    fake._step_i = round(1.5 / fake.dt)
    assert torque(fake) == 0.0
