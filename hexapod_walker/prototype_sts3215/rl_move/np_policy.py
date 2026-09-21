"""Portable RL policies as data: validate, upload, run anywhere.

The robot already runs plain-JSON numpy MLPs (export_policy_np.py
output — tanh(W1 x + b1) -> tanh(W2 h + b2) -> Wout h + bout, clipped
to [-1, 1]; no torch on the board).  The same artifact format now also
supports the mode-gated dual-GRU actor used by the unified stand/walk
line.  GRU arrays are packed as base64 float32 inside JSON: this keeps a
256-wide recurrent actor below the upload limit without adding a binary
sidecar or a new runtime dependency.

POST either artifact to /api/rl/policies on a robot OR the MuJoCo sim
web session and it lands in ~/.hexapod_policies (outside any deploy
tree), shows up in the /api/rl/policies picker, and runs through the
existing /api/rl/* machinery — stand, walk, drive, roles.  Two robots
given the same file walk with the same brain.

Artifact = the export_policy_np.py JSON:

    {"meta": {"name": "...", "notes": "...", "source": "...",
              "obs_dim": 68|72|74|75|81|93, "act_dim": 18,
              "training_hz": 25.0,  # REQUIRED trained control rate
              "hidden": [h1, h2], "activation": "tanh",
              "control_hz": 100,       # optional trained policy rate
              "inner_hz": 100,         # optional robot stream override
              "drive_write_hz": 50,    # optional live robot bus cadence
              "bus_write_speed": 1500, # optional robot bus profile
              "bus_write_acc": 80,
              "profile": {...},        # optional trained goal ramps
              "phase_hz": 0.1667},     # REQUIRED for phase obs
     "W1": [[...]], "b1": [...], "W2": [[...]], "b2": [...],
     "Wout": [[...]], "bout": [...]}

Dual-GRU exports use ``meta.architecture="dual_gru"`` plus a
``dual_gru`` object containing two GRU cells and their two actor heads.
Both cells advance on every tick; the frozen six-wide mode one-hot at
the observation tail selects the output.  ``NumpyDualGruModel`` owns
that persistent hidden state and exposes ``reset()`` at episode
boundaries.

Plain (non-mode-gated) single-GRU exports -- the bare ``--gru`` flag,
e.g. the standwalk DR-ladder lineage -- use
``meta.architecture="gru"`` plus a ``gru`` object: one GRU cell
(``weight_ih``/``weight_hh``/``bias_ih``/``bias_hh``) feeding an
N-layer tanh head (``gru.head.layers``/``Wout``/``bout``, same shape
convention as the generic MLP ``"layers"`` format).  ``NumpyGruModel``
owns the single persistent hidden state.

Actors deeper than two hidden layers, or using ``ELU`` instead of
``tanh`` (e.g. ``net-arch 256,256,128``), export as the generic
N-layer format instead of the legacy two-matrix layout: a top-level
``"layers"`` list of ``{"W": <packed>, "b": <packed>}`` objects (one
per hidden layer, in order) plus the usual ``"Wout"``/``"bout"`` head,
with ``meta.activation`` one of ``"tanh"``/``"elu"`` naming the single
activation shared by every hidden layer.  ``NumpyMLPNLayerModel`` is
the stateless, torch-free runner for this format; it is selected by
``"layers" in obj``, never by ``meta.architecture`` (which stays
``"mlp"`` for both layouts) so old validators/loaders that only know
about ``ARCH_MLP`` still route correctly.

Validation is strict enough to make an upload safe to run: obs_dim
must fit a known slot, act_dim 18, training_hz must declare the trained
control rate, every array must have a consistent shape and finite
values, and a smoke forward pass must return 18 finite actions.

CLI (mirrors dance_script.py):
    uv run python -m rl_move.np_policy validate policies/foo.json
    uv run python -m rl_move.np_policy push foo.json --host http://hexapod.local:8080
    uv run python -m rl_move.np_policy pull foo --host http://robot-b.local:8080
"""
from __future__ import annotations

import base64
import binascii
import json
import math
import re
import urllib.request
from pathlib import Path

import numpy as np

UPLOAD_DIR = Path.home() / ".hexapod_policies"
MAX_POLICY_BYTES = 8_000_000
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
KNOWN_OBS = (68, 72, 74, 75, 81, 93)
PHASE_OBS = (74, 75, 81, 93)
YAW_OBS = (75, 81, 93)
MODE_ONEHOT_ORDER = ("hold", "rise", "lower", "walk", "turn", "quad")
ARCH_MLP = "mlp"
ARCH_DUAL_GRU = "dual_gru"
ARCH_SINGLE_GRU = "gru"
_MATS = ("W1", "b1", "W2", "b2", "Wout", "bout")
_GRU_MATS = ("weight_ih", "weight_hh", "bias_ih", "bias_hh")
# meta.activation values accepted for the generic N-layer MLP format
# (obj["layers"] present). The legacy 2-layer format above stays tanh-only.
_NLAYER_ACTIVATIONS = {
    "tanh": np.tanh,
    # torch.nn.ELU default alpha=1.0: x if x>0 else exp(x)-1.
    "elu": lambda x: np.where(x > 0.0, x, np.expm1(x)),
}


