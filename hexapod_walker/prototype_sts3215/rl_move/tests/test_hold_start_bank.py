"""goal.hold_start_bank / goal.hold_start_bank_frac (2026-09-25,
standwalk STATUS ~01:2x/~01:3x): composed-session hold-entry (real
post-rise) pose exposure -- the hold-mode generalization of
goal.rise_start_bank/goal.lower_start_bank/goal.walk_entry_bank, since
every hold episode today starts from the idealized static plant
(start_at="plant") or a small synthetic crouch jitter
(hold_start_jitter_frac) around that SAME plant target, never a real
rise-exit pose/momentum. Contract under test mirrors
test_lower_start_bank.py:
  - default OFF and bit-exact: frac>0 with no bank path changes
    nothing;
  - bank + frac=1: every hold episode starts from a bank pose
    (start_at="hold_bank", start_kind "post_rise_hold"), overriding
    the jitter branch when both are configured;
  - frac=0.5 mixes bank and synthetic (plant/jitter) starts;
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
    p = tmp_path / "hold_entry_bank.npz"
    np.savez(p, q_rad=q, meta="{}", joint_frame="robot_abs",
             joint_contract="robot_abs_tibia_v2")
    return p, q


def _hold_env(seed: int, **goal_over) -> SimHexapodGoalEnv:
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["hold_start_jitter_frac"] = 0.0
    goal["hold_height_cmd_frac"] = 0.0
    for k, v in goal_over.items():
        goal[k] = v
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "hold" else 0.0)
    return env


def test_frac_without_bank_is_bit_exact():
    env_a = _hold_env(seed=7)
    env_b = _hold_env(seed=7, hold_start_bank_frac=0.7)
    for _ in range(6):
        env_a.reset()
        env_b.reset()
        assert env_b._goal_traj.start_at != "hold_bank"
        assert env_a._goal_traj.start_at == env_b._goal_traj.start_at
        np.testing.assert_array_equal(
            env_a.data.qpos[env_a._qadr], env_b.data.qpos[env_b._qadr])
    env_a.close()
    env_b.close()


def test_bank_frac_one_starts_from_bank(tmp_path):
    bank_path, bank = _mk_bank(tmp_path)
    env = _hold_env(seed=3, hold_start_bank=str(bank_path),
                    hold_start_bank_frac=1.0)
    for _ in range(5):
        obs, info = env.reset()
        assert info["goal_mode"] == "hold"
        assert env._goal_traj.start_at == "hold_bank"
        assert start_kind_of(env._goal_traj) == "post_rise_hold"
        assert np.all(np.isfinite(obs))
        q = env.data.qpos[env._qadr]
        d = np.abs(bank - q[None, :]).max(axis=1).min()
        assert d < 0.25, f"reset pose {d:.3f} rad from nearest bank row"
    env.close()


def test_bank_frac_mixes_kinds(tmp_path):
    bank_path, _ = _mk_bank(tmp_path)
    env = _hold_env(seed=11, hold_start_bank=str(bank_path),
                    hold_start_bank_frac=0.5)
    kinds = set()
    for _ in range(16):
        env.reset()
        kinds.add(env._goal_traj.start_at)
    assert "hold_bank" in kinds, "bank starts never sampled at frac=0.5"
    assert kinds - {"hold_bank"}, "frac=0.5 must keep synthetic starts"
    env.close()


def test_bank_overrides_jitter_when_both_configured(tmp_path):
    bank_path, _ = _mk_bank(tmp_path)
    env = _hold_env(seed=13, hold_start_bank=str(bank_path),
                    hold_start_bank_frac=1.0,
                    hold_start_jitter_frac=1.0)
    for _ in range(5):
        env.reset()
        # Bank draw is unconditional at frac=1.0 and runs AFTER the
        # jitter branch, so it always wins when both fire together.
        assert env._goal_traj.start_at == "hold_bank"
        assert env._goal_traj.crouch_dz == 0.0
    env.close()


def test_malformed_bank_raises(tmp_path):
    bad = tmp_path / "bad.npz"
    np.savez(bad, q_rad=np.zeros((3, 7)))
    env = _hold_env(seed=1, hold_start_bank=str(bad),
                    hold_start_bank_frac=1.0)
    with pytest.raises(ValueError, match="hold_start_bank"):
        for _ in range(3):
            env.reset()
    env.close()
