"""Fast contract tests for the Hexapod 2 replay matrix runner."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from urllib import request

import numpy as np
import pytest

from rl_move.sim import replay_hexapod2_matrix as MATRIX
from rl_move.sim.joint_series_flex import ACTIVE_JOINT_NAMES
from rl_move.sim.replay_hexapod2_matrix import (
    _SafeAuthRedirectHandler,
    _artifact_request,
    _passes_attitude_gate,
    _summaries,
    load_manifest,
    main,
    verify_entries,
)


def _entry(**updates) -> dict:
    entry = {
        "run_id": "abc123",
        "filename": "rl_drive.csv",
        "family": "test_gait",
        "split": "fit",
        "artifact": "csv/trace.csv",
        "sha256": "a" * 64,
    }
    entry.update(updates)
    return entry


def _write_manifest(tmp_path, entries):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema_version": 1, "entries": entries}))
    return path


def test_load_manifest_accepts_fit_and_holdout_entries(tmp_path):
    entries = [
        _entry(),
        _entry(run_id="def456", split="holdout",
               filename="second.csv", artifact="csv/second.csv",
               sha256="b" * 64),
    ]

    manifest = load_manifest(_write_manifest(tmp_path, entries))

    assert manifest["entries"] == entries


@pytest.mark.parametrize("updates", [
    {"artifact": "../secret.csv"},
    {"filename": "nested/trace.csv"},
    {"run_id": "abc/../../runs"},
    {"split": "training"},
    {"sha256": "not-a-sha"},
])
def test_load_manifest_rejects_unsafe_or_invalid_entries(tmp_path, updates):
    with pytest.raises(ValueError):
        load_manifest(_write_manifest(tmp_path, [_entry(**updates)]))


def test_load_manifest_rejects_conflicting_duplicate_artifact(tmp_path):
    entries = [_entry(), _entry(run_id="def456", sha256="b" * 64)]

    with pytest.raises(ValueError, match="conflicting SHA-256"):
        load_manifest(_write_manifest(tmp_path, entries))


def test_artifact_request_only_authenticates_robot_lab_origin():
    publisher = SimpleNamespace(
        base_url="https://lab.example", token="private-token")

    relative = _artifact_request(publisher, "files/trace.csv")
    external = _artifact_request(
        publisher, "https://objects.example/signed/trace.csv")

    assert relative.full_url == "https://lab.example/files/trace.csv"
    assert relative.get_header("Authorization") == "Bearer private-token"
    assert external.get_header("Authorization") is None


def test_cross_origin_redirect_strips_authorization():
    original = request.Request(
        "https://lab.example/files/trace.csv",
        headers={"Authorization": "Bearer private-token"})

    redirected = _SafeAuthRedirectHandler().redirect_request(
        original, None, 302, "Found", {},
        "https://objects.example/signed/trace.csv")

    assert redirected is not None
    assert redirected.get_header("Authorization") is None


def test_https_artifact_url_cannot_downgrade_to_http():
    publisher = SimpleNamespace(
        base_url="https://lab.example", token="private-token")

    with pytest.raises(RuntimeError, match="HTTPS-to-HTTP"):
        _artifact_request(publisher, "http://lab.example/trace.csv")


def test_verify_entries_requires_matching_bytes(tmp_path):
    body = b"servo telemetry\n"
    digest = hashlib.sha256(body).hexdigest()
    entry = _entry(sha256=digest)
    target = tmp_path / entry["artifact"]
    target.parent.mkdir()
    target.write_bytes(body)

    verify_entries([entry], tmp_path)
    target.write_bytes(body + b"changed")

    with pytest.raises(RuntimeError, match="SHA mismatch"):
        verify_entries([entry], tmp_path)


def test_no_fetch_fetch_only_still_verifies_selected_artifacts(tmp_path):
    manifest_path = _write_manifest(tmp_path, [_entry()])

    with pytest.raises(RuntimeError, match="missing replay artifact"):
        main([
            "--manifest", str(manifest_path),
            "--data-dir", str(tmp_path / "data"),
            "--no-fetch", "--fetch-only",
        ])


@pytest.mark.parametrize(("metrics", "expected"), [
    ({"hw_peak_roll_rel_deg": 10.0,
      "sim_peak_roll_rel_deg": 13.0,
      "roll_waveform_rmse_deg": 3.0}, True),
    ({"hw_peak_roll_rel_deg": 2.0,
      "sim_peak_roll_rel_deg": 4.01,
      "roll_waveform_rmse_deg": 1.0}, False),
    ({"hw_peak_roll_rel_deg": 10.0,
      "sim_peak_roll_rel_deg": 10.0,
      "roll_waveform_rmse_deg": 3.01}, False),
    ({"hw_peak_roll_rel_deg": 10.0,
      "sim_peak_roll_rel_deg": np.nan,
      "roll_waveform_rmse_deg": 1.0}, False),
])
def test_attitude_gate(metrics, expected):
    assert _passes_attitude_gate(metrics) is expected


def test_summaries_group_splits_and_compute_medians():
    records = [
        {"split": "fit", "attitude_gate_pass": True,
         "sim_peak_roll_rel_deg": 8.0, "hw_peak_roll_rel_deg": 10.0,
         "roll_waveform_rmse_deg": 1.0, "q_rmse_moving_deg": 2.0},
        {"split": "fit", "attitude_gate_pass": False,
         "sim_peak_roll_rel_deg": 4.0, "hw_peak_roll_rel_deg": 10.0,
         "roll_waveform_rmse_deg": 5.0, "q_rmse_moving_deg": 4.0},
        {"split": "holdout", "attitude_gate_pass": True,
         "sim_peak_roll_rel_deg": 3.0, "hw_peak_roll_rel_deg": 4.0,
         "roll_waveform_rmse_deg": 2.0, "q_rmse_moving_deg": 1.0},
    ]

    assert _summaries(records) == {
        "fit": {
            "n": 2,
            "attitude_gate_passed": 1,
            "median_roll_peak_abs_error_deg": 4.0,
            "median_roll_waveform_rmse_deg": 3.0,
            "median_q_rmse_deg": 3.0,
        },
        "holdout": {
            "n": 1,
            "attitude_gate_passed": 1,
            "median_roll_peak_abs_error_deg": 1.0,
            "median_roll_waveform_rmse_deg": 2.0,
            "median_q_rmse_deg": 1.0,
        },
    }


def _series_config() -> dict:
    return {
        "joint_series_flex": {
            "enabled": 1,
            "legs": [4],
            "axes": ["pitch", "knee"],
            "joints": {
                name: {
                    "stiffness_nm_rad": 30.0,
                    "damping_nms_rad": 0.2,
                    "frictionloss_nm": 0.0,
                    "springref_deg": 0.0,
                    "range_deg": [-6.0, 6.0],
                }
                for name in ACTIVE_JOINT_NAMES
            },
        }
    }


def test_matrix_cli_reports_series_topology_and_defaults_to_loaded_fit(
        tmp_path, monkeypatch):
    manifest = _write_manifest(tmp_path, [_entry()])
    series_path = tmp_path / "series.json"
    series_path.write_text(json.dumps(_series_config()))
    out = tmp_path / "report.json"
    captured = {}

    def fake_load(path=None):
        captured["servo_path"] = path
        return object()

    def fake_run(entries, data_dir, *, params, model_source,
                 mount_flex=None, series_flex=None, imu_pos_mm=(0., 0., 0.)):
        captured["series"] = series_flex
        return [{
            "split": "fit",
            "attitude_gate_pass": True,
            "sim_peak_roll_rel_deg": 8.0,
            "hw_peak_roll_rel_deg": 10.0,
            "roll_waveform_rmse_deg": 1.0,
            "q_rmse_moving_deg": 2.0,
        }]

    monkeypatch.setattr(MATRIX.SimServoParams, "load", staticmethod(fake_load))
    monkeypatch.setattr(MATRIX, "run_matrix", fake_run)

    assert main([
        "--manifest", str(manifest),
        "--data-dir", str(tmp_path / "data"),
        "--no-fetch",
        "--joint-series-flex-json", str(series_path),
        "--out", str(out),
    ]) == 0

    report = json.loads(out.read_text())
    assert captured["servo_path"] == MATRIX.LOADED_MODEL_PATH
    assert captured["series"].selected_joint_names == (
        "L4_pitch", "L4_knee")
    assert report["servo_params"] == "loaded"
    assert report["leg_mount_flex"] is None
    assert report["joint_series_flex"]["selected_joint_names"] == [
        "L4_pitch", "L4_knee"]
