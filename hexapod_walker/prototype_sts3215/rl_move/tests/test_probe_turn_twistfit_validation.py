"""CLI and scientific-verdict regressions for the steering twist-fit probe.

The CLI uses recorded synthetic rollout summaries, so these tests exercise its
real orchestration, reference validation, output writing, and verdict code
without starting MuJoCo or training. Path summaries are obtained from the real
stage analyzer; a common rigid command bias is not leg-path inconsistency.
"""
from __future__ import annotations

import copy
import json
import math
import sys

import numpy as np
import pytest

from rl_move.sim import probe_turn_twistfit as probe
from rl_move.sim import probe_turn_stancearm as stancearm


COMMANDS = [(0.08, 0.15), (0.08, -0.15), (0.08, 0.0)]
PHASES = [0.0, math.pi]


def _path_summary(wz, *, inconsistent):
    """Fit measured paths, rather than hand-setting the support statistics."""
    angles = (np.arange(6) + 0.5) * math.pi / 3.0
    current = 0.22 * np.column_stack((np.cos(angles), np.sin(angles)))
    paths = [current.copy()]
    commanded = (0.08, 0.0, wz)
    # Every foot following the same wrong twist must not count as inconsistent.
    actual = commanded if inconsistent else (0.035, 0.0, 0.4 * wz)
    mismatch = np.zeros((6, 2))
    if inconsistent:
        mismatch[:, 0] = np.array([1, -1, 1, -1, 1, -1]) * 0.065
    for _ in range(59):
        for _ in range(10):
            current = current + (
                probe.twist_pred_vel(current, actual) + mismatch
            ) * 0.001
        paths.append(current.copy())
    paths = np.asarray(paths)
    summary = probe.analyze_stage(
        paths, np.ones((len(paths), 6), dtype=bool), 0.01,
        cmd_twists=np.tile(commanded, (len(paths), 1)),
    )
    assert summary is not None
    return summary


@pytest.fixture
def recorded_cells():
    summaries = {
        wz: _path_summary(wz, inconsistent=True) for _, wz in COMMANDS
    }
    cells = []
    for phase in PHASES:
        for vx, wz in COMMANDS:
            stages = {
                name: {
                    "plan": copy.deepcopy(summaries[wz]),
                    "contact": copy.deepcopy(summaries[wz]),
                }
                for name in ("des", "safe", "act", "pads")
            }
            cells.append({
                "vx_cmd": vx, "wz_cmd": wz, "phase_offset": phase,
                "seed": 0, "fell": False, "n_scored_ticks": 1300,
                "body": {"vx_med": 0.069, "wz_med": 0.37 * wz},
                "model_identity": {
                    "model_variant": "full_mesh", "model_nmesh": 34,
                    "model_mass_kg": 4.80573,
                },
                "edge_erode_ticks": 2, "stages": stages,
                "parity": {"ok": True},
            })
    return cells


def _reference(cells):
    return {
        "policy": "scripted", "seed": 0, "episode_seconds": 15.0,
        "cfg_set": ["control.hz=100", "env.model_source=mesh"],
        "results": [
            {
                "vx_cmd": row["vx_cmd"], "wz_cmd": row["wz_cmd"],
                "scripted_start_phase": row["phase_offset"], "seed": 0,
                "wz_med": row["body"]["wz_med"],
                "vx_med": row["body"]["vx_med"],
                "n_walk_ticks": row["n_scored_ticks"], "fell": False,
            }
            for row in cells
        ],
    }


def _feasible():
    return {
        "raw_ik_calls": 7200, "raw_ik_failures": 0,
        "n_ticks_per_cell": 400, "period_scale": 1.0,
        "joint_margins": {
            axis: {"margin_deg": 10.0}
            for axis in ("yaw", "hip", "knee")
        },
    }


