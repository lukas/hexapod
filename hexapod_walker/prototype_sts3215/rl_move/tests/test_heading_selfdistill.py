"""Tests for heading_selfdistill.py (walkcurr widen8/headexplore's
"push the mean directly" next lever, 09-09).

Layers: (1) pure index/formula math against the known 72-wide plain
walk-task frame (n_act=18, matches rot60.py's own FRAME_WALK/
OBS_VREF constants -- a cross-check that both modules agree on the
same layout independently); (2) attach-time validation (raises loudly
on an unsupported obs config instead of silently indexing the wrong
columns); (3) a real-PPO integration smoke test with a tiny synthetic
env matching the exact obs-width contract, checking the off path
(coef=0) is bit-exact and the armed path actually moves the
mean-network weights (and leaves log_std untouched, since
``Normal.entropy()``/``.mode()`` for a DiagGaussianDistribution never
touches the mean gradient through log_std)."""
from __future__ import annotations

import numpy as np
import pytest

import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim.heading_selfdistill import (
    attach_heading_selfdistill,
    heading_cos,
    heading_frame_width,
    heading_vref_index,
    make_heading_selfdistill_ppo_class,
)


# ---------------------------------------------------------------------
# 1. Pure formula/index math.
# ---------------------------------------------------------------------

def test_index_and_frame_width_match_rot60_walk_frame():
    """n_act=18 (joint-space action, the widen8/crutchoff recipe's own
    task) must reproduce rot60.py's independently-hand-derived
    FRAME_WALK=72 / OBS_VREF_X=68 constants exactly."""
    from rl_move.sim.rot60 import FRAME_WALK, OBS_VREF_X
    assert heading_frame_width(18) == FRAME_WALK == 72
    assert heading_vref_index(18) == OBS_VREF_X == 68


def test_heading_cos_forward_side_backward_and_stop():
    vref = np.array([
        [1.0, 0.0],    # pure forward -> cos +1
        [0.0, 1.0],    # pure left (side) -> cos 0
        [-1.0, 0.0],   # pure backward -> cos -1
        [0.0, 0.0],    # stop command -> treated as forward (cos 1)
    ], dtype=np.float32)
    cos_h = heading_cos(vref)
    np.testing.assert_allclose(cos_h, [1.0, 0.0, -1.0, 1.0], atol=1e-6)


def test_heading_cos_clips_to_valid_range():
    # scaled obs columns can carry tiny fp noise; must stay in [-1, 1]
    vref = np.array([[1e6, 0.0], [-1e6, 1e-9]], dtype=np.float32)
    cos_h = heading_cos(vref)
    assert np.all(cos_h <= 1.0) and np.all(cos_h >= -1.0)


# ---------------------------------------------------------------------
# 2. Attach-time validation.
# ---------------------------------------------------------------------

class _FakeModel:
    def __init__(self, obs_dim, act_dim, action_dist=None):
        self.observation_space = spaces.Box(-1, 1, (obs_dim,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (act_dim,),
                                       dtype=np.float32)

        class _Policy:
            pass
        self.policy = _Policy()
        if action_dist is not None:
            self.policy.action_dist = action_dist


def test_attach_raises_on_obs_width_mismatch():
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )
    m = _FakeModel(obs_dim=999, act_dim=18,
                   action_dist=DiagGaussianDistribution(18))
    with pytest.raises(SystemExit, match="obs-width mismatch"):
        attach_heading_selfdistill(m, coef=1.0, grad_clip=0.0,
                                   cos_max=0.5, cfg={})


def test_attach_raises_on_nonzero_phase_obs():
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )
    m = _FakeModel(obs_dim=heading_frame_width(18), act_dim=18,
                   action_dist=DiagGaussianDistribution(18))
    cfg = {"goal": {"walk_phase_obs": 1.0}}
    with pytest.raises(SystemExit, match="walk_phase_obs"):
        attach_heading_selfdistill(m, coef=1.0, grad_clip=0.0,
                                   cos_max=0.5, cfg=cfg)


def test_attach_raises_on_history_frames_gt_1():
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )
    m = _FakeModel(obs_dim=heading_frame_width(18) * 2, act_dim=18,
                   action_dist=DiagGaussianDistribution(18))
    cfg = {"obs": {"history_frames": 2}}
    with pytest.raises(SystemExit, match="history_frames"):
        attach_heading_selfdistill(m, coef=1.0, grad_clip=0.0,
                                   cos_max=0.5, cfg=cfg)


