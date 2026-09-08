"""Synthetic and pinned-source tests only; no archived-data audit or simulator."""

import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SOURCES = HERE.parents[2] / "hexapod_walker/prototype_sts3215"
SAFETY_SHA = "e64db0dc6afb409ef840cbd2e5a0254ec475b702d4483067f4f308a2638332ad"
FRAME_SHA = "3c46e2d26d419f8afcee6c24b44f1efaeb77cf67e9e7324f2eeb132d6f164041"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return load_file("first_write_under_test", HERE / "first_write_audit.py")


@pytest.fixture(scope="module")
def source_safety_tail():
    """Compile only the exact finite-target/rate/joint-clamp tail, not imports."""
    path = SOURCES / "rl_move/safety.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SAFETY_SHA
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SafetyLayer")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "filter")
    start = next(i for i, n in enumerate(method.body)
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "q" for t in n.targets))
    function = ast.FunctionDef(
        name="pinned_tail",
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in ("self", "proposed_q", "status")],
                           kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=copy.deepcopy(method.body[start:]), decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))

    def evaluate(q, last, cap, lo, hi):
        namespace = {"np": np, "N_JOINTS": 18,
                     "_JOINT_LIMIT_LO_RAD": np.asarray(lo), "_JOINT_LIMIT_HI_RAD": np.asarray(hi)}
        exec(compile(module, str(path) + ":finite-tail", "exec"), namespace)
        safety = SimpleNamespace(_last_safe=np.asarray(last).copy(), max_dq=cap,
                                 entry_ramp_s=0., _entry_ticks=200, _hz=100., entry_start_dq=.001)
        status = object()
        output, returned_status = namespace["pinned_tail"](safety, q, status)
        assert returned_status is status
        assert safety._entry_ticks == 201
        np.testing.assert_array_equal(safety._last_safe, output)
        return output

    return evaluate


@pytest.fixture(scope="module")
def source_frame():
    path = SOURCES / "hexapod_core/joint_frame.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FRAME_SHA
    return load_file("first_write_pinned_joint_frame", path)


def test_vec_requires_finite_eighteen_values_and_float64(audit):
    value = np.arange(18, dtype=np.float32)
    result = audit.vec(value)
    assert result.shape == (18,)
    assert result.dtype == np.dtype("float64")
    np.testing.assert_array_equal(result, value)


@pytest.mark.parametrize("value", [None, 1., np.zeros(17), np.zeros(19), np.zeros((2, 9)),
                                  [np.nan] * 18, [np.inf] * 18, ["bad"] * 18])
def test_vec_rejects_missing_nonfinite_and_wrong_shape(audit, value):
    with pytest.raises((ValueError, TypeError)):
        audit.vec(value)


def test_decode_hardware_limits_at_action_endpoints_and_midpoint(audit):
    center = np.tile([0., .25, 1.], 6)
    half = np.tile([.5, .75, .5], 6)
    for action, expected in [(np.zeros(18), center), (np.ones(18), center + half),
                             (-np.ones(18), center - half)]:
        np.testing.assert_array_equal(audit.decode(action, center, half), expected)


@pytest.mark.parametrize("q,last,cap,lo,hi", [
    (np.tile([.75, -.75, .03125], 6), np.zeros(18), .125, -np.ones(18), np.ones(18)),
    (np.tile([.2, -.2, .1], 6), np.tile([.09375, -.09375, 0.], 6), .125,
     np.full(18, -.1), np.full(18, .1)),
    (np.linspace(-2., 2., 18), np.linspace(-.4, .4, 18), .006544984694978736,
     np.linspace(-.6, -.1, 18), np.linspace(.1, .6, 18)),
], ids=["rate-boundaries", "rate-then-joint-clamp", "mixed-realistic-cap"])
def test_safe_target_matches_exact_pinned_source_tail(audit, source_safety_tail, q, last, cap, lo, hi):
    originals = [x.copy() for x in (q, last, lo, hi)]
    expected = source_safety_tail(q, last, cap, lo, hi)
    actual = audit.safe_target(q, last, cap, lo, hi)
    audit.exact(actual, expected, "pinned safety tail")
    for value, original in zip((q, last, lo, hi), originals):
        np.testing.assert_array_equal(value, original)


