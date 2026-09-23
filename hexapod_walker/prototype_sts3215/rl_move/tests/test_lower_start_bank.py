"""goal.lower_start_bank / goal.lower_start_bank_frac (2026-09-23,
standwalk STATUS ~18:3x): composed-session lower-entry (real
walk-exit) pose exposure -- the lower-mode generalization of
goal.rise_start_bank's post-lower rise fix, since every lower episode
today starts from the idealized symmetric plant instead of a real
mid-gait walk-exit pose. Contract under test mirrors
test_rise_start_bank.py:
  - default OFF and bit-exact: frac>0 with no bank path changes
    nothing;
  - bank + frac=1: every non-belly/non-partial lower episode starts
    from a bank pose (start_at="lower_bank", start_kind
    "post_walk_lower");
  - frac=0.5 mixes bank and synthetic (plant) starts;
  - a malformed bank fails loudly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.sim_env import N_JOINTS
from rl_move.env import start_kind_of


def _mk_bank(tmp_path: Path, k: int = 4) -> tuple[Path, np.ndarray]:
    q = np.zeros((k, N_JOINTS))
    for i in range(k):
        q[i, 2::3] = 0.20 + 0.05 * i
    p = tmp_path / "lower_entry_bank.npz"
    np.savez(p, q_rad=q, meta="{}", joint_frame="robot_abs",
             joint_contract="robot_abs_tibia_v2")
    return p, q


def _lower_env(seed: int, **goal_over) -> SimHexapodGoalEnv:
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["lower_belly_start_frac"] = 0.0
    goal["lower_partial_frac"] = 0.0
    for k, v in goal_over.items():
        goal[k] = v
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "lower" else 0.0)
    return env


def test_frac_without_bank_is_bit_exact():
    env_a = _lower_env(seed=7)
    env_b = _lower_env(seed=7, lower_start_bank_frac=0.7)
    for _ in range(6):
        env_a.reset()
        env_b.reset()
        assert env_b._goal_traj.start_at != "lower_bank"
        assert env_a._goal_traj.start_at == env_b._goal_traj.start_at
        np.testing.assert_array_equal(
            env_a.data.qpos[env_a._qadr], env_b.data.qpos[env_b._qadr])
    env_a.close()
    env_b.close()


def test_bank_frac_one_starts_from_bank(tmp_path):
    bank_path, bank = _mk_bank(tmp_path)
    env = _lower_env(seed=3, lower_start_bank=str(bank_path),
                     lower_start_bank_frac=1.0)
    for _ in range(5):
        obs, info = env.reset()
        assert info["goal_mode"] == "lower"
        assert env._goal_traj.start_at == "lower_bank"
        assert start_kind_of(env._goal_traj) == "post_walk_lower"
        assert np.all(np.isfinite(obs))
        q = env.data.qpos[env._qadr]
        d = np.abs(bank - q[None, :]).max(axis=1).min()
        assert d < 0.25, f"reset pose {d:.3f} rad from nearest bank row"
    env.close()


def test_bank_frac_mixes_kinds(tmp_path):
    bank_path, _ = _mk_bank(tmp_path)
    env = _lower_env(seed=11, lower_start_bank=str(bank_path),
                     lower_start_bank_frac=0.5)
    kinds = set()
    for _ in range(16):
        env.reset()
        kinds.add(env._goal_traj.start_at)
    assert "lower_bank" in kinds, "bank starts never sampled at frac=0.5"
    assert kinds - {"lower_bank"}, "frac=0.5 must keep synthetic starts"
    env.close()


def test_malformed_bank_raises(tmp_path):
    bad = tmp_path / "bad.npz"
    np.savez(bad, q_rad=np.zeros((3, 7)))
    env = _lower_env(seed=1, lower_start_bank=str(bad),
                     lower_start_bank_frac=1.0)
    with pytest.raises(ValueError, match="lower_start_bank"):
        for _ in range(3):
            env.reset()
    env.close()