def pack_f32(array) -> dict:
    """JSON-safe, compact representation of one little-endian f32 array."""
    values = np.asarray(array, dtype="<f4", order="C")
    return {
        "dtype": "float32",
        "shape": list(values.shape),
        "data_b64": base64.b64encode(values.tobytes(order="C")).decode("ascii"),
    }


def unpack_f32(obj, *, name: str = "array") -> np.ndarray:
    """Decode a :func:`pack_f32` value, rejecting malformed payloads."""
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be a packed float32 object")
    if obj.get("dtype") != "float32":
        raise ValueError(f"{name}.dtype must be 'float32'")
    shape = obj.get("shape")
    if (not isinstance(shape, list) or len(shape) > 2
            or any(not isinstance(v, int) or v < 0 or v > 100_000
                   for v in shape)):
        raise ValueError(f"{name}.shape is invalid")
    count = math.prod(shape)
    if count > 10_000_000:
        raise ValueError(f"{name} is too large")
    try:
        raw = base64.b64decode(obj.get("data_b64", ""), validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ValueError(f"{name}.data_b64 is invalid: {exc}") from exc
    if len(raw) != count * 4:
        raise ValueError(
            f"{name} byte count {len(raw)} != {count * 4} for shape {shape}")
    # copy(): the immutable decoded bytes would otherwise produce a
    # read-only view, surprising callers that restore recurrent state.
    return np.frombuffer(raw, dtype="<f4").reshape(shape).copy()


def _phase_meta_errors(meta: dict, obs: int, errs: list[str]) -> None:
    if obs not in PHASE_OBS:
        return
    try:
        phase_hz = float(meta["phase_hz"])
    except (KeyError, TypeError, ValueError):
        errs.append(f"obs {obs} (phase clock) requires numeric meta.phase_hz")
    else:
        if not math.isfinite(phase_hz) or phase_hz <= 0.0:
            errs.append("meta.phase_hz must be finite and > 0")
    if obs in (75, 81):
        if meta.get("walk_yaw_cmd") is not True:
            errs.append(f"obs {obs} requires meta.walk_yaw_cmd=true")
        if not isinstance(meta.get("walk_phase_run_on_yaw"), bool):
            errs.append(
                f"obs {obs} requires boolean meta.walk_phase_run_on_yaw")


def _validate_head(head, *, name: str, input_dim: int,
                   act_dim: int) -> tuple[list[str], list[np.ndarray]]:
    errs: list[str] = []
    if not isinstance(head, dict):
        return [f"{name} must be an object"], []
    arrays: dict[str, np.ndarray] = {}
    for key in _MATS:
        if key not in head:
            errs.append(f"missing {name}.{key}")
            continue
        try:
            arrays[key] = unpack_f32(head[key], name=f"{name}.{key}")
        except ValueError as exc:
            errs.append(str(exc))
    if errs:
        return errs, []
    W1, b1 = arrays["W1"], arrays["b1"]
    W2, b2 = arrays["W2"], arrays["b2"]
    Wo, bo = arrays["Wout"], arrays["bout"]
    ranks = {"W1": (W1, 2), "b1": (b1, 1),
             "W2": (W2, 2), "b2": (b2, 1),
             "Wout": (Wo, 2), "bout": (bo, 1)}
    for key, (value, rank) in ranks.items():
        if value.ndim != rank:
            errs.append(f"{name}.{key} must be rank {rank}, got {value.shape}")
        if not np.all(np.isfinite(value)):
            errs.append(f"{name}.{key} contains non-finite values")
    if errs:
        return errs, []
    chain = [
        ("W1", W1, (b1.shape[0], input_dim)),
        ("b1", b1, (W1.shape[0],)),
        ("W2", W2, (b2.shape[0], W1.shape[0])),
        ("b2", b2, (W2.shape[0],)),
        ("Wout", Wo, (act_dim, W2.shape[0])),
        ("bout", bo, (act_dim,)),
    ]
    for key, value, want in chain:
        if value.shape != want:
            errs.append(f"{name}.{key} shape {value.shape} != {want}")
    return errs, [W1, b1, W2, b2, Wo, bo]


def _validate_dual_gru(obj: dict, meta: dict, obs: int,
                       act: int) -> tuple[list[str], dict]:
    errs: list[str] = []
    if obs != 81:
        errs.append(f"dual_gru requires obs_dim 81, got {obs!r}")
    if list(meta.get("mode_onehot_order") or []) != list(MODE_ONEHOT_ORDER):
        errs.append(
            "dual_gru requires frozen meta.mode_onehot_order "
            f"{list(MODE_ONEHOT_ORDER)!r}")
    try:
        hidden = int(meta["recurrent_hidden_size"])
    except (KeyError, TypeError, ValueError):
        errs.append("dual_gru requires integer meta.recurrent_hidden_size")
        hidden = 0
    if hidden < 1 or hidden > 4096:
        errs.append("meta.recurrent_hidden_size must be in [1, 4096]")
    recurrent = obj.get("dual_gru")
    if not isinstance(recurrent, dict):
        return errs + ["missing dual_gru object"], {}

    decoded: dict[str, dict[str, np.ndarray]] = {}
    for core_name in ("core_a", "core_b"):
        core = recurrent.get(core_name)
        if not isinstance(core, dict):
            errs.append(f"missing dual_gru.{core_name} object")
            continue
        decoded[core_name] = {}
        for key in _GRU_MATS:
            try:
                value = unpack_f32(
                    core.get(key), name=f"dual_gru.{core_name}.{key}")
            except ValueError as exc:
                errs.append(str(exc))
                continue
            decoded[core_name][key] = value
        if len(decoded[core_name]) == len(_GRU_MATS) and hidden:
            expected = {
                "weight_ih": (3 * hidden, obs),
                "weight_hh": (3 * hidden, hidden),
                "bias_ih": (3 * hidden,),
                "bias_hh": (3 * hidden,),
            }
            for key, want in expected.items():
                value = decoded[core_name][key]
                if value.shape != want:
                    errs.append(
                        f"dual_gru.{core_name}.{key} shape "
                        f"{value.shape} != {want}")
                if not np.all(np.isfinite(value)):
                    errs.append(
                        f"dual_gru.{core_name}.{key} contains non-finite values")

    head_dims: list[int] | None = None
    for head_name in ("head_a", "head_b"):
        head_errs, arrays = _validate_head(
            recurrent.get(head_name), name=f"dual_gru.{head_name}",
            input_dim=hidden, act_dim=act)
        errs.extend(head_errs)
        if arrays:
            dims = [int(arrays[0].shape[0]), int(arrays[2].shape[0])]
            if head_dims is None:
                head_dims = dims
            elif dims != head_dims:
                errs.append(
                    f"dual_gru actor head widths differ: {head_dims} vs {dims}")
            decoded[head_name] = dict(zip(_MATS, arrays, strict=True))
    return errs, {"hidden": [hidden, *(head_dims or [])], "decoded": decoded}


def _validate_single_gru(obj: dict, meta: dict, obs: int,
                         act: int) -> tuple[list[str], dict]:
    """Validate the plain (non-mode-gated) single-core GRU format.

    Mirrors :func:`_validate_dual_gru`'s shape checks for the one-core
    case: no mode one-hot tail, an N-layer tanh head (reuses
    :func:`_validate_mlp_nlayer`'s shape logic with the GRU's hidden
    size as the head's input width).
    """
    errs: list[str] = []
    try:
        hidden = int(meta["recurrent_hidden_size"])
    except (KeyError, TypeError, ValueError):
        errs.append("gru requires integer meta.recurrent_hidden_size")
        hidden = 0
    if hidden < 1 or hidden > 4096:
        errs.append("meta.recurrent_hidden_size must be in [1, 4096]")
    recurrent = obj.get("gru")
    if not isinstance(recurrent, dict):
        return errs + ["missing gru object"], {}

    decoded: dict[str, np.ndarray] = {}
    for key in _GRU_MATS:
        try:
            decoded[key] = unpack_f32(recurrent.get(key), name=f"gru.{key}")
        except ValueError as exc:
            errs.append(str(exc))
    if len(decoded) == len(_GRU_MATS) and hidden:
        expected = {
            "weight_ih": (3 * hidden, obs),
            "weight_hh": (3 * hidden, hidden),
            "bias_ih": (3 * hidden,),
            "bias_hh": (3 * hidden,),
        }
        for key, want in expected.items():
            value = decoded[key]
            if value.shape != want:
                errs.append(f"gru.{key} shape {value.shape} != {want}")
            if not np.all(np.isfinite(value)):
                errs.append(f"gru.{key} contains non-finite values")

    head = recurrent.get("head")
    if not isinstance(head, dict):
        return errs + ["missing gru.head object"], {}
    if head.get("activation", "tanh") not in _NLAYER_ACTIVATIONS:
        errs.append(
            "gru.head.activation must be one of "
            f"{sorted(_NLAYER_ACTIVATIONS)}, got {head.get('activation')!r}")
    head_errs, head_info = _validate_mlp_nlayer(
        {"layers": head.get("layers"), "Wout": head.get("Wout"),
         "bout": head.get("bout")},
        hidden or 0, act)
    errs.extend(f"gru.head.{e}" for e in head_errs)
    if errs:
        return errs, {}
    return [], {"hidden": [hidden, *head_info["hidden"]]}


def _validate_mlp_nlayer(obj: dict, obs: int, act: int) -> tuple[list[str], dict]:
    """Validate the generic N-layer ``obj["layers"]`` MLP format."""
    errs: list[str] = []
    layers = obj.get("layers")
    if not isinstance(layers, list) or not layers:
        return ["layers must be a non-empty list"], {}
    if len(layers) > 16:
        return ["layers has an implausible length (>16)"], {}
    decoded: list[tuple[np.ndarray, np.ndarray]] = []
    input_dim = obs
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict) or "W" not in layer or "b" not in layer:
            errs.append(f"layers[{i}] must be an object with W and b")
            continue
        try:
            W = unpack_f32(layer["W"], name=f"layers[{i}].W")
            b = unpack_f32(layer["b"], name=f"layers[{i}].b")
        except ValueError as exc:
            errs.append(str(exc))
            continue
        if W.ndim != 2 or b.ndim != 1:
            errs.append(f"layers[{i}] W/b must be rank 2/1, got "
                        f"{W.shape}/{b.shape}")
            continue
        if not (np.all(np.isfinite(W)) and np.all(np.isfinite(b))):
            errs.append(f"layers[{i}] contains non-finite values")
            continue
        if W.shape != (b.shape[0], input_dim):
            errs.append(
                f"layers[{i}].W shape {W.shape} != {(b.shape[0], input_dim)}")
            continue
        decoded.append((W, b))
        input_dim = int(W.shape[0])
    if errs:
        return errs, {}
    for key in ("Wout", "bout"):
        if key not in obj:
            errs.append(f"missing {key}")
    if errs:
        return errs, {}
    try:
        Wo = unpack_f32(obj["Wout"], name="Wout")
        bo = unpack_f32(obj["bout"], name="bout")
    except ValueError as exc:
        return [str(exc)], {}
    if not (np.all(np.isfinite(Wo)) and np.all(np.isfinite(bo))):
        return ["Wout/bout contains non-finite values"], {}
    if Wo.shape != (act, input_dim) or bo.shape != (act,):
        errs.append(
            f"Wout/bout shape {Wo.shape}/{bo.shape} != "
            f"{(act, input_dim)}/{(act,)}")
        return errs, {}
    return [], {"hidden": [int(w.shape[0]) for w, _ in decoded]}


