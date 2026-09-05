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


def _stop_condition_mapping(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe which proposed stops are executor-bound, conservatively."""

    mappings = []
    for condition in parameters.get("stop_conditions", []):
        lowered = str(condition).lower()
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


def qualify(document: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Return a deterministic compatibility report for the saved proposal."""

    parameters = _parameters(document)
    mismatches = [
        key for key, expected in EXPECTED.items()
        if parameters.get(key) != expected
    ]
    # Older saved plans grouped these fields under guarded_supervision; current
    # Robot Lab plans store them directly in parameters.  Accept both shapes so
    # qualification evaluates the saved plan rather than a schema translation.
    supervision = parameters.get("guarded_supervision") or parameters
    camera = parameters.get("camera") or parameters
    schema_ok = (
        not mismatches
        and supervision.get("camera_required") is True
        and supervision.get("expected_live_motors") == 18
        and supervision.get("healthy_motor_samples") == 3
        and supervision.get("remote_abort_required") is True
        and camera.get("minimum_target_tag_coverage_fraction") == 0.9
        and camera.get("required_target_tags")
        == {"L2": [18, 25], "L5": [48, 64]}
    )

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

    # The current vision helper records sidecar state but does not accept or
    # enforce required tag IDs, minimum coverage, or a stale-stream callback.
    camera_guard_ok = all(
        token in run_hw
        for token in (
            "minimum_target_tag_coverage_fraction",
            "required_target_tags",
            "camera_guard_failed",
        )
    )
    # Current preflight performs one feedback read.  The on-robot runner
    # debounces missing IDs and current/temperature trips, but no interface
    # binds three fresh pre-motion samples, voltage bounds, or state age.
    telemetry_guard_ok = all(
        token in run_hw
        for token in (
            "healthy_motor_samples",
            "expected_live_motors",
            "max_state_age_ms",
        )
    ) and "voltage_trip" in runner

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
            if not camera_guard_ok else "Required tag coverage and camera freshness are executor-bound.",
        ),
        "telemetry_guard_binding": _check(
            telemetry_guard_ok,
            ["sysid/run_hw.py", "linux_control/sysid_runner.py"],
            "Preflight reads feedback once; three fresh 18/18 samples, voltage bounds, and state age are not executor-bound."
            if not telemetry_guard_ok else "Fresh motor, voltage, and state-age guards are executor-bound.",
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
    qualified = all(item["passed"] for item in checks.values())
    order = parameters.get("order") if isinstance(parameters.get("order"), list) else []
    stop_mapping = _stop_condition_mapping(parameters)
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
        "command_sequence_digest": _sequence_digest(order, protocols),
        "final_state_limp_assertion": checks["final_limp_binding"],
        "stop_condition_mapping": stop_mapping,
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
    args = parser.parse_args(argv)
    document = json.loads(args.experiment.read_text(encoding="utf-8"))
    project_root = PROTO_DIR
    report = qualify(document, project_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
