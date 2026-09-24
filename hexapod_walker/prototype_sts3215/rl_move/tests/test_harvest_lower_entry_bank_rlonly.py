"""Mechanics-only tests for harvest_lower_entry_bank_rlonly.py (per
RESEARCH_RULES "Tests": fast, no mujoco/rollouts, no artifacts)."""
import sys

import numpy as np
import pytest


def test_cli_registers_flags_with_sane_defaults(capsys):
    from rl_move.sim import harvest_lower_entry_bank_rlonly as mod

    old_argv = sys.argv
    sys.argv = ["harvest_lower_entry_bank_rlonly", "--help"]
    try:
        with pytest.raises(SystemExit):
            mod.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--walk" in out
    assert "--walk-recipe" in out
    assert "slew_smooth_s0" in out
    assert "--episodes" in out
    assert "--sample-every-s" in out
    assert "--out" in out


def test_cli_requires_out(capsys):
    from rl_move.sim import harvest_lower_entry_bank_rlonly as mod

    old_argv = sys.argv
    sys.argv = ["harvest_lower_entry_bank_rlonly"]
    try:
        with pytest.raises(SystemExit):
            mod.main()
    finally:
        sys.argv = old_argv


def test_written_npz_round_trips_through_the_production_loader(tmp_path):
    """Build a tiny fake bank with the EXACT save call this module
    uses (copy of its own np.savez args, no mujoco/env dependency) and
    confirm sim_env.py's own production loader (_load_robot_abs_q_npz)
    accepts it and the qvel companion shape-checks clean -- this is
    the one contract the harvester MUST satisfy, checked without
    paying for a real rollout."""
    from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
    from rl_move.sim.balance_helpers import _load_robot_abs_q_npz

    out = tmp_path / "fake_bank.npz"
    q_deg = np.zeros((3, 18))
    qvel = np.ones((3, 18)) * 0.5
    np.savez(out, q_rad=q_deg * (np.pi / 180.0), qvel_mujoco=qvel,
             joint_frame=FRAME_ROBOT_ABS, joint_contract=JOINT_CONTRACT,
             source_walk="fake", walk_recipe="slew_smooth_s0",
             episodes=1, sample_every_s=1.0)
    arr, npz = _load_robot_abs_q_npz(str(out), source="test")
    assert arr.shape == (3, 18)
    qvel_loaded = np.asarray(npz["qvel_mujoco"])
    assert qvel_loaded.shape == arr.shape
    npz.close()
