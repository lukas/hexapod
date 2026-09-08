"""Event-sync CLI validation and observational-scope regressions.

Synthetic recorded rollout summaries are computed with the real analysis
functions. These tests run main(), including matrix preflight, pinned-row
checks, strict report serialization, and failure handling, without simulation.
"""
from __future__ import annotations

import copy
import json
import math
import sys

import numpy as np
import pytest

from rl_move.sim import probe_turn_eventsync as probe


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
def recorded_cells():
    n = 1300
    t = np.arange(n)
    plan = np.zeros((n, 6), dtype=bool)
    contact = np.zeros((n, 6), dtype=bool)
    for foot in range(6):
        phase = 37 if foot % 2 else 0
        plan[:, foot] = (t + phase) % 75 < 37
        contact[:, foot] = (t + phase - 2 * foot) % 75 < 37
    events = probe.event_offsets(plan, contact, 75.0)
    assert all(leg["touchdown_n"] >= 2 for leg in events["per_leg"].values())
    loaded = np.zeros((n, 6), dtype=bool)
    loaded[:260, [0, 2, 4]] = True
    loaded[260:520, [1, 3, 5]] = True
    loaded[520:910, :4] = True
    loaded[910:, 0] = True
    rows = []
    for (vx_cmd, wz_cmd, phase), (wz_med, vx_med, ticks) in probe.PARITY_REF.items():
        wz = np.full(n, wz_med)
        if wz_cmd:
            # The actual median stays pinned, while pure-support samples
            # have larger signed yaw. This passes the historical screen.
            wz[:520] = 1.5 * wz_med
            wz[910:] = 0.5 * wz_med
        support = probe.support_state_stats(loaded, wz, np.full(n, vx_med))
        assert support["wz_med_overall"] == wz_med
        rows.append({
            "policy": "scripted", "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
            "phase_offset": phase, "seed": 0, "fell": False,
            "n_scored_ticks": ticks, "period_eff_s": 0.75,
            "model_identity": {
                "model_variant": "full_mesh", "model_nmesh": 34,
                "model_mass_kg": 4.80573,
            },
            "motor_contract": {
                "bus.write_speed": 400.0, "bus.write_acc": 20.0,
                "safety.max_delta_q_deg": 0.375, "slew_limit_deg_s": 37.5,
                "resolved_vel_max_counts_s_max": 350.0, "control.hz": 100.0,
            },
            "body": {"vx_med": vx_med, "wz_med": wz_med},
            "parity": {
                "ref_wz_med": wz_med, "ref_vx_med": vx_med,
                "ref_n_scored_ticks": ticks, "ok": True,
            },
            "events": copy.deepcopy(events),
            "support_states": support,
            "duty_contact": contact.mean(axis=0).tolist(),
            "duty_loaded": loaded.mean(axis=0).tolist(),
        })
    return rows


