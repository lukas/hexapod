"""audit_dr_hold_correlate.py pure functions (standwalk STATUS Next#1,
2026-09-04): correlate per-episode DR draws against a fired
termination reason."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.sim.audit_dr_hold_correlate import correlate, load_episodes  # noqa: E402


def _ep(term_reason: str, friction_scale: float, fault: str = "none"):
    return {
        "term_reason": term_reason,
        "randomization": {"friction_scale": friction_scale,
                          "mass_scale": 1.0, "fault": fault},
    }


def test_correlate_separates_fired_from_clean():
    episodes = (
        [_ep("hold_min_load", 0.4) for _ in range(4)]
        + [_ep("", 1.2) for _ in range(4)]
    )
    out = correlate(episodes, reason="hold_min_load")
    assert out["n_fired"] == 4 and out["n_clean"] == 4
    assert not out["low_n_warning"]
    fs = out["fields"]["friction_scale"]
    assert fs["fired_median"] == 0.4
    assert fs["clean_median"] == 1.2
    assert fs["std_mean_diff"] < -1.0  # fired group's friction is much lower
    assert out["ranked_fields"][0] == "friction_scale"


def test_correlate_low_n_warning_and_no_crash_on_empty_group():
    out = correlate([_ep("hold_min_load", 0.4)], reason="hold_min_load")
    assert out["n_fired"] == 1 and out["n_clean"] == 0
    assert out["low_n_warning"]
    assert out["fields"]["friction_scale"]["clean_median"] is None
    assert out["fields"]["friction_scale"]["std_mean_diff"] is None


def test_correlate_fault_categorical_counts():
    episodes = [_ep("hold_min_load", 1.0, fault="weak:j2@0.3"),
                _ep("", 1.0, fault="none")]
    out = correlate(episodes, reason="hold_min_load")
    assert out["fault_fired_counts"] == {"weak:j2@0.3": 1}
    assert out["fault_clean_counts"] == {"none": 1}


def test_load_episodes_skips_episodes_without_randomization(tmp_path):
    report = {"episodes": {"walk/plant": [
        {"term_reason": "hold_min_load"},  # no randomization -> skipped
        {"term_reason": "", "randomization": {"friction_scale": 1.0}},
    ]}}
    p = tmp_path / "report.json"
    import json
    p.write_text(json.dumps(report))
    eps = load_episodes([p])
    assert len(eps) == 1
    assert eps[0]["randomization"]["friction_scale"] == 1.0
