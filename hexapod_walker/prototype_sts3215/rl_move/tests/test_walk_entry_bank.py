"""goal.walk_entry_bank / goal.walk_entry_bank_frac (2026-09-23,
standwalk STATUS ~18:3x): composed-session walk-entry pose exposure,
the walk-mode generalization of goal.rise_start_bank's post-lower
rise fix. Contract under test:
  - default OFF and bit-exact: frac>0 with no bank path changes
    nothing;
  - bank + frac=1: every non-park walk episode starts from a bank
    pose (start_at="walk_entry_bank", start_kind "post_rise_walk");
  - frac=0.5 mixes bank and synthetic starts;
  - a malformed bank fails loudly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.sim_env import N_JOINTS
from rl_move.env import start_kind_of


def _mk_bank(tmp_path: Path, k: int = 4) -> tuple[Path, np.ndarray]:
    q = np.zeros((k, N_JOINTS))
    for i in range(k):
        q[i, 1::3] = 0.05 * (i + 1)  # distinct hip offsets per row
    p = tmp_path / "walk_entry_bank.npz"
    np.savez(p, q_rad=q, meta="{}", joint_frame="robot_abs",
             joint_contract="robot_abs_tibia_v2")
    return p, q


def _walk_env(seed: int, **goal_over) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_park_start_frac"] = 0.0
    goal["walk_gait_start_frac"] = 0.0
    goal["walk_turn_in_place_frac"] = 0.0
    for k, v in goal_over.items():
        goal[k] = v
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    return env


def test_frac_without_bank_is_bit_exact():
    env_a = _walk_env(seed=7)
    env_b = _walk_env(seed=7, walk_entry_bank_frac=0.7)
    for _ in range(6):
        env_a.reset()
        env_b.reset()
        assert env_b._goal_traj.start_at != "walk_entry_bank"
        assert env_a._goal_traj.start_at == env_b._goal_traj.start_at
        np.testing.assert_array_equal(
            env_a.data.qpos[env_a._qadr], env_b.data.qpos[env_b._qadr])
    env_a.close()
    env_b.close()


def test_bank_frac_one_starts_from_bank(tmp_path):
    bank_path, bank = _mk_bank(tmp_path)
    env = _walk_env(seed=3, walk_entry_bank=str(bank_path),
                    walk_entry_bank_frac=1.0)
    for _ in range(5):
        obs, info = env.reset()
        assert info["goal_mode"] == "walk"
        assert env._goal_traj.start_at == "walk_entry_bank"
        assert start_kind_of(env._goal_traj) == "post_rise_walk"
        assert np.all(np.isfinite(obs))
        q = env.data.qpos[env._qadr]
        d = np.abs(bank - q[None, :]).max(axis=1).min()
        assert d < 0.25, f"reset pose {d:.3f} rad from nearest bank row"
    env.close()


def test_bank_frac_mixes_kinds(tmp_path):
    bank_path, _ = _mk_bank(tmp_path)
    env = _walk_env(seed=11, walk_entry_bank=str(bank_path),
                    walk_entry_bank_frac=0.5)
    kinds = set()
    for _ in range(16):
        env.reset()
        kinds.add(env._goal_traj.start_at)
    assert "walk_entry_bank" in kinds, "bank starts never sampled"
    assert kinds - {"walk_entry_bank"}, "frac=0.5 must keep plant starts"
    env.close()


def test_malformed_bank_raises(tmp_path):
    bad = tmp_path / "bad.npz"
    np.savez(bad, q_rad=np.zeros((3, 7)))
    env = _walk_env(seed=1, walk_entry_bank=str(bad),
                    walk_entry_bank_frac=1.0)
    with pytest.raises(ValueError, match="walk_entry_bank"):
        for _ in range(3):
            env.reset()
    env.close()
