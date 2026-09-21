"""Mechanics-only tests for the `cw-walk50hz-fs-bisect-drv-
safewiden6-acq1` walk-role cfg-set recipe (walkcurr packaging,
2026-09-21). No rollouts, no rankings -- just checks the arg list is
well-formed and applies cleanly, per RESEARCH_RULES "Tests". Mirrors
test_cfg_recipe_walk50hz_slew_smooth_s0.py 1:1 for this sibling
module."""
from rl_move.sim.cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1 import (
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


def test_differs_from_slew_smooth_s0_on_the_widened_latency_axis():
    """The whole point of this being a SEPARATE module: this
    checkpoint's own 5-group safe-widen bundle differs from its
    parent's recipe on the one always-on dr key that changed
    (latency_scale), even though the difference is inert at eval's own
    dr-scale=0.0 (see module docstring)."""
    args = dict(kv.split("=", 1) for kv in build_cfg_args())
    assert args["dr.latency_scale"] == "0.7,2.0"
    assert args["reward.k_gyro"] == "0.15"
    assert args["reward.k_action_delta"] == "0.03"
    assert args["reward.k_current"] == "0.02"
    assert args["reward.k_action_accel"] == "0.02"
    assert args["bus.current_model"] == "power"


def test_apply_to_cfg_parses_list_and_string_and_float_values():
    cfg = apply_to_cfg({})
    assert cfg["control"]["hz"] == 50.0
    assert isinstance(cfg["goal"]["walk_heading_set"], list)
    assert len(cfg["goal"]["walk_heading_set"]) == 8
    assert cfg["bus"]["servo_vel_max_counts_s"] == "write_speed"
    assert cfg["dr"]["latency_scale"] == "0.7,2.0"


def test_apply_to_cfg_does_not_mutate_module_list():
    before = list(CFG_ARGS)
    apply_to_cfg({})
    assert CFG_ARGS == before
