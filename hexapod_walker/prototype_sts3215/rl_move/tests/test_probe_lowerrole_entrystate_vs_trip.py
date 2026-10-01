"""Mechanics-only tests for the lower-role entry-state-vs-trip-leg
probe (walkcurr, 2026-10-01): pure array analysis, no mujoco/env, per
RESEARCH_RULES "Tests"."""
import json

import numpy as np

from rl_move.sim.probe_lowerrole_entrystate_vs_trip import (
    FREE_JOINT_QPOS,
    load_trace_records,
    per_leg_abnormality,
    summarize,
    trip_leg_rank,
)


def test_per_leg_abnormality_flags_the_outlier_leg():
    # 5 "normal" episodes near 0, leg 2 (joints 6,7,8) spikes on the 6th.
    vals = np.zeros((6, 18))
    vals[5, 6:9] = 10.0
    abn = per_leg_abnormality(vals)
    assert abn.shape == (6, 6)
    assert int(np.argmax(abn[5])) == 2


def test_per_leg_abnormality_rejects_wrong_width():
    import pytest
    with pytest.raises(ValueError):
        per_leg_abnormality(np.zeros((4, 17)))


def test_per_leg_abnormality_zero_variance_is_not_nan():
    vals = np.ones((4, 18)) * 3.0  # every column constant
    abn = per_leg_abnormality(vals)
    assert np.all(np.isfinite(abn))
    assert np.allclose(abn, 0.0, atol=1e-3)


def test_trip_leg_rank_most_abnormal_is_rank_1():
    row = np.array([0.1, 5.0, 0.2, 0.3, 0.4, 0.05])
    assert trip_leg_rank(row, final_leg=1) == 1
    assert trip_leg_rank(row, final_leg=5) == 6


def test_summarize_no_information_case_gives_chance_rank():
    # final_leg cycles independently of which leg is actually abnormal
    # -> long-run mean rank should sit near the no-information value,
    # and in this constructed worst case the trip leg is NEVER the
    # most-abnormal one (always rank 6 of 6).
    recs = []
    rng = np.random.default_rng(0)
    for i in range(12):
        qpos18 = rng.normal(size=18)
        qpos18[0:3] = 0.0  # leg 0 always the LEAST abnormal column set
        recs.append({
            "joint_qpos": qpos18, "joint_qvel": qpos18.copy(),
            "final_leg": 0, "final_joint": 0,
        })
    out = summarize(recs)
    assert out["n"] == 12
    assert out["chance_mean_rank"] == 3.5
    assert out["qpos_mean_rank"] == 6.0
    assert out["qpos_frac_rank1"] == 0.0


def test_summarize_empty_is_n_zero():
    assert summarize([]) == {"n": 0}


def test_load_trace_records_parses_written_json(tmp_path):
    d = tmp_path / "trace"
    d.mkdir()
    qpos = [0.0] * FREE_JOINT_QPOS + list(range(18))
    qvel = [0.0] * 6 + list(range(18))
    payload = {
        "walk_exit_qpos": qpos, "walk_exit_qvel": qvel,
        "trip_summary": {"final_joint": 16, "final_joint_label": "L5 hip"},
    }
    (d / "direct_1_over_current.json").write_text(json.dumps(payload))
    recs = load_trace_records([str(d)])
    assert len(recs) == 1
    r = recs[0]
    assert r["final_joint"] == 16
    assert r["final_leg"] == 5
    assert list(r["joint_qpos"]) == list(range(18))
    assert r["final_joint_label"] == "L5 hip"
