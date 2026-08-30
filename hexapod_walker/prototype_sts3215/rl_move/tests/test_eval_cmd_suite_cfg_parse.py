"""Regression test (2026-08-30, singleframe-acq1-stdanneal cmd_suite
launch): eval_cmd_suite.py used to reimplement its own float-or-
string-only --cfg-set parser instead of sharing
train_ppo_sim._parse_cfg_set, silently keeping a '[..]' JSON-list
value (e.g. goal.walk_heading_set=[0,0.785,-0.785]) as the literal
bracketed STRING. walk_task.py's heading-set code handles a genuine
list fine but crashes float('[0') when handed that raw string --
exactly the class of bug eval_checkpoint.py's own docstring already
names and fixed once (08-10, cw-stand-b2p1). This pins both the
shared parser's list behavior and that eval_cmd_suite.py now imports
it instead of reimplementing it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_move.sim.train_ppo_sim import _parse_cfg_set  # noqa: E402


def test_bracket_value_parses_as_a_json_list():
    out = _parse_cfg_set(["goal.walk_heading_set=[0,0.7853982,"
                          "-0.7853982]"])
    assert out["goal.walk_heading_set"] == [0, 0.7853982, -0.7853982]


def test_plain_float_and_string_values_unchanged():
    out = _parse_cfg_set(["reward.k_action=0.005",
                          "goal.walk_park_bank=some/path.npz"])
    assert out["reward.k_action"] == 0.005
    assert out["goal.walk_park_bank"] == "some/path.npz"


def test_eval_cmd_suite_shares_the_parser_not_a_local_reimplementation():
    src = (ROOT / "rl_move" / "sim" / "eval_cmd_suite.py").read_text()
    assert "_parse_cfg_set" in src, (
        "eval_cmd_suite.py must import/use train_ppo_sim._parse_cfg_set "
        "for --cfg-set parsing, never a local float-or-string-only copy "
        "(that copy silently mishandled '[..]' JSON-list values)")


def test_eval_cmd_suite_cfg_dict_matches_shared_parser():
    """End-to-end check of the exact block eval_cmd_suite.main() runs
    (without importing the module itself, which pulls in mujoco/torch
    at import time): apply _parse_cfg_set output the same way the tool
    does and confirm the walk_heading_set survives as a real list."""
    specs = ["env.model_source=mesh",
            "goal.walk_heading_set=[0,0.7853982,-0.7853982]",
            "reward.k_action=0.005"]
    cfg: dict = {}
    for key, parsed in _parse_cfg_set(specs).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    assert cfg["goal"]["walk_heading_set"] == [0, 0.7853982, -0.7853982]
    assert cfg["env"]["model_source"] == "mesh"
    assert cfg["reward"]["k_action"] == 0.005