def validate_np_policy(obj) -> tuple[list[str], dict]:
    """Return (errors, info).  Empty errors == runnable policy."""
    errs: list[str] = []
    info: dict = {}
    if not isinstance(obj, dict):
        return (["policy must be a JSON object"], info)
    meta = obj.get("meta")
    if not isinstance(meta, dict):
        return (["missing meta object"], info)
    obs = meta.get("obs_dim")
    act = meta.get("act_dim")
    architecture = str(meta.get("architecture", ARCH_MLP))
    info = {"name": meta.get("name") or "", "obs_dim": obs,
            "act_dim": act, "source": meta.get("source", ""),
            "notes": meta.get("notes", ""),
            "architecture": architecture}
    if obs not in KNOWN_OBS:
        errs.append(f"obs_dim {obs!r} fits no slot "
                    f"(68 stance / 72 walk / 74 phase-walk / "
                    f"75 phase+yaw walk / 81 dual-GRU unified / "
                    f"93 AMP yaw+fault walk)")
    if act != 18:
        errs.append(f"act_dim must be 18, got {act!r}")
    try:
        from hexapod_core.joint_frame import require_robot_abs_joint_frame
        require_robot_abs_joint_frame(meta, source="numpy policy")
    except ValueError as exc:
        errs.append(str(exc))
    if architecture not in (ARCH_MLP, ARCH_DUAL_GRU, ARCH_SINGLE_GRU):
        errs.append(f"unsupported meta.architecture {architecture!r}")
    is_nlayer = architecture == ARCH_MLP and isinstance(obj, dict) and "layers" in obj
    activation = meta.get("activation", "tanh")
    if is_nlayer:
        if activation not in _NLAYER_ACTIVATIONS:
            errs.append(
                "meta.activation must be one of "
                f"{sorted(_NLAYER_ACTIVATIONS)} for the layers format, "
                f"got {activation!r}")
    elif activation != "tanh":
        errs.append("activation must be tanh (export_policy_np contract)")
    try:
        training_hz = float(meta["training_hz"])
    except KeyError:
        errs.append("meta.training_hz is required")
    except (TypeError, ValueError):
        errs.append("meta.training_hz must be numeric")
    else:
        if (not math.isfinite(training_hz)
                or training_hz < 1.0 or training_hz > 200.0):
            errs.append("meta.training_hz must be finite and in [1, 200]")
        else:
            info["training_hz"] = training_hz
    _phase_meta_errors(meta, obs, errs)
    if errs:
        return (errs, info)

    if architecture == ARCH_DUAL_GRU:
        recurrent_errs, recurrent_info = _validate_dual_gru(
            obj, meta, int(obs), int(act))
        errs.extend(recurrent_errs)
        if errs:
            return errs, info
        info["hidden"] = recurrent_info["hidden"]
        try:
            model = NumpyDualGruModel(obj)
            probe = np.zeros(int(obs), dtype=np.float32)
            probe[-len(MODE_ONEHOT_ORDER)] = 1.0
            action = model.act(probe)
        except (KeyError, TypeError, ValueError) as exc:
            errs.append(f"dual_gru smoke forward pass failed: {exc}")
        else:
            if action.shape != (18,) or not np.all(np.isfinite(action)):
                errs.append("dual_gru smoke forward pass failed")
        return errs, info

    if architecture == ARCH_SINGLE_GRU:
        recurrent_errs, recurrent_info = _validate_single_gru(
            obj, meta, int(obs), int(act))
        errs.extend(recurrent_errs)
        if errs:
            return errs, info
        info["hidden"] = recurrent_info["hidden"]
        try:
            model = NumpyGruModel(obj)
            probe = np.zeros(int(obs), dtype=np.float32)
            action = model.act(probe)
        except (KeyError, TypeError, ValueError) as exc:
            errs.append(f"gru smoke forward pass failed: {exc}")
        else:
            if action.shape != (18,) or not np.all(np.isfinite(action)):
                errs.append("gru smoke forward pass failed")
        return errs, info

    if is_nlayer:
        layer_errs, layer_info = _validate_mlp_nlayer(
            obj, int(obs), int(act))
        errs.extend(layer_errs)
        if errs:
            return errs, info
        info["hidden"] = layer_info["hidden"]
        try:
            model = NumpyMLPNLayerModel(obj)
            action = model.act(np.zeros(int(obs), dtype=np.float64))
        except (KeyError, TypeError, ValueError) as exc:
            errs.append(f"mlp_nlayer smoke forward pass failed: {exc}")
        else:
            if action.shape != (18,) or not np.all(np.isfinite(action)):
                errs.append("mlp_nlayer smoke forward pass failed")
        return errs, info

    if obs == 81:
        return (["obs_dim 81 requires meta.architecture='dual_gru'"], info)
    for k in _MATS:
        if k not in obj:
            errs.append(f"missing matrix {k}")
    if errs:
        return (errs, info)
    try:
        W1 = np.asarray(obj["W1"], dtype=np.float64)
        b1 = np.asarray(obj["b1"], dtype=np.float64)
        W2 = np.asarray(obj["W2"], dtype=np.float64)
        b2 = np.asarray(obj["b2"], dtype=np.float64)
        Wo = np.asarray(obj["Wout"], dtype=np.float64)
        bo = np.asarray(obj["bout"], dtype=np.float64)
    except (TypeError, ValueError) as e:
        return ([f"matrices are not numeric arrays: {e}"], info)
    ranks = {"W1": (W1, 2), "b1": (b1, 1),
             "W2": (W2, 2), "b2": (b2, 1),
             "Wout": (Wo, 2), "bout": (bo, 1)}
    for name, (matrix, rank) in ranks.items():
        if matrix.ndim != rank:
            errs.append(f"{name} must be rank {rank}, got {matrix.shape}")
        if not np.all(np.isfinite(matrix)):
            errs.append(f"{name} contains non-finite values")
    if errs:
        return errs, info
    chain = [("W1", W1, (b1.shape[0], obs)), ("b1", b1, (W1.shape[0],)),
             ("W2", W2, (b2.shape[0], W1.shape[0])),
             ("b2", b2, (W2.shape[0],)),
             ("Wout", Wo, (18, W2.shape[0])), ("bout", bo, (18,))]
    for name, m, want in chain:
        if m.shape != want:
            errs.append(f"{name} shape {m.shape} != {want}")
    if errs:
        return (errs, info)
    # Smoke forward pass — an uploaded brain must at least not explode.
    h = np.tanh(W1 @ np.zeros(obs) + b1)
    h = np.tanh(W2 @ h + b2)
    a = np.clip(Wo @ h + bo, -1.0, 1.0)
    if a.shape != (18,) or not np.all(np.isfinite(a)):
        errs.append("smoke forward pass failed")
    info["hidden"] = [int(W1.shape[0]), int(W2.shape[0])]
    return (errs, info)


