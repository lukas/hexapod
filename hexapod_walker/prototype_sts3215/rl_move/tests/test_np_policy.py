import copy

import numpy as np
import pytest

from rl_move.np_policy import (
    ARCH_DUAL_GRU,
    ARCH_TRANSFORMER,
    MODE_ONEHOT_ORDER,
    NumpyDualGruModel,
    NumpyMLPNLayerModel,
    NumpyTransformerModel,
    load_np_policy,
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


def _nlayer_policy(activation="elu", hidden=(4, 3)):
    rng = np.random.default_rng(0)
    layers = []
    in_dim = 68
    for h in hidden:
        layers.append({
            "W": pack_f32(rng.normal(size=(h, in_dim)).astype(np.float32)),
            "b": pack_f32(rng.normal(size=h).astype(np.float32)),
        })
        in_dim = h
    return {
        "meta": {
            "obs_dim": 68,
            "act_dim": 18,
            "activation": activation,
            "training_hz": 100.0,
            "joint_frame": "robot_abs",
            "joint_contract": "robot_abs_tibia_v2",
        },
        "layers": layers,
        "Wout": pack_f32(rng.normal(size=(18, in_dim)).astype(np.float32)),
        "bout": pack_f32(rng.normal(size=18).astype(np.float32)),
    }


def test_nlayer_mlp_valid_policy_loads_and_runs():
    obj = _nlayer_policy()
    errs, info = validate_np_policy(obj)
    assert errs == []
    assert info["hidden"] == [4, 3]
    model = NumpyMLPNLayerModel(obj)
    assert model.recurrent is False
    action, state = model.predict(np.zeros(68, dtype=np.float32))
    assert state is None
    assert action.shape == (18,)
    assert np.all(np.isfinite(action))
    assert np.all(np.abs(action) <= 1.0)


def test_nlayer_mlp_dispatches_through_load_np_policy(tmp_path):
    import json

    path = tmp_path / "deep.json"
    path.write_text(json.dumps(_nlayer_policy()))
    loaded = load_np_policy(path)
    assert isinstance(loaded, NumpyMLPNLayerModel)


def test_nlayer_mlp_rejects_bad_activation():
    obj = _nlayer_policy(activation="relu")
    errs, _ = validate_np_policy(obj)
    assert any("activation" in e for e in errs)


def test_nlayer_mlp_rejects_shape_mismatch():
    obj = _nlayer_policy()
    # Corrupt layers[1].W's input width so it no longer matches
    # layers[0]'s output width.
    bad = unpack_f32(obj["layers"][1]["W"])
    obj["layers"][1]["W"] = pack_f32(bad[:, :-1])
    errs, _ = validate_np_policy(obj)
    assert any("shape" in e for e in errs)


def test_nlayer_mlp_legacy_two_layer_tanh_still_uses_old_format():
    """The plain 2-layer-tanh policy() fixture stays on the W1/W2 path."""
    obj = _policy()
    errs, info = validate_np_policy(obj)
    assert errs == []
    assert "layers" not in obj
    assert info["hidden"] == [1, 1]


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


def _transformer_payload(n_frames=3, frame_w=68, d_model=4, n_heads=2,
                         n_layers=2, ff_dim=6, hidden=(6,), seed=0,
                         extra_meta=None):
    """Build a small (payload, torch reference modules) pair mirroring
    ``transformer_policy.FrameStackTransformerExtractor``'s exact layout,
    without constructing a full gym env / SB3 policy (keeps this test
    fast and torch-import-local, matching the dual-GRU test's style)."""
    import torch as th
    import torch.nn as nn

    th.manual_seed(seed)
    obs_dim = n_frames * frame_w
    embed = nn.Linear(frame_w, d_model)
    pos_embed = nn.Parameter(th.randn(1, n_frames, d_model) * 0.02)
    layers = nn.ModuleList([
        nn.TransformerEncoderLayer(
            d_model, n_heads, dim_feedforward=ff_dim, dropout=0.0,
            activation="gelu", batch_first=True, norm_first=True)
        for _ in range(n_layers)
    ])
    out_norm = nn.LayerNorm(d_model)
    head_linears = []
    in_dim = d_model
    for h in hidden:
        head_linears.append(nn.Linear(in_dim, h))
        in_dim = h
    action_net = nn.Linear(in_dim, 18)
    for m in (embed, out_norm, action_net, *head_linears):
        pass  # default torch init is fine; no reset needed for this test

    def tpack(t):
        return pack_f32(t.detach().numpy())

    def layer_json(layer):
        return {
            "ln1_w": tpack(layer.norm1.weight), "ln1_b": tpack(layer.norm1.bias),
            "in_proj_w": tpack(layer.self_attn.in_proj_weight),
            "in_proj_b": tpack(layer.self_attn.in_proj_bias),
            "out_proj_w": tpack(layer.self_attn.out_proj.weight),
            "out_proj_b": tpack(layer.self_attn.out_proj.bias),
            "ln2_w": tpack(layer.norm2.weight), "ln2_b": tpack(layer.norm2.bias),
            "lin1_w": tpack(layer.linear1.weight), "lin1_b": tpack(layer.linear1.bias),
            "lin2_w": tpack(layer.linear2.weight), "lin2_b": tpack(layer.linear2.bias),
        }

    meta = {
        "obs_dim": obs_dim, "act_dim": 18, "activation": "tanh",
        "architecture": ARCH_TRANSFORMER, "training_hz": 50.0,
        "tf_n_frames": n_frames, "tf_d_model": d_model,
        "tf_n_layers": n_layers, "tf_n_heads": n_heads,
        "joint_frame": "robot_abs", "joint_contract": "robot_abs_tibia_v2",
        **(extra_meta or {}),
    }
    payload = {
        "meta": meta,
        "transformer": {
            "embed_w": tpack(embed.weight), "embed_b": tpack(embed.bias),
            "pos_embed": tpack(pos_embed[0]),
            "out_norm_w": tpack(out_norm.weight), "out_norm_b": tpack(out_norm.bias),
            "layers": [layer_json(layer) for layer in layers],
            "head": {
                "layers": [{"W": tpack(lin.weight), "b": tpack(lin.bias)}
                          for lin in head_linears],
                "Wout": tpack(action_net.weight), "bout": tpack(action_net.bias),
                "activation": "tanh",
            },
        },
    }

    def torch_forward(obs: np.ndarray) -> np.ndarray:
        x = th.as_tensor(obs, dtype=th.float32).view(1, n_frames, frame_w)
        x = x.flip(1)
        x = embed(x) + pos_embed
        causal = th.triu(th.full((n_frames, n_frames), float("-inf")), diagonal=1)
        for layer in layers:
            x = layer(x, src_mask=causal)
        newest = out_norm(x[:, -1])
        h = newest
        for lin in head_linears:
            h = th.tanh(lin(h))
        action = action_net(h)
        return th.clamp(action, -1.0, 1.0)[0].detach().numpy()

    return payload, torch_forward


def test_transformer_numpy_matches_torch_layer_stack():
    payload, torch_forward = _transformer_payload()
    errs, info = validate_np_policy(payload)
    assert errs == []
    assert info["architecture"] == ARCH_TRANSFORMER
    assert info["hidden"] == [4, 6]

    model = NumpyTransformerModel(payload)
    rng = np.random.default_rng(1)
    for _ in range(10):
        obs = rng.normal(size=payload["meta"]["obs_dim"]).astype(np.float32)
        np.testing.assert_allclose(
            model.act(obs), torch_forward(obs), rtol=0, atol=2e-5)


def test_transformer_dispatches_through_load_np_policy(tmp_path):
    payload, _ = _transformer_payload()
    path = tmp_path / "tf.json"
    import json
    path.write_text(json.dumps(payload))
    model = load_np_policy(path)
    assert isinstance(model, NumpyTransformerModel)
    action, state = model.predict(
        np.zeros(payload["meta"]["obs_dim"], dtype=np.float32))
    assert action.shape == (18,)
    assert np.all(np.isfinite(action))
    assert state is None  # stateless: no persistent hidden state to thread


def test_transformer_validation_rejects_frame_count_mismatch():
    payload, _ = _transformer_payload()
    payload["meta"]["obs_dim"] = payload["meta"]["obs_dim"] + 1
    errs, _ = validate_np_policy(payload)
    assert any("not a multiple" in e for e in errs)


def test_transformer_validation_rejects_bad_head_count_of_layers():
    payload, _ = _transformer_payload()
    payload["transformer"]["layers"].pop()
    errs, _ = validate_np_policy(payload)
    assert any("transformer.layers must be a list of length" in e for e in errs)


def test_transformer_requires_phase_hz_when_frame_width_is_phase_obs():
    # frame_width=74 is a phase-clock single-frame width (see PHASE_OBS);
    # a transformer over it must carry meta.phase_hz, exactly like a
    # plain MLP/GRU over the same per-tick layout would.
    payload, _ = _transformer_payload(frame_w=74, d_model=4, n_heads=2)
    errs, _ = validate_np_policy(payload)
    assert any("phase_hz" in e for e in errs)

    payload, _ = _transformer_payload(
        frame_w=74, d_model=4, n_heads=2, extra_meta={"phase_hz": 1.5})
    errs, _ = validate_np_policy(payload)
    assert errs == []


def test_transformer_validation_rejects_heads_not_dividing_d_model():
    payload, _ = _transformer_payload(d_model=4, n_heads=2)
    payload["meta"]["tf_n_heads"] = 3  # 4 % 3 != 0; mutate meta only, no
    # need to rebuild mismatched attention weights -- caught before decode.
    errs, _ = validate_np_policy(payload)
    assert any("tf_n_heads" in e for e in errs)


def test_tick_obs_width_unstacks_transformer_artifacts():
    from rl_move.np_policy import tick_obs_width
    assert tick_obs_width({"obs_dim": 74}) == 74
    assert tick_obs_width({"obs_dim": 81, "architecture": "dual_gru"}) == 81
    assert tick_obs_width({"obs_dim": 1184, "architecture": "transformer",
                           "tf_n_frames": 16}) == 74
    # a stacked width that is not a multiple of K is left alone (validator
    # rejects it elsewhere); unusable meta -> None
    assert tick_obs_width({"obs_dim": 1183, "architecture": "transformer",
                           "tf_n_frames": 16}) == 1183
    assert tick_obs_width({}) is None
    assert tick_obs_width(None) is None
