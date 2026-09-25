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
    ARCH_SINGLE_GRU,
    MAX_POLICY_BYTES,
    NumpyDualGruModel,
    NumpyGruModel,
    NumpyMLPNLayerModel,
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


def test_export_single_gru_is_compact_valid_and_loadable(tmp_path):
    """Plain --gru (non-mode-gated, e.g. the standwalk DR-ladder lineage):
    single core + N-layer tanh head, no mode one-hot required."""
    from sb3_contrib import RecurrentPPO

    from rl_move.sim.gru_policy import GruActorCriticPolicy

    model = RecurrentPPO(
        GruActorCriticPolicy, _ExportEnv(74), n_steps=8,
        batch_size=8, n_epochs=1, seed=4, device="cpu",
        policy_kwargs={"lstm_hidden_size": 8, "net_arch": [16, 12, 9]})
    _stamp(model)
    checkpoint = tmp_path / "single.zip"
    artifact = tmp_path / "single.json"
    model.save(checkpoint)

    payload = export(
        str(checkpoint), str(artifact), training_hz=50.0,
        extra_meta={"phase_hz": 1.333333})

    assert payload["meta"]["architecture"] == ARCH_SINGLE_GRU
    assert payload["meta"]["hidden"] == [8, 16, 12, 9]
    assert "mode_onehot_order" not in payload["meta"]
    assert artifact.stat().st_size < MAX_POLICY_BYTES
    errors, info = validate_np_policy(json.loads(artifact.read_text()))
    assert errors == []
    assert info["hidden"] == [8, 16, 12, 9]
    loaded = load_np_policy(artifact)
    assert isinstance(loaded, NumpyGruModel)
    assert loaded.recurrent is True
    obs = np.zeros(74, dtype=np.float32)
    assert loaded.act(obs).shape == (18,)
    loaded.reset()  # the smoke act() above left residual hidden state

    # Sequence parity, including a mid-episode reset -- the state
    # convention (plain (1, 1, hidden) h, unlike the dual model's
    # stacked-2-core packing) must round-trip through both the numpy
    # runner and the real RecurrentPPO checkpoint identically.
    rng = np.random.default_rng(2)
    state_sb3 = None
    state_np = None
    worst = 0.0
    for tick in range(40):
        probe = rng.normal(0, 1, 74).astype(np.float32)
        episode_start = np.asarray([tick == 17], dtype=bool)
        a_sb3, state_sb3 = model.predict(
            probe, state=state_sb3, episode_start=episode_start,
            deterministic=True)
        a_np, state_np = loaded.predict(
            probe, state=state_np, episode_start=episode_start,
            deterministic=True)
        worst = max(worst, float(np.max(np.abs(a_np - a_sb3))))
    assert worst < 1e-5


def test_export_dual_gru_subclasses_stay_unsupported(tmp_path):
    """Triple/mode-experts GRU also set lstm_actor but to a multi-core
    module this exporter cannot pack yet -- must fail loudly, not
    silently mis-treat them as the plain single-core case."""
    from sb3_contrib import RecurrentPPO

    from rl_move.sim.gru_policy import TripleGruActorCriticPolicy

    model = RecurrentPPO(
        TripleGruActorCriticPolicy, _ExportEnv(81), n_steps=8,
        batch_size=8, n_epochs=1, seed=6, device="cpu",
        policy_kwargs={"lstm_hidden_size": 8, "net_arch": [16, 12]})
    _stamp(model)
    checkpoint = tmp_path / "triple.zip"
    model.save(checkpoint)
    with pytest.raises(ValueError, match="only mode-gated"):
        export(str(checkpoint), str(tmp_path / "no.json"),
               training_hz=100.0,
               extra_meta={"phase_hz": 1.333333,
                           "walk_phase_run_on_yaw": True})


def test_export_transformer_is_compact_valid_and_loadable(tmp_path):
    """Causal-transformer trunk (standwalk PHASE-1/PHASE-2, obs.history_
    frames=N): stateless given the frame-stacked obs, so parity is a
    random-obs sweep (no episode-reset/hidden-state protocol like GRU)."""
    from stable_baselines3 import PPO

    from rl_move.np_policy import ARCH_TRANSFORMER, NumpyTransformerModel
    from rl_move.sim.transformer_policy import TransformerActorCriticPolicy

    n_frames, frame_w = 3, 74
    model = PPO(
        TransformerActorCriticPolicy, _ExportEnv(n_frames * frame_w),
        n_steps=8, batch_size=8, n_epochs=1, seed=7, device="cpu",
        policy_kwargs={"n_frames": n_frames, "d_model": 8, "n_layers": 2,
                       "n_heads": 2, "ff_dim": 16, "net_arch": [12, 9]})
    _stamp(model)
    checkpoint = tmp_path / "tf.zip"
    artifact = tmp_path / "tf.json"
    model.save(checkpoint)

    payload = export(
        str(checkpoint), str(artifact), training_hz=50.0,
        extra_meta={"phase_hz": 1.333333, "walk_phase_run_on_yaw": True})

    assert payload["meta"]["architecture"] == ARCH_TRANSFORMER
    assert payload["meta"]["tf_n_frames"] == n_frames
    assert payload["meta"]["tf_d_model"] == 8
    assert payload["meta"]["tf_n_layers"] == 2
    assert payload["meta"]["tf_n_heads"] == 2
    assert payload["meta"]["hidden"] == [8, 12, 9]
    assert artifact.stat().st_size < MAX_POLICY_BYTES
    errors, info = validate_np_policy(json.loads(artifact.read_text()))
    assert errors == []
    assert info["hidden"] == [8, 12, 9]
    loaded = load_np_policy(artifact)
    assert isinstance(loaded, NumpyTransformerModel)
    assert loaded.recurrent is False

    rng = np.random.default_rng(9)
    worst = 0.0
    for _ in range(30):
        obs = rng.normal(0, 1, n_frames * frame_w).astype(np.float32)
        a_sb3, _ = model.predict(obs, deterministic=True)
        a_np, state = loaded.predict(obs, deterministic=True)
        assert state is None
        worst = max(worst, float(np.max(np.abs(a_np - a_sb3))))
    assert worst < 1e-5


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