@pytest.fixture
def run_cli(monkeypatch, tmp_path, recorded_cells):
    def run(*, rows=None, reference=None, include_reference=True,
            cell_args="0.08:0.15,0.08:-0.15,0.08:0",
            phases="0.0,3.14159265", feasibility_error=None):
        rows = copy.deepcopy(recorded_cells if rows is None else rows)
        reference = copy.deepcopy(
            _reference(recorded_cells) if reference is None else reference
        )
        calls = []

        def fake_rollout(**kwargs):
            calls.append(kwargs)
            key = (
                round(kwargs["vx_cmd"], 6), round(kwargs["wz_cmd"], 6),
                round(kwargs["phase_offset"], 6),
            )
            matches = [
                row for row in rows
                if (
                    round(row["vx_cmd"], 6), round(row["wz_cmd"], 6),
                    round(row["phase_offset"], 6),
                ) == key
            ]
            assert matches, "Test fixture lacks the requested rollout."
            row = copy.deepcopy(matches[0])
            row.pop("parity", None)  # The CLI must establish this itself.
            return row

        def fake_guard(*args, **kwargs):
            if feasibility_error is not None:
                raise feasibility_error
            return _feasible()

        monkeypatch.setattr(probe, "rollout", fake_rollout)
        monkeypatch.setattr(stancearm, "feasibility_guard", fake_guard)
        config_path = tmp_path / "cfg.json"
        reference_path = tmp_path / "reference.json"
        output_path = tmp_path / "result.json"
        config_path.write_text(json.dumps(["control.hz=100"]))
        reference_path.write_text(json.dumps(reference))
        argv = [
            "probe_turn_twistfit", "--cfg-json", str(config_path),
            "--cells", cell_args, "--phase-offsets", phases,
            "--seed", "0", "--episode-seconds", "15",
            "--out", str(output_path),
        ]
        if include_reference:
            argv += ["--parity-json", str(reference_path)]
        monkeypatch.setattr(sys, "argv", argv)
        status = probe.main()
        assert output_path.exists(), "Rejected evaluations must write their reasons."

        def reject_nonfinite(value):
            pytest.fail(f"Output is not strict JSON: {value}")

        report = json.loads(
            output_path.read_text(), parse_constant=reject_nonfinite
        )
        return status, report, calls

    return run


def _assert_rejected(status, report):
    assert status != 0
    assert report["validation"]["valid"] is False
    assert report["validation"]["reasons"]
    assert report["support_verdict"]["supported"] is False


def test_cli_accepts_complete_parity_matched_inconsistent_matrix(run_cli):
    status, report, calls = run_cli()
    assert status == 0
    assert len(calls) == 6
    assert report["validation"]["valid"] is True
    assert report["support_verdict"]["supported"] is True
    assert report["support_verdict"]["legacy_bar_supported"] is True
    assert len(report["support_verdict"]["checks"]) == 4
    assert all(row["parity"]["ok"] for row in report["results"])


def test_common_wrong_rigid_twist_is_bias_not_path_inconsistency(recorded_cells):
    for row in recorded_cells:
        stage = _path_summary(row["wz_cmd"], inconsistent=False)
        row["stages"]["des"]["plan"] = stage
        assert stage["resid_norm"] < 0.001
        assert stage["cmd_exact_resid_norm"] > 0.10
    validation = probe.validate_matrix(
        recorded_cells, feasibility=_feasible()
    )
    verdict = probe.support_verdict(recorded_cells, validation=validation)
    assert validation["valid"] is True
    assert verdict["legacy_bar_supported"] is True
    assert all(check["S1"] or check["S2"] for check in verdict["checks"])
    assert verdict["supported"] is False
    assert verdict["path_inconsistency_threshold"] == pytest.approx(0.10)
    assert verdict["interpretation"]


def test_cli_common_wrong_rigid_twist_does_not_support_correction(
    recorded_cells, run_cli,
):
    for row in recorded_cells:
        row["stages"]["des"]["plan"] = _path_summary(
            row["wz_cmd"], inconsistent=False
        )
    status, report, _ = run_cli(rows=recorded_cells)
    assert status == 0
    assert report["validation"]["valid"] is True
    assert report["support_verdict"]["legacy_bar_supported"] is True
    assert report["support_verdict"]["supported"] is False


def test_inconsistency_must_be_present_in_every_arc(recorded_cells):
    recorded_cells[0]["stages"]["des"]["plan"] = _path_summary(
        0.15, inconsistent=False
    )
    validation = probe.validate_matrix(
        recorded_cells, feasibility=_feasible()
    )
    verdict = probe.support_verdict(recorded_cells, validation=validation)
    assert validation["valid"] is True
    assert verdict["legacy_bar_supported"] is True
    assert verdict["supported"] is False


