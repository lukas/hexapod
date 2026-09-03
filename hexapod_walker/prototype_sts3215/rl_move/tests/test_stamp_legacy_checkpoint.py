"""stamp_legacy_checkpoint.py -- the pre-migration checkpoint
backfill tool (2026-09-03, fleet-wide `require_checkpoint_joint_
contract` gap: every checkpoint saved by a process launched before
the 66c4af30/b7e7ea05 joint-frame-v2 merge landed has no stamp at
all, permanently blocking every `--init-from`/respec warm-start
until backfilled -- see OPERATOR_QUESTIONS.md 2026-09-03)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from stable_baselines3 import PPO

from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS, JOINT_CONTRACT, require_checkpoint_joint_contract,
)
from rl_move.sim.stamp_legacy_checkpoint import stamp_one


def _make_unstamped_checkpoint(path: Path) -> None:
    import gymnasium as gym

    env = gym.make("Pendulum-v1")
    model = PPO("MlpPolicy", env, n_steps=4, batch_size=4, verbose=0)
    model.save(path)


def test_stamp_one_adds_contract_and_preserves_weights(tmp_path):
    ckpt = tmp_path / "legacy.zip"
    _make_unstamped_checkpoint(ckpt)

    with zipfile.ZipFile(ckpt) as z:
        before_data = json.loads(z.read("data"))
        before_policy = z.read("policy.pth")
    assert "joint_frame" not in before_data

    with pytest.raises(ValueError):
        require_checkpoint_joint_contract(ckpt)

    result = stamp_one(ckpt)
    assert result == "stamped"

    with zipfile.ZipFile(ckpt) as z:
        after_data = json.loads(z.read("data"))
        after_policy = z.read("policy.pth")
    assert after_data["joint_frame"] == FRAME_ROBOT_ABS
    assert after_data["joint_contract"] == JOINT_CONTRACT
    assert after_policy == before_policy  # bit-exact weights

    assert require_checkpoint_joint_contract(ckpt) == JOINT_CONTRACT

    # Still loads as a real model afterwards.
    reloaded = PPO.load(ckpt, device="cpu")
    assert reloaded.joint_frame == FRAME_ROBOT_ABS


def test_stamp_one_is_idempotent(tmp_path):
    ckpt = tmp_path / "legacy.zip"
    _make_unstamped_checkpoint(ckpt)
    assert stamp_one(ckpt) == "stamped"
    assert stamp_one(ckpt) == "already"


def test_stamp_one_refuses_a_real_foreign_contract(tmp_path):
    ckpt = tmp_path / "foreign.zip"
    _make_unstamped_checkpoint(ckpt)
    with zipfile.ZipFile(ckpt) as z:
        data = json.loads(z.read("data"))
        members = {n: z.read(n) for n in z.namelist()}
    data["joint_frame"] = "mujoco_rel"
    data["joint_contract"] = "some_other_contract"
    members["data"] = json.dumps(data).encode()
    with zipfile.ZipFile(ckpt, "w") as out:
        for name, blob in members.items():
            out.writestr(name, blob)

    with pytest.raises(ValueError, match="refuses to overwrite"):
        stamp_one(ckpt)
