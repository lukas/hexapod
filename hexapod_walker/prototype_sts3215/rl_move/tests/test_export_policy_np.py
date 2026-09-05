"""Portable MLP/dual-GRU exporter regression tests."""
from __future__ import annotations

import json

import gymnasium as gym
import numpy as np
import pytest
from gymnasium import spaces

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.np_policy import (
    ARCH_DUAL_GRU,
    MAX_POLICY_BYTES,
    NumpyDualGruModel,
    load_np_policy,
    validate_np_policy,
)
from rl_move.sim.export_policy_np import export


class _ExportEnv(gym.Env):
    def __init__(self, obs_dim: int):
        self.observation_space = spaces.Box(
            -np.inf, np.inf, (obs_dim,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (18,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(self.observation_space.shape, dtype=np.float32), {}

    def step(self, action):
        return (np.zeros(self.observation_space.shape, dtype=np.float32),
                0.0, False, False, {})


def _stamp(model) -> None:
    model.joint_frame = FRAME_ROBOT_ABS
    model.joint_contract = JOINT_CONTRACT


def test_export_dual_gru_is_compact_valid_and_loadable(tmp_path):
    from sb3_contrib import RecurrentPPO

    from rl_move.sim.gru_policy import DualGruActorCriticPolicy

    model = RecurrentPPO(
        DualGruActorCriticPolicy, _ExportEnv(81), n_steps=8,
        batch_size=8, n_epochs=1, seed=3, device="cpu",
        policy_kwargs={"lstm_hidden_size": 8, "net_arch": [16, 12]})
    _stamp(model)
    checkpoint = tmp_path / "dual.zip"
    artifact = tmp_path / "dual.json"
    model.save(checkpoint)

    payload = export(
        str(checkpoint), str(artifact), training_hz=100.0,
        extra_meta={"phase_hz": 1.333333,
                    "walk_phase_run_on_yaw": True})

    assert payload["meta"]["architecture"] == ARCH_DUAL_GRU
    assert payload["meta"]["mode_onehot_order"] == [
        "hold", "rise", "lower", "walk", "turn", "quad"]
    assert artifact.stat().st_size < MAX_POLICY_BYTES
    errors, info = validate_np_policy(json.loads(artifact.read_text()))
    assert errors == []
    assert info["hidden"] == [8, 16, 12]
    loaded = load_np_policy(artifact)
    assert isinstance(loaded, NumpyDualGruModel)
    obs = np.zeros(81, dtype=np.float32)
    obs[-3] = 1.0
    assert loaded.act(obs).shape == (18,)


def test_export_obs75_mlp_keeps_legacy_matrix_layout(tmp_path):
    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy", _ExportEnv(75), n_steps=8, batch_size=8,
        n_epochs=1, seed=5, device="cpu",
        policy_kwargs={"net_arch": [11, 9]})
    _stamp(model)
    checkpoint = tmp_path / "mlp.zip"
    artifact = tmp_path / "mlp.json"
    model.save(checkpoint)

    payload = export(
        str(checkpoint), str(artifact), training_hz=100.0,
        extra_meta={"phase_hz": 1.333333,
                    "walk_phase_run_on_yaw": True})

    assert payload["meta"]["architecture"] == "mlp"
    assert all(key in payload for key in
               ("W1", "b1", "W2", "b2", "Wout", "bout"))
    assert load_np_policy(artifact).observation_space.shape == (75,)


def test_export_refuses_unstamped_checkpoint(tmp_path):
    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy", _ExportEnv(75), n_steps=8, batch_size=8,
        n_epochs=1, seed=7, device="cpu",
        policy_kwargs={"net_arch": [8, 8]})
    checkpoint = tmp_path / "unstamped.zip"
    model.save(checkpoint)
    with pytest.raises(ValueError, match="cannot be relabeled"):
        export(str(checkpoint), str(tmp_path / "no.json"),
               training_hz=100.0,
               extra_meta={"phase_hz": 1.333333,
                           "walk_phase_run_on_yaw": True})