@pytest.mark.parametrize("mutation", [
    "missing_straight", "missing_arc", "duplicate", "wrong_speed",
    "nonfinite", "fall", "no_fits", "failed_parity", "missing_parity",
])
def test_invalid_matrix_cannot_support_even_with_arc_breaches(
    recorded_cells, mutation,
):
    if mutation == "missing_straight":
        recorded_cells.pop(2)
    elif mutation == "missing_arc":
        recorded_cells.pop(0)
    elif mutation == "duplicate":
        recorded_cells.append(copy.deepcopy(recorded_cells[0]))
    elif mutation == "wrong_speed":
        recorded_cells[2]["vx_cmd"] = 0.09
    elif mutation == "nonfinite":
        recorded_cells[2]["body"]["vx_med"] = float("nan")
    elif mutation == "fall":
        recorded_cells[2]["fell"] = True
    elif mutation == "no_fits":
        recorded_cells[0]["stages"]["des"]["plan"]["n_fits"] = 0
    elif mutation == "failed_parity":
        recorded_cells[2]["parity"]["ok"] = False
    elif mutation == "missing_parity":
        recorded_cells[2].pop("parity")
    validation = probe.validate_matrix(
        recorded_cells, feasibility=_feasible()
    )
    assert validation["valid"] is False
    assert validation["reasons"]
    assert probe.support_verdict(
        recorded_cells, validation=validation
    )["supported"] is False


@pytest.mark.parametrize("reference_case", [
    "missing", "duplicate", "policy", "seed", "duration", "row_seed", "config",
])
def test_cli_rejects_incomplete_or_unmatched_reference(
    recorded_cells, run_cli, reference_case,
):
    ref = _reference(recorded_cells)
    if reference_case == "missing":
        ref["results"].pop()
    elif reference_case == "duplicate":
        ref["results"].append(copy.deepcopy(ref["results"][0]))
    elif reference_case == "policy":
        ref["policy"] = "checkpoint"
    elif reference_case == "seed":
        ref["seed"] = 42
    elif reference_case == "duration":
        ref["episode_seconds"] = 5.0
    elif reference_case == "row_seed":
        ref["results"][0]["seed"] = 42
    elif reference_case == "config":
        ref["cfg_set"] = ["control.hz=50"]
    status, report, _ = run_cli(reference=ref)
    _assert_rejected(status, report)


def test_cli_allows_historical_reference_without_outer_seed_or_duration(
    recorded_cells, run_cli,
):
    ref = _reference(recorded_cells)
    ref.pop("seed")
    ref.pop("episode_seconds")
    status, report, _ = run_cli(reference=ref)
    assert status == 0
    assert report["validation"]["valid"] is True


def test_cli_requires_reference(run_cli):
    status, report, _ = run_cli(include_reference=False)
    _assert_rejected(status, report)


@pytest.mark.parametrize("cell_args,phases", [
    ("0.08:0.15,0.08:-0.15", "0.0,3.14159265"),
    ("0.08:0.15,0.08:-0.15,0.08:0,0.08:0", "0.0,3.14159265"),
    ("0.08:0.15,0.08:-0.15,0.08:0", "0.0,0.0"),
])
def test_cli_requires_six_unique_requested_cells(run_cli, cell_args, phases):
    status, report, _ = run_cli(cell_args=cell_args, phases=phases)
    _assert_rejected(status, report)


@pytest.mark.parametrize("field", ["vx_med", "n_walk_ticks", "fell"])
def test_cli_parity_covers_behavior_length_and_termination(
    recorded_cells, run_cli, field,
):
    ref = _reference(recorded_cells)
    ref["results"][0][field] = {
        "vx_med": 0.079, "n_walk_ticks": 1299, "fell": True,
    }[field]
    status, report, _ = run_cli(reference=ref)
    _assert_rejected(status, report)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_cli_nonfinite_rollout_is_rejected_and_output_remains_strict_json(
    recorded_cells, run_cli, bad_value,
):
    recorded_cells[0]["stages"]["des"]["plan"]["resid_norm"] = bad_value
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


def test_cli_fall_rejects_matrix_even_when_scalar_parity_matches(
    recorded_cells, run_cli,
):
    recorded_cells[2]["fell"] = True
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


@pytest.mark.parametrize("error", [
    SystemExit("FEASIBILITY FAIL: raw IK target"),
    RuntimeError("FEASIBILITY FAIL: joint margin"),
])
def test_cli_feasibility_failure_is_reported_without_starting_rollouts(
    run_cli, error,
):
    status, report, calls = run_cli(feasibility_error=error)
    _assert_rejected(status, report)
    assert not calls
    assert "feasib" in json.dumps(report["validation"]["reasons"]).lower()


def test_failed_feasibility_blocks_otherwise_valid_support(recorded_cells):
    infeasible = _feasible()
    infeasible["raw_ik_failures"] = 1
    validation = probe.validate_matrix(
        recorded_cells, feasibility=infeasible
    )
    assert validation["valid"] is False
    assert probe.support_verdict(
        recorded_cells, validation=validation
    )["supported"] is False
