import copy

import numpy as np
import pytest

from rl_move.np_policy import (
    ARCH_DUAL_GRU,
    MODE_ONEHOT_ORDER,
    NumpyDualGruModel,
    pack_f32,
    unpack_f32,
    validate_np_policy,
)


def _policy(training_hz=25.0):
    return {
        "meta": {
            "obs_dim": 68,
            "act_dim": 18,
            "activation": "tanh",
            "training_hz": training_hz,
            "joint_frame": "robot_abs",
            "joint_contract": "robot_abs_tibia_v2",
        },
        "W1": [[0.0] * 68],
        "b1": [0.0],
        "W2": [[0.0]],
        "b2": [0.0],
        "Wout": [[0.0] for _ in range(18)],
        "bout": [0.0] * 18,
    }


def test_validate_np_policy_requires_training_hz():
    obj = _policy()
    del obj["meta"]["training_hz"]
    errs, _ = validate_np_policy(obj)
    assert "meta.training_hz is required" in errs


def test_validate_np_policy_reports_training_hz():
    errs, info = validate_np_policy(_policy(training_hz=100.0))
    assert errs == []
    assert info["training_hz"] == 100.0


def test_validate_np_policy_rejects_bad_training_hz():
    obj = _policy(training_hz=25.0)
    for bad in ("fast", 0.0, 500.0):
        bad_obj = copy.deepcopy(obj)
        bad_obj["meta"]["training_hz"] = bad
        errs, _ = validate_np_policy(bad_obj)
        assert any("meta.training_hz" in e for e in errs)


def test_obs75_requires_explicit_phase_and_yaw_contract():
    obj = _policy(training_hz=100.0)
    obj["meta"]["obs_dim"] = 75
    obj["W1"] = [[0.0] * 75]
    errs, _ = validate_np_policy(obj)
    assert any("phase_hz" in error for error in errs)
    assert any("walk_yaw_cmd" in error for error in errs)
    assert any("walk_phase_run_on_yaw" in error for error in errs)

    obj["meta"].update(phase_hz=1.333333, walk_yaw_cmd=True,
                       walk_phase_run_on_yaw=True)
    errs, info = validate_np_policy(obj)
    assert errs == []
    assert info["obs_dim"] == 75


def test_malformed_scalar_matrices_are_validation_errors_not_exceptions():
    obj = _policy()
    obj["b1"] = 0.0
    errs, _ = validate_np_policy(obj)
    assert any("b1 must be rank 1" in error for error in errs)


def _packed_module(module) -> dict:
    return {
        "weight_ih": pack_f32(module.weight_ih_l0.detach().numpy()),
        "weight_hh": pack_f32(module.weight_hh_l0.detach().numpy()),
        "bias_ih": pack_f32(module.bias_ih_l0.detach().numpy()),
        "bias_hh": pack_f32(module.bias_hh_l0.detach().numpy()),
    }


def _packed_head(net, action_net) -> dict:
    return {
        "W1": pack_f32(net[0].weight.detach().numpy()),
        "b1": pack_f32(net[0].bias.detach().numpy()),
        "W2": pack_f32(net[2].weight.detach().numpy()),
        "b2": pack_f32(net[2].bias.detach().numpy()),
        "Wout": pack_f32(action_net.weight.detach().numpy()),
        "bout": pack_f32(action_net.bias.detach().numpy()),
    }