@pytest.mark.parametrize("cap", [0., -.1, np.nan, np.inf])
def test_safe_target_rejects_invalid_rate_cap(audit, cap):
    with pytest.raises((ValueError, TypeError)):
        audit.safe_target(np.zeros(18), np.zeros(18), cap, -np.ones(18), np.ones(18))


def test_safe_target_rejects_inverted_joint_bounds(audit):
    lo, hi = -np.ones(18), np.ones(18)
    lo[7] = 2.
    with pytest.raises(ValueError):
        audit.safe_target(np.zeros(18), np.zeros(18), .1, lo, hi)


@pytest.mark.parametrize("base,changed,expected_decoded,expected_safe", [
    (.75, .875, .125, 0.),
    (.75, .625, -.125, 0.),
    (.1875, .0625, -.125, -.0625),
    (0., .0625, .0625, .0625),
    (.75, -.75, -1.5, -.25),
], ids=["outward-masked", "inward-still-masked", "partial", "full", "cross-both-limits"])
def test_masking_distinguishes_requested_sign_and_actual_transfer(audit, base, changed, expected_decoded, expected_safe):
    q0, q1 = np.full(18, base), np.full(18, changed)
    last, lo, hi = np.zeros(18), -np.ones(18), np.ones(18)
    delta = audit.safe_target(q1, last, .125, lo, hi) - audit.safe_target(q0, last, .125, lo, hi)
    np.testing.assert_array_equal(q1 - q0, np.full(18, expected_decoded))
    np.testing.assert_array_equal(delta, np.full(18, expected_safe))
    result = audit.classify(q1 - q0, delta)
    np.testing.assert_array_equal(result["masked"], np.full(18, expected_safe == 0.))
    assert result["decoded_l2_rad"] == pytest.approx(np.sqrt(18) * abs(expected_decoded))
    assert result["safe_l2_rad"] == pytest.approx(np.sqrt(18) * abs(expected_safe))
    assert result["ratio"] == pytest.approx(abs(expected_safe / expected_decoded))


def test_zero_control_has_no_masked_perturbation_and_undefined_ratio(audit):
    result = audit.classify(np.zeros(18), np.zeros(18))
    assert not np.any(result["masked"])
    assert result["decoded_l2_rad"] == result["safe_l2_rad"] == 0.
    assert result["ratio"] is None


def test_mixed_coordinate_masking_uses_exact_zero_not_tolerance(audit):
    decoded = np.tile([.125, -.125, 0.], 6)
    safe = np.tile([0., -.0625, 0.], 6)
    safe[0] = 1e-100
    result = audit.classify(decoded, safe)
    expected = np.tile([True, False, False], 6)
    expected[0] = False
    np.testing.assert_array_equal(result["masked"], expected)


def test_native_mapping_matches_pinned_joint_contract_and_hip_knee_coupling(audit, source_frame):
    logical = np.tile([.125, -.25, .5], 6)
    expected = np.tile([.125, -.25, .75], 6)
    np.testing.assert_array_equal(audit.logical_to_mj(logical), expected)
    audit.exact(audit.logical_to_mj(logical), source_frame.robot_abs_rad_to_mujoco_rel_rad(logical),
                "pinned frame")
    # A logical hip-only command necessarily changes the relative knee goal.
    hip_only = np.zeros(18)
    hip_only[1] = .125
    expected = np.zeros(18)
    expected[1:3] = [.125, -.125]
    np.testing.assert_array_equal(audit.logical_to_mj(hip_only), expected)
    # Equal absolute hip/knee motion cancels at the relative knee hinge.
    hip_only[2] = .125
    expected[2] = 0.
    np.testing.assert_array_equal(audit.logical_to_mj(hip_only), expected)


def test_inject_matches_archived_float32_operation_order_and_preserves_inputs(audit):
    action = np.tile(np.array([.001, -.9934568, .99999994], dtype=np.float32), 6)
    delta = np.tile([.025, -.04, .00000002], 6)
    original_action, original_delta = action.copy(), delta.copy()
    # Literal historical wrapper arithmetic: particularly the final subtraction
    # takes place in float32, rather than promoting its operands to float64.
    raw = np.asarray(action, dtype=np.float32).copy() + delta
    clipped = np.clip(raw, np.full(18, -1., dtype=np.float32), np.ones(18, dtype=np.float32))
    changed = clipped.astype(np.float32)
    applied = changed - np.asarray(action)
    result = audit.inject(action, delta)
    for key, expected in {"raw": raw, "clipped": clipped, "changed": changed, "applied": applied}.items():
        actual = np.asarray(result[key])
        # Receipts may serialize to lists, but their values must retain the
        # historical rounding; changed actions themselves must stay float32.
        np.testing.assert_array_equal(actual, expected)
    assert np.asarray(result["changed"]).dtype == np.dtype("float32")
    assert result["clip_hits"] == 6
    assert np.any(applied.astype(np.float64) != changed.astype(np.float64) - action.astype(np.float64))
    audit.exact(action, original_action, "unchanged source action")
    audit.exact(delta, original_delta, "unchanged frozen delta")