class _Space:
    def __init__(self, n: int):
        self.shape = (n,)


class NumpyMLPModel:
    """SB3-shaped adapter around a numpy MLP policy.

    Exposes exactly the surface the sim web session uses on PPO
    checkpoints — .predict(obs, deterministic=True) -> (action, None),
    .observation_space.shape, .action_space.shape — so an uploaded
    JSON policy plugs into the same stance/walk/role slots.
    """

    def __init__(self, obj: dict, path: Path | None = None):
        self.meta = dict(obj["meta"])
        self.path = path
        self.W1 = np.asarray(obj["W1"], dtype=np.float64)
        self.b1 = np.asarray(obj["b1"], dtype=np.float64)
        self.W2 = np.asarray(obj["W2"], dtype=np.float64)
        self.b2 = np.asarray(obj["b2"], dtype=np.float64)
        self.Wo = np.asarray(obj["Wout"], dtype=np.float64)
        self.bo = np.asarray(obj["bout"], dtype=np.float64)
        self.observation_space = _Space(int(self.meta["obs_dim"]))
        self.action_space = _Space(int(self.meta.get("act_dim", 18)))
        self.hidden = [int(self.W1.shape[0]), int(self.W2.shape[0])]
        self.recurrent = False

    def reset(self) -> None:
        """Stateless compatibility hook shared with recurrent artifacts."""

    def act(self, obs: np.ndarray) -> np.ndarray:
        h = np.tanh(self.W1 @ obs + self.b1)
        h = np.tanh(self.W2 @ h + self.b2)
        return np.clip(self.Wo @ h + self.bo, -1.0, 1.0)

    def predict(self, obs, deterministic: bool = True, **_kw):
        return self.act(np.asarray(obs, dtype=np.float64)), None


