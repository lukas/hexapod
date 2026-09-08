"""Focused measurement and non-invasive state parity regressions."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import math
import numpy as np
import pytest
import mujoco

spec = importlib.util.spec_from_file_location("reviewed_bank", Path(__file__).with_name("reviewed_probe_action_response_bank.py"))
bank = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bank)


def fixture_env():
    pads = "".join(f'<body name="L{i}_pad" pos="{(i%3-1)*.12} {(i//3-.5)*.25} -.04"><geom type="sphere" size=".05" mass=".1"/></body>' for i in range(6))
    xml = f'<mujoco><option timestep=".002" integrator="Euler"/><worldbody><geom type="plane" size="1 1 .1"/><body name="chassis" pos="0 0 .088"><freejoint/><geom type="box" size=".03 .03 .02" mass="1"/>{pads}</body></worldbody></mujoco>'
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return SimpleNamespace(model=model, data=data, _mujoco=mujoco, _chassis_bid=model.body("chassis").id)


def test_real_pitch_key_and_missing_metric():
    assert bank._relative_tilt({"roll_rel_deg": 0, "pitch_deg": 12}, [0, math.radians(2)]) == pytest.approx((0, 10))
    with pytest.raises(ValueError, match="pitch"):
        bank._relative_tilt({"roll_rel_deg": 0}, [0, 0])
    with pytest.raises(ValueError, match="nonfinite"):
        bank._relative_tilt({"roll_rel_deg": 0, "pitch_deg": float("nan")}, [0, 0])


def test_rolling_material_point_vs_center_proxy():
    theta = .2
    c, s = math.cos(theta), math.sin(theta)
    rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    point, x0 = np.zeros(3), np.array([0, 0, .1])
    x1 = point - rot @ (point - x0)
    assert np.linalg.norm((x1-x0)[:2]) > .019
    contacts = [(point, 2.)]
    assert bank.pta._material_slip(contacts, x0, np.eye(3), x1, rot) == pytest.approx(0, abs=1e-15)
    slip = bank.pta._material_slip(contacts, x0, np.eye(3), x1 + [0.007, 0, 0], rot)
    assert slip == pytest.approx(.007)
    rows = [{"h": .005, "fn": [2, 0, 0, 0, 0, 0], "slip_material": [slip, 0, 0, 0, 0, 0], "body_vx": .1}]
    distance, loaded, progress = bank._material_interval(rows, .005)
    assert distance.sum() == pytest.approx(.007)  # already a distance: no second dt factor
    assert loaded.sum() == pytest.approx(.005)
    assert progress == pytest.approx(.0005)
    with pytest.raises(ValueError, match="incomplete"):
        bank._material_interval(rows, .01)


def test_body_command_progress_not_initial_heading_chord():
    n = 81
    tr = {"n_ticks_done": n, "yaw": np.linspace(0, 1, n), "endpoint_yaw": np.linspace(0, 1, n),
          "xy": np.column_stack((np.linspace(0, .5, n), np.linspace(0, .3, n))),
          "pad_xy": np.zeros((n, 6, 2)), "contact": np.ones((n, 6), bool),
          "material_slip": np.full((n, 6), .001), "loaded_time": np.full((n, 6), .01),
          "body_forward": np.full(n, .01), "roll": np.zeros(n), "pitch": np.full(n, 7.),
          "modes": ["walk"]*n, "term_tick": None, "term_reason": "", "phase": np.zeros(n)}
    result = bank._window_metrics(tr, 1)
    assert result["fwd_disp_m"] == pytest.approx(.8)
    assert result["legacy_initial_heading_fwd_disp_m"] == pytest.approx(.5)
    assert result["window_ticks"] == 80 and result["window_state_samples"] == 81
    assert result["max_abs_pitch_deg"] == 7
    tr["loaded_time"][:] = 0
    with pytest.raises(ValueError, match="no loaded"):
        bank._window_metrics(tr, 1)


def test_complete_state_catches_velocity_and_controller_history():
    from rl_move.sim.mjx_host import snap_attrs_for
    env = fixture_env()
    for name in snap_attrs_for(type(env)):
        setattr(env, name, None)
    env._profile = SimpleNamespace(q=np.zeros(18), _queue=[])
    env._goal_gen = SimpleNamespace(rng=np.random.default_rng(0))
    env._phase = .1
    env.rng = np.random.default_rng(0)
    model = SimpleNamespace(_state=np.zeros((1, 2)), _episode_start=False)
    obs = np.zeros(3)
    first = bank._capture_state(env, model, obs)
    assert bank._state_match(first, bank._capture_state(env, model, obs))
    env.data.qvel[0] += .1
    changed = bank._capture_state(env, model, obs)
    assert first["qpos"] == changed["qpos"]
    assert not bank._state_match(first, changed)
    env.data.qvel[0] -= .1
    model._state[0, 0] = 1
    changed = bank._capture_state(env, model, obs)
    assert first["physics_state_sha256"] == changed["physics_state_sha256"]
    assert not bank._state_match(first, changed)


def test_substep_audit_does_not_perturb_live_mujoco_state():
    env = fixture_env()
    direct = mujoco.MjData(env.model)
    mujoco.mj_forward(env.model, direct)
    audit = bank._DynamicsAudit(env)
    audit.begin_interval(phase=0, record=True)
    for _ in range(20):
        mujoco.mj_step(env.model, direct)
        audit.mj_step(env.model, env.data)
        audit.endpoint_yaw()
    for name in ("qpos", "qvel", "qacc_warmstart", "xpos", "xmat", "sensordata"):
        np.testing.assert_array_equal(getattr(direct, name), getattr(env.data, name))
    distances, times, forward = bank._material_interval(audit.pending, .04)
    assert times.sum() > 0
    assert np.isfinite(distances).all() and math.isfinite(forward)


def test_deque_observation_history_preserves_order_and_capacity():
    from collections import deque
    history = deque([np.array([1., 2.]), np.array([3., 4.])], maxlen=4)
    same = deque([x.copy() for x in history], maxlen=4)
    assert bank._digest(history) == bank._digest(same)
    assert bank._digest(history) != bank._digest(deque(history, maxlen=5))
    assert bank._digest(history) != bank._digest(deque(reversed(history), maxlen=4))