def test_inject_zero_and_synthetic_boundaries(audit):
    action = np.tile(np.array([-1., -.5, 1.], dtype=np.float32), 6)
    result = audit.inject(action, np.zeros(18))
    np.testing.assert_array_equal(result["changed"], action)
    assert not np.any(result["applied"])
    assert result["clip_hits"] == 0
    result = audit.inject(action, np.tile([-.025, .025, .025], 6))
    np.testing.assert_array_equal(result["changed"], np.tile(np.array([-1., -.475, 1.], dtype=np.float32), 6))
    assert result["clip_hits"] == 12


def test_exact_accepts_equal_contiguous_values_and_noncontiguous_copy(audit):
    values = np.arange(36, dtype=np.float64).reshape(2, 18).T
    audit.exact(values, np.ascontiguousarray(values), "equal logical arrays")


@pytest.mark.parametrize("kind", ["dtype", "shape", "one-ulp", "signed-zero"])
def test_exact_rejects_nonidentical_dtype_shape_or_bytes(audit, kind):
    left = np.array([0., 1.], dtype=np.float64)
    right = left.copy()
    if kind == "dtype":
        right = right.astype(np.float32)
    elif kind == "shape":
        right = right.reshape(1, 2)
    elif kind == "one-ulp":
        right[1] = np.nextafter(right[1], 2.)
    else:
        right[0] = -0.
    with pytest.raises(ValueError):
        audit.exact(left, right, "must fail")


@pytest.fixture
def synthetic_cell(source_safety_tail, source_frame):
    """Build a short untouched sequence using pinned source as the oracle."""
    ticks = 3
    lo = np.tile(np.array([-35., -80., -20.]) * (np.pi / 180), 6)
    hi = np.tile(np.array([35., 40., 150.]) * (np.pi / 180), 6)
    center, half = (lo + hi) / 2., (hi - lo) / 2.
    action = np.array([[.0625, -.125, .25] * 6, [-.25, .125, -.5] * 6,
                       [.5, -.25, .125] * 6], dtype=np.float32)
    decoded = center + action.astype(np.float64) * half
    cap = np.deg2rad(.375)
    previous, safe = [], []
    last = center.copy()
    for q in decoded:
        previous.append(last.copy())
        last = source_safety_tail(q, last, cap, lo, hi)
        safe.append(last.copy())
    safe = np.stack(safe)
    chain = {
        "control__tick": np.arange(ticks),
        "control__policy_action": action,
        "control__env_input_action": action.copy(),
        "control__decoder_action": action.astype(np.float64),
        "control__decoded_logical_rad": decoded,
        "control__safety_input_logical_rad": decoded.copy(),
        "control__safety_previous_logical_rad": np.stack(previous),
        "control__safety_output_logical_rad": safe,
        "control__latched_logical_rad": safe.copy(),
        "control__safety_max_delta_rad": np.full(ticks, cap),
        "control__safety_entry_ramp_s": np.zeros(ticks),
        "control__command_start": np.arange(ticks),
        "control__command_count": np.ones(ticks, dtype=np.int64),
        "commands__tick": np.arange(ticks),
        "commands__q_mj_rad": np.stack([source_frame.robot_abs_rad_to_mujoco_rel_rad(q) for q in safe]),
        "control__decoder_reason": np.full(ticks, "", dtype="<U16"),
        "control__safety_reason": np.full(ticks, "", dtype="<U16"),
    }
    for key in ("decoder_ok", "safety_ok"):
        chain["control__" + key] = np.ones(ticks, dtype=bool)
    for key in ("safety_held", "safety_terminate", "terminated", "truncated"):
        chain["control__" + key] = np.zeros(ticks, dtype=bool)
    return chain, {"affine_center_rad": center, "affine_half_range_rad": half}, ticks