class NumpyMLPNLayerModel:
    """Stateless numpy runner for the generic N-layer MLP format.

    Same duck-typed surface as :class:`NumpyMLPModel` (``.act``,
    ``.predict``, ``.reset``, ``.observation_space``/``.action_space``,
    ``.hidden``, ``.recurrent``), so every existing caller of
    ``load_np_policy`` keeps working unchanged. Selected by ``"layers"
    in obj`` (see :func:`validate_np_policy`), not by
    ``meta.architecture`` — deeper nets and non-tanh activations (e.g.
    the ``net-arch 256,256,128`` + ELU PPO shape) export here instead
    of the legacy fixed two-matrix layout, which stays byte-for-byte
    unchanged for existing artifacts.
    """

    def __init__(self, obj: dict, path: Path | None = None):
        self.meta = dict(obj["meta"])
        self.path = path
        self.layers = [
            (unpack_f32(layer["W"], name="layers.W"),
             unpack_f32(layer["b"], name="layers.b"))
            for layer in obj["layers"]
        ]
        self.Wo = unpack_f32(obj["Wout"], name="Wout")
        self.bo = unpack_f32(obj["bout"], name="bout")
        activation = str(self.meta.get("activation", "tanh"))
        if activation not in _NLAYER_ACTIVATIONS:
            raise ValueError(f"unsupported activation {activation!r}")
        self._act_fn = _NLAYER_ACTIVATIONS[activation]
        self.observation_space = _Space(int(self.meta["obs_dim"]))
        self.action_space = _Space(int(self.meta.get("act_dim", 18)))
        self.hidden = [int(W.shape[0]) for W, _ in self.layers]
        self.recurrent = False

    def reset(self) -> None:
        """Stateless compatibility hook shared with recurrent artifacts."""

    def act(self, obs: np.ndarray) -> np.ndarray:
        h = np.asarray(obs, dtype=np.float64)
        for W, b in self.layers:
            h = self._act_fn(W @ h + b)
        return np.clip(self.Wo @ h + self.bo, -1.0, 1.0)

    def predict(self, obs, deterministic: bool = True, **_kw):
        return self.act(np.asarray(obs, dtype=np.float64)), None


