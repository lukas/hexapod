"""Mechanics-only tests for the rl_only lifecycle-composition handoff
tool (walkcurr, 2026-09-17): the pure physical-state copy helper, no
mujoco/PPO/rollouts, per RESEARCH_RULES "Tests"."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from rl_move.sim.eval_lifecycle_handoff_rlonly import (
    PhysicalState,
    apply_physical_state,
    capture_physical_state,
    heading_to_vxvy,
    joint_label,
    sacrificed_legs,
    trip_summary,
    write_mp4,
    zeroed_qvel_state,
)


def _fake_env(n=4):
    data = SimpleNamespace(
        qpos=np.arange(n, dtype=float),
        qvel=np.arange(n, dtype=float) * 2.0,
        ctrl=np.arange(n, dtype=float) * 3.0,
        act=np.zeros(0),
    )
    safety = SimpleNamespace(_last_safe=np.arange(n, dtype=float) * 5.0)
    return SimpleNamespace(data=data, safety=safety)


def test_capture_physical_state_copies_not_aliases():
    env = _fake_env()
    state = capture_physical_state(env)
    env.data.qpos[0] = 999.0
    env.safety._last_safe[0] = 999.0
    assert state.qpos[0] == 0.0
    assert state.last_safe[0] == 0.0


def test_apply_physical_state_overwrites_destination_arrays():
    src = _fake_env()
    state = capture_physical_state(src)
    dst = _fake_env()
    dst.data.qpos[:] = -1.0
    dst.data.qvel[:] = -1.0
    dst.data.ctrl[:] = -1.0
    dst.safety._last_safe[:] = -1.0
    apply_physical_state(dst, state)
    assert np.array_equal(dst.data.qpos, state.qpos)
    assert np.array_equal(dst.data.qvel, state.qvel)
    assert np.array_equal(dst.data.ctrl, state.ctrl)
    assert np.array_equal(dst.safety._last_safe, state.last_safe)
    # mutating the source state's captured array afterward must not
    # leak into the destination env (own copy, not aliased)
    state.last_safe[0] = 12345.0
    assert dst.safety._last_safe[0] != 12345.0


def test_zeroed_qvel_state_zeros_only_velocity():
    state = PhysicalState(qpos=np.array([1.0, 2.0]),
                           qvel=np.array([3.0, 4.0]),
                           ctrl=np.array([5.0, 6.0]),
                           act=np.array([7.0, 8.0]),
                           last_safe=np.array([9.0, 10.0]))
    diag = zeroed_qvel_state(state)
    assert np.array_equal(diag.qvel, np.zeros(2))
    assert np.array_equal(diag.qpos, state.qpos)
    assert np.array_equal(diag.ctrl, state.ctrl)
    assert np.array_equal(diag.act, state.act)
    assert np.array_equal(diag.last_safe, state.last_safe)


def test_zeroed_qvel_state_does_not_alias_or_mutate_input():
    state = PhysicalState(qpos=np.array([1.0]), qvel=np.array([3.0]),
                           ctrl=np.array([5.0]), act=None,
                           last_safe=np.array([9.0]))
    diag = zeroed_qvel_state(state)
    assert diag.act is None
    diag.qpos[0] = -1.0
    assert state.qpos[0] == 1.0
    assert state.qvel[0] == 3.0  # original untouched, not zeroed in place


def test_apply_physical_state_handles_empty_act():
    env = _fake_env()
    state = PhysicalState(qpos=np.zeros(4), qvel=np.zeros(4),
                           ctrl=np.zeros(4), act=None,
                           last_safe=np.zeros(4))
    # must not raise even though env.data.act is size-0
    apply_physical_state(env, state)


# --- full-direction extension (2026-09-20): heading_to_vxvy + CLI flags ---

def test_heading_to_vxvy_zero_matches_old_forward_only_default():
    # heading_deg=0.0 is the new default; must reproduce the ORIGINAL
    # forward-only SCHEDULE(v) = (v, 0.0) bit-exactly.
    vx, vy = heading_to_vxvy(0.06, 0.0)
    assert vx == pytest.approx(0.06)
    assert vy == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("heading_deg,exp_vx,exp_vy", [
    (90.0, 0.0, 0.06),
    (-90.0, 0.0, -0.06),
    (180.0, -0.06, 0.0),
    (45.0, 0.06 * math.sqrt(0.5), 0.06 * math.sqrt(0.5)),
])
def test_heading_to_vxvy_matches_eval_checkpoint_convention(
        heading_deg, exp_vx, exp_vy):
    # Same 0/+-45/+-90/+-135/180 convention eval_checkpoint.py's
    # PINNED_HEADING_DEFAULTS uses (0=forward, +90=left/+y).
    vx, vy = heading_to_vxvy(0.06, heading_deg)
    assert vx == pytest.approx(exp_vx, abs=1e-9)
    assert vy == pytest.approx(exp_vy, abs=1e-9)
    assert math.hypot(vx, vy) == pytest.approx(0.06)


# --- sacrificed_legs: same formula as eval_checkpoint.py's own gate ---

def _contact_pad(pattern: list[list[bool]]):
    contact = np.asarray(pattern, dtype=bool)
    pad_xy = np.zeros((contact.shape[0], contact.shape[1], 2))
    return contact, pad_xy


def test_sacrificed_legs_flags_permanently_airborne_leg():
    # leg 0 never touches the ground (duty=0 < 0.10) across 10 ticks;
    # every other leg alternates (duty=0.5, some swings).
    pattern = [[False, True, False, True, False, True] for _ in range(10)]
    for t in range(0, 10, 2):
        pattern[t] = [False, False, True, False, True, False]
    contact, pad_xy = _contact_pad(pattern)
    sac = sacrificed_legs(contact, pad_xy)
    assert 0 in sac


def test_sacrificed_legs_flags_dragged_anchor_no_swings():
    # leg 0 stays planted (duty>0.95) for the WHOLE window with zero
    # swing transitions -- a dragged anchor, not real support cycling.
    pattern = [[True, False, True, False, True, False] for _ in range(10)]
    contact, pad_xy = _contact_pad(pattern)
    sac = sacrificed_legs(contact, pad_xy)
    assert 0 in sac


def test_sacrificed_legs_clears_when_every_leg_cycles():
    pattern = [[bool((t + f) % 2) for f in range(6)] for t in range(20)]
    contact, pad_xy = _contact_pad(pattern)
    assert sacrificed_legs(contact, pad_xy) == []


def test_cli_registers_heading_and_rot60_flags_default_off(capsys):
    import sys

    from rl_move.sim import eval_lifecycle_handoff_rlonly as mod

    old_argv = sys.argv
    sys.argv = ["eval_lifecycle_handoff_rlonly", "--help"]
    try:
        with pytest.raises(SystemExit):
            mod.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--heading-deg" in out
    assert "--rot60" in out
    assert "--hold-s" in out
    assert "--video" in out
    assert "--walk-recipe" in out
    assert "rlonly_v2" in out
    assert "slew_smooth_s0" in out
    assert "safewiden6_acq1" in out
    assert "--lower" in out
    assert "--lower-recipe" in out
    assert "--lower-episode-s" in out
    assert "--diag-zero-lower-qvel" in out


def test_lower_cfg_recipe_excludes_ramp_and_obs_keys():
    """The --lower cfg recipe (imported lazily only when --lower is
    passed, per module docstring) must be well-formed and NOT carry
    env.dr_stage_ramp_steps (moot/crash-prone at randomize=False, see
    module docstring) or any obs.* override (this launch command set
    none -- config.yaml's own defaults apply, verified against the
    ledger's own extra_args, not assumed from a sibling lineage)."""
    from rl_move.sim.cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (  # noqa: E501
        CFG_ARGS,
    )
    assert "env.model_source=mesh_mjx" in CFG_ARGS
    assert "control.hz=50" in CFG_ARGS
    assert not any(k.startswith("env.dr_stage_ramp_steps") for k in CFG_ARGS)
    assert not any(k.startswith("obs.") for k in CFG_ARGS)
    # 2026-10-01 forensics fix: this checkpoint trained before the
    # operator's 2026-09-26 bus-default bump (f77d8e987) and has no
    # training sidecar to auto-recover the old 400/20 profile from --
    # pinned explicitly so this eval harness doesn't silently replay
    # it under today's 2000/80 default.
    assert "bus.write_speed=400" in CFG_ARGS
    assert "bus.write_acc=20" in CFG_ARGS


def test_write_mp4_empty_frames_is_noop(tmp_path):
    out = tmp_path / "clip.mp4"
    write_mp4([], out, fps=25)
    assert not out.exists()


def test_write_mp4_writes_a_nonempty_file(tmp_path):
    frames = [np.zeros((8, 16, 3), dtype=np.uint8) for _ in range(4)]
    out = tmp_path / "sub" / "clip.mp4"
    write_mp4(frames, out, fps=25)
    assert out.exists()
    assert out.stat().st_size > 0


def test_joint_label_matches_safety_joint_name_convention():
    # L0 yaw/hip/knee is indices 0/1/2 (hexapod_core.joint_frame order,
    # same as safety._joint_name's own f"L{leg} {axis}" format).
    assert joint_label(0) == "L0 yaw"
    assert joint_label(1) == "L0 hip"
    assert joint_label(2) == "L0 knee"
    assert joint_label(16) == "L5 hip"


def test_trip_summary_picks_the_hot_joint_at_the_last_tick():
    # 4 ticks, 18 joints, all quiet except joint 7 which ramps hot and
    # stays over threshold (2.5 A) for the last 2 ticks -- the episode
    # "terminated" exactly when this trace was captured (termination
    # landed on the last row), mirroring a real over_current trip.
    trace = np.zeros((4, 18))
    trace[:, 7] = [0.5, 1.0, 3.0, 3.2]
    out = trip_summary(trace, max_current=2.5)
    assert out["final_joint"] == 7
    assert out["final_joint_label"] == joint_label(7)
    assert out["final_current_a"] == pytest.approx(3.2)
    assert out["hot_run_ticks"] == 2
    assert out["trip_frac"] == pytest.approx(1.0)
    assert len(out["per_joint_max"]) == 18
    assert out["per_joint_max"][7] == pytest.approx(3.2)


def test_trip_summary_hot_run_resets_if_joint_dips_below_threshold():
    trace = np.zeros((5, 18))
    # joint 3 spikes once, dips back down, then spikes again at the end
    # -- hot_run_ticks must only count the TRAILING consecutive run,
    # not the total number of over-threshold ticks (which is 3).
    trace[:, 3] = [3.0, 0.1, 3.0, 3.0, 3.0]
    out = trip_summary(trace, max_current=2.5)
    assert out["final_joint"] == 3
    assert out["hot_run_ticks"] == 3


def test_trip_summary_rejects_empty_trace():
    with pytest.raises(ValueError):
        trip_summary(np.zeros((0, 18)), max_current=2.5)


def test_trip_summary_omits_stall_classification_when_arrays_absent():
    trace = np.zeros((4, 18))
    trace[:, 7] = [0.5, 1.0, 3.0, 3.2]
    out = trip_summary(trace, max_current=2.5)
    assert "stall_classification" not in out
    assert "hot_qvel_med_rad_s" not in out


def test_trip_summary_classifies_corroborated_stall():
    # Joint 7 hot for the trailing 2 ticks; near-zero qvel throughout
    # and the chassis height barely moves over that window -- a real
    # stall, not a rail image of a still-working joint.
    trace = np.zeros((4, 18))
    trace[:, 7] = [0.5, 1.0, 3.0, 3.2]
    qvel = np.zeros((4, 18))
    qvel[:, 7] = [0.3, 0.2, 0.01, 0.02]
    height_mm = np.array([100.0, 95.0, 90.0, 89.8])
    out = trip_summary(trace, max_current=2.5, qvel_trace=qvel,
                       height_trace_mm=height_mm)
    assert out["stall_classification"] == "CORROBORATED_STALL"
    assert out["hot_qvel_med_rad_s"] == pytest.approx(0.015, abs=1e-3)
    assert out["hot_window_height_delta_mm"] == pytest.approx(-0.2, abs=1e-3)


def test_trip_summary_classifies_rail_moving_when_joint_still_turning():
    # Same current trace, but the joint is still clearly turning during
    # the hot window -- high modeled load, not a stall.
    trace = np.zeros((4, 18))
    trace[:, 7] = [0.5, 1.0, 3.0, 3.2]
    qvel = np.zeros((4, 18))
    qvel[:, 7] = [0.3, 0.2, 0.9, 1.1]
    height_mm = np.array([100.0, 95.0, 90.0, 89.8])
    out = trip_summary(trace, max_current=2.5, qvel_trace=qvel,
                       height_trace_mm=height_mm)
    assert out["stall_classification"] == "RAIL_MOVING"


def test_trip_summary_classifies_rail_moving_when_body_still_descending():
    # Joint itself is static but the body is still making real height
    # progress over the hot window -- not a dead stall either.
    trace = np.zeros((4, 18))
    trace[:, 7] = [0.5, 1.0, 3.0, 3.2]
    qvel = np.zeros((4, 18))
    qvel[:, 7] = [0.3, 0.2, 0.01, 0.01]
    height_mm = np.array([100.0, 95.0, 70.0, 50.0])
    out = trip_summary(trace, max_current=2.5, qvel_trace=qvel,
                       height_trace_mm=height_mm)
    assert out["stall_classification"] == "RAIL_MOVING"


def test_trip_summary_rejects_mismatched_qvel_length():
    trace = np.zeros((4, 18))
    with pytest.raises(ValueError):
        trip_summary(trace, max_current=2.5, qvel_trace=np.zeros((3, 18)),
                    height_trace_mm=np.zeros(4))


def test_trip_summary_rejects_mismatched_height_length():
    trace = np.zeros((4, 18))
    with pytest.raises(ValueError):
        trip_summary(trace, max_current=2.5, qvel_trace=np.zeros((4, 18)),
                    height_trace_mm=np.zeros(3))
