"""Real MuJoCo endpoint timing and actual rollout neutrality regressions.

The portable rollout uses the mesh twin and explicitly replaces only the
frozen full-mesh identity assertion. An optional local full-mesh case uses
HEXAPOD_TWISTFIT_TEST_MESH_ROOT, retaining every production plant assertion.
Neither is a new scientific qualification or a gait correction.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import pytest

from rl_move.sim import probe_turn_twistfit as tf
from rl_move.sim import probe_turn_authority as pta
from rl_move.sim import servo_model


def _live_snapshot(data):
    names = ("qpos", "qvel", "ctrl", "qacc", "qacc_warmstart", "xpos", "xmat",
             "sensordata", "qfrc_applied", "xfrc_applied", "mocap_pos", "mocap_quat")
    return {k: getattr(data, k).copy() for k in names}


def test_endpoint_private_kinematics_ignores_stale_solve_transforms():
    model = mujoco.MjModel.from_xml_string("""<mujoco>
      <option timestep="0.002" gravity="0 0 0"/>
      <worldbody><body name="chassis"><freejoint/><geom type="sphere" size=".1" mass="1"/>
      <body name="arm" pos=".2 0 0"><joint type="hinge" axis="0 0 1"/>
      <geom type="sphere" size=".02" pos=".05 0 0" mass=".1"/>
      <body name="pad" pos=".1 0 0"><geom type="sphere" size=".01" mass=".01"/></body></body>
      </body><body name="marker" mocap="true" pos="0 1 0"/></worldbody></mujoco>""")
    data = mujoco.MjData(model)
    data.qvel[5] = 2.0
    data.qvel[6] = 1.0
    mujoco.mj_forward(model, data)
    mujoco.mj_step(model, data)
    chassis = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    pad = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pad")
    env = SimpleNamespace(model=model, data=data, _mujoco=mujoco,
                          _chassis_bid=chassis, _pad_bids=[pad]*6,
                          _touch_adr=[-1]*6,
                          _state=SimpleNamespace(joint_position=data.qpos[7:].copy()))
    sampler = tf._EndpointKinematics(env)
    before = _live_snapshot(data)
    result = sampler.sample()
    after = _live_snapshot(data)
    assert all(np.array_equal(before[k], after[k]) for k in before)
    assert np.array_equal(result["q_act"], data.qpos[7:])
    assert result["endpoint_time_s"] == data.time
    assert result["contact_solve_time_s"] == pytest.approx(data.time - .002)
    assert not result["contact"].any()  # missing sensors never index [-1]
    endpoint = mujoco.MjData(model)
    endpoint.qpos[:] = data.qpos
    endpoint.mocap_pos[:] = data.mocap_pos
    endpoint.mocap_quat[:] = data.mocap_quat
    mujoco.mj_kinematics(model, endpoint)
    expected = (endpoint.xpos[pad]-endpoint.xpos[chassis]) @ endpoint.xmat[chassis].reshape(3,3)
    assert np.array_equal(result["pads_xy"][0], expected[:2])
    # Both the root frame and the moving distal pad distinguish endpoint
    # sampling from the old cached last-solve implementation.
    stale = (data.xpos[pad]-data.xpos[chassis]) @ data.xmat[chassis].reshape(3,3)
    assert np.linalg.norm(result["pads_xy"][0] - stale[:2]) > 1e-5
    assert not np.array_equal(endpoint.xmat[chassis], data.xmat[chassis])
    assert np.array_equal(sampler.scratch.mocap_pos, data.mocap_pos)


@pytest.mark.parametrize("plant", ["twin", "full_mesh"])
def test_actual_rollout_endpoint_reads_preserve_every_physics_tick(monkeypatch, plant):
    root = Path(__file__).resolve().parents[4]
    report = json.loads((root / "artifacts/rl_watchdog/root_fullcone_20260908/scripted_audit_fm.json").read_text())
    cfg = report["cfg_set"]
    if plant == "full_mesh":
        path = os.environ.get("HEXAPOD_TWISTFIT_TEST_MESH_ROOT")
        if not path:
            pytest.skip("optional full STL assets not configured; portable twin case still runs")
        path = Path(path)
        assert (path / "hexapod_mesh.xml").is_file()
        monkeypatch.setattr(servo_model, "MESH_DIR", path)
        monkeypatch.setattr(servo_model, "MESH_XML", path / "hexapod_mesh.xml")
        monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    else:
        monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
        def assert_twin(env):
            identity = tf.model_identity(env)
            assert identity["model_variant"] == "mesh_mjx_twin"
            assert env.dt == .01
            return identity
        monkeypatch.setattr(tf, "_assert_frozen_env", assert_twin)
    make_env = pta.make_env
    traces = []
    def traced_env(*args, **kwargs):
        env = make_env(*args, **kwargs)
        original = env.step
        trace = []
        traces.append(trace)
        def step(action):
            result = original(action)
            trace.append((np.asarray(action).copy(), env.data.qpos.copy(),
                          env.data.qvel.copy(), env.data.ctrl.copy(),
                          env.data.qacc_warmstart.copy(), result[1:4]))
            return result
        env.step = step
        return env
    monkeypatch.setattr(pta, "make_env", traced_env)
    sample = tf._EndpointKinematics.sample
    checked = []
    def checked_sample(self):
        before = _live_snapshot(self.env.data)
        result = sample(self)
        after = _live_snapshot(self.env.data)
        assert all(np.array_equal(before[k], after[k]) for k in before)
        checked.append(result)
        return result
    monkeypatch.setattr(tf._EndpointKinematics, "sample", checked_sample)
    args = dict(cfg_set=cfg, vx_cmd=.08, wz_cmd=.15, seed=0,
                episode_seconds=4.1, phase_offset=np.pi)
    measured = tf.rollout(**args)
    baseline = pta.rollout(model=None, env_cls_kwargs={"cfg_set": cfg},
                           policy="scripted", contact_audit=False,
                           **{k: v for k, v in args.items() if k != "cfg_set"})
    assert len(traces[0]) == len(traces[1])
    for a, b in zip(*traces):
        for left, right in zip(a[:5], b[:5]):
            assert np.array_equal(left, right)
        assert a[5] == b[5]  # reward and terminal/truncation status each tick
    assert measured["n_scored_ticks"] == baseline["n_walk_ticks"] >= 200
    assert measured["body"]["vx_med"] == baseline["vx_med"]
    assert measured["body"]["wz_med"] == baseline["wz_med"]
    assert measured["model_identity"]["model_variant"] == ("full_mesh" if plant == "full_mesh" else "mesh_mjx_twin")
    assert len(checked) == measured["n_scored_ticks"]
    for sample in checked:
        assert sample["endpoint_time_s"] - sample["contact_solve_time_s"] == pytest.approx(measured["sampling"]["physics_dt_s"])
    assert all("plan_contact" in stage for stage in measured["stages"].values())
    assert np.all(np.asarray(measured["duty_plan_contact"]) <= measured["duty_contact"])