class _NumpyGruCell:
    """One PyTorch-compatible, single-layer GRU cell in numpy."""

    def __init__(self, obj: dict):
        self.weight_ih = unpack_f32(obj["weight_ih"], name="weight_ih")
        self.weight_hh = unpack_f32(obj["weight_hh"], name="weight_hh")
        self.bias_ih = unpack_f32(obj["bias_ih"], name="bias_ih")
        self.bias_hh = unpack_f32(obj["bias_hh"], name="bias_hh")
        self.hidden_size = h = self.weight_hh.shape[1]
        nx = self.input_size = self.weight_ih.shape[1]
        # Hot-path layout (2026-09-21, measured on the Uno Q: a 256-wide cell cost 1.08 ms of
        # which only 0.43 ms was the two matvecs; the rest was ~20 small numpy calls, and
        # np.clip alone was ~70 us per call through its Python wrapper).  step() works on
        # one vector xh = [x, 1, h]: the constant 1 lets every bias ride inside its matvec.
        #   rz  = sigmoid([W_ih_rz | b_rz | W_hh_rz] @ xh)          one matvec, no adds
        #   n   = tanh([W_in | b_in] @ xh[:nx+1] + r * ([b_hn | W_hn] @ xh[nx:]))
        # The candidate keeps its hidden half separate because torch gates it by r first.
        f32 = np.float32
        b_rz = (self.bias_ih[:2 * h] + self.bias_hh[:2 * h]).astype(f32)
        self._w_rz = np.ascontiguousarray(np.concatenate(
            [self.weight_ih[:2 * h], b_rz[:, None], self.weight_hh[:2 * h]], axis=1), dtype=f32)
        self._w_in = np.ascontiguousarray(np.concatenate(
            [self.weight_ih[2 * h:], self.bias_ih[2 * h:, None]], axis=1), dtype=f32)
        self._w_hn = np.ascontiguousarray(np.concatenate(
            [self.bias_hh[2 * h:, None], self.weight_hh[2 * h:]], axis=1), dtype=f32)
        self._one = np.ones(1, dtype=f32)
        self._nx = nx

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        # sigmoid(x) = (1 + tanh(x/2)) / 2: saturates cleanly on an extreme observation,
        # no overflow, no clip; matches torch.sigmoid to float32 precision.
        x *= 0.5
        np.tanh(x, out=x)
        x += 1.0
        x *= 0.5
        return x

    def step(self, x: np.ndarray, hidden: np.ndarray) -> np.ndarray:
        h, nx = self.hidden_size, self._nx
        xh = np.concatenate((np.asarray(x, dtype=np.float32), self._one, hidden))
        rz = self._sigmoid(self._w_rz @ xh)
        reset, update = rz[:h], rz[h:]
        hn = self._w_hn @ xh[nx:]
        hn *= reset
        hn += self._w_in @ xh[:nx + 1]
        candidate = np.tanh(hn, out=hn)
        # (1 - z) * n + z * h == n + z * (h - n): fewer ops, same value to float32 rounding
        delta = hidden - candidate
        delta *= update
        delta += candidate
        return delta


class _NumpyActorHead:
    def __init__(self, obj: dict):
        for key in _MATS:
            setattr(self, key, unpack_f32(obj[key], name=key))

    def forward(self, recurrent_out: np.ndarray) -> np.ndarray:
        h = np.tanh(self.W1 @ recurrent_out + self.b1)
        h = np.tanh(self.W2 @ h + self.b2)
        return self.Wout @ h + self.bout


