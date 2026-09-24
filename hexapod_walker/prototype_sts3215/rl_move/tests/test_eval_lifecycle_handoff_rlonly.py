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
    sacrificed_legs,
    write_mp4,
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
