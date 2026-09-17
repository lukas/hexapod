"""Mechanics-only tests for the bundle_rlonly_v2 walk-role cfg-set
recipe (walkcurr lifecycle-composition build, 2026-09-17). No
rollouts, no rankings -- just checks the arg list is well-formed and
applies cleanly, per RESEARCH_RULES "Tests"."""
from rl_move.sim.cfg_recipe_walk50hz_rlonly_v2 import (
    CFG_ARGS,
    apply_to_cfg,
    build_cfg_args,
)


def test_cfg_args_are_key_value_strings_no_dupes():
    args = build_cfg_args()
    assert args, "cfg arg list must not be empty"
    keys = [kv.split("=", 1)[0] for kv in args]
    assert all("=" in kv for kv in args)
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, dupes


def test_model_source_and_control_hz_present():
    args = set(build_cfg_args())
    assert "env.model_source=mesh_mjx" in args
    assert "control.hz=50" in args


def test_apply_to_cfg_parses_list_and_string_and_float_values():
    cfg = apply_to_cfg({})
    # float
    assert cfg["control"]["hz"] == 50.0
    # bracketed JSON-list value
    assert isinstance(cfg["goal"]["walk_heading_set"], list)
    assert len(cfg["goal"]["walk_heading_set"]) == 8
    # bare non-numeric string ('write_speed' is a literal token, not a
    # bus field lookup key -- the trainer resolves it downstream)
    assert cfg["bus"]["servo_vel_max_counts_s"] == "write_speed"
    # comma-separated pair that is NOT bracketed stays a literal string
    # (same convention as every other dr.*_scale="lo,hi" cfg-set value
    # on this project -- the consumer splits it, not this parser)
    assert cfg["dr"]["latency_scale"] == "1,1"


def test_apply_to_cfg_does_not_mutate_module_list():
    before = list(CFG_ARGS)
    apply_to_cfg({})
    assert CFG_ARGS == before