class NumpyDualGruModel:
    """Persistent dual-core GRU deterministic actor, without torch.

    Both cores advance for every observation, exactly like
    :class:`rl_move.sim.gru_policy.DualGruActorCriticPolicy`.  The sum
    of the final three mode slots (walk/turn/quad) gates core A; the
    first three slots gate core B.  One object must therefore be kept
    across command/mode changes for the whole control episode.
    """

    def __init__(self, obj: dict, path: Path | None = None):
        self.meta = dict(obj["meta"])
        self.path = path
        recurrent = obj["dual_gru"]
        self.core_a = _NumpyGruCell(recurrent["core_a"])
        self.core_b = _NumpyGruCell(recurrent["core_b"])
        self.head_a = _NumpyActorHead(recurrent["head_a"])
        self.head_b = _NumpyActorHead(recurrent["head_b"])
        self.observation_space = _Space(int(self.meta["obs_dim"]))
        self.action_space = _Space(int(self.meta.get("act_dim", 18)))
        self.hidden = [self.core_a.hidden_size,
                       int(self.head_a.W1.shape[0]),
                       int(self.head_a.W2.shape[0])]
        self.recurrent = True
        self.reset()

    def reset(self) -> None:
        self.h_a = np.zeros(self.core_a.hidden_size, dtype=np.float32)
        self.h_b = np.zeros(self.core_b.hidden_size, dtype=np.float32)

    def _state_tuple(self):
        hidden = np.stack([self.h_a, self.h_b])[:, None, :]
        return hidden.copy(), np.zeros_like(hidden)

    def _restore_state(self, state) -> None:
        hidden = state[0] if isinstance(state, tuple) else state
        hidden = np.asarray(hidden, dtype=np.float32)
        if hidden.ndim == 3 and hidden.shape[1] == 1:
            hidden = hidden[:, 0, :]
        want = (2, self.core_a.hidden_size)
        if hidden.shape != want:
            raise ValueError(f"dual_gru state shape {hidden.shape} != {want}")
        self.h_a = hidden[0].copy()
        self.h_b = hidden[1].copy()

    def act(self, obs: np.ndarray) -> np.ndarray:
        obs = np.asarray(obs, dtype=np.float32)
        if obs.shape != self.observation_space.shape:
            raise ValueError(
                f"observation shape {obs.shape} != {self.observation_space.shape}")
        self.h_a = self.core_a.step(obs, self.h_a)
        self.h_b = self.core_b.step(obs, self.h_b)
        gate = min(1.0, max(0.0, float(np.sum(obs[-3:]))))
        mean = gate * self.head_a.forward(self.h_a) \
            + (1.0 - gate) * self.head_b.forward(self.h_b)
        np.maximum(mean, -1.0, out=mean)
        np.minimum(mean, 1.0, out=mean)
        return mean.astype(np.float32, copy=False)

    def predict(self, obs, state=None, episode_start=None,
                deterministic: bool = True, **_kw):
        del deterministic  # exported actors are deterministic-only
        batched = np.asarray(obs).ndim == 2
        values = np.asarray(obs, dtype=np.float32)
        if batched:
            if values.shape[0] != 1:
                raise ValueError("numpy dual_gru supports one stream at a time")
            values = values[0]
        if state is not None:
            self._restore_state(state)
        if episode_start is not None and bool(np.asarray(episode_start).reshape(-1)[0]):
            self.reset()
        action = self.act(values)
        if batched:
            action = action[None, :]
        return action, self._state_tuple()


