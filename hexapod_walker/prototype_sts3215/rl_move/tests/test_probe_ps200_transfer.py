import math
from types import SimpleNamespace

import numpy as np
import pytest

from rl_move.sim.domain_rand import DomainRandomizer, RandRanges
from rl_move.sim.probe_ps200_transfer import (
    Intervention,
    TransferProbeEnv,
    _policy_cfg,
    periodic_active,
    periodic_half_sine,
    periodic_phase_s,
)
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

_FAKE_META = {
    "control_hz": 50.0,
    "max_delta_q_deg": 12.0,
    "walk_speed_min_m_s": 0.05,
    "walk_speed_max_m_s": 0.15,
    "phase_hz": 1.0,
}


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


def test_deadband_intervention_defaults_to_nominal_scale():
    iv = Intervention("baseline")
    assert iv.deadband_scale == pytest.approx(1.0)
    dosed = Intervention("deadband_x6", mechanism="deadband",
                         deadband_scale=6.0)
    assert dosed.deadband_scale == pytest.approx(6.0)


def test_load_trigger_defaults_and_fields():
    iv = Intervention("baseline")
    assert iv.mechanism == "none"
    assert iv.trigger_leg == 4
    assert iv.force_threshold_n == pytest.approx(0.0)
    dosed = Intervention("loadtrig_L1_thr5_peak5.00_d0.3",
                         mechanism="load_triggered", trigger_leg=1,
                         force_threshold_n=5.0, torque_peak_nm=5.0,
                         duration_s=0.3)
    assert dosed.trigger_leg == 1
    assert dosed.force_threshold_n == pytest.approx(5.0)


def test_load_trigger_fires_only_on_rising_grf_edge(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    iv = Intervention("lt", mechanism="load_triggered", trigger_leg=4,
                      force_threshold_n=5.0)
    fake = SimpleNamespace(
        _foot_prev_force=[0.0] * 6, _lt_was_high=False,
        _lt_pulse_start_step=None, _step_i=10)
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step is None  # below threshold: no edge

    fake._foot_prev_force[4] = 6.0
    fake._step_i = 11
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 11  # rising edge -> pulse starts

    fake._step_i = 12  # stays loaded: must NOT retrigger
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 11

    fake._foot_prev_force[4] = 0.0  # unloads
    fake._step_i = 13
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 11  # unchanged, no edge on drop

    fake._foot_prev_force[4] = 7.0  # loads again: new edge
    fake._step_i = 20
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 20

    # A different leg's force never arms this trigger leg's edge.
    other = SimpleNamespace(
        _foot_prev_force=[9.0, 9.0, 9.0, 9.0, 0.0, 9.0], _lt_was_high=False,
        _lt_pulse_start_step=None, _step_i=0)
    TransferProbeEnv._lt_maybe_trigger(other, iv)
    assert other._lt_pulse_start_step is None


def test_load_trigger_torque_is_smooth_half_sine_after_pulse_starts():
    dt = 0.02
    iv = Intervention("lt", mechanism="load_triggered", torque_peak_nm=5.0,
                      duration_s=0.3)
    fake = SimpleNamespace(
        intervention=iv, dt=dt, _step_i=100,
        _goal_traj=SimpleNamespace(mode="walk"),
        _lt_pulse_start_step=None, _lt_active_ticks=0)
    torque = TransferProbeEnv._walk_push_torque_nm
    assert torque(fake) == 0.0  # no pulse armed yet

    fake._lt_pulse_start_step = 100
    assert torque(fake) == pytest.approx(0.0, abs=1e-9)  # elapsed 0
    fake._step_i = 107  # elapsed = 7 * dt = 0.14 s, inside the 0.3 s window
    elapsed = 7 * dt
    assert torque(fake) == pytest.approx(
        5.0 * math.sin(math.pi * elapsed / 0.3))
    fake._step_i = 100 + round(0.3 / dt)  # pulse has ended
    assert torque(fake) == 0.0
    assert fake._lt_active_ticks == 2  # the two in-window calls above

    fake._goal_traj = SimpleNamespace(mode="rise")
    fake._step_i = 105
    assert torque(fake) == 0.0  # gated off outside walk mode


def test_policy_cfg_pins_a_degenerate_deadband_range(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    baseline_cfg = _policy_cfg(_FAKE_META, Intervention("baseline"))
    assert baseline_cfg["dr"]["deadband_scale"] == "1.0,1.0"

    dosed_cfg = _policy_cfg(
        _FAKE_META,
        Intervention("deadband_x6", mechanism="deadband",
                     deadband_scale=6.0))
    assert dosed_cfg["dr"]["deadband_scale"] == "6.0,6.0"
    # A pinned dose must still round-trip through the SAME absolute-override
    # path (dr.<field> = "lo,hi") every other intervention field uses, well
    # past the 1.8x ceiling ordinary training DR samples.
    ranges = RandRanges()
    lo, hi = (float(x) for x in dosed_cfg["dr"]["deadband_scale"].split(","))
    setattr(ranges, "deadband_scale", (lo, hi))
    assert ranges.deadband_scale == (6.0, 6.0)
