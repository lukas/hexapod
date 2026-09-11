"""``distill_gru.py --walk-teacher-run/--stance-teacher-run`` cfg pull
(standwalk STATUS 2026-09-11 ~20:1x binding: hand-transcribing a
teacher's --cfg-set list is error-prone -- pull it from the run's own
ledger entry instead). Fast, mechanics-only, no GPU/checkpoints/
artifacts (RESEARCH_RULES "Tests").

Locks:
1. ``_extract_cfg_set_pairs``/``_extract_flag_value`` read the flat
   ``extra_args`` token list the same way argparse's own
   ``action="append"`` would have collected it.
2. ``pull_teacher_run`` resolves a ledger run to its checkpoint path +
   parsed cfg dict, and raises loudly (not silently) on a missing run,
   a missing --out-name, or a checkpoint that doesn't exist on disk.
3. ``merge_teacher_cfgs`` is bit-exact with the legacy single-cfg call
   when neither side pulls anything; namespace-merges pulled cfg with
   explicit --cfg-set (explicit wins) and structural requirements; and
   RAISES on any real stance-vs-walk key conflict unless the user's
   own --cfg-set already resolves it.
"""
from __future__ import annotations

import json

import pytest

from rl_move.sim.distill_gru import (
    _extract_cfg_set_pairs, _extract_flag_value, merge_teacher_cfgs,
    pull_teacher_run,
)


def test_extract_cfg_set_pairs_adjacent_and_equals_form():
    extra_args = ["--seed", "0", "--cfg-set", "bus.write_speed=1500",
                 "--cfg-set", "bus.write_acc=80", "--out-name", "foo",
                 "--cfg-set=safety.max_delta_q_deg=2.5"]
    assert _extract_cfg_set_pairs(extra_args) == [
        "bus.write_speed=1500", "bus.write_acc=80",
        "safety.max_delta_q_deg=2.5"]


def test_extract_cfg_set_pairs_dangling_flag_ignored():
    assert _extract_cfg_set_pairs(["--cfg-set"]) == []
    assert _extract_cfg_set_pairs([]) == []
    assert _extract_cfg_set_pairs(None) == []


def test_extract_flag_value_both_forms_and_missing():
    extra_args = ["--out-name", "ppo_goal_foo", "--dr-scale=0.2"]
    assert _extract_flag_value(extra_args, "--out-name") == "ppo_goal_foo"
    assert _extract_flag_value(extra_args, "--dr-scale") == "0.2"
    assert _extract_flag_value(extra_args, "--missing") is None


def _write_ledger(path, entries):
    path.write_text(json.dumps(entries))


def test_pull_teacher_run_happy_path(tmp_path, monkeypatch):
    ckpt_dir = tmp_path / "policies"
    ckpt_dir.mkdir()
    (ckpt_dir / "ppo_goal_myrun.zip").write_bytes(b"fake")
    ledger = tmp_path / "experiments.json"
    _write_ledger(ledger, [
        {"run": "myrun", "status": "PASS", "created": "t0",
         "extra_args": ["--out-name", "ppo_goal_myrun", "--dr-scale", "0.2",
                        "--cfg-set", "bus.write_speed=1500",
                        "--cfg-set", "safety.max_delta_q_deg=2.5"]},
    ])
    import rl_move.sim.distill_gru as dg
    from rl_move.orchestrator import state_dir
    monkeypatch.setattr(state_dir, "LEDGER", ledger)
    monkeypatch.setattr(dg, "POLICY_DIR", ckpt_dir)
    out = pull_teacher_run("myrun")
    assert out["checkpoint"] == ckpt_dir / "ppo_goal_myrun.zip"
    assert out["dr_scale"] == 0.2
    assert out["cfg"] == {"bus.write_speed": 1500.0,
                          "safety.max_delta_q_deg": 2.5}
    assert out["status"] == "PASS"


def test_pull_teacher_run_unknown_run_raises(tmp_path, monkeypatch):
    ledger = tmp_path / "experiments.json"
    _write_ledger(ledger, [])
    from rl_move.orchestrator import state_dir
    monkeypatch.setattr(state_dir, "LEDGER", ledger)
    with pytest.raises(SystemExit, match="no ledger entry"):
        pull_teacher_run("nope")


def test_pull_teacher_run_missing_checkpoint_raises(tmp_path, monkeypatch):
    ledger = tmp_path / "experiments.json"
    _write_ledger(ledger, [
        {"run": "myrun", "status": "PASS", "created": "t0",
         "extra_args": ["--out-name", "ppo_goal_myrun"]},
    ])
    import rl_move.sim.distill_gru as dg
    from rl_move.orchestrator import state_dir
    monkeypatch.setattr(state_dir, "LEDGER", ledger)
    monkeypatch.setattr(dg, "POLICY_DIR", tmp_path / "empty_policies")
    (tmp_path / "empty_policies").mkdir()
    with pytest.raises(SystemExit, match="does not exist"):
        pull_teacher_run("myrun")


def test_merge_teacher_cfgs_bit_exact_when_nothing_pulled():
    explicit = {"reward.k_step_event": 0.0}
    structural = {"obs.mode_onehot": 1.0}
    stance, walk = merge_teacher_cfgs(None, None, explicit, structural)
    legacy = structural | explicit
    assert stance == legacy
    assert walk == legacy


def test_merge_teacher_cfgs_precedence_pulled_lt_structural_lt_explicit():
    stance_pulled = {"bus.write_speed": 400.0, "safety.max_delta_q_deg": 0.75}
    walk_pulled = {"bus.write_speed": 400.0, "safety.max_delta_q_deg": 0.75}
    explicit = {"safety.max_delta_q_deg": 5.0}  # user forces this value
    structural = {"obs.mode_onehot": 1.0}
    stance, walk = merge_teacher_cfgs(stance_pulled, walk_pulled, explicit,
                                      structural)
    # explicit overrides the (agreeing) pulled value on both sides
    assert stance["safety.max_delta_q_deg"] == 5.0
    assert walk["safety.max_delta_q_deg"] == 5.0
    assert stance["bus.write_speed"] == 400.0
    assert stance["obs.mode_onehot"] == 1.0


def test_merge_teacher_cfgs_raises_on_unresolved_conflict():
    stance_pulled = {"safety.max_delta_q_deg": 0.75}
    walk_pulled = {"safety.max_delta_q_deg": 7.2}
    with pytest.raises(SystemExit, match="cfg conflict"):
        merge_teacher_cfgs(stance_pulled, walk_pulled, {}, {})


def test_merge_teacher_cfgs_explicit_resolves_conflict():
    stance_pulled = {"safety.max_delta_q_deg": 0.75}
    walk_pulled = {"safety.max_delta_q_deg": 7.2}
    explicit = {"safety.max_delta_q_deg": 0.75}
    stance, walk = merge_teacher_cfgs(stance_pulled, walk_pulled, explicit, {})
    assert stance["safety.max_delta_q_deg"] == 0.75
    assert walk["safety.max_delta_q_deg"] == 0.75