def test_validate_cell_accepts_pinned_source_synthetic_chain_without_mutation(audit, synthetic_cell):
    chain, metadata, ticks = synthetic_cell
    original_chain, original_metadata = copy.deepcopy(chain), copy.deepcopy(metadata)
    result = audit.validate_cell(chain, metadata, ticks)
    assert result["ticks"] == result["actual_writes"] == ticks
    for key in ("decode_max_error_rad", "safe_max_error_rad", "write_max_error_rad"):
        assert result[key] == 0.
    for key in chain:
        audit.exact(chain[key], original_chain[key], "unmodified synthetic " + key)
    for key in metadata:
        audit.exact(metadata[key], original_metadata[key], "unmodified metadata " + key)


@pytest.mark.parametrize("kind", [
    "missing-field", "short-vector", "nan", "missing-write", "extra-write",
    "duplicate-tick", "missing-tick", "wrong-command-offset", "reordered-write",
    "policy-env-mismatch", "decoder-action-change", "decoded-value-change",
    "safety-input-change", "previous-safe-change", "safe-output-change", "latched-change",
    "native-write-change", "non-nominal-cap", "active-entry-ramp", "nonempty-reason",
    "wrong-action-dtype", "wrong-decoder-dtype", "wrong-tick-count",
])
def test_validate_cell_rejects_corrupted_transfer_or_coverage(audit, synthetic_cell, kind):
    z, metadata, ticks = synthetic_cell
    if kind == "missing-field":
        del z["control__safety_previous_logical_rad"]
    elif kind == "short-vector":
        z["control__latched_logical_rad"] = z["control__latched_logical_rad"][:, :-1]
    elif kind == "nan":
        z["control__safety_previous_logical_rad"][1, 0] = np.nan
    elif kind == "missing-write":
        z["control__command_count"][1] = 0
    elif kind == "extra-write":
        z["control__command_count"][1] = 2
    elif kind == "duplicate-tick":
        z["control__tick"][1] = 0
    elif kind == "missing-tick":
        z["control__tick"] = z["control__tick"][:-1]
    elif kind == "wrong-command-offset":
        z["control__command_start"][1] = 0
    elif kind == "reordered-write":
        z["commands__tick"] = z["commands__tick"][::-1].copy()
    elif kind == "policy-env-mismatch":
        z["control__env_input_action"][1, 0] += .125
    elif kind == "decoder-action-change":
        z["control__decoder_action"][1, 0] += .125
    elif kind == "decoded-value-change":
        z["control__decoded_logical_rad"][1, 0] += .001
    elif kind == "safety-input-change":
        z["control__safety_input_logical_rad"][1, 0] += .001
    elif kind == "previous-safe-change":
        z["control__safety_previous_logical_rad"][1, 0] += .001
    elif kind == "safe-output-change":
        z["control__safety_output_logical_rad"][1, 0] += .001
    elif kind == "latched-change":
        z["control__latched_logical_rad"][1, 0] += .001
    elif kind == "native-write-change":
        z["commands__q_mj_rad"][1, 0] += .001
    elif kind == "non-nominal-cap":
        z["control__safety_max_delta_rad"][1] = np.nextafter(z["control__safety_max_delta_rad"][1], np.inf)
    elif kind == "active-entry-ramp":
        z["control__safety_entry_ramp_s"][1] = 1.
    elif kind == "nonempty-reason":
        z["control__safety_reason"][1] = "hold"
    elif kind == "wrong-action-dtype":
        z["control__policy_action"] = z["control__policy_action"].astype(np.float64)
        z["control__env_input_action"] = z["control__env_input_action"].astype(np.float64)
    elif kind == "wrong-decoder-dtype":
        z["control__decoder_action"] = z["control__decoder_action"].astype(np.float32)
    else:
        ticks += 1
    with pytest.raises((ValueError, KeyError)):
        audit.validate_cell(z, metadata, ticks)


@pytest.mark.parametrize("key", ["decoder_ok", "safety_ok", "safety_held", "safety_terminate", "terminated", "truncated"])
def test_validate_cell_rejects_every_unhealthy_status(audit, synthetic_cell, key):
    z, metadata, ticks = synthetic_cell
    z["control__" + key][1] = not z["control__" + key][1]
    with pytest.raises(ValueError):
        audit.validate_cell(z, metadata, ticks)
