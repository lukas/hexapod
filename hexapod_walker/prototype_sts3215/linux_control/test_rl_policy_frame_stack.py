"""NumpyPolicy frame stack for causal-transformer artifacts (2026-09-26).

A transformer walk policy is trained on the env's ``obs.history_frames``
stack (K single-tick frames, NEWEST-FIRST, zero frames at an episode
start). The drive loop builds one tick per step, so NumpyPolicy owns the
ring buffer. These tests pin the contract with a fake model: no torch, no
weights, well under the half-second rule.
"""
from __future__ import annotations

import numpy as np
import pytest

import rl_policy
from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT


class _FakeStacked:
    """Stands in for rl_move.np_policy.NumpyTransformerModel."""

    def __init__(self, frames: int, width: int):
        self.n_frames = frames
        self.frame_width = width
        self.meta = {"obs_dim": frames * width, "act_dim": 18,
                     "architecture": "transformer", "tf_n_frames": frames,
                     "joint_frame": FRAME_ROBOT_ABS,
                     "joint_contract": JOINT_CONTRACT}
        self.recurrent = False
        self.seen: list[np.ndarray] = []
        self.resets = 0

    def act(self, obs):
        obs = np.asarray(obs)
        assert obs.shape == (self.n_frames * self.frame_width,)
        self.seen.append(obs.copy())
        return np.zeros(18, dtype=np.float32)

    def reset(self):
        self.resets += 1


class _FakeFlat:
    """An MLP-style artifact: no frames attribute at all."""

    meta = {"obs_dim": 74, "act_dim": 18, "joint_frame": FRAME_ROBOT_ABS,
            "joint_contract": JOINT_CONTRACT}
    recurrent = False

    def act(self, obs):
        return np.asarray(obs, dtype=np.float32)[:18]

    def reset(self):
        pass


@pytest.fixture
def stacked(monkeypatch):
    fake = _FakeStacked(frames=4, width=3)
    monkeypatch.setattr(rl_policy, "load_np_policy", lambda path: fake)
    return fake, rl_policy.NumpyPolicy("fake-transformer.json")


def test_presents_single_tick_width_and_stacked_width(stacked):
    fake, pol = stacked
    assert pol.meta["obs_dim"] == 3           # what the loop validates
    assert pol.meta["stacked_obs_dim"] == 12  # what the model consumes
    assert pol.frames == 4
    assert pol.recurrent is True              # loop must reset it per episode
    assert fake.meta["obs_dim"] == 12         # model meta untouched


def test_newest_first_with_first_frame_fill_matches_sim_contract(stacked):
    fake, pol = stacked
    t1 = np.array([1, 1, 1], dtype=np.float32)
    t2 = np.array([2, 2, 2], dtype=np.float32)
    t3 = np.array([3, 3, 3], dtype=np.float32)
    pol.act(t1)
    pol.act(t2)
    pol.act(t3)
    # frame 0 = current tick, older ticks behind it; at an episode start every
    # slot holds the first observation (sim_env._final_obs reset semantics)
    np.testing.assert_array_equal(
        fake.seen[0], np.concatenate([t1, t1, t1, t1]))
    np.testing.assert_array_equal(
        fake.seen[2], np.concatenate([t3, t2, t1, t1]))


def test_oldest_frame_drops_off_after_k_ticks(stacked):
    fake, pol = stacked
    for k in range(1, 7):
        pol.act(np.full(3, float(k), dtype=np.float32))
    np.testing.assert_array_equal(
        fake.seen[-1], np.repeat([6.0, 5.0, 4.0, 3.0], 3))


def test_reset_zeroes_the_stack_and_forwards(stacked):
    fake, pol = stacked
    pol.act(np.ones(3, dtype=np.float32))
    pol.reset()
    assert fake.resets == 1
    pol.act(np.full(3, 9.0, dtype=np.float32))
    np.testing.assert_array_equal(
        fake.seen[-1], np.repeat([9.0], 12))


def test_wrong_tick_width_is_rejected(stacked):
    _, pol = stacked
    with pytest.raises(ValueError, match="frame width"):
        pol.act(np.zeros(12, dtype=np.float32))  # a pre-stacked vector


def test_inconsistent_frame_geometry_is_rejected(monkeypatch):
    fake = _FakeStacked(frames=4, width=3)
    fake.meta["obs_dim"] = 13  # not frames x width
    monkeypatch.setattr(rl_policy, "load_np_policy", lambda path: fake)
    with pytest.raises(ValueError, match="ring buffer"):
        rl_policy.NumpyPolicy("bad.json")


def test_flat_artifacts_pass_through_unchanged(monkeypatch):
    monkeypatch.setattr(rl_policy, "load_np_policy", lambda path: _FakeFlat())
    pol = rl_policy.NumpyPolicy("mlp.json")
    assert pol.frames == 1
    assert pol.meta["obs_dim"] == 74
    assert "stacked_obs_dim" not in pol.meta
    assert pol.recurrent is False
    obs = np.arange(74, dtype=np.float32)
    np.testing.assert_array_equal(pol.act(obs), obs[:18])