def test_export_deep_elu_mlp_uses_generic_layers_format(tmp_path):
    """net-arch 256,256,128 + ELU (the walkcurr widen8 shape) exports."""
    import torch.nn as nn
    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy", _ExportEnv(72), n_steps=8, batch_size=8,
        n_epochs=1, seed=11, device="cpu",
        policy_kwargs={"net_arch": [10, 9, 7], "activation_fn": nn.ELU})
    _stamp(model)
    checkpoint = tmp_path / "deep.zip"
    artifact = tmp_path / "deep.json"
    model.save(checkpoint)

    payload = export(
        str(checkpoint), str(artifact), training_hz=100.0,
        extra_meta={"phase_hz": 1.333333,
                    "walk_phase_run_on_yaw": True})

    # Legacy fixed-schema keys are absent; this is the new format only.
    assert "layers" in payload and "W1" not in payload
    assert payload["meta"]["architecture"] == "mlp"
    assert payload["meta"]["activation"] == "elu"
    assert payload["meta"]["hidden"] == [10, 9, 7]

    errors, info = validate_np_policy(json.loads(artifact.read_text()))
    assert errors == []
    assert info["hidden"] == [10, 9, 7]

    loaded = load_np_policy(artifact)
    assert isinstance(loaded, NumpyMLPNLayerModel)
    assert loaded.recurrent is False
    obs = np.zeros(72, dtype=np.float32)
    action, _ = loaded.predict(obs)
    assert action.shape == (18,)
    assert np.all(np.isfinite(action))

    # Same parity bar as the legacy path: exact production loader class.
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(50):
        probe = rng.normal(0, 1, 72).astype(np.float32)
        a_np = loaded.act(probe)
        a_sb3, _ = model.predict(probe, deterministic=True)
        worst = max(worst, float(np.max(np.abs(a_np - a_sb3))))
    assert worst < 1e-5


def test_generic_hidden_layers_refuses_mixed_activation():
    """A hand-built Tanh-then-ELU stack must fail loudly, not silently.

    (Unit-level: SB3 checkpoints always rebuild one activation_fn from
    policy_kwargs on load, so this shape cannot round-trip through a
    real .zip -- exercise the splitter directly instead.)
    """
    import torch.nn as nn

    from rl_move.sim.export_policy_np import _generic_hidden_layers

    net = nn.Sequential(
        nn.Linear(4, 3), nn.Tanh(), nn.Linear(3, 3), nn.ELU())
    with pytest.raises(ValueError, match="mixed activations"):
        _generic_hidden_layers(net, name="MLP actor")


def test_generic_hidden_layers_refuses_unsupported_activation():
    import torch.nn as nn

    from rl_move.sim.export_policy_np import _generic_hidden_layers

    net = nn.Sequential(nn.Linear(4, 3), nn.ReLU())
    with pytest.raises(ValueError, match="unsupported activation"):
        _generic_hidden_layers(net, name="MLP actor")


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


def test_export_records_source_run_from_the_ledger(tmp_path, monkeypatch):
    """meta.source_run = the ledger run whose checkpoint this is (by the
    launcher's ppo_goal_<run> naming contract); absent when no ledger."""
    from stable_baselines3 import PPO

    from rl_move import ledger

    model = PPO(
        "MlpPolicy", _ExportEnv(75), n_steps=8, batch_size=8,
        n_epochs=1, seed=5, device="cpu",
        policy_kwargs={"net_arch": [11, 9]})
    _stamp(model)
    checkpoint = tmp_path / "ppo_goal_cw_walk50hz_demo_acq1.zip"
    model.save(checkpoint)
    monkeypatch.setattr(ledger, "load_ledger", lambda: [
        {"run": "cw-walk50hz-demo-acq1", "status": "PASS",
         "created": "2026-09-20T10:00:00+00:00"},
        {"run": "cw-other", "status": "FAIL",
         "created": "2026-09-20T11:00:00+00:00"}])

    phase = {"phase_hz": 0.6667, "walk_phase_run_on_yaw": True}
    payload = export(str(checkpoint), str(tmp_path / "a.json"), training_hz=50.0,
                     extra_meta=phase)
    assert payload["meta"]["source_run"] == "cw-walk50hz-demo-acq1"
    assert payload["meta"]["source"] == str(checkpoint)

    def _missing():
        raise FileNotFoundError("no state dir")
    monkeypatch.setattr(ledger, "load_ledger", _missing)
    payload = export(str(checkpoint), str(tmp_path / "b.json"), training_hz=50.0,
                     extra_meta=phase)
    assert "source_run" not in payload["meta"]
