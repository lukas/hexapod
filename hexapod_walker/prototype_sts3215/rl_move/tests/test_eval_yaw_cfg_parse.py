"""Regression test (2026-09-29, cw-walk50hz-tf128l2h16-yaw-contract-
turngate-s0's own registered eval_yaw gate): eval_yaw.py used to
reimplement its own float-or-string-only --cfg-set parser instead of
sharing cfg_set._parse_cfg_set, silently keeping a '[..]' JSON-list
value (e.g. goal.walk_heading_set=[]) as the literal bracketed STRING.
walk_task.py's heading-set code handles a genuine list fine but
crashes float('[]') when handed that raw string -- the exact same bug
class eval_checkpoint.py's docstring already names and fixed once
(08-10, cw-stand-b2p1) and eval_cmd_suite.py fixed again (08-30,
test_eval_cmd_suite_cfg_parse.py) -- eval_yaw.py was the one caller
still carrying the broken local copy. This pins that eval_yaw.py now
imports the shared parser instead of reimplementing it.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from rl_move.sim.cfg_set import _parse_cfg_set


def test_eval_yaw_shares_the_parser_not_a_local_reimplementation():
    src = (ROOT / "rl_move" / "sim" / "eval_yaw.py").read_text()
    assert "_parse_cfg_set" in src, (
        "eval_yaw.py must import/use cfg_set._parse_cfg_set for "
        "--cfg-set parsing, never a local float-or-string-only copy "
        "(that copy silently mishandled '[..]' JSON-list values, e.g. "
        "goal.walk_heading_set=[] crashing float('[]') deep in "
        "walk_task._sample_walk)")


def test_eval_yaw_cfg_dict_matches_shared_parser():
    """End-to-end check of the exact block eval_yaw.main() runs
    (without importing the module itself, which pulls in mujoco/torch
    at import time): apply _parse_cfg_set output the same way the tool
    does and confirm an empty heading-set bracket survives as a real
    empty list, not the literal string '[]'."""
    specs = ["env.model_source=mesh",
            "goal.walk_heading_set=[]",
            "reward.k_current=0.005"]
    cfg: dict = {}
    for key, parsed in _parse_cfg_set(specs).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    assert cfg["goal"]["walk_heading_set"] == []
    assert cfg["env"]["model_source"] == "mesh"
    assert cfg["reward"]["k_current"] == 0.005
