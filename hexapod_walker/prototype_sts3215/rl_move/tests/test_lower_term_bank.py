"""goal.lower_term_bank / goal.lower_term_start_frac (2026-10-04,
walkcurr lowerrole_terminal_support_forensics_2026-10-02 item 1 /
STATUS Next 6 "composed sub-controller dedicated to the terminal-hold
phase"): terminal-hold specialist start states -- spawn ALREADY AT a
harvested post-ramp converged pose with the height ref FLAT at that
row's own recorded target for the whole episode, instead of the normal
plant-start descent-then-hold schedule. Contract under test mirrors
test_lower_start_bank.py, PLUS the index-coupling invariant unique to
this bank (pose and height target must agree on the same row, unlike
every other bank here which draws its spawn row independently of the
height schedule):
  - default OFF and bit-exact: frac>0 with no bank path changes
    nothing;
  - bank + frac=1: every non-belly lower episode starts from a bank
    row (start_at="lower_term") with height flat at THAT row's
    target_m, and the spawned pose matches the SAME row (not just
    "some" row);
  - frac=0.5 mixes bank and synthetic starts;
  - a bank missing target_m, or with mismatched q_rad/target_m
    lengths, fails loudly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.sim_env import N_JOINTS


def _mk_bank(tmp_path: Path, k: int = 4) -> tuple[Path, np.ndarray, np.ndarray]:
    q = np.zeros((k, N_JOINTS))
    targets = np.zeros(k)
    for i in range(k):
        q[i, 2::3] = 0.30 + 0.05 * i
        targets[i] = -0.03 - 0.005 * i
    p = tmp_path / "lower_term_bank.npz"
    np.savez(p, q_rad=q, qvel_mujoco=np.zeros_like(q), target_m=targets,
             meta="{}", joint_frame="robot_abs",
             joint_contract="robot_abs_tibia_v2")
    return p, q, targets


def _lower_env(seed: int, **goal_over) -> SimHexapodGoalEnv:
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["lower_belly_start_frac"] = 0.0
    goal["lower_partial_frac"] = 0.0
    goal["lower_start_bank_frac"] = 0.0
    for k, v in goal_over.items():
        goal[k] = v
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "lower" else 0.0)
    return env


def test_frac_without_bank_is_bit_exact():
    env_a = _lower_env(seed=7)
    env_b = _lower_env(seed=7, lower_term_start_frac=0.7)
    for _ in range(6):
        env_a.reset()
        env_b.reset()
        assert env_b._goal_traj.start_at != "lower_term"
        assert env_a._goal_traj.start_at == env_b._goal_traj.start_at
        np.testing.assert_array_equal(
            env_a.data.qpos[env_a._qadr], env_b.data.qpos[env_b._qadr])
        np.testing.assert_array_equal(
            env_a._goal_traj.height, env_b._goal_traj.height)
    env_a.close()
    env_b.close()


def test_bank_frac_one_starts_from_matching_row(tmp_path):
    bank_path, bank_q, targets = _mk_bank(tmp_path)
    env = _lower_env(seed=3, lower_term_bank=str(bank_path),
                     lower_term_start_frac=1.0)
    for _ in range(8):
        obs, info = env.reset()
        assert info["goal_mode"] == "lower"
        traj = env._goal_traj
        assert traj.start_at == "lower_term"
        assert 0 <= traj.term_bank_idx < len(bank_q)
        assert np.all(np.isfinite(obs))
        # Height ref is FLAT at the drawn row's own target for the
        # whole episode (no ramp, no pre-descent hold).
        np.testing.assert_allclose(
            traj.height, targets[traj.term_bank_idx])
        # Spawned pose matches THAT SAME row (index-coupling
        # invariant), not merely "some" row in the bank.
        q = env.data.qpos[env._qadr]
        d = np.abs(bank_q[traj.term_bank_idx] - q).max()
        assert d < 0.25, f"reset pose {d:.3f} rad from its own drawn row"
    env.close()


def test_bank_frac_mixes_kinds(tmp_path):
    bank_path, _, _ = _mk_bank(tmp_path)
    env = _lower_env(seed=11, lower_term_bank=str(bank_path),
                     lower_term_start_frac=0.5)
    kinds = set()
    for _ in range(16):
        env.reset()
        kinds.add(env._goal_traj.start_at)
    assert "lower_term" in kinds, "bank starts never sampled at frac=0.5"
    assert kinds - {"lower_term"}, "frac=0.5 must keep synthetic starts"
    env.close()


def test_missing_target_m_raises(tmp_path):
    bad = tmp_path / "bad.npz"
    q = np.zeros((3, N_JOINTS))
    np.savez(bad, q_rad=q, qvel_mujoco=q,
             joint_frame="robot_abs", joint_contract="robot_abs_tibia_v2")
    env = _lower_env(seed=1, lower_term_bank=str(bad),
                     lower_term_start_frac=1.0)
    with pytest.raises(ValueError, match="target_m"):
        for _ in range(3):
            env.reset()
    env.close()


def test_malformed_pose_bank_raises(tmp_path):
    bad = tmp_path / "bad_pose.npz"
    np.savez(bad, q_rad=np.zeros((3, 7)), target_m=np.zeros(3))
    env = _lower_env(seed=1, lower_term_bank=str(bad),
                     lower_term_start_frac=1.0)
    with pytest.raises(ValueError, match="lower_term_bank"):
        for _ in range(3):
            env.reset()
    env.close()
