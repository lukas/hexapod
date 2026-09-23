"""build_seg_entry_bank.py — pooling a --dump-seg-qpos npz's tagged
rows into a goal.walk_entry_bank/lower_start_bank npz (2026-09-23,
standwalk STATUS ~18:3x generalization of rise_start_bank; v2 adds
qvel_mujoco per row, 2026-09-23 ~19:5x — see sim_env.
_apply_bank_qvel_handoff). Pure numpy, no mujoco/checkpoint
dependency (RESEARCH_RULES "Tests")."""
from __future__ import annotations

import numpy as np
import pytest

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.robot_state import DEG2RAD, N_JOINTS
from rl_move.sim.build_seg_entry_bank import extract_bank_rows


def _mk_dump(tmp_path, name, tags, seed=0):
    rng = np.random.default_rng(seed)
    n = len(tags)
    q_deg = rng.uniform(-10.0, 10.0, size=(n, N_JOINTS))
    qvel = rng.uniform(-0.5, 0.5, size=(n, N_JOINTS))
    p = tmp_path / name
    np.savez(p, seg=np.array(tags), ep=np.arange(n), t_s=np.zeros(n),
             q_deg=q_deg, qvel_rad_s=qvel,
             height_err_mm=np.zeros(n), roll_deg=np.zeros(n),
             pitch_deg=np.zeros(n))
    return p, q_deg, qvel


def test_pools_only_the_requested_tag(tmp_path):
    p, q_deg, qvel = _mk_dump(
        tmp_path, "a.npz",
        ["walk_cold_reset", "walk_entry", "walk_mid", "lower_entry"])
    q_out, qvel_out = extract_bank_rows([p], "walk_entry")
    assert q_out.shape == (1, N_JOINTS)
    assert qvel_out.shape == (1, N_JOINTS)
    np.testing.assert_allclose(q_out[0], q_deg[1] * DEG2RAD)
    np.testing.assert_allclose(qvel_out[0], qvel[1])


def test_pools_across_multiple_files(tmp_path):
    p1, q1, v1 = _mk_dump(tmp_path, "a.npz", ["walk_entry", "walk_entry"],
                          seed=1)
    p2, q2, v2 = _mk_dump(tmp_path, "b.npz", ["walk_entry"], seed=2)
    q_out, qvel_out = extract_bank_rows([p1, p2], "walk_entry")
    assert q_out.shape == (3, N_JOINTS)
    np.testing.assert_allclose(q_out[:2], q1 * DEG2RAD)
    np.testing.assert_allclose(q_out[2:], q2 * DEG2RAD)
    np.testing.assert_allclose(qvel_out[:2], v1)
    np.testing.assert_allclose(qvel_out[2:], v2)


def test_zero_matching_rows_raises(tmp_path):
    p, _, _ = _mk_dump(tmp_path, "a.npz", ["walk_cold_reset", "walk_mid"])
    with pytest.raises(ValueError, match="zero rows"):
        extract_bank_rows([p], "walk_entry")


def test_not_a_dump_npz_raises(tmp_path):
    p = tmp_path / "bad.npz"
    np.savez(p, q_rad=np.zeros((2, N_JOINTS)))
    with pytest.raises(ValueError, match="dump-seg-qpos"):
        extract_bank_rows([p], "walk_entry")


def test_missing_qvel_raises(tmp_path):
    p = tmp_path / "noqvel.npz"
    np.savez(p, seg=np.array(["walk_entry"]), ep=np.zeros(1),
             t_s=np.zeros(1), q_deg=np.zeros((1, N_JOINTS)))
    with pytest.raises(ValueError, match="qvel_rad_s"):
        extract_bank_rows([p], "walk_entry")


def test_main_writes_a_loadable_bank(tmp_path):
    from rl_move.sim.build_seg_entry_bank import main
    p, q_deg, qvel = _mk_dump(tmp_path, "a.npz",
                              ["lower_entry", "lower_entry"])
    out = tmp_path / "bank.npz"
    import sys
    argv = sys.argv
    sys.argv = ["build_seg_entry_bank", "--npz", str(p), "--tag",
               "lower_entry", "--out", str(out)]
    try:
        rc = main()
    finally:
        sys.argv = argv
    assert rc == 0
    d = np.load(out, allow_pickle=True)
    assert str(d["joint_frame"]) == FRAME_ROBOT_ABS
    assert str(d["joint_contract"]) == JOINT_CONTRACT
    np.testing.assert_allclose(d["q_rad"], q_deg * DEG2RAD)
    np.testing.assert_allclose(d["qvel_mujoco"], qvel)
