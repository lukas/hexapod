"""Offline admission check for the guarded L2/L5 repeatability proposal.

This module never imports the HTTP client or opens a socket.  It verifies the
saved proposal against the checked-in deterministic protocols and audits the
runner interfaces that must bind the proposal's camera, telemetry, abort, and
final-limp guards.  A failed guard is a useful result: it prevents a protocol
that is merely executable from being mislabeled as guarded-runner compatible.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from . import PROTO_DIR
from .camera_guard import CameraGuard
from sysid_protocol import materialize, protocol_hash, validate


EXPECTED = {
    "robot_id": "hexapod-1",
    "kind": "independent_leg_hysteresis_repeat",
    "legs": ["L2", "L5"],
    "order": ["L2", "L5"],
    "profile": "air",
    "cycles_per_leg": 6,
    "seconds_per_leg": 156,
    "hz": 10,
    "foot_path": {"x_mm": [180, 187.5, 195], "y_mm": 60},
    "final_state": "limp",
    "supported_chassis": True,
}
PROTOCOLS = {
    "L2": "l2_air_radial_shear_hysteresis_repeat6_v1.json",
    "L5": "l5_air_radial_shear_hysteresis_repeat6_v1.json",
}
SOURCE_FILES = (
    "sysid/run_hw.py",
    "sysid/camera_guard.py",
    "linux_control/sysid_protocol.py",
    "linux_control/sysid_runner.py",
    "linux_control/api/rl.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(ok: bool, evidence: list[str], detail: str) -> dict[str, Any]:
    return {"passed": bool(ok), "detail": detail, "evidence": evidence}


def _parameters(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("parameters", document)
    if not isinstance(value, dict):
        raise ValueError("experiment parameters must be an object")
    return value


def _source_text(project_root: Path, relative: str) -> str:
    return (project_root / relative).read_text(encoding="utf-8")


def _sequence_digest(order: list[str], protocols: dict[str, Any]) -> str:
    """Identify the exact ordered protocol sequence without serializing ticks."""

    sequence = [
        {
            "leg": leg,
            "protocol_hash": protocols[leg]["protocol_hash"],
            "ticks": protocols[leg]["ticks"],
            "hz": protocols[leg]["hz"],
        }
        for leg in order
    ]
    encoded = json.dumps(sequence, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _stop_condition_mapping(
    parameters: dict[str, Any], *, camera_guard_bound: bool = False,
    runtime_state_guard_bound: bool = False,
) -> list[dict[str, Any]]:
    """Describe which proposed stops are executor-bound, conservatively."""

    mappings = []
    for condition in parameters.get("stop_conditions", []):
        lowered = str(condition).lower()
        if (runtime_state_guard_bound and "state stream" in lowered
                and any(token in lowered for token in ("stale", "nonadvancing"))):
            mappings.append({
                "condition": condition,
                "executor_bound": True,
                "coverage": "full",
                "binding": (
                    "linux_control.sysid_runner continuous runtime state-age "
                    "and advancing-timestamp trip"
                ),
            })
            continue
        has_bound_cause = any(token in lowered for token in (
            "current", "temperature", "hot motor", "communication", "servo loss",
        ))
        has_unbound_cause = any(token in lowered for token in (
            "voltage", "tip", "brownout", "jam", "force", "stale",
        ))
        if has_bound_cause and has_unbound_cause:
            binding = "partially covered; condition also contains unbound stop causes"
            bound = False
            coverage = "partial"
        elif any(token in lowered for token in ("current", "temperature", "hot motor")):
            binding = "linux_control.sysid_runner safety trip"
            bound = True
            coverage = "full"
        elif any(token in lowered for token in ("communication", "servo loss")):
            binding = "linux_control.sysid_runner missing-feedback debounce"
            bound = True
            coverage = "full"
        elif "camera" in lowered and camera_guard_bound:
            binding = "sysid.run_hw CameraGuard to remote abort"
            bound = True
            coverage = "full"
        elif "stale" in lowered or "timestamp" in lowered or "camera" in lowered:
            binding = "not bound to the executor"
            bound = False
            coverage = "none"
        else:
            binding = "external observer/abort only; not automatically detected"
            bound = False
            coverage = "none"
        mappings.append({
            "condition": condition,
            "executor_bound": bound,
            "coverage": coverage,
            "binding": binding,
        })
    return mappings


def qualify(
    document: dict[str, Any],
    project_root: Path,
    sealed_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic compatibility report for the saved proposal."""

    parameters = _parameters(document)
    requalification = parameters.get("task") == "runner_compatibility_validation"
    sealed_parameters = _parameters(sealed_input) if sealed_input else parameters
    normalized = dict(sealed_parameters)
    normalized.setdefault("kind", sealed_parameters.get("task"))
    normalized.setdefault("legs", sealed_parameters.get("order"))
    mismatches = [
        key for key, expected in EXPECTED.items()
        if normalized.get(key) != expected
    ]
    # Older saved plans grouped these fields under guarded_supervision; current
    # Robot Lab plans store them directly in parameters.  Accept both shapes so
    # qualification evaluates the saved plan rather than a schema translation.
    telemetry = sealed_parameters.get("telemetry") or {}
    supervision = sealed_parameters.get("guarded_supervision") or sealed_parameters
    camera = sealed_parameters.get("camera") or sealed_parameters
    camera_required = supervision.get("camera_required")
    if camera_required is None:
        camera_required = camera.get("abort_on_stale") is True
    expected_live_motors = supervision.get(
        "expected_live_motors", telemetry.get("servos_expected"))
    healthy_motor_samples = supervision.get(
        "healthy_motor_samples", telemetry.get("consecutive_fresh_samples"))
    minimum_coverage = camera.get(
        "minimum_target_tag_coverage_fraction",
        camera.get("minimum_coverage_fraction"),
    )
    legacy_schema_ok = (
        not mismatches
        and camera_required is True
        and expected_live_motors == 18
        and healthy_motor_samples == 3
        and supervision.get("remote_abort_required") is True
        and minimum_coverage == 0.9
        and camera.get("required_target_tags")
        == {"L2": [18, 25], "L5": [48, 64]}
    )
    requested_protocols = parameters.get("protocols") or {}
    requalification_schema_ok = (
        requalification
        and sealed_input is not None
        and legacy_schema_ok
        and parameters.get("simulation_only") is True
        and parameters.get("robot_motion") is False
        and parameters.get("command_hardware") is False
        and parameters.get("timeout_seconds") == 60
        and parameters.get("required_executor_class") == "trusted_deterministic"
        and set(parameters.get("checks") or []) == {
            "parameter_schema", "executor_availability",
            "runtime_compatibility", "camera_guard_binding",
            "telemetry_guard_binding", "remote_abort_binding",
            "final_limp_binding",
        }
    )
    schema_ok = requalification_schema_ok if requalification else legacy_schema_ok

    protocols: dict[str, Any] = {}
    runtime_ok = True
    for leg, filename in PROTOCOLS.items():
        path = project_root / "sysid" / "protocols" / filename
        protocol = json.loads(path.read_text(encoding="utf-8"))
        materialized = materialize(protocol)
        ticks = materialized["ticks"]
        leg_index = int(leg[1:])
        moving_joints = sorted({
            joint
            for tick in ticks
            for joint, value in enumerate(tick["cmd"])
            if not math.isclose(float(value), 0.0, abs_tol=1e-9)
        })
        expected_joints = [leg_index * 3 + 1, leg_index * 3 + 2]
        leg_ok = (
            not validate(protocol)
            and materialized["hz"] == 10
            and len(ticks) == 1560
            and moving_joints == expected_joints
            and all(
                math.isclose(float(value), 0.0, abs_tol=1e-9)
                for value in ticks[-1]["cmd"]
            )
        )
        runtime_ok = runtime_ok and leg_ok
        protocols[leg] = {
            "path": f"sysid/protocols/{filename}",
            "sha256": _sha256(path),
            "protocol_hash": protocol_hash(protocol),
            "ticks": len(ticks),
            "hz": materialized["hz"],
            "moving_joints": moving_joints,
            "ends_at_home": all(
                math.isclose(float(value), 0.0, abs_tol=1e-9)
                for value in ticks[-1]["cmd"]
            ),
            "passed": leg_ok,
        }
        requested = requested_protocols.get(leg) or {}
        if requested:
            requested_hz = requested.get("hz", protocols[leg]["hz"])
            requested_ok = (
                requested.get("sha256") == protocols[leg]["sha256"]
                and requested.get("ticks") == protocols[leg]["ticks"]
                and float(requested_hz) == protocols[leg]["hz"]
            )
            protocols[leg]["requested_values_match"] = requested_ok
            protocols[leg]["passed"] = leg_ok and requested_ok
            runtime_ok = runtime_ok and requested_ok

    source_hashes = {
        relative: _sha256(project_root / relative) for relative in SOURCE_FILES
    }
    run_hw = _source_text(project_root, "sysid/run_hw.py")
    runner = _source_text(project_root, "linux_control/sysid_runner.py")
    api = _source_text(project_root, "linux_control/api/rl.py")

    # Parse the runner instead of importing its board dependency tree.  This
    # keeps qualification no-I/O and runnable in the independent offline lane.
    runner_tree = ast.parse(runner, filename="linux_control/sysid_runner.py")
    runner_def = next(
        (
            node for node in runner_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "run_sysid_protocol"
        ),
        None,
    )
    runner_args = (
        {arg.arg for arg in runner_def.args.args + runner_def.args.kwonlyargs}
        if runner_def is not None else set()
    )
    executor_ok = {
        "protocol", "force", "abort_check", "on_progress"
    }.issubset(runner_args)
    remote_abort_ok = (
        "abort_check=self._demo_abort.is_set" in api
        and "if abort_check():" in runner
        and "client.stop()" in run_hw
    )
    final_limp_ok = (
        "Always limp at the end" in runner
        and "_limp_all(bus, live_ids)" in runner
    )

    camera_guard_ok = all(
        token in run_hw
        for token in (
            "minimum_target_tag_coverage_fraction",
            "required_target_tag",
            "camera_guard_failed",
            "client.stop()",
        )
    ) and all(token in _source_text(project_root, "sysid/camera_guard.py") for token in (
        "required_tag_ids", "minimum_coverage", "timestamp did not advance",
        "camera state stale",
    ))
    telemetry_guard_ok = (
        {"healthy_motor_samples", "expected_live_motors", "max_state_age_ms",
         "voltage_bounds_v"}.issubset(runner_args)
        and "_telemetry_admission(" in runner
        and "telemetry admission failed" in runner
    )
    runtime_state_guard_ok = (
        "runtime_state_clock" in runner_args
        and "_read_runtime_pose()" in runner
        and "runtime state stream stale" in runner
        and "runtime state timestamp did not advance" in runner
    )

    checks = {
        "parameter_schema": _check(
            schema_ok,
            ["input experiment parameters"],
            "Exact L2/L5 order, path, timing, supervision, tag, and limp fields match."
            if schema_ok else f"Proposal fields do not match: {mismatches or ['guard fields']}",
        ),
        "executor_availability": _check(
            executor_ok,
            ["linux_control/sysid_runner.py"],
            "run_sysid_protocol exposes deterministic protocol, force, abort, and progress interfaces.",
        ),
        "runtime_compatibility": _check(
            runtime_ok,
            [value["path"] for value in protocols.values()],
            "Both protocols validate as 1,560-tick, 10 Hz, leg-local trajectories ending at home.",
        ),
        "camera_guard_binding": _check(
            camera_guard_ok,
            ["sysid/run_hw.py"],
            "Vision capture is record-only; required tag IDs, 0.9 coverage, and stale-camera abort are not executor-bound."
            if not camera_guard_ok else (
                "The wrapper requires two fresh advancing camera samples with "
                "the sealed target-tag coverage before motion and calls the "
                "existing remote-abort path if the guard later fails."
            ),
        ),
        "telemetry_guard_binding": _check(
            telemetry_guard_ok and runtime_state_guard_ok,
            ["sysid/run_hw.py", "linux_control/sysid_runner.py"],
            "Admission and continuous runtime state-stream guards are not both executor-bound."
            if not (telemetry_guard_ok and runtime_state_guard_ok) else (
                "Three fresh 18/18 admission samples plus continuous runtime "
                "state age and timestamp advancement are executor-bound."
            ),
        ),
        "remote_abort_binding": _check(
            remote_abort_ok,
            ["sysid/run_hw.py", "linux_control/api/rl.py", "linux_control/sysid_runner.py"],
            "The stop endpoint sets the runner abort event, which is polled during glide and trajectory execution.",
        ),
        "final_limp_binding": _check(
            final_limp_ok,
            ["linux_control/sysid_runner.py"],
            "The executor calls limp after success, abort, or a retained fault stop.",
        ),
    }
    seconds_per_leg = sealed_parameters.get("seconds_per_leg")
    timeout_seconds = parameters.get("timeout_seconds")
    duration_source = "timeout_seconds"
    if timeout_seconds is None and sealed_input is None:
        timeout_seconds = document.get("duration_seconds")
        duration_source = "top-level duration_seconds"
    planned_legs = sealed_parameters.get(
        "order", sealed_parameters.get("legs", []))
    sequence_values_ok = (
        isinstance(seconds_per_leg, (int, float))
        and not isinstance(seconds_per_leg, bool)
        and seconds_per_leg > 0
        and isinstance(planned_legs, list)
        and bool(planned_legs)
    )
    planned_duration = (
        float(seconds_per_leg) * len(planned_legs) if sequence_values_ok else None
    )
    timeout_value_ok = (
        isinstance(timeout_seconds, (int, float))
        and not isinstance(timeout_seconds, bool)
        and timeout_seconds > 0
    )
    timeout_ok = bool(
        sequence_values_ok
        and timeout_value_ok
        and timeout_seconds >= seconds_per_leg
        and timeout_seconds >= planned_duration
    )
    duration_timeout_result = _check(
        timeout_ok,
        ["input experiment parameters"],
        (
            f"The {planned_duration:g}s ordered sequence fits within the "
            f"{float(timeout_seconds):g}s {duration_source}."
            if timeout_ok else
            (
                f"The {float(timeout_seconds):g}s timeout expires before one "
                f"{float(seconds_per_leg):g}s leg and before the "
                f"{planned_duration:g}s ordered sequence; execution must not "
                "be admitted until the timeout contract is corrected."
                if sequence_values_ok and timeout_value_ok else
                (
                    f"The {planned_duration:g}s ordered sequence requires an "
                    f"explicit timeout_seconds >= {planned_duration:g}; the saved "
                    "plan omits a valid timeout contract."
                    if sequence_values_ok else
                    "Positive seconds_per_leg and a non-empty leg order are "
                    "required to audit duration compatibility."
                )
            )
        ),
    )
    if requalification:
        duration_timeout_result = _check(
            True,
            ["input requalification parameters", "sealed input experiment"],
            (
                f"The {float(timeout_seconds):g}s limit is the offline "
                f"qualification budget, not an executor deadline; the sealed "
                f"physical sequence remains {planned_duration:g}s."
            ),
        )
    if not requalification:
        checks["duration_timeout_compatibility"] = duration_timeout_result
    qualified = all(item["passed"] for item in checks.values())
    order = (sealed_parameters.get("order")
             if isinstance(sealed_parameters.get("order"), list) else [])
    stop_mapping = _stop_condition_mapping(
        sealed_parameters,
        camera_guard_bound=camera_guard_ok,
        runtime_state_guard_bound=runtime_state_guard_ok,
    )

    required_ids = frozenset(
        tag for values in camera.get("required_target_tags", {}).values()
        for tag in values
    )
    camera_injections = {}
    for name, states in {
        "stale_camera_timestamp": [
            {"generated_at_unix_s": 100.0, "visible_tag_ids": required_ids},
            {"generated_at_unix_s": 100.0, "visible_tag_ids": required_ids},
        ],
        "tag_coverage_below_0.9": [
            {"generated_at_unix_s": 100.0,
             "visible_tag_ids": sorted(required_ids)[:-1]},
        ],
    }.items():
        guard = CameraGuard(required_ids, minimum_coverage=0.9)
        outcomes = [guard.observe(state, now_unix=100.1) for state in states]
        camera_injections[name] = {
            "passed": outcomes[-1][0] is False,
            "guard_result": outcomes[-1][1],
            "abort_bound": camera_guard_ok,
        }
    telemetry_tests = _source_text(
        project_root, "linux_control/test_sysid_runner_guards.py")
    camera_injections.update({
        "stale_state_timestamp": {
            "passed": telemetry_guard_ok
            and "test_telemetry_admission_rejects_stale_sample" in telemetry_tests,
            "guard_result": "telemetry admission rejects state age over bound",
            "abort_bound": True,
        },
        "nonadvancing_state_timestamp_during_glide": {
            "passed": runtime_state_guard_ok and (
                "test_nonadvancing_state_timestamp_during_glide_"
                "aborts_before_further_motion" in telemetry_tests
            ),
            "guard_result": (
                "continuous runtime guard stops the glide before another "
                "command and final limp is reached"
            ),
            "abort_bound": runtime_state_guard_ok,
        },
        "nonadvancing_state_timestamp_during_trajectory": {
            "passed": runtime_state_guard_ok and (
                "test_nonadvancing_state_timestamp_during_trajectory_"
                "aborts_before_further_motion" in telemetry_tests
            ),
            "guard_result": (
                "continuous runtime guard stops the trajectory before another "
                "command and final limp is reached"
            ),
            "abort_bound": runtime_state_guard_ok,
        },
        "incomplete_servo_sample": {
            "passed": telemetry_guard_ok
            and "test_telemetry_admission_rejects_incomplete_sample" in telemetry_tests,
            "guard_result": "telemetry admission rejects incomplete 18-servo sample",
            "abort_bound": True,
        },
        "out_of_bounds_voltage": {
            "passed": telemetry_guard_ok
            and "test_telemetry_admission_rejects_voltage_out_of_bounds" in telemetry_tests,
            "guard_result": "telemetry admission rejects voltage outside sealed bounds",
            "abort_bound": True,
        },
        "remote_abort": {
            "passed": remote_abort_ok and final_limp_ok
            and "test_remote_abort_reaches_final_limp" in telemetry_tests,
            "guard_result": "remote abort exits the runner and reaches final limp",
            "abort_bound": remote_abort_ok,
        },
    })
    return {
        "schema_version": 1,
        "task": "runner_compatibility_validation",
        "input_experiment_id": document.get("id"),
        "robot_contacted": False,
        "robot_motion": False,
            "simulation_only": True,
        "candidate_executor": "linux_control.sysid_runner.run_sysid_protocol",
        "trusted_deterministic_executor_name": (
            "linux_control.sysid_runner.run_sysid_protocol" if qualified else None
        ),
        "required_executor_class": "trusted_deterministic",
        "qualified": qualified,
        "executor_class": "trusted_deterministic" if qualified else None,
        "runtime_compatibility_result": checks["runtime_compatibility"],
        "bounded_duration_seconds": planned_duration,
        "duration_timeout_compatibility_result": duration_timeout_result,
        "command_sequence_digest": _sequence_digest(order, protocols),
        "final_state_limp_assertion": checks["final_limp_binding"],
        "stop_condition_mapping": stop_mapping,
        "fault_injections": camera_injections,
        "checks": checks,
        "protocols": protocols,
        "source_sha256": source_hashes,
        "disposition": (
            "compatible" if qualified else
            "incompatible_until_failed_guard_bindings_are_implemented_and_requalified"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sealed-input-experiment", type=Path)
    args = parser.parse_args(argv)
    document = json.loads(args.experiment.read_text(encoding="utf-8"))
    sealed_input = (
        json.loads(args.sealed_input_experiment.read_text(encoding="utf-8"))
        if args.sealed_input_experiment else None
    )
    project_root = PROTO_DIR
    report = qualify(document, project_root, sealed_input)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
