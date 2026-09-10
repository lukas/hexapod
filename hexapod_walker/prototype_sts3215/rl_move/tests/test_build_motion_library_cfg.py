"""Mechanics tests for build_motion_library --cfg-set plumbing
(2026-09-10 50 Hz deployment retrain order). Fast, no env rollout."""
import copy

from rl_move.sim.build_motion_library import (
    _apply_cfg_overrides, _parse_cfg_set)


def test_parse_cfg_set_semantics():
    out = _parse_cfg_set([
        "control.hz=50", "goal.rise_height_mm=[79, 87]",
        "goal.walk_park_bank=some/path.npz"])
    assert out["control.hz"] == 50.0
    assert out["goal.rise_height_mm"] == [79, 87]
    assert out["goal.walk_park_bank"] == "some/path.npz"
    assert _parse_cfg_set(None) == {}
    assert _parse_cfg_set([]) == {}


def test_apply_cfg_overrides_nested_and_noop():
    cfg = {"control": {"hz": 25.0}, "safety": {"max_delta_q_deg": 1.5}}
    before = copy.deepcopy(cfg)
    # empty overrides = untouched (bit-exact legacy path)
    assert _apply_cfg_overrides(cfg, None) == before
    assert _apply_cfg_overrides(cfg, {}) == before
    out = _apply_cfg_overrides(cfg, {"control.hz": 50.0,
                                     "safety.max_delta_q_deg": 2.5,
                                     "bus.write_speed": 1500.0})
    assert out["control"]["hz"] == 50.0
    assert out["safety"]["max_delta_q_deg"] == 2.5
    assert out["bus"]["write_speed"] == 1500.0  # created nested section
