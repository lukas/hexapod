"""Pure capture/provenance tests. No simulator or frozen rollout helper imports."""

import copy
import importlib.util
import math
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def capture():
    module = import_file("control_chain_under_test", HERE / "capture_control_chain.py")
    assert module.BASE is None
    return module


def test_fixed_matrix_is_exactly_six_existing_cells_and_6020_ticks(capture):
    jobs = capture.fixed_cells()
    assert len(jobs) == len({job["id"] for job in jobs}) == 6
    assert [job["id"] for job in jobs] == [
        "w+0.15_ph0_baseline", "w+0.15_ph1_baseline",
        "w-0.15_ph0_baseline", "w-0.15_ph1_baseline",
        "w+0.00_ph0_straight_baseline", "w+0.00_ph1_straight_baseline",
    ]
    assert [job["ticks"] for job in jobs] == [755] * 4 + [1500] * 2
    assert sum(job["ticks"] for job in jobs) == 6020
    assert [(job["cell"]["vx"], job["cell"]["wz"], job["cell"]["phase_offset"])
            for job in jobs] == [(.08, wz, phase) for wz in (.15, -.15, 0.) for phase in (0., math.pi)]


def test_frame_maps_match_real_pinned_joint_contract_and_derivative(capture):
    # This source only defines NumPy conversions and metadata checks; importing
    # it does not load MuJoCo or perform a rollout.
    proto = Path(os.environ.get("HEXAPOD_PROTOTYPE_ROOT", HERE.parents[2] / "hexapod_walker/prototype_sts3215"))
    source = proto / "hexapod_core/joint_frame.py"
    expected_hash = json.loads((HERE / "PREREGISTRATION.json").read_text())["additional_source_hashes"]["hexapod_core/joint_frame.py"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_hash
    frame = import_file("pinned_control_chain_joint_frame", source)
    logical = np.tile([.2, .4, 1.1], 6)
    expected = frame.robot_abs_rad_to_mujoco_rel_rad(logical)
    original = logical.copy()
    np.testing.assert_array_equal(capture.logical_to_mj(logical), expected)
    np.testing.assert_allclose(capture.mj_to_logical(expected), logical, rtol=0., atol=2e-16)
    np.testing.assert_array_equal(logical, original)
    batch = np.stack([logical, logical + .07])
    np.testing.assert_array_equal(capture.logical_to_mj(batch), np.stack([
        frame.robot_abs_rad_to_mujoco_rel_rad(q) for q in batch]))
    expected_derivative = np.kron(np.eye(6), [[1., 0., 0.], [0., 1., 0.], [0., -1., 1.]])
    epsilon = 1e-6
    observed = np.column_stack([
        (capture.logical_to_mj(logical + epsilon * np.eye(18)[j])
         - capture.logical_to_mj(logical - epsilon * np.eye(18)[j])) / (2 * epsilon)
        for j in range(18)
    ])
    np.testing.assert_allclose(observed, expected_derivative, rtol=0., atol=1e-9)
    velocity = np.arange(18, dtype=float) / 100
    np.testing.assert_allclose(capture.logical_to_mj(velocity), expected_derivative @ velocity, atol=1e-16)


def test_reference_compare_accepts_copied_identical_arrays(capture):
    reference = {"q": np.arange(36, dtype=np.float64).reshape(2, 18), "contact": np.array([True, False])}
    assert capture.compare_arrays({k: v.copy() for k, v in reference.items()}, reference) == {"q": True, "contact": True}


@pytest.mark.parametrize("kind", ["field", "shape", "value", "dtype", "signed-zero"])
def test_reference_compare_requires_byte_exact_values_dtype_and_fields(capture, kind):
    reference = {"q": np.array([0., 1.], dtype=np.float64)}
    actual = {"q": reference["q"].copy()}
    if kind == "field":
        actual["extra"] = np.zeros(1)
    elif kind == "shape":
        actual["q"] = actual["q"].reshape(1, 2)
    elif kind == "value":
        actual["q"][1] = np.nextafter(1., 2.)
    elif kind == "dtype":
        actual["q"] = actual["q"].astype(np.float32)
    else:
        actual["q"][0] = -0.
    with pytest.raises(ValueError):
        capture.compare_arrays(actual, reference)


def test_pack_preserves_numeric_and_reason_fields(capture):
    rows = [{"tick": i, "q": np.ones(18) * i, "reason": "", "ok": True} for i in range(2)]
    packed = capture.pack(rows)
    assert packed["q"].shape == (2, 18)
    np.testing.assert_array_equal(packed["tick"], [0, 1])
    assert packed["reason"].tolist() == ["", ""]
    assert packed["ok"].tolist() == [True, True]


@pytest.mark.parametrize("rows", [
    [{"a": 1}, {"b": 2}],
    [{"a": np.ones(18)}, {"a": np.ones(17)}],
    [{"a": None}],
    [{"a": {"nested": 1}}],
    [{"a": np.array([1., np.nan])}],
    [{"a": np.array([np.inf])}],
], ids=["missing-field", "ragged", "missing-value", "object", "nan", "infinity"])
def test_pack_rejects_missing_ragged_and_nonfinite_records(capture, rows):
    with pytest.raises(ValueError):
        capture.pack(rows)


@pytest.mark.parametrize("value", [None, [np.nan] * 18, [np.inf] * 18, np.ones(17), ["x"] * 18])
def test_required_joint_vectors_fail_closed(capture, value):
    with pytest.raises(ValueError):
        capture.vec(value)


class FakeSafety:
    def __init__(self):
        self._last_safe = np.zeros(18)
        self.max_dq = .01
        self._entry_ticks = 0
        self.entry_ramp_s = 0.
        self.entry_start_dq = .001
        self._hz = 100.
        self.calls = []
        self.returned = None

    def filter(self, q, state, **kwargs):
        self.calls.append((q, state, kwargs))
        self._last_safe = q.copy()
        self._entry_ticks += 1
        status = SimpleNamespace(ok=True, terminate=False, held=False, reason="")
        self.returned = (q, status)
        return self.returned


class FakeProfile:
    def __init__(self):
        self._latency_s = np.full(18, .03)
        self._deadband = np.full(18, .005)
        self._vel_default = np.ones(18)
        self._acc_default = np.ones(18) * 2
        self.goal = np.zeros(18)
        self.target = np.zeros(18)
        self._v = np.zeros(18)
        self._vel_now = self._vel_default.copy()
        self._acc_now = self._acc_default.copy()
        self._queue = []
        self._t = 0.
        self.commands = []
        self.ticks = []
        self.command_return = object()

    def command(self, q, **kwargs):
        self.commands.append((q, kwargs))
        self._queue.append((self._t, q.copy(), self._vel_now.copy(), self._acc_now.copy()))
        return self.command_return

    def tick(self, dt):
        self.ticks.append(dt)
        self._t += dt
        self.target = np.full(18, self._t)
        return self.target


class FakeEnv:
    def __init__(self, safety_class=FakeSafety, profile_class=FakeProfile):
        self._profile = profile_class()
        self.safety = safety_class()
        self.dt = .01
        self._substeps = 5
        self._qadr = self._vadr = self._pos_act = np.arange(18)
        self.model = SimpleNamespace(
            opt=SimpleNamespace(timestep=.002), actuator_gainprm=np.zeros((18, 10)),
            actuator_biasprm=np.zeros((18, 10)), actuator_forcerange=np.zeros((18, 2)),
            actuator_ctrlrange=np.zeros((18, 2)), actuator_forcelimited=np.ones(18, dtype=np.uint8),
            actuator_ctrllimited=np.zeros(18, dtype=np.uint8),
        )
        self.data = SimpleNamespace(time=0., qpos=np.zeros(18), qvel=np.zeros(18),
                                    qfrc_actuator=np.zeros(18), ctrl=np.zeros(18))
        self.write_speed_deg_s = 35.15625
        self.write_acc_units = 20.
        self._step_i = 0
        self._phase = 1.
        self._cmd = np.zeros(18)
        self._state = SimpleNamespace(joint_position=np.zeros(18), joint_velocity=np.zeros(18), servo_current=np.zeros(18))
        self.decode_calls = []
        self.step_calls = []
        self.physics_calls = []
        self.decode_result = (np.linspace(-.2, .2, 18, dtype=np.float32).astype(float) * .5, True, "")
        self.step_result = (np.zeros(12), 0., False, False, {})
        self.physics_return = object()
        self.physics_dispatch = self.original_physics
        self.raise_in_step = None
        self.skip_profile = False

    def _act_to_q(self, action):
        self.decode_calls.append(action)
        return self.decode_result

    def original_physics(self, model, data):
        self.physics_calls.append((model, data))
        data.time += .002
        data.qpos[:] = data.time
        return self.physics_return

    def step(self, action):
        self.step_calls.append(action)
        decoded = self._act_to_q(action)
        assert decoded is self.decode_result
        safe = self.safety.filter(decoded[0], self._state, ik_ok=decoded[1], ik_reason=decoded[2], action=action)
        assert safe is self.safety.returned
        self._cmd = safe[0].copy()
        if self.raise_in_step is not None:
            raise self.raise_in_step
        written = self._profile.command(self._cmd, speed_deg_s=self.write_speed_deg_s, acc_units=self.write_acc_units)
        assert written is self._profile.command_return
        for _ in range(self._substeps):
            if not self.skip_profile:
                target = self._profile.tick(.002)
                assert target is self._profile.target
                self.data.ctrl[:] = target
            assert self.physics_dispatch(self.model, self.data) is self.physics_return
        self._step_i += 1
        self._state.joint_position = self.data.qpos.copy()
        return self.step_result


def fake_model():
    model = SimpleNamespace(_state=np.zeros(2), _episode_start=np.array([True]), calls=[])
    model.result = (np.linspace(-.2, .2, 18, dtype=np.float32), object())

    def predict(obs, deterministic=True):
        model.calls.append((obs, deterministic))
        model._state = model._state + 1
        model._episode_start = np.array([False])
        return model.result

    model.predict = predict
    return model


def make_recorder(capture, env=None):
    env = env or FakeEnv()
    rec = capture.Recorder(env, lambda value: repr(value))
    env.physics_dispatch = lambda model, data: rec.physics_step(env.original_physics, model, data)
    return env, rec


def recorded_tables(capture, n=2):
    env, rec = make_recorder(capture)
    model = fake_model()
    try:
        rec.install()
        for _ in range(n):
            result = rec.predict(model, np.zeros(12))
            env.step(result[0])
    finally:
        rec.restore()
    return tuple(capture.pack(rows) for rows in (rec.control, rec.profile, rec.physics, rec.commands))


def test_recording_preserves_calls_arguments_returns_and_instance_keys(capture):
    env, rec = make_recorder(capture)
    safety_keys, profile_keys, env_keys = set(vars(env.safety)), set(vars(env._profile)), set(vars(env))
    model = fake_model()
    obs = np.arange(12, dtype=np.float32)
    methods = (FakeSafety.filter, FakeProfile.command, FakeProfile.tick)
    try:
        rec.install()
        assert set(vars(env.safety)) == safety_keys
        assert set(vars(env._profile)) == profile_keys
        predicted = rec.predict(model, obs, deterministic=False)
        assert predicted is model.result
        returned = env.step(predicted[0])
        assert returned is env.step_result
        assert len(model.calls) == len(env.step_calls) == len(env.decode_calls) == len(env.safety.calls) == 1
        assert model.calls[0][0] is obs and model.calls[0][1] is False
        assert env.step_calls[0] is env.decode_calls[0] is predicted[0]
        assert env.safety.calls[0][0] is env.decode_result[0]
        assert env.safety.calls[0][2]["action"] is predicted[0]
        assert len(env._profile.commands) == 1
        assert env._profile.commands[0][0] is env._cmd
        assert len(env._profile.ticks) == len(env.physics_calls) == 5
        assert all(m is env.model and d is env.data for m, d in env.physics_calls)
        assert len(rec.control) == 1 and len(rec.profile) == len(rec.physics) == 5 and len(rec.commands) == 1
        np.testing.assert_array_equal(rec.control[0]["policy_action"], predicted[0])
        assert rec.control[0]["recurrent_before"] != rec.control[0]["recurrent_after"]
        # The recorder must copy arrays/status now, not retain changing aliases.
        env.safety.returned[1].reason = "later mutation"
        model.result[0][:] = 0
        assert rec.control[0]["safety_reason"] == ""
        assert np.any(rec.control[0]["policy_action"] != 0)
    finally:
        rec.restore()
    assert (FakeSafety.filter, FakeProfile.command, FakeProfile.tick) == methods
    assert set(vars(env.safety)) == safety_keys and set(vars(env._profile)) == profile_keys
    assert set(vars(env)) == env_keys
    rec.restore()  # Repeated cleanup is harmless.


def test_hooks_dispatch_other_instances_to_original_without_recording(capture):
    env, rec = make_recorder(capture)
    other_safety, other_profile = FakeSafety(), FakeProfile()
    try:
        rec.install()
        q = np.ones(18)
        result = other_safety.filter(q, object())
        assert result is other_safety.returned
        assert other_profile.command(q) is other_profile.command_return
        assert other_profile.tick(.002) is other_profile.target
        assert rec.control == rec.profile == rec.physics == rec.commands == []
    finally:
        rec.restore()


def test_inherited_class_methods_are_deleted_again_on_restore(capture):
    class SafetyChild(FakeSafety):
        pass

    class ProfileChild(FakeProfile):
        pass

    env, rec = make_recorder(capture, FakeEnv(SafetyChild, ProfileChild))
    assert "filter" not in vars(SafetyChild)
    assert "command" not in vars(ProfileChild) and "tick" not in vars(ProfileChild)
    try:
        rec.install()
        assert "filter" in vars(SafetyChild) and "tick" in vars(ProfileChild)
    finally:
        rec.restore()
    assert "filter" not in vars(SafetyChild)
    assert "command" not in vars(ProfileChild) and "tick" not in vars(ProfileChild)
    assert SafetyChild.filter is FakeSafety.filter and ProfileChild.tick is FakeProfile.tick


def test_original_failure_propagates_and_cleanup_restores_hooks(capture):
    env, rec = make_recorder(capture)
    error = RuntimeError("synthetic original step failure")
    env.raise_in_step = error
    methods = (FakeSafety.filter, FakeProfile.command, FakeProfile.tick)
    env_keys = set(vars(env))
    try:
        rec.install()
        result = rec.predict(fake_model(), np.zeros(12))
        with pytest.raises(RuntimeError) as raised:
            env.step(result[0])
        assert raised.value is error
        assert not rec.active
        assert rec.control == [] and rec.row is not None
        assert len(env.step_calls) == len(env.decode_calls) == len(env.safety.calls) == 1
        assert env.physics_calls == [] and env._profile.commands == []
    finally:
        rec.restore()
    assert (FakeSafety.filter, FakeProfile.command, FakeProfile.tick) == methods
    assert set(vars(env)) == env_keys


def test_ordering_rejects_unpaired_predict_duplicate_stage_and_physics_first(capture):
    env, rec = make_recorder(capture)
    try:
        rec.install()
        with pytest.raises(ValueError):
            env.step(np.zeros(18))
        result = rec.predict(fake_model(), np.zeros(12))
        with pytest.raises(ValueError):
            rec.predict(fake_model(), np.zeros(12))
        rec._put("test_stage", 1)
        with pytest.raises(ValueError):
            rec._put("test_stage", 2)
        env.skip_profile = True
        with pytest.raises(ValueError, match="ordering"):
            env.step(result[0])
        assert env.physics_calls == []
    finally:
        rec.restore()


def test_valid_mock_capture_has_one_command_and_five_substeps_per_tick(capture):
    tables = recorded_tables(capture)
    assert capture.validate_capture(*tables, n=2, substeps=5)
    assert [len(table["tick"]) for table in tables] == [2, 10, 10, 2]


@pytest.mark.parametrize("fault", [
    "missing-control", "duplicate-control", "missing-profile", "duplicate-profile", "profile-order",
    "physics-order", "profile-count", "physics-count", "command-count", "command-index", "command-order",
    "terminated", "decoder-failed", "changed-action", "changed-decode", "nonfinite",
])
def test_validate_capture_rejects_missing_duplicate_misordered_and_changed_data(capture, fault):
    c, p, f, w = copy.deepcopy(recorded_tables(capture))
    if fault == "missing-control":
        c["tick"] = c["tick"][:-1]
    elif fault == "duplicate-control":
        c["tick"][1] = 0
    elif fault == "missing-profile":
        p["tick"] = p["tick"][:-1]
    elif fault == "duplicate-profile":
        p["substep"][1] = 0
    elif fault == "profile-order":
        p["tick"] = p["tick"][::-1]
    elif fault == "physics-order":
        f["substep"] = f["substep"][::-1]
    elif fault == "profile-count":
        c["profile_count"][0] = 4
    elif fault == "physics-count":
        c["physics_count"][0] = 4
    elif fault == "command-count":
        c["command_count"][0] = 2
    elif fault == "command-index":
        w["tick"][0] = 1
    elif fault == "command-order":
        w = {k: v[::-1] for k, v in w.items()}
    elif fault == "terminated":
        c["terminated"][0] = True
    elif fault == "decoder-failed":
        c["decoder_ok"][0] = False
    elif fault == "changed-action":
        c["env_input_action"][0, 0] += .01
    elif fault == "changed-decode":
        c["safety_input_logical_rad"][0, 0] += .01
    else:
        f["q_mj_post_rad"][0, 0] = np.nan
    with pytest.raises(ValueError):
        capture.validate_capture(c, p, f, w, n=2, substeps=5)


def test_predictor_forwards_live_recurrent_state_without_an_extra_call(capture):
    env, rec = make_recorder(capture)
    model = fake_model()
    predictor = capture.Predictor(model, rec)
    assert predictor._state is model._state
    assert predictor._episode_start is model._episode_start
    result = predictor.predict(np.zeros(12), deterministic=False)
    assert result is model.result and len(model.calls) == 1
    assert predictor._state is model._state
    assert predictor._episode_start is model._episode_start


def test_observed_no_write_is_not_replaced_by_a_fabricated_command(capture):
    c, p, f, w = recorded_tables(capture)
    c["command_count"][1] = 0
    w = {key: value[:1] for key, value in w.items()}
    assert capture.validate_capture(c, p, f, w, n=2, substeps=5)


def timing_example(capture):
    c, p, f, _ = recorded_tables(capture)
    metadata = dict(control_dt=.01, physics_dt=.002, substeps=5,
                    affine_center_rad=np.zeros(18), affine_half_range_rad=np.full(18, .5))
    return c, p, f, metadata


def test_complete_mock_timing_and_affine_contract_pass(capture):
    assert capture.validate_timing(*timing_example(capture))


@pytest.mark.parametrize("fault", [
    "dt", "profile-delta", "physics-delta", "stage-clock", "control-pre-clock",
    "control-post-clock", "control-pre-q", "control-post-q", "control-profile-clock", "affine",
    "internal-physics-time-gap", "internal-profile-time-gap", "internal-q-gap", "internal-qvel-gap",
    "internal-profile-state-gap",
])
def test_timing_rejects_boundary_and_internal_discontinuities(capture, fault):
    c, p, f, metadata = timing_example(capture)
    if fault == "dt":
        p["dt"][2] += .001
    elif fault == "profile-delta":
        p["profile_time_after"][2] += .001
    elif fault == "physics-delta":
        f["sim_time_post"][2] += .001
    elif fault == "stage-clock":
        p["sim_time"][2] += .001
    elif fault == "control-pre-clock":
        c["sim_time_pre"][0] += .001
    elif fault == "control-post-clock":
        c["sim_time_post"][0] += .001
    elif fault == "control-pre-q":
        c["actual_mj_pre_rad"][0, 0] += .001
    elif fault == "control-post-q":
        c["actual_mj_post_rad"][0, 0] += .001
    elif fault == "control-profile-clock":
        c["profile_time_post"][0] += .001
    elif fault == "affine":
        c["decoded_logical_rad"][0, 0] += .001
    elif fault == "internal-physics-time-gap":
        # Keep this substep's own dt and profile/physics alignment valid:
        # only continuity with adjacent substeps reveals the missing time.
        f["sim_time_pre"][2] += .001
        f["sim_time_post"][2] += .001
        p["sim_time"][2] += .001
    elif fault == "internal-profile-time-gap":
        p["profile_time_before"][2] += .001
        p["profile_time_after"][2] += .001
    elif fault == "internal-q-gap":
        f["q_mj_pre_rad"][2, 0] += .001
    elif fault == "internal-qvel-gap":
        f["q_mj_pre_rad_s"][2, 0] += .001
    else:
        p["target_before"][2, 0] += .001
    with pytest.raises(ValueError):
        capture.validate_timing(c, p, f, metadata)