def _dual_policy(seed=0):
    import torch as th
    from torch import nn

    th.manual_seed(seed)
    obs, hidden, act = 81, 5, 18
    core_a = nn.GRU(obs, hidden)
    core_b = nn.GRU(obs, hidden)
    head_a = nn.Sequential(nn.Linear(hidden, 7), nn.Tanh(),
                           nn.Linear(7, 6), nn.Tanh())
    head_b = nn.Sequential(nn.Linear(hidden, 7), nn.Tanh(),
                           nn.Linear(7, 6), nn.Tanh())
    action_a = nn.Linear(6, act)
    action_b = nn.Linear(6, act)
    payload = {
        "meta": {
            "obs_dim": obs,
            "act_dim": act,
            "activation": "tanh",
            "architecture": ARCH_DUAL_GRU,
            "training_hz": 100.0,
            "phase_hz": 1.333333,
            "walk_yaw_cmd": True,
            "walk_phase_run_on_yaw": True,
            "mode_onehot_order": list(MODE_ONEHOT_ORDER),
            "recurrent_hidden_size": hidden,
            "joint_frame": "robot_abs",
            "joint_contract": "robot_abs_tibia_v2",
        },
        "dual_gru": {
            "core_a": _packed_module(core_a),
            "core_b": _packed_module(core_b),
            "head_a": _packed_head(head_a, action_a),
            "head_b": _packed_head(head_b, action_b),
        },
    }
    return payload, (core_a, core_b, head_a, head_b, action_a, action_b)


def test_pack_f32_roundtrip_and_rejects_bad_byte_count():
    source = np.arange(12, dtype=np.float32).reshape(3, 4)
    np.testing.assert_array_equal(unpack_f32(pack_f32(source)), source)
    bad = pack_f32(source)
    bad["shape"] = [3, 5]
    with pytest.raises(ValueError, match="byte count"):
        unpack_f32(bad)


def test_dual_gru_numpy_sequence_matches_torch_and_threads_both_cores():
    import torch as th

    payload, modules = _dual_policy()
    core_a, core_b, head_a, head_b, action_a, action_b = modules
    errs, info = validate_np_policy(payload)
    assert errs == []
    assert info["architecture"] == ARCH_DUAL_GRU
    assert info["hidden"] == [5, 7, 6]

    model = NumpyDualGruModel(payload)
    h_a = th.zeros(1, 1, 5)
    h_b = th.zeros(1, 1, 5)
    rng = np.random.default_rng(4)
    first_action = None
    for tick in range(18):
        obs = rng.normal(size=81).astype(np.float32)
        obs[-6:] = 0.0
        mode = tick % 6
        obs[-6 + mode] = 1.0
        if tick in (0, 11):
            model.reset()
            h_a.zero_()
            h_b.zero_()
        x = th.as_tensor(obs).view(1, 1, -1)
        with th.no_grad():
            out_a, h_a = core_a(x, h_a)
            out_b, h_b = core_b(x, h_b)
            gate = float(np.clip(obs[-3:].sum(), 0.0, 1.0))
            ref = gate * action_a(head_a(out_a[0, 0])) \
                + (1.0 - gate) * action_b(head_b(out_b[0, 0]))
            ref = ref.clamp(-1.0, 1.0).numpy()
        action = model.act(obs)
        np.testing.assert_allclose(action, ref, rtol=0, atol=3e-7)
        np.testing.assert_allclose(model.h_a, h_a[0, 0].numpy(), atol=3e-7)
        np.testing.assert_allclose(model.h_b, h_b[0, 0].numpy(), atol=3e-7)
        if tick == 0:
            first_action = action.copy()

    # The first tick was hold/core B, but core A must still have advanced:
    # this is what keeps locomotion memory warm across mode switches.
    model.reset()
    hold_obs = np.zeros(81, dtype=np.float32)
    hold_obs[-6] = 1.0
    model.act(hold_obs)
    assert np.linalg.norm(model.h_a) > 0.0

    model.reset()
    obs0 = np.random.default_rng(4).normal(size=81).astype(np.float32)
    obs0[-6:] = 0.0
    obs0[-6] = 1.0
    np.testing.assert_allclose(model.act(obs0), first_action, atol=3e-7)


def test_dual_gru_validation_rejects_mode_order_and_shape_drift():
    payload, _ = _dual_policy()
    payload["meta"]["mode_onehot_order"] = list(reversed(MODE_ONEHOT_ORDER))
    errs, _ = validate_np_policy(payload)
    assert any("mode_onehot_order" in error for error in errs)

    payload, _ = _dual_policy()
    payload["dual_gru"]["core_a"]["weight_ih"]["shape"] = [14, 81]
    errs, _ = validate_np_policy(payload)
    assert any("byte count" in error or "shape" in error for error in errs)