@pytest.fixture
def run_cli(monkeypatch, tmp_path, recorded_cells):
    def run(*, rows=None, cells="0.08:0.15,0.08:-0.15,0.08:0",
            phases=f"0.0,{math.pi}", plant="fullmesh", seed=0,
            seconds=15.0, guard_error=None, pin_error=None):
        bank = copy.deepcopy(recorded_cells if rows is None else rows)
        calls = []

        def fake_rollout(**kwargs):
            calls.append(kwargs)
            key = (
                round(kwargs["vx_cmd"], 6), round(kwargs["wz_cmd"], 6),
                round(kwargs["phase_offset"], 6),
            )
            matches = [
                row for row in bank
                if (
                    round(row["vx_cmd"], 6), round(row["wz_cmd"], 6),
                    round(row["phase_offset"], 6),
                ) == key
            ]
            assert matches, "Synthetic fixture lacks requested rollout."
            row = copy.deepcopy(matches[0])
            row["seed"] = kwargs["seed"]
            if kwargs["plant"] == "twin":
                row["model_identity"]["model_variant"] = "mesh_mjx_twin"
                row["model_identity"]["model_nmesh"] = 0
            return row

        def fake_guard(*args, **kwargs):
            if guard_error is not None:
                raise guard_error
            return _feasible()

        def fake_pins(*args, **kwargs):
            if pin_error is not None:
                raise pin_error
            return {"fixture": "unchanged frozen plant"}

        monkeypatch.setattr(probe, "rollout", fake_rollout)
        monkeypatch.setattr(probe, "feasibility_guard", fake_guard)
        monkeypatch.setattr(probe, "pin_manifest", fake_pins)
        config = tmp_path / "cfg.json"
        output = tmp_path / "result.json"
        config.write_text(json.dumps(["control.hz=100"]))
        monkeypatch.setattr(sys, "argv", [
            "probe_turn_eventsync", "--cfg-json", str(config),
            "--cells", cells, "--phase-offsets", phases,
            "--plant", plant, "--seed", str(seed),
            "--episode-seconds", str(seconds), "--out", str(output),
        ])
        status = probe.main()
        assert output.exists(), "Invalid evaluations must write a report."

        def reject_nonfinite(value):
            pytest.fail(f"Output is not strict JSON: {value}")

        report = json.loads(output.read_text(), parse_constant=reject_nonfinite)
        return status, report, calls

    return run


def _assert_rejected(status, report):
    assert status != 0
    assert report["validation"]["valid"] is False
    assert report["validation"]["reasons"]
    assert report["support_verdict"]["supported"] is False
    assert report["support_verdict"]["observational_screen_passed"] is False


def test_positive_screen_remains_observational(recorded_cells):
    validation = probe.validate_matrix(recorded_cells, feasibility=_feasible())
    result = probe.verdict(recorded_cells, validation=validation)
    assert validation["valid"] is True
    assert result["historical_bar_supported"] is True
    assert result["observational_screen_passed"] is True
    assert result["supported"] is False
    assert isinstance(result["scope"], str) and result["scope"]


def test_cli_complete_valid_bank_reports_observation_without_causal_support(run_cli):
    status, report, calls = run_cli()
    assert status == 0
    assert len(calls) == 6
    assert report["validation"]["valid"] is True
    assert report["support_verdict"]["historical_bar_supported"] is True
    assert report["support_verdict"]["observational_screen_passed"] is True
    assert report["support_verdict"]["supported"] is False


def test_negative_screen_also_makes_no_intervention_claim(recorded_cells):
    for row in recorded_cells:
        stats = row["support_states"]
        stats["wz_counterfactual_mean"] = stats["wz_mean_overall"]
    validation = probe.validate_matrix(recorded_cells, feasibility=_feasible())
    result = probe.verdict(recorded_cells, validation=validation)
    assert validation["valid"] is True
    assert result["historical_bar_supported"] is False
    assert result["observational_screen_passed"] is False
    assert result["supported"] is False
    assert result["scope"]