def test_attach_succeeds_and_sets_attrs_on_valid_config():
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )
    n_act = 18
    m = _FakeModel(obs_dim=heading_frame_width(n_act), act_dim=n_act,
                   action_dist=DiagGaussianDistribution(n_act))
    attach_heading_selfdistill(m, coef=2.0, grad_clip=0.5, cos_max=0.3,
                               cfg={})
    assert m.heading_selfdistill_coef == 2.0
    assert m.heading_selfdistill_grad_clip == 0.5
    assert m.heading_selfdistill_cos_max == 0.3
    assert m._heading_selfdistill_vref_idx == heading_vref_index(n_act)


# ---------------------------------------------------------------------
# 3. Real-PPO integration: tiny synthetic env matching the exact
#    obs-width contract (n_act=4 -> frame width 45+13=58, small and
#    fast; the specific columns' semantics don't matter to the
#    mechanism, only that [idx:idx+2] carries a controllable heading
#    command and SOME samples get positive advantage).
# ---------------------------------------------------------------------

_N_ACT = 4
_OBS_DIM = heading_frame_width(_N_ACT)
_VREF_IDX = heading_vref_index(_N_ACT)


class _TinyHeadingEnv(gym.Env):
    """Deterministic (no np_random draws in the obs) tiny env: obs is
    all-zero except a fixed [vx_ref, vy_ref] pair at the contract's own
    index, cycled per-episode-step through a small set of headings.
    Reward rewards actions near a per-heading "good" action, so
    rollouts carry real advantage variance for the distillation step
    to filter on."""

    metadata = {}

    def __init__(self, heading_idx: int = 0):
        super().__init__()
        self.observation_space = spaces.Box(-10, 10, (_OBS_DIM,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (_N_ACT,), dtype=np.float32)
        self._t = 0
        # headings: forward (cos=1) and straight-back (cos=-1)
        self._headings = [(1.0, 0.0), (-1.0, 0.0)]
        self._h = heading_idx % len(self._headings)

    def _obs(self):
        obs = np.zeros(_OBS_DIM, dtype=np.float32)
        vx, vy = self._headings[self._h]
        obs[_VREF_IDX] = vx
        obs[_VREF_IDX + 1] = vy
        return obs

    def reset(self, *, seed=None, options=None):
        self._t = 0
        self._h = (self._h + 1) % len(self._headings)
        return self._obs(), {}

    def step(self, action):
        self._t += 1
        # reward highest near action == +1 at the "back" heading (h=1)
        # and near action == -1 at the "forward" heading (h=0) -- an
        # arbitrary but LEARNABLE, heading-conditioned target so
        # advantage correlates with (heading, action) jointly.
        target = 1.0 if self._h == 1 else -1.0
        reward = -float(np.mean((np.asarray(action) - target) ** 2))
        term = self._t >= 8
        return self._obs(), reward, term, False, {}


def _make_ppo(cls, seed=0):
    venv = DummyVecEnv([lambda: _TinyHeadingEnv(i) for i in range(4)])
    m = cls("MlpPolicy", venv, n_steps=16, batch_size=32, n_epochs=2,
            seed=seed, device="cpu", policy_kwargs=dict(net_arch=[16]))
    m.set_random_seed(seed)
    return m


def test_heading_selfdistill_off_path_is_bit_exact():
    """coef=0 -> _heading_selfdistill_step is a hard no-op: PPO's own
    train() must produce identical params to the un-wrapped class."""
    plain = _make_ppo(PPO)
    wrapped = _make_ppo(make_heading_selfdistill_ppo_class(PPO))
    assert wrapped.heading_selfdistill_coef == 0.0
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        p_wrap.data.copy_(p_plain.data)

    from stable_baselines3.common.logger import configure
    plain.set_logger(configure(None, ["stdout"]))
    wrapped.set_logger(configure(None, ["stdout"]))
    plain.set_random_seed(0)
    plain.learn(total_timesteps=32)
    wrapped.set_random_seed(0)
    wrapped.learn(total_timesteps=32)
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        np.testing.assert_allclose(
            p_plain.detach().numpy(), p_wrap.detach().numpy(),
            atol=1e-6,
            err_msg="heading_selfdistill_coef=0 changed training output")


def test_heading_selfdistill_armed_moves_mean_not_log_std():
    """Armed (coef>0, attached): the extra step must actually run
    (verified via a monkeypatched counter) and, run in isolation on a
    rollout with real advantage variance, must change actor mean-path
    weights while leaving log_std BIT-IDENTICAL (entropy/mode() of a
    DiagGaussianDistribution never has a mean-gradient path through
    log_std -- the whole reason this module exists instead of an
    entropy-bonus reweight)."""
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )

    cls = make_heading_selfdistill_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_selfdistill(m, coef=5.0, grad_clip=0.0, cos_max=0.5,
                              cfg={})
    assert isinstance(m.policy.action_dist, DiagGaussianDistribution)

    # Collect one real rollout (fills rollout_buffer with observations/
    # actions/advantages) without letting super().train() consume it.
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)

    log_std_before = m.policy.log_std.detach().clone()
    mean_w_before = m.policy.action_net.weight.detach().clone()

    m._heading_selfdistill_step()

    log_std_after = m.policy.log_std.detach().clone()
    mean_w_after = m.policy.action_net.weight.detach().clone()

    np.testing.assert_allclose(
        log_std_before.numpy(), log_std_after.numpy(), atol=1e-8,
        err_msg="the self-distillation step must never move log_std")
    assert not np.allclose(mean_w_before.numpy(), mean_w_after.numpy()), (
        "the self-distillation step should have moved the mean-action "
        "network weights given a rollout with real advantage variance")


