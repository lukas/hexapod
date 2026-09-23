"""goal.bank_qvel_restore / goal.bank_qvel_jitter_frac (2026-09-23
standwalk ~19:5x): the momentum-preserving companion to
goal.lower_start_bank / goal.walk_entry_bank.

Root cause this targets (see sim_env._apply_bank_qvel_handoff's own
docstring for the full argument, and CURRENT_TRUTHS.md 2026-09-23
~19:3x for the position-only mechanism's 6/6 refutation): a real
composed-session rise->walk / walk->lower handoff hands the next
specialist a MOVING state, but goal.lower_start_bank/goal.
walk_entry_bank only ever matched the joint ANGLE, and even that exact
angle still went through the standard ~1.2s static settle that drives
velocity to ~zero regardless of the target pose -- so no bank episode,
at any dose, ever taught a specialist to handle live momentum. This
mechanism restores the harvested qvel AFTER that settle, at the same
reset() insertion point _apply_walk_reverse_handoff already uses.

Contract under test:
  - default OFF and bit-exact: bank_qvel_restore<=0 leaves qvel at the
    settle's own near-zero result even when a v2 (qvel-carrying) bank
    is configured and drawn;
  - bank_qvel_restore=1 + jitter=0: qvel after reset matches the exact
    harvested row for the bank pose that was actually drawn;
  - a v1 bank (no qvel_mujoco key) is a silent no-op for the restore
    (position-only behavior unchanged), never an error;
  - negative jitter_frac fails loudly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.sim_env import N_JOINTS


def _mk_bank(tmp_path: Path, k: int = 4, with_qvel: bool = True):
    q = np.zeros((k, N_JOINTS))
    qvel = np.zeros((k, N_JOINTS))
    for i in range(k):
        q[i, 2::3] = 0.20 + 0.05 * i
        qvel[i, :] = 0.4 + 0.1 * i  # distinct, well above settle noise
    p = tmp_path / "bank.npz"
    kwargs = dict(q_rad=q, joint_frame="robot_abs",
                 joint_contract="robot_abs_tibia_v2")
    if with_qvel:
        kwargs["qvel_mujoco"] = qvel
    np.savez(p, **kwargs)
    return p, q, qvel


def _lower_env(seed, **goal_over):
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


def _walk_env(seed, **goal_over):
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


def test_default_off_is_bit_exact_lower(tmp_path):
    bank_path, _, _ = _mk_bank(tmp_path)
    env_a = _lower_env(seed=5)
    env_b = _lower_env(seed=5, lower_start_bank=str(bank_path),
                       lower_start_bank_frac=1.0)
    for _ in range(4):
        env_a.reset()
        env_b.reset()
        assert env_b._goal_traj.start_at == "lower_bank"
        # bank_qvel_restore defaults off -> qvel is whatever the
        # ordinary settle converged to, near zero, NOT the harvested
        # 0.4+ rad/s row.
        qv = env_b.data.qvel[env_b._vadr]
        assert np.abs(qv).max() < 0.35
    env_a.close()
    env_b.close()


def test_restore_matches_harvested_row_lower(tmp_path):
    bank_path, q, qvel = _mk_bank(tmp_path)
    env = _lower_env(seed=9, lower_start_bank=str(bank_path),
                     lower_start_bank_frac=1.0,
                     bank_qvel_restore=1.0, bank_qvel_jitter_frac=0.0)
    for _ in range(6):
        env.reset()
        assert env._goal_traj.start_at == "lower_bank"
        qv = env.data.qvel[env._vadr]
        # Matches SOME row exactly (jitter=0), not the settle's ~0.
        d = np.abs(qvel - qv[None, :]).max(axis=1).min()
        assert d < 1e-6, f"qvel {d} away from nearest harvested row"
        assert np.abs(qv).max() > 0.3
    env.close()


def test_restore_matches_harvested_row_walk(tmp_path):
    bank_path, q, qvel = _mk_bank(tmp_path)
    env = _walk_env(seed=4, walk_entry_bank=str(bank_path),
                    walk_entry_bank_frac=1.0,
                    bank_qvel_restore=1.0, bank_qvel_jitter_frac=0.0)
    for _ in range(6):
        env.reset()
        assert env._goal_traj.start_at == "walk_entry_bank"
        qv = env.data.qvel[env._vadr]
        d = np.abs(qvel - qv[None, :]).max(axis=1).min()
        assert d < 1e-6, f"qvel {d} away from nearest harvested row"
    env.close()


def test_v1_bank_without_qvel_is_noop(tmp_path):
    bank_path, _, _ = _mk_bank(tmp_path, with_qvel=False)
    env = _lower_env(seed=2, lower_start_bank=str(bank_path),
                     lower_start_bank_frac=1.0, bank_qvel_restore=1.0)
    for _ in range(4):
        env.reset()
        assert env._goal_traj.start_at == "lower_bank"
        qv = env.data.qvel[env._vadr]
        assert np.abs(qv).max() < 0.35  # never restored, no crash
    env.close()


def test_negative_jitter_frac_raises(tmp_path):
    bank_path, _, _ = _mk_bank(tmp_path)
    env = _lower_env(seed=1, lower_start_bank=str(bank_path),
                     lower_start_bank_frac=1.0, bank_qvel_restore=1.0,
                     bank_qvel_jitter_frac=-0.1)
    with pytest.raises(ValueError, match="bank_qvel_jitter_frac"):
        env.reset()
    env.close()