class NumpyGruModel:
    """Persistent single-core GRU deterministic actor, without torch.

    Mirrors :class:`rl_move.sim.gru_policy.GruActorCriticPolicy` (the
    plain, non-mode-gated recurrent actor trained with a bare
    ``--gru`` flag -- e.g. the standwalk DR-ladder lineage) rather
    than the mode-gated dual-core actor above: one GRU cell advances
    every tick, feeding an N-layer tanh head. Recurrent state is kept
    in sb3-contrib's OWN convention (``h`` shaped
    ``(num_layers=1, n_envs, hidden)``, ``c`` all-zeros and unused) --
    unlike :class:`NumpyDualGruModel`'s custom 2-core packing, there is
    only one core here, so no repacking is needed and a state captured
    from (or fed back into) the real ``RecurrentPPO`` model round-trips
    unchanged.
    """

    def __init__(self, obj: dict, path: Path | None = None):
        self.meta = dict(obj["meta"])
        self.path = path
        recurrent = obj["gru"]
        self.core = _NumpyGruCell(recurrent)
        head = recurrent["head"]
        self.layers = [
            (unpack_f32(layer["W"], name="gru.head.layers.W"),
             unpack_f32(layer["b"], name="gru.head.layers.b"))
            for layer in head["layers"]
        ]
        self.Wo = unpack_f32(head["Wout"], name="gru.head.Wout")
        self.bo = unpack_f32(head["bout"], name="gru.head.bout")
        activation = str(head.get("activation", "tanh"))
        if activation not in _NLAYER_ACTIVATIONS:
            raise ValueError(f"unsupported activation {activation!r}")
        self._act_fn = _NLAYER_ACTIVATIONS[activation]
        self.observation_space = _Space(int(self.meta["obs_dim"]))
        self.action_space = _Space(int(self.meta.get("act_dim", 18)))
        self.hidden = [self.core.hidden_size] + [
            int(W.shape[0]) for W, _ in self.layers]
        self.recurrent = True
        self.reset()

    def reset(self) -> None:
        self.h = np.zeros(self.core.hidden_size, dtype=np.float32)

    def _state_tuple(self):
        hidden = self.h[None, None, :].copy()
        return hidden, np.zeros_like(hidden)

    def _restore_state(self, state) -> None:
        hidden = state[0] if isinstance(state, tuple) else state
        hidden = np.asarray(hidden, dtype=np.float32)
        if hidden.ndim == 3 and hidden.shape[0] == 1 and hidden.shape[1] == 1:
            hidden = hidden[0, 0, :]
        want = (self.core.hidden_size,)
        if hidden.shape != want:
            raise ValueError(f"gru state shape {hidden.shape} != {want}")
        self.h = hidden.copy()

    def act(self, obs: np.ndarray) -> np.ndarray:
        obs = np.asarray(obs, dtype=np.float32)
        if obs.shape != self.observation_space.shape:
            raise ValueError(
                f"observation shape {obs.shape} != {self.observation_space.shape}")
        self.h = self.core.step(obs, self.h)
        hidden = self.h
        for W, b in self.layers:
            hidden = self._act_fn(W @ hidden + b)
        mean = self.Wo @ hidden + self.bo
        return np.clip(mean, -1.0, 1.0).astype(np.float32, copy=False)

    def predict(self, obs, state=None, episode_start=None,
                deterministic: bool = True, **_kw):
        del deterministic  # exported actors are deterministic-only
        batched = np.asarray(obs).ndim == 2
        values = np.asarray(obs, dtype=np.float32)
        if batched:
            if values.shape[0] != 1:
                raise ValueError("numpy gru supports one stream at a time")
            values = values[0]
        if state is not None:
            self._restore_state(state)
        if episode_start is not None and bool(np.asarray(episode_start).reshape(-1)[0]):
            self.reset()
        action = self.act(values)
        if batched:
            action = action[None, :]
        return action, self._state_tuple()


def load_np_policy(
    path,
) -> NumpyMLPModel | NumpyMLPNLayerModel | NumpyDualGruModel | NumpyGruModel:
    obj = json.loads(Path(path).read_text())
    errs, _ = validate_np_policy(obj)
    if errs:
        raise ValueError(f"{Path(path).name}: " + "; ".join(errs[:3]))
    if obj["meta"].get("architecture", ARCH_MLP) == ARCH_DUAL_GRU:
        return NumpyDualGruModel(obj, Path(path))
    if obj["meta"].get("architecture") == ARCH_SINGLE_GRU:
        return NumpyGruModel(obj, Path(path))
    if "layers" in obj:
        return NumpyMLPNLayerModel(obj, Path(path))
    return NumpyMLPModel(obj, Path(path))


def np_policy_obs_width(path) -> int | None:
    """meta.obs_dim of a policy JSON, or None if unreadable."""
    try:
        return int(json.loads(Path(path).read_text())["meta"]["obs_dim"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def safe_policy_name(name: str) -> str | None:
    """Sanitized file stem for an uploaded policy, or None if invalid."""
    stem = Path(str(name)).name
    if stem.endswith(".json"):
        stem = stem[:-5]
    return stem if NAME_RE.match(stem) else None


# ---------------------------------------------------------------------------
# CLI

def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a policy JSON")
    v.add_argument("file")
    p = sub.add_parser("push", help="upload a policy to a robot or sim")
    p.add_argument("file")
    p.add_argument("--host", default="http://hexapod.local:8080")
    p.add_argument("--name", default=None,
                   help="store under this name (default: file stem)")
    g = sub.add_parser("pull", help="download an uploaded policy")
    g.add_argument("name")
    g.add_argument("--host", default="http://hexapod.local:8080")
    g.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    if args.cmd == "validate":
        obj = json.loads(Path(args.file).read_text())
        errs, info = validate_np_policy(obj)
        if errs:
            raise SystemExit("INVALID: " + "; ".join(errs))
        print(f"ok: obs {info['obs_dim']}, hidden {info['hidden']}, "
              f"name {info['name'] or Path(args.file).stem!r}")
    elif args.cmd == "push":
        path = Path(args.file)
        body = path.read_bytes()
        if len(body) > MAX_POLICY_BYTES:
            raise SystemExit(f"{path} too big")
        name = safe_policy_name(args.name or path.stem)
        if name is None:
            raise SystemExit("bad name (want [A-Za-z0-9._-]{1,64})")
        req = urllib.request.Request(
            args.host.rstrip("/") + "/api/rl/policies?name=" + name,
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"{path.name}: {r.read().decode()}")
    elif args.cmd == "pull":
        url = (args.host.rstrip("/") + "/api/rl/policies/"
               + str(args.name))
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        out = Path(args.out or f"{args.name}.json")
        out.write_bytes(data)
        print(f"pulled {args.name} -> {out} ({len(data)/1024:.0f} KB)")


if __name__ == "__main__":
    _cli()
