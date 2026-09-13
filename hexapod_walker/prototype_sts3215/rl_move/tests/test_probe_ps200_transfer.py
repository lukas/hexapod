import math
from types import SimpleNamespace

import numpy as np
import pytest

from rl_move.sim.domain_rand import DomainRandomizer, RandRanges
from rl_move.sim.probe_ps200_transfer import (
    Intervention,
    TransferProbeEnv,
    _policy_cfg,
    _temporary_foot_ground_friction,
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


def test_load_share_defaults_and_fields():
    iv = Intervention("baseline")
    assert iv.front_legs == (0, 5)
    assert iv.rear_legs == (2, 3)
    assert iv.share_threshold == pytest.approx(0.0)
    dosed = Intervention("loadshare_front0.7_peak5.00_d0.3",
                         mechanism="load_share", share_threshold=0.7,
                         torque_peak_nm=5.0, duration_s=0.3)
    assert dosed.share_threshold == pytest.approx(0.7)


def test_load_share_fires_only_on_rising_front_share_edge(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    iv = Intervention("ls", mechanism="load_share", share_threshold=0.6)
    fake = SimpleNamespace(
        _foot_prev_force=[0.0] * 6, _lt_was_high=False,
        _lt_pulse_start_step=None, _step_i=10)
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step is None  # 0/0 share -> sensed=0, no edge

    # Front (L0/L5) carries 3N, rear (L2/L3) carries 7N -> share 0.3: no edge.
    fake._foot_prev_force = [3.0, 0.0, 3.5, 3.5, 0.0, 0.0]
    fake._step_i = 11
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step is None

    # Front now carries 8N, rear 2N -> share 0.8 >= 0.6: rising edge.
    fake._foot_prev_force = [4.0, 0.0, 1.0, 1.0, 0.0, 4.0]
    fake._step_i = 12
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 12

    fake._step_i = 13  # stays high: must NOT retrigger
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 12

    # Share drops back under threshold, then crosses again -> new edge.
    fake._foot_prev_force = [1.0, 0.0, 4.0, 4.0, 0.0, 1.0]
    fake._step_i = 14
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 12

    fake._foot_prev_force = [5.0, 0.0, 1.0, 1.0, 0.0, 4.0]
    fake._step_i = 20
    TransferProbeEnv._lt_maybe_trigger(fake, iv)
    assert fake._lt_pulse_start_step == 20

    # A rear-only load (mid legs 1/4 don't count in either group) never
    # arms the trigger regardless of magnitude.
    other = SimpleNamespace(
        _foot_prev_force=[0.0, 9.0, 0.0, 0.0, 9.0, 0.0], _lt_was_high=False,
        _lt_pulse_start_step=None, _step_i=0)
    TransferProbeEnv._lt_maybe_trigger(other, iv)
    assert other._lt_pulse_start_step is None


def test_load_share_torque_reuses_the_load_triggered_pulse_shape():
    dt = 0.02
    iv = Intervention("ls", mechanism="load_share", torque_peak_nm=5.0,
                      duration_s=0.3)
    fake = SimpleNamespace(
        intervention=iv, dt=dt, _step_i=100,
        _goal_traj=SimpleNamespace(mode="walk"),
        _lt_pulse_start_step=None, _lt_active_ticks=0)
    torque = TransferProbeEnv._walk_push_torque_nm
    assert torque(fake) == 0.0  # no pulse armed yet

    fake._lt_pulse_start_step = 100
    fake._step_i = 107
    elapsed = 7 * dt
    assert torque(fake) == pytest.approx(
        5.0 * math.sin(math.pi * elapsed / 0.3))
    fake._step_i = 100 + round(0.3 / dt)  # pulse has ended
    assert torque(fake) == 0.0
    assert fake._lt_active_ticks == 1

    fake._goal_traj = SimpleNamespace(mode="rise")
    fake._step_i = 105
    assert torque(fake) == 0.0  # gated off outside walk mode


def test_friction_loss_defaults_and_fields():
    iv = Intervention("baseline")
    assert iv.friction_scale == pytest.approx(1.0)
    dosed = Intervention("friction_L4_x0.1_d0.3_p0.375",
                         mechanism="friction_loss", dropout_legs=(4,),
                         friction_scale=0.1, duration_s=0.3, phase_s=0.375)
    assert dosed.friction_scale == pytest.approx(0.1)
    assert dosed.dropout_legs == (4,)


def test_friction_loss_reuses_the_support_loss_periodic_window():
    # friction_loss schedules on the SAME periodic_active window as
    # support_loss (dropout_legs/duration_s/phase_s/period_s) -- only the
    # world edit inside that window differs (scaled friction vs removed
    # contact), so the timing math needs no new test, just this one check
    # that both mechanisms agree on the same window for identical fields.
    common = dict(duration_s=0.3, phase_s=0.25, start_s=2.0, period_s=1.5)
    support = Intervention("drop", mechanism="support_loss", **common)
    friction = Intervention("slip", mechanism="friction_loss",
                            friction_scale=0.15, **common)
    for t in (1.9, 2.24, 2.25, 2.4, 2.54, 2.55, 3.75):
        assert periodic_active(t, support) == periodic_active(t, friction)


def test_friction_loss_changes_effective_pair_and_restores(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    mujoco = pytest.importorskip("mujoco")
    model = mujoco.MjModel.from_xml_string("""
        <mujoco>
          <worldbody>
            <geom name="floor" type="plane" size="1 1 .1"
                  friction="1.5 .05 .0001"/>
            <body pos="-.1 0 .04">
              <freejoint/>
              <geom name="target" type="sphere" size=".05"
                    friction="2 .1 .001"/>
            </body>
            <body pos=".1 0 .04">
              <freejoint/>
              <geom name="other" type="sphere" size=".05"
                    friction="2 .1 .001"/>
            </body>
          </worldbody>
        </mujoco>
    """)
    data = mujoco.MjData(model)
    obj = mujoco.mjtObj.mjOBJ_GEOM
    floor = mujoco.mj_name2id(model, obj, "floor")
    target = mujoco.mj_name2id(model, obj, "target")
    other = mujoco.mj_name2id(model, obj, "other")
    baseline = model.geom_friction.copy()
    mujoco.mj_forward(model, data)

    def contacts_by_pair():
        return {
            frozenset((int(c.geom1), int(c.geom2))): {
                "friction": np.asarray(c.friction).copy(),
                "solref": np.asarray(c.solref).copy(),
                "dim": int(c.dim),
            }
            for c in data.contact
        }

    baseline_contacts = contacts_by_pair()

    with _temporary_foot_ground_friction(
            model, (target,), (floor,), 0.1):
        mujoco.mj_forward(model, data)
        by_pair = contacts_by_pair()
        target_pair = frozenset((floor, target))
        other_pair = frozenset((floor, other))
        # Target pair really reaches 2.0 * 0.1 instead of being pinned at
        # the unmodified floor's 1.5.  MuJoCo expands the three geom values
        # to five contact values; the other foot remains at baseline.
        assert by_pair[target_pair]["friction"] == pytest.approx(
            [0.2, 0.2, 0.01, 0.0001, 0.0001])
        assert by_pair[other_pair]["friction"] == pytest.approx(
            [2.0, 2.0, 0.1, 0.001, 0.001])
        # The correction must not alter contact dimensionality or solver
        # impedance/reference parameters (as changing geom priority would).
        for pair in (target_pair, other_pair):
            assert by_pair[pair]["solref"] == pytest.approx(
                baseline_contacts[pair]["solref"])
            assert by_pair[pair]["dim"] == baseline_contacts[pair]["dim"]

    assert model.geom_friction == pytest.approx(baseline)


def test_friction_loss_restores_after_failed_tick(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    model = SimpleNamespace(geom_friction=np.array([
        [1.5, 0.05, 0.0001],
        [2.0, 0.1, 0.001],
    ]))
    baseline = model.geom_friction.copy()
    with pytest.raises(RuntimeError, match="tick failed"):
        with _temporary_foot_ground_friction(model, (1,), (0,), 0.02):
            assert model.geom_friction[1, 0] == pytest.approx(0.04)
            assert model.geom_friction[0, 0] == pytest.approx(0.04)
            raise RuntimeError("tick failed")
    assert model.geom_friction == pytest.approx(baseline)


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
