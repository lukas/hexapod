"""Export an SB3 actor to a dependency-light JSON numpy policy.

Supported actor architectures:

* PPO ``MlpPolicy``: two tanh layers and a linear action head (legacy
  artifact layout, still accepted unchanged).
* PPO ``MlpPolicy`` with a deeper stack and/or ELU activation (e.g.
  ``net-arch 256,256,128``): exports as the generic N-layer
  ``"layers"`` format instead (see ``rl_move/np_policy.py``); the
  legacy two-matrix layout above is untouched when the actor actually
  is Linear,Tanh,Linear,Tanh.
* ``DualGruActorCriticPolicy``: the two actor GRU cells plus their two
  tanh action heads. Both hidden states persist and advance every tick;
  the six-wide mode one-hot at the observation tail selects the output.

The Uno Q does not need torch. Recurrent arrays are base64-packed
little-endian float32 values inside the JSON so the artifact remains a
single portable file and stays under the policy-upload size limit.

The exporter runs deterministic sequence parity against the original
checkpoint before writing. It also applies the normal coordinate-stamp
gate: legacy checkpoints must first be copied and stamped explicitly;
the exporter never relabels a source checkpoint.

Usage::

    uv run python -m rl_move.sim.export_policy_np \
        --policy rl_move/sim/policies/ppo_goal_cw_lower.zip \
        --out linux_control/rl_policy_weights.json \
        --training-hz 25
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.np_policy import (
    ARCH_DUAL_GRU,
    ARCH_MLP,
    MODE_ONEHOT_ORDER,
    NumpyDualGruModel,
    NumpyMLPNLayerModel,
    pack_f32,
    validate_np_policy,
)


def _t2l(tensor) -> list:
    return tensor.detach().cpu().numpy().astype(np.float64).tolist()


def _tpack(tensor) -> dict:
    return pack_f32(tensor.detach().cpu().numpy())


def _two_layer_tanh(net, *, name: str):
    """Return the two Linear layers of the frozen supported head shape."""
    import torch.nn as nn

    if (len(net) != 4 or not isinstance(net[0], nn.Linear)
            or not isinstance(net[1], nn.Tanh)
            or not isinstance(net[2], nn.Linear)
            or not isinstance(net[3], nn.Tanh)):
        raise ValueError(
            f"{name}: expected Linear,Tanh,Linear,Tanh; got {net!r}")
    return net[0], net[2]


def _generic_hidden_layers(net, *, name: str):
    """Split an arbitrary-depth Sequential into (Linear, activation) pairs.

    Every hidden layer must share ONE activation (all ``Tanh`` or all
    ``ELU``) so a single ``meta.activation`` string describes the whole
    stack; this matches every net-arch this project trains today
    (SB3's ``MlpExtractor`` applies one ``activation_fn`` throughout).
    Returns ``(linears, activation_name)``.
    """
    import torch.nn as nn

    layers = list(net)
    if not layers or len(layers) % 2 != 0:
        raise ValueError(
            f"{name}: expected alternating Linear/activation pairs, "
            f"got {net!r}")
    linears: list = []
    activation_name: str | None = None
    for i in range(0, len(layers), 2):
        lin, act = layers[i], layers[i + 1]
        if not isinstance(lin, nn.Linear):
            raise ValueError(f"{name}: expected Linear at index {i}, got {lin!r}")
        if isinstance(act, nn.Tanh):
            this_name = "tanh"
        elif isinstance(act, nn.ELU):
            this_name = "elu"
        else:
            raise ValueError(
                f"{name}: unsupported activation {act!r} at index {i + 1} "
                "(only Tanh/ELU are exportable)")
        if activation_name is None:
            activation_name = this_name
        elif activation_name != this_name:
            raise ValueError(
                f"{name}: mixed activations ({activation_name} then "
                f"{this_name}) are not exportable")
        linears.append(lin)
    assert activation_name is not None  # len(layers) > 0 guaranteed above
    return linears, activation_name


def _packed_head(net, action_net, *, name: str) -> dict:
    first, second = _two_layer_tanh(net, name=name)
    return {
        "W1": _tpack(first.weight),
        "b1": _tpack(first.bias),
        "W2": _tpack(second.weight),
        "b2": _tpack(second.bias),
        "Wout": _tpack(action_net.weight),
        "bout": _tpack(action_net.bias),
    }


def _validated_hz(value) -> float:
    if value is None:
        raise ValueError(
            "training_hz is required; pass --training-hz or include "
            "{\"training_hz\": ...} in --extra-meta")
    hz = float(value)
    if not math.isfinite(hz) or hz < 1.0 or hz > 200.0:
        raise ValueError(
            f"training_hz must be finite and in [1, 200]: {hz!r}")
    return hz


def _structural_meta(pol, architecture: str) -> dict:
    meta = {
        "obs_dim": int(pol.observation_space.shape[0]),
        "act_dim": int(pol.action_space.shape[0]),
        "activation": "tanh",
        "architecture": architecture,
        "joint_frame": FRAME_ROBOT_ABS,
        "joint_contract": JOINT_CONTRACT,
    }
    if architecture == ARCH_DUAL_GRU:
        meta.update({
            "recurrent_hidden_size": int(pol.lstm_actor.hidden_size),
            "mode_onehot_order": list(MODE_ONEHOT_ORDER),
        })
    return meta


def _mlp_payload(pol, meta: dict) -> dict:
    net = pol.mlp_extractor.policy_net
    try:
        first, second = _two_layer_tanh(net, name="MLP actor")
    except ValueError:
        # Not the frozen legacy 2-layer-tanh shape (e.g. net-arch
        # 256,256,128 + ELU): fall back to the generic N-layer format.
        # This never touches the legacy branch above, which stays
        # byte-for-byte identical for every existing 2-layer-tanh actor.
        return _mlp_payload_nlayer(pol, meta)
    meta["hidden"] = [int(first.out_features), int(second.out_features)]
    return {
        "meta": meta,
        "W1": _t2l(first.weight),
        "b1": _t2l(first.bias),
        "W2": _t2l(second.weight),
        "b2": _t2l(second.bias),
        "Wout": _t2l(pol.action_net.weight),
        "bout": _t2l(pol.action_net.bias),
    }


def _mlp_payload_nlayer(pol, meta: dict) -> dict:
    net = pol.mlp_extractor.policy_net
    linears, activation = _generic_hidden_layers(net, name="MLP actor")
    meta["hidden"] = [int(lin.out_features) for lin in linears]
    meta["activation"] = activation
    return {
        "meta": meta,
        "layers": [
            {"W": _tpack(lin.weight), "b": _tpack(lin.bias)}
            for lin in linears
        ],
        "Wout": _tpack(pol.action_net.weight),
        "bout": _tpack(pol.action_net.bias),
    }


def _dual_gru_payload(pol, meta: dict) -> dict:
    from .gru_policy import DualGruActorCriticPolicy

    if not isinstance(pol, DualGruActorCriticPolicy):
        raise TypeError(
            f"expected DualGruActorCriticPolicy, got {type(pol)}")
    if (pol.lstm_actor.core_a.num_layers != 1
            or pol.lstm_actor.core_b.num_layers != 1):
        raise ValueError("only single-layer dual GRU cores are supported")
    # The deployed actor reads the raw observation directly. A learned
    # feature extractor would need to be serialized as another layer.
    if (getattr(pol.features_extractor, "features_dim", None)
            != int(pol.observation_space.shape[0])):
        raise ValueError(
            "dual-GRU export requires an identity/flatten extractor")

    def core(module) -> dict:
        return {
            "weight_ih": _tpack(module.weight_ih_l0),
            "weight_hh": _tpack(module.weight_hh_l0),
            "bias_ih": _tpack(module.bias_ih_l0),
            "bias_hh": _tpack(module.bias_hh_l0),
        }

    first, second = _two_layer_tanh(
        pol.mlp_extractor.policy_net, name="dual-GRU core-A actor head")
    meta["hidden"] = [int(pol.lstm_actor.hidden_size),
                      int(first.out_features), int(second.out_features)]
    return {
        "meta": meta,
        "dual_gru": {
            "core_a": core(pol.lstm_actor.core_a),
            "core_b": core(pol.lstm_actor.core_b),
            "head_a": _packed_head(
                pol.mlp_extractor.policy_net, pol.action_net, name="head_a"),
            "head_b": _packed_head(
                pol.mlp_extractor_b.policy_net, pol.action_net_b,
                name="head_b"),
        },
    }


def _parity_mlp(model, payload: dict, samples: int = 200) -> float:
    if "layers" in payload:
        # Generic N-layer path: run through the ACTUAL production loader
        # class, not a re-derived formula, so parity also exercises the
        # exact code the robot/sim runtime will execute.
        numpy_model = NumpyMLPNLayerModel(payload)
        rng = np.random.default_rng(0)
        worst = 0.0
        for _ in range(samples):
            obs = rng.normal(
                0, 1, payload["meta"]["obs_dim"]).astype(np.float32)
            action_np = numpy_model.act(obs)
            action_sb3, _ = model.predict(obs, deterministic=True)
            worst = max(
                worst, float(np.max(np.abs(action_np - action_sb3))))
        return worst
    W1 = np.asarray(payload["W1"])
    b1 = np.asarray(payload["b1"])
    W2 = np.asarray(payload["W2"])
    b2 = np.asarray(payload["b2"])
    Wo = np.asarray(payload["Wout"])
    bo = np.asarray(payload["bout"])
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(samples):
        obs = rng.normal(
            0, 1, payload["meta"]["obs_dim"]).astype(np.float32)
        hidden = np.tanh(W1 @ obs + b1)
        hidden = np.tanh(W2 @ hidden + b2)
        action_np = np.clip(Wo @ hidden + bo, -1.0, 1.0)
        action_sb3, _ = model.predict(obs, deterministic=True)
        worst = max(
            worst, float(np.max(np.abs(action_np - action_sb3))))
    return worst


def _parity_dual_gru(model, payload: dict, samples: int = 200
                     ) -> tuple[float, float]:
    """Sequence parity, including mode switches and episode resets."""
    numpy_model = NumpyDualGruModel(payload)
    rng = np.random.default_rng(0)
    state_sb3 = None
    state_np = None
    worst_action = 0.0
    worst_hidden = 0.0
    reset_ticks = {0, 37, 113, 177}
    for tick in range(samples):
        obs = rng.normal(
            0, 1, payload["meta"]["obs_dim"]).astype(np.float32)
        obs[-len(MODE_ONEHOT_ORDER):] = 0.0
        obs[-len(MODE_ONEHOT_ORDER) + tick % len(MODE_ONEHOT_ORDER)] = 1.0
        episode_start = np.asarray([tick in reset_ticks], dtype=bool)
        action_sb3, state_sb3 = model.predict(
            obs, state=state_sb3, episode_start=episode_start,
            deterministic=True)
        action_np, state_np = numpy_model.predict(
            obs, state=state_np, episode_start=episode_start,
            deterministic=True)
        worst_action = max(
            worst_action, float(np.max(np.abs(action_np - action_sb3))))
        worst_hidden = max(
            worst_hidden,
            float(np.max(np.abs(np.asarray(state_np[0])
                                - np.asarray(state_sb3[0])))))
    return worst_action, worst_hidden


def export(policy_path: str, out_path: str, *, name: str = "",
           notes: str = "", extra_meta: dict | None = None,
           training_hz: float | None = None,
           control_hz: float | None = None) -> dict:
    """Export, verify, and write one portable actor artifact."""
    from .gru_policy import DualGruActorCriticPolicy, load_checkpoint_auto

    model = load_checkpoint_auto(policy_path, device="cpu")
    if (getattr(model, "joint_frame", None) != FRAME_ROBOT_ABS
            or getattr(model, "joint_contract", None) != JOINT_CONTRACT):
        raise ValueError(
            f"{policy_path}: checkpoint lacks the {FRAME_ROBOT_ABS!r}/"
            f"{JOINT_CONTRACT!r} coordinate contract; old checkpoints "
            "cannot be relabeled during export")
    pol = model.policy
    if getattr(pol, "lstm_actor", None) is not None:
        if not isinstance(pol, DualGruActorCriticPolicy):
            raise ValueError(
                "only mode-gated DualGruActorCriticPolicy recurrent "
                f"checkpoints are deployable (got {type(pol).__name__})")
        architecture = ARCH_DUAL_GRU
    else:
        architecture = ARCH_MLP

    extra = dict(extra_meta or {})
    hz = _validated_hz(extra.pop("training_hz", training_hz))
    meta = {
        "source": str(policy_path),
        **({"name": name} if name else {}),
        **({"notes": notes} if notes else {}),
        **_structural_meta(pol, architecture),
        "training_hz": hz,
        **extra,
    }
    meta.setdefault(
        "control_hz", float(control_hz if control_hz is not None else hz))
    # These widths are unambiguous descendants of the phase+yaw lineage.
    # Write the contract explicitly so the validator/runner never has to
    # infer it from a number alone.
    if meta["obs_dim"] in (75, 81):
        meta["walk_yaw_cmd"] = True
    required = _structural_meta(pol, architecture)
    for key, expected in required.items():
        if meta.get(key) != expected:
            raise ValueError(
                f"extra metadata cannot override structural {key}: "
                f"{meta.get(key)!r} != {expected!r}")

    payload = (_dual_gru_payload(pol, meta)
               if architecture == ARCH_DUAL_GRU
               else _mlp_payload(pol, meta))
    errors, _ = validate_np_policy(payload)
    if errors:
        raise ValueError(
            "export metadata/payload invalid: " + "; ".join(errors))

    if architecture == ARCH_DUAL_GRU:
        worst, hidden_worst = _parity_dual_gru(model, payload)
        print("parity: max |a_np - a_sb3| over recurrent sequence = "
              f"{worst:.2e}; max |h_np - h_sb3| = {hidden_worst:.2e}")
        if worst >= 1e-5 or hidden_worst >= 1e-5:
            raise AssertionError("numpy dual-GRU forward does not match SB3")
    else:
        worst = _parity_mlp(model, payload)
        print(
            f"parity: max |a_np - a_sb3| over 200 random obs = {worst:.2e}")
        if worst >= 1e-5:
            raise AssertionError("numpy MLP forward does not match SB3")

    out = Path(out_path)
    out.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    return payload


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="",
                    help="display name for the robot's policy picker")
    ap.add_argument("--notes", default="",
                    help="one-line operator notes shown in the picker")
    ap.add_argument("--extra-meta", default="",
                    help="JSON object merged into meta (phase_hz and the "
                         "trained command/safety contract belong here)")
    ap.add_argument("--training-hz", type=float, default=None,
                    help="trained control-loop rate (required)")
    ap.add_argument("--inner-hz", type=float, default=None,
                    help="optional robot-only servo stream rate override")
    ap.add_argument("--bus-write-speed", type=int, default=None,
                    help="optional robot bus write_speed for this policy")
    ap.add_argument("--bus-write-acc", type=int, default=None,
                    help="optional robot bus write_acc for this policy")
    ap.add_argument("--control-hz", type=float, default=None,
                    help="trained control rate alias (default: training_hz)")
    args = ap.parse_args()
    extra_meta = json.loads(args.extra_meta) if args.extra_meta else {}
    for key, value in (
        ("control_hz", args.control_hz),
        ("inner_hz", args.inner_hz),
        ("bus_write_speed", args.bus_write_speed),
        ("bus_write_acc", args.bus_write_acc),
    ):
        if value is not None:
            extra_meta[key] = value
    export(args.policy, args.out, name=args.name, notes=args.notes,
           extra_meta=extra_meta or None,
           training_hz=args.training_hz,
           control_hz=args.control_hz)


if __name__ == "__main__":
    _main()