@pytest.mark.parametrize("mutation", [
    "missing_straight", "duplicate", "wrong_speed", "wrong_seed",
    "short_row", "wrong_mass", "wrong_mesh_count", "wrong_variant",
    "failed_parity", "truthy_nonboolean_parity", "missing_parity",
    "dishonest_parity", "error", "fall", "missing_events",
    "empty_states", "missing_leg_events", "nonfinite",
])
def test_invalid_rows_never_pass_observational_screen(recorded_cells, mutation):
    row = recorded_cells[0]
    if mutation == "missing_straight":
        recorded_cells.pop()
    elif mutation == "duplicate":
        recorded_cells.append(copy.deepcopy(row))
    elif mutation == "wrong_speed":
        row["vx_cmd"] = 0.09
    elif mutation == "wrong_seed":
        row["seed"] = 1
    elif mutation == "short_row":
        row["n_scored_ticks"] = 1299
    elif mutation == "wrong_mass":
        row["model_identity"]["model_mass_kg"] = 4.9
    elif mutation == "wrong_mesh_count":
        row["model_identity"]["model_nmesh"] = 0
    elif mutation == "wrong_variant":
        row["model_identity"]["model_variant"] = "mesh_mjx_twin"
    elif mutation == "failed_parity":
        row["parity"]["ok"] = False
    elif mutation == "truthy_nonboolean_parity":
        row["parity"]["ok"] = 1
    elif mutation == "missing_parity":
        row.pop("parity")
    elif mutation == "dishonest_parity":
        row["body"]["vx_med"] += 0.01
    elif mutation == "error":
        row["error"] = "insufficient scored ticks"
    elif mutation == "fall":
        row["fell"] = True
    elif mutation == "missing_events":
        row.pop("events")
    elif mutation == "empty_states":
        row["support_states"] = {}
    elif mutation == "missing_leg_events":
        row["events"]["per_leg"][0]["touchdown_n"] = 0
    elif mutation == "nonfinite":
        row["support_states"]["wz_mean_overall"] = float("nan")
    validation = probe.validate_matrix(recorded_cells, feasibility=_feasible())
    assert validation["valid"] is False
    assert validation["reasons"]
    result = probe.verdict(recorded_cells, validation=validation)
    assert result["supported"] is False
    assert result["observational_screen_passed"] is False


def test_cli_rejects_missing_straight_cells(run_cli):
    status, report, calls = run_cli(cells="0.08:0.15,0.08:-0.15")
    _assert_rejected(status, report)
    assert not calls


def test_cli_rejects_duplicate_phase_cells(run_cli):
    status, report, calls = run_cli(phases="0.0,0.0")
    _assert_rejected(status, report)
    assert not calls


def test_cli_rejects_duplicate_commands(run_cli):
    status, report, calls = run_cli(
        cells="0.08:0.15,0.08:-0.15,0.08:0,0.08:0"
    )
    _assert_rejected(status, report)
    assert not calls


def test_cli_rejects_failed_parity(recorded_cells, run_cli):
    recorded_cells[0]["parity"]["ok"] = False
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


def test_cli_verifies_pinned_values_even_if_parity_flag_claims_success(
    recorded_cells, run_cli,
):
    recorded_cells[0]["body"]["wz_med"] += 0.01
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_cli_nonfinite_measurements_are_rejected_with_strict_json(
    recorded_cells, run_cli, value,
):
    recorded_cells[0]["events"]["interleg_spread_ms"] = value
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


def test_cli_fall_invalidates_whole_bank(recorded_cells, run_cli):
    recorded_cells[-1]["fell"] = True
    status, report, _ = run_cli(rows=recorded_cells)
    _assert_rejected(status, report)


@pytest.mark.parametrize("overrides", [
    {"plant": "twin"}, {"seed": 1}, {"seconds": 5.0},
])
def test_cli_smoke_or_unpinned_run_cannot_be_a_validated_bank(run_cli, overrides):
    status, report, _ = run_cli(**overrides)
    _assert_rejected(status, report)


@pytest.mark.parametrize("error", [
    SystemExit("FEASIBILITY FAIL: raw IK target"),
    RuntimeError("FEASIBILITY FAIL: joint margin"),
])
def test_cli_guard_failure_writes_rejection_before_any_rollout(run_cli, error):
    status, report, calls = run_cli(guard_error=error)
    _assert_rejected(status, report)
    assert not calls
    assert "feasib" in json.dumps(report["validation"]["reasons"]).lower()


def test_cli_pin_failure_is_reported_without_rollouts(run_cli):
    status, report, calls = run_cli(pin_error=RuntimeError("pin mismatch"))
    _assert_rejected(status, report)
    assert not calls


def test_infeasibility_blocks_otherwise_positive_screen(recorded_cells):
    feasibility = _feasible()
    feasibility["raw_ik_failures"] = 1
    validation = probe.validate_matrix(
        recorded_cells, feasibility=feasibility
    )
    assert validation["valid"] is False
    assert probe.verdict(
        recorded_cells, validation=validation
    )["observational_screen_passed"] is False
