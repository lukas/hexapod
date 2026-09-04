"""Tests for rescore_turn_authority.py (standwalk steering-axis
re-score tool, 09-04 idle-kick)."""
from rl_move.sim.rescore_turn_authority import (
    ledger_cfg_args,
    magnitude,
    magnitude_pct,
    rescore_cell,
    summarize_probe,
)


def test_ledger_cfg_args_drops_train_and_non_cfg_set():
    extra_args = [
        "--task", "joint_walk",
        "--gru-dual",
        "--cfg-set", "reward.k_walk_yaw=1.0",
        "--cfg-set", "train.yaw_credit_coef=1.0",
        "--seed", "0",
        "--cfg-set", "env.model_source=mesh",
    ]
    assert ledger_cfg_args(extra_args) == [
        "reward.k_walk_yaw=1.0",
        "env.model_source=mesh",
    ]


def test_ledger_cfg_args_empty_on_no_cfg_set():
    assert ledger_cfg_args(["--task", "joint_walk"]) == []


def _result(rows):
    return {"results": [
        {"wz_cmd": wz, "vx_cmd": vx, "seed": s, "wz_med": med}
        for (wz, vx, s, med) in rows
    ]}


def test_summarize_probe_medians_across_seeds():
    result = _result([
        (0.25, 0.0, 0, 0.20), (0.25, 0.0, 1, 0.18),
        (-0.25, 0.0, 0, -0.19), (-0.25, 0.0, 1, -0.21),
    ])
    summary = summarize_probe(result)
    assert summary[(0.25, 0.0)] == 0.19
    assert summary[(-0.25, 0.0)] == -0.20


def test_magnitude_flips_sign_for_negative_wz_cmd():
    summary = {(0.25, 0.0): 0.20, (-0.25, 0.0): -0.19}
    assert magnitude(summary, 0.25, 0.0) == 0.20
    assert magnitude(summary, -0.25, 0.0) == 0.19  # magnitude, not raw


def test_magnitude_pct_positive_means_more_authority():
    assert magnitude_pct(0.22, 0.20) > 0
    assert magnitude_pct(0.18, 0.20) < 0


def test_rescore_cell_pass_requires_both_combined_signs_and_pure_turn_cap():
    control = _result([
        (0.25, 0.0, 0, 0.20), (0.25, 0.0, 1, 0.20),
        (-0.25, 0.0, 0, -0.20), (-0.25, 0.0, 1, -0.20),
        (0.25, 0.08, 0, 0.12), (0.25, 0.08, 1, 0.12),
        (-0.25, 0.08, 0, -0.15), (-0.25, 0.08, 1, -0.15),
    ])
    winner = _result([
        (0.25, 0.0, 0, 0.20), (0.25, 0.0, 1, 0.19),   # pure-turn ~ok
        (-0.25, 0.0, 0, -0.19), (-0.25, 0.0, 1, -0.19),
        (0.25, 0.08, 0, 0.14), (0.25, 0.08, 1, 0.14),  # combined both up
        (-0.25, 0.08, 0, -0.18), (-0.25, 0.08, 1, -0.18),
    ])
    loser_pure_turn_breach = _result([
        (0.25, 0.0, 0, 0.16), (0.25, 0.0, 1, 0.16),   # -20% pure-turn
        (-0.25, 0.0, 0, -0.20), (-0.25, 0.0, 1, -0.20),
        (0.25, 0.08, 0, 0.14), (0.25, 0.08, 1, 0.14),
        (-0.25, 0.08, 0, -0.18), (-0.25, 0.08, 1, -0.18),
    ])
    loser_combined_flat = _result([
        (0.25, 0.0, 0, 0.20), (0.25, 0.0, 1, 0.20),
        (-0.25, 0.0, 0, -0.20), (-0.25, 0.0, 1, -0.20),
        (0.25, 0.08, 0, 0.10), (0.25, 0.08, 1, 0.10),  # combined worse
        (-0.25, 0.08, 0, -0.16), (-0.25, 0.08, 1, -0.16),
    ])

    ctrl = summarize_probe(control)
    assert rescore_cell(summarize_probe(winner), ctrl)["pass"] is True
    cell = rescore_cell(summarize_probe(loser_pure_turn_breach), ctrl)
    assert cell["pass"] is False
    assert cell["pure_turn_cap_ok"] is False
    cell2 = rescore_cell(summarize_probe(loser_combined_flat), ctrl)
    assert cell2["pass"] is False
    assert cell2["combined_both_sign_win"] is False
