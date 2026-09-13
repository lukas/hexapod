"""Mechanics tests for the DR held-out robustness gate harness.

Fast, pure scoring/reconstruction mechanics -- no MuJoCo model, no
rollouts, no artifacts (RESEARCH_RULES "Tests"). Synthetic row dicts
stand in for `probe_dr_joint_panel.rollout()` output.
"""
import dataclasses
import json

from rl_move.sim.eval_dr_robustness_gate import (
    gait_valid,
    gate_report,
    hard_subset,
    load_heldout_ensembles,
)
from rl_move.sim.probe_dr_joint_panel import Ensemble


def _ens(n=4):
    return [Ensemble(mode="independent", index=i, split="heldout",
                     params={"x": i}, latents={})
            for i in range(n)]


def _row(ensemble, roll, *, speed=0.05, terminated=False,
         duty=(0.3, 0.3, 0.3, 0.3, 0.3, 0.3)):
    return {"ensemble": ensemble, "peak_abs_roll_deg": roll,
            "forward_speed_after_2s_m_s": speed, "terminated": terminated,
            "contact_duty": list(duty)}


def test_heldout_manifest_roundtrip(tmp_path):
    ens = _ens(3)
    manifest = {
        "heldout_seeds": [2, 3, 4], "episode_s": 14.0, "cmd_m_s": 0.10,
        "ensembles": [dataclasses.asdict(e) for e in ens],
    }
    (tmp_path / "heldout_manifest.json").write_text(json.dumps(manifest))
    loaded, proto = load_heldout_ensembles(tmp_path)
    assert [e.name for e in loaded] == [e.name for e in ens]
    assert proto == {"heldout_seeds": (2, 3, 4), "episode_s": 14.0,
                      "cmd_m_s": 0.10}


def test_heldout_manifest_empty_raises(tmp_path):
    (tmp_path / "heldout_manifest.json").write_text(json.dumps(
        {"heldout_seeds": [2], "episode_s": 1.0, "cmd_m_s": 0.1,
         "ensembles": []}))
    try:
        load_heldout_ensembles(tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on empty manifest")


def test_gait_valid_requires_six_cycling_legs():
    assert gait_valid(_row("e0", 1.0, duty=(0.3,) * 6))
    assert not gait_valid(_row("e0", 1.0, duty=(0.0, 0.3, 0.3, 0.3, 0.3, 0.3)))
    assert not gait_valid(_row("e0", 1.0, duty=(1.0, 0.3, 0.3, 0.3, 0.3, 0.3)))
    assert not gait_valid(_row("e0", 1.0, duty=(0.3, 0.3, 0.3)))
    assert not gait_valid({"contact_duty": None})


def test_hard_subset_picks_highest_parent_roll():
    ens = _ens(4)
    parent_rows = [_row("independent_000", 2.0), _row("independent_001", 8.0),
                    _row("independent_002", 1.0), _row("independent_003", 5.0)]
    hard = hard_subset(parent_rows, ens, hard_frac=0.5)
    assert hard == {"independent_001", "independent_003"}


def test_gate_report_passes_on_a_clear_win():
    ens = _ens(2)
    parent_rows = [_row("independent_000", 16.0, speed=0.05),
                   _row("independent_001", 14.0, speed=0.05)]
    parent_nominal = [_row("nominal", 1.0, speed=0.05)]
    cand_rows = [_row("independent_000", 8.0, speed=0.045),
                 _row("independent_001", 7.0, speed=0.045)]
    cand_nominal = [_row("nominal", 1.0, speed=0.048)]
    report = gate_report(parent_name="parent", parent_rows=parent_rows,
                         parent_nominal=parent_nominal, cand_name="cand",
                         cand_rows=cand_rows, cand_nominal=cand_nominal,
                         ensembles=ens, hard_frac=0.5)
    assert report["gate_pass"] is True
    assert report["checks"]["a_roll_reduction_overall_ge_30pct"]
    assert report["roll_reduction_overall"] > 0.4


def test_gate_report_fails_on_no_improvement_and_falls():
    ens = _ens(2)
    parent_rows = [_row("independent_000", 16.0), _row("independent_001", 14.0)]
    parent_nominal = [_row("nominal", 1.0)]
    # Identical policy as its own "candidate": zero reduction, must FAIL (a).
    cand_rows = [_row("independent_000", 16.0), _row("independent_001", 14.0)]
    cand_nominal = [_row("nominal", 1.0)]
    report = gate_report(parent_name="parent", parent_rows=parent_rows,
                         parent_nominal=parent_nominal, cand_name="same",
                         cand_rows=cand_rows, cand_nominal=cand_nominal,
                         ensembles=ens, hard_frac=0.5)
    assert report["gate_pass"] is False
    assert not report["checks"]["a_roll_reduction_overall_ge_30pct"]

    # A falling candidate must fail (b) even with a lower roll reading.
    cand_rows_fall = [_row("independent_000", 5.0, terminated=True),
                      _row("independent_001", 5.0, terminated=True)]
    report2 = gate_report(parent_name="parent", parent_rows=parent_rows,
                          parent_nominal=parent_nominal, cand_name="faller",
                          cand_rows=cand_rows_fall, cand_nominal=cand_nominal,
                          ensembles=ens, hard_frac=0.5)
    assert report2["gate_pass"] is False
    assert not report2["checks"]["b_zero_falls"]


def test_resolve_policy_branches():
    # .json / exported artifacts -> None (rollout's own np-policy path);
    # .zip without parent meta must fail loudly, never silently fall back.
    from rl_move.sim.eval_dr_robustness_gate import resolve_policy
    assert resolve_policy("policies/foo.json", {"control_hz": 50}) is None
    assert resolve_policy("policies/foo.json", None) is None
    try:
        resolve_policy("policies/foo.zip", None)
    except ValueError as e:
        assert "parent" in str(e)
    else:
        raise AssertionError("zip without parent meta must raise")
