"""Regression tests for the offline sealed walking evidence audit."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from rl_move.scripts.audit_sealed_walk_experiment import AuditError, PILOTS, audit


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(run_dir: Path) -> str:
    run_dir.mkdir()
    for index, pilot in enumerate(PILOTS):
        fell = pilot == "course"
        summary_ok = pilot != "forward"
        result = {
            "ok": True,
            "duration_s": 2.0 if pilot != "course" else 6.0,
            "ticks": 200,
            "overruns": 50,
            "fell": fell,
            "max_current_a": 0.8,
            "tilt_rel_max_deg": 4.0,
            "tail_tilt_max_deg": 55.5 if fell else 8.0,
        }
        entry = {
            "phase": pilot,
            "request": None if pilot == "course" else {"vx": 0.08, "vy": 0},
            "result": result,
        }
        if pilot == "course":
            entry["segments"] = [{"name": name} for name in PILOTS[:4]]
        (run_dir / f"{pilot}_summary.json").write_text(
            json.dumps(
                {
                    "ok": summary_ok,
                    "error": None if summary_ok else "health samples not clear",
                    "requested_phases": [pilot],
                    "policy": {
                        "walk": {
                            "safety": {"max_roll_deg": 25, "max_pitch_deg": 25}
                        }
                    },
                    "results": [entry],
                }
            )
        )
        base = 1000.0 + index * 100
        phase = "direction_course" if pilot == "course" else f"drive_{pilot}"
        telemetry = [
            {
                "unix_s": base + offset,
                "phase": phase,
                "live": 17 if pilot == "forward" and offset == 1 else 18,
                "roll_deg": offset,
                "pitch_deg": -offset,
                "max_current_a": 0.1 + offset,
                "bus_current_a": 0.2 + offset,
                "max_temp_c": 40 + offset,
                "min_voltage_v": 11.3 - 0.1 * offset,
            }
            for offset in (1, 2, 4)
        ]
        _write_csv(
            run_dir / f"{pilot}_telemetry.csv", list(telemetry[0]), telemetry
        )
        camera = [
            {
                "frame": frame,
                "elapsed_s": frame,
                "unix_s": base + frame,
                "width": 1280,
                "height": 720,
            }
            for frame in range(6)
        ]
        _write_csv(
            run_dir / f"{pilot}_camera_timestamps.csv", list(camera[0]), camera
        )

    artifacts = []
    for path in sorted(run_dir.iterdir()):
        payload = path.read_bytes()
        artifacts.append(
            {
                "name": path.name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {"schema_version": 2, "artifacts": artifacts}
    (run_dir / "manifest.json").write_text(json.dumps(manifest))
    return hashlib.sha256((run_dir / "manifest.json").read_bytes()).hexdigest()


def test_audit_verifies_and_surfaces_acceptance_blockers(tmp_path):
    run_dir = tmp_path / "experiment-1"
    manifest_sha256 = _fixture(run_dir)
    report = audit(run_dir, manifest_sha256)

    assert report["manifest_verified"] is True
    assert report["camera_telemetry_alignment"][
        "all_phase_windows_overlap_camera"
    ] is True
    assert report["acceptance"] == {
        "runner_completion_is_locomotion_acceptance": False,
        "all_pilot_summaries_ok": False,
        "recorded_falls": 1,
        "metric_direction_or_displacement_available": False,
        "decision": "not_accepted",
        "reason": (
            "One pilot failed overall health clearance, the course records a fall, "
            "and the sealed bundle lacks phase-bound metric chassis trajectories."
        ),
    }
    assert report["pilots"][0]["result"]["overrun_rate"] == pytest.approx(0.25)
    assert report["pilots"][0]["timing"]["telemetry_drive_label_sample_span_s"] == 3
    assert report["pilots"][0]["phase_windows"][0]["camera_first_frame"] == 1
    assert report["pilots"][0]["phase_windows"][0]["camera_last_frame"] == 4
    assert {flag["kind"] for flag in report["safety_and_integrity_flags"]} == {
        "overall_runner_failure",
        "recorded_fall",
        "incomplete_servo_scan_present",
        "reported_tail_tilt_exceeds_policy_limit",
    }


def test_audit_refuses_tampered_artifact(tmp_path):
    run_dir = tmp_path / "experiment-2"
    manifest_sha256 = _fixture(run_dir)
    (run_dir / "course_summary.json").write_text("{}")

    with pytest.raises(AuditError, match="artifact .* differs"):
        audit(run_dir, manifest_sha256)


def test_audit_refuses_wrong_manifest_digest(tmp_path):
    run_dir = tmp_path / "experiment-3"
    _fixture(run_dir)

    with pytest.raises(AuditError, match="manifest digest mismatch"):
        audit(run_dir, "0" * 64)