class _FakeLogger:
    """Minimal stand-in for SB3's Logger.record, capturing the last
    value written per key (matches how mirror.py/bc_anchor.py's own
    diagnostics are tested)."""

    def __init__(self):
        self.values = {}

    def record(self, key, value):
        self.values[key] = value


def test_heading_selfdistill_logs_diagnostics_on_armed_success():
    """When the step actually fires, it must log loss/off_axis_frac/
    n_keep to self.logger -- the gate text's "(if logged)" diagnostics
    clause this module's own canary triage flagged as missing."""
    cls = make_heading_selfdistill_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_selfdistill(m, coef=5.0, grad_clip=0.0, cos_max=0.5,
                              cfg={})
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    m._heading_selfdistill_step()
    assert "train/heading_selfdistill_loss" in fake_logger.values
    assert "train/heading_selfdistill_off_axis_frac" in fake_logger.values
    assert "train/heading_selfdistill_n_keep" in fake_logger.values
    assert fake_logger.values["train/heading_selfdistill_n_keep"] >= 8
    assert 0.0 <= fake_logger.values[
        "train/heading_selfdistill_off_axis_frac"] <= 1.0


def test_heading_selfdistill_logs_zero_n_keep_when_masked_out():
    """The no-op-via-mask branch (cos_max impossible to hit) must still
    log off_axis_frac/n_keep=0 so a W&B curve shows the mechanism ran
    but found no usable signal, rather than going silent."""
    cls = make_heading_selfdistill_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_selfdistill(m, coef=5.0, grad_clip=0.0, cos_max=-2.0,
                              cfg={})  # impossible bar: cos in [-1,1]
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    m._heading_selfdistill_step()
    assert fake_logger.values["train/heading_selfdistill_n_keep"] == 0
    assert fake_logger.values["train/heading_selfdistill_off_axis_frac"] == 0.0
    assert "train/heading_selfdistill_loss" not in fake_logger.values


def test_heading_selfdistill_noop_when_no_off_axis_signal(monkeypatch):
    """If every sample in the rollout is masked out (cos_max below any
    achievable heading), the step must be a clean no-op: no
    optimizer.step(), no parameter change."""
    cls = make_heading_selfdistill_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_selfdistill(m, coef=5.0, grad_clip=0.0, cos_max=-2.0,
                              cfg={})  # impossible bar: cos in [-1,1]

    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)

    w_before = m.policy.action_net.weight.detach().clone()
    m._heading_selfdistill_step()
    w_after = m.policy.action_net.weight.detach().clone()
    np.testing.assert_allclose(w_before.numpy(), w_after.numpy(),
                               atol=1e-8)
