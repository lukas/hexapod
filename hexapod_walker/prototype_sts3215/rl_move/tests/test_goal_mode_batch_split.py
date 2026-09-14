"""Tests for goal_mode_batch_split.py (walkcurr hold-collapse
escalation, 09-14 -- see the module docstring for the tb-modeadvnorm-6m
FAIL-MECHANISM this answers: per-group SCALE parity was fixed but hold
still collapsed because hold's raw TICK COUNT is too small a share of
any shared random minibatch to move the gradient).

Layers: (1) the off/disarmed paths are bit-exact vs plain PPO; (2) a
real-PPO integration test on a tiny multi-mode env proving every
minibatch this mechanism builds contains ONLY ONE mode's samples
(the core "never mixed" contract); (3) small-group/missing-capture
fallback behavior; (4) W&B payload forwarding.
"""
from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.logger import configure

from rl_move.sim.goal_mode_batch_split import (
    attach_goal_mode_batch_split,
    make_goal_mode_batch_split_ppo_class,
    GoalModeCaptureCallback,
    goal_mode_batch_split_wandb_payload,
    GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX,
    _labels_to_flat,
)
from rl_move.sim.goal_mode_adv_norm import _goal_mode_label


_OBS_DIM = 6
_N_ACT = 3
_MODES = ("hold", "lower")


class _TinyModeEnv(gym.Env):
    """Deterministic tiny env: each instance is permanently one mode
    (set by env index), emits `info["goal_mode"]` every step, and
    rewards actions near a per-mode target at a deliberately different
    scale (mirrors test_goal_mode_adv_norm.py's fixture)."""

    metadata = {}

    def __init__(self, env_idx: int):
        super().__init__()
        self.observation_space = spaces.Box(-10, 10, (_OBS_DIM,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (_N_ACT,), dtype=np.float32)
        self._mode = _MODES[env_idx % len(_MODES)]
        self._t = 0

    def reset(self, *, seed=None, options=None):
        self._t = 0
        return np.zeros(_OBS_DIM, dtype=np.float32), {}

    def step(self, action):
        self._t += 1
        target = 1.0 if self._mode == "lower" else -1.0
        scale = 100.0 if self._mode == "lower" else 1.0
        reward = -scale * float(np.mean(
            (np.asarray(action) - target) ** 2))
        term = self._t >= 8
        return (np.zeros(_OBS_DIM, dtype=np.float32), reward, term,
                False, {"goal_mode": self._mode})


def _make_ppo(cls, seed=0, n_envs=8):
    venv = DummyVecEnv([lambda i=i: _TinyModeEnv(i) for i in range(n_envs)])
    m = cls("MlpPolicy", venv, n_steps=16, batch_size=32, n_epochs=2,
            seed=seed, device="cpu", policy_kwargs=dict(net_arch=[16]))
    m.set_random_seed(seed)
    return m


def _collect(m):
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    from stable_baselines3.common.callbacks import CallbackList
    cb = CallbackList([callback, GoalModeCaptureCallback()])
    cb.init_callback(m)
    m.collect_rollouts(m.env, callback=cb, rollout_buffer=m.rollout_buffer,
                      n_rollout_steps=16)


# ---------------------------------------------------------------------
# 1. Off-path bit-exactness.
# ---------------------------------------------------------------------

def test_off_path_is_bit_exact():
    plain = _make_ppo(PPO)
    wrapped = _make_ppo(make_goal_mode_batch_split_ppo_class(PPO))
    assert wrapped.goal_mode_batch_split_enabled is False
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        p_wrap.data.copy_(p_plain.data)
    plain.set_logger(configure(None, ["stdout"]))
    wrapped.set_logger(configure(None, ["stdout"]))
    plain.set_random_seed(0)
    plain.learn(total_timesteps=32)
    wrapped.set_random_seed(0)
    wrapped.learn(total_timesteps=32)
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        np.testing.assert_allclose(
            p_plain.detach().numpy(), p_wrap.detach().numpy(), atol=1e-6,
            err_msg="goal_mode_batch_split disabled changed training "
                   "output")


def test_attached_but_disabled_never_replaces_train():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_batch_split(m, enabled=False, min_group=8)
    assert not hasattr(m, "goal_mode_batch_split_enabled") or \
        m.goal_mode_batch_split_enabled is False


# ---------------------------------------------------------------------
# 2. Pure label-flatten helper.
# ---------------------------------------------------------------------

def test_labels_to_flat_shape_mismatch_returns_none():
    assert _labels_to_flat([["a", "b"]], n_steps=2, n_envs=2) is None
    assert _labels_to_flat(None, n_steps=2, n_envs=2) is None
    assert _labels_to_flat([], n_steps=0, n_envs=2) is None


def test_labels_to_flat_matches_swap_and_flatten_order():
    # 2 steps, 3 envs; verify env-major flatten (index = env*n_steps+step).
    labels = [["e0s0", "e1s0", "e2s0"], ["e0s1", "e1s1", "e2s1"]]
    flat = _labels_to_flat(labels, n_steps=2, n_envs=3)
    assert flat.tolist() == ["e0s0", "e0s1", "e1s0", "e1s1", "e2s0", "e2s1"]


# ---------------------------------------------------------------------
# 3. Real-PPO integration: minibatches are never mode-mixed.
# ---------------------------------------------------------------------

def test_armed_minibatches_never_mix_modes():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4)
    m.set_logger(configure(None, ["stdout"]))
    _collect(m)

    labels_flat = _labels_to_flat(
        m._goal_mode_step_labels, m.rollout_buffer.buffer_size,
        m.rollout_buffer.n_envs)
    seen_minibatch_label_sets = []

    orig_get_samples = m.rollout_buffer._get_samples

    def _spy_get_samples(batch_inds, env=None):
        these_labels = set(labels_flat[batch_inds].tolist())
        seen_minibatch_label_sets.append(these_labels)
        return orig_get_samples(batch_inds, env=env)

    m.rollout_buffer._get_samples = _spy_get_samples
    m.train()

    assert seen_minibatch_label_sets, "no minibatches were processed"
    for label_set in seen_minibatch_label_sets:
        assert len(label_set) == 1, (
            f"a minibatch mixed modes: {label_set}")


def test_armed_logs_applied_and_per_group_counts():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied") == 1
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 2
    for mode in _MODES:
        assert fake_logger.name_to_value.get(
            f"{GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX}{mode}_n", 0) > 0


def test_capture_missing_falls_back_to_plain_train():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    # Collect WITHOUT the capture callback -> _goal_mode_step_labels
    # stays whatever attach_ initialized it to (empty list).
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                       rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    m.train()  # must not raise
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied") == 0


def test_small_groups_below_min_group_fall_back_to_plain_train():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    # min_group higher than any single mode's tick count this rollout
    # (16 steps * 4 envs per mode = 64 ticks/mode -> set min_group way
    # above that).
    attach_goal_mode_batch_split(m, enabled=True, min_group=10_000)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()  # must not raise, must fall back
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied") == 0
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 0


# ---------------------------------------------------------------------
# 3b. Asymmetric isolate-modes variant (09-14 escalation: only isolate
# the named mode(s), pool everything else into one `_merged` group).
# ---------------------------------------------------------------------

def test_isolate_modes_default_none_isolates_everything():
    """Unset isolate_modes must reproduce the original all-modes-split
    behavior bit-for-bit (n_groups == number of distinct modes, no
    `_merged` group)."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 isolate_modes=None)
    assert m.goal_mode_batch_split_isolate_modes is None

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == len(_MODES)
    for mode in _MODES:
        assert fake_logger.name_to_value.get(
            f"{GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX}{mode}_n", 0) > 0
    assert (GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "_merged_n"
           ) not in fake_logger.name_to_value


def test_isolate_one_mode_pools_the_rest_into_merged_group():
    """isolate_modes=['hold'] must isolate ONLY hold; 'lower' samples
    must land in a single shared `_merged` group, and every minibatch
    trained must still be single-mode-only WITHIN the isolated group
    (the merged group is allowed to mix its own pooled modes -- that's
    the point -- but 'hold' must never appear inside a merged batch)."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 isolate_modes=["hold"])
    assert m.goal_mode_batch_split_isolate_modes == frozenset({"hold"})
    m.set_logger(configure(None, ["stdout"]))
    _collect(m)

    labels_flat = _labels_to_flat(
        m._goal_mode_step_labels, m.rollout_buffer.buffer_size,
        m.rollout_buffer.n_envs)
    seen_minibatch_label_sets = []
    orig_get_samples = m.rollout_buffer._get_samples

    def _spy_get_samples(batch_inds, env=None):
        seen_minibatch_label_sets.append(
            set(labels_flat[batch_inds].tolist()))
        return orig_get_samples(batch_inds, env=env)

    m.rollout_buffer._get_samples = _spy_get_samples
    m.train()

    assert seen_minibatch_label_sets
    for label_set in seen_minibatch_label_sets:
        if "hold" in label_set:
            assert label_set == {"hold"}, (
                f"hold leaked into a mixed minibatch: {label_set}")


def test_isolate_one_mode_logs_merged_group_and_two_groups_total():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 isolate_modes=["hold"])

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied") == 1
    # hold isolated (1 group) + everything else pooled (1 "_merged"
    # group) == 2 groups total, regardless of how many other distinct
    # modes exist.
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 2
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "hold_n", 0) > 0
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "_merged_n", 0) > 0


def test_isolate_unknown_mode_pools_everything_into_merged():
    """Naming a mode that never appears this rollout must not crash --
    it just never forms its own group, and everything falls into
    `_merged` (same effect as isolate_modes=() in practice for that
    rollout)."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 isolate_modes=["nonexistent_mode"])

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()  # must not raise
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 1
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "_merged_n", 0) > 0


# ---------------------------------------------------------------------
# 4. W&B payload forwarding.
# ---------------------------------------------------------------------

def test_wandb_payload_none_logger_is_empty():
    assert goal_mode_batch_split_wandb_payload(None) == {}


def test_wandb_payload_only_forwards_prefixed_keys():
    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, k, v, **kw):
            self.name_to_value[k] = v

    fake_logger = _FakeLogger()
    fake_logger.record(GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied", 1)
    fake_logger.record(GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "hold_n", 12)
    fake_logger.record("train/entropy_loss", -1.0)  # unrelated
    payload = goal_mode_batch_split_wandb_payload(fake_logger)
    assert payload == {
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied": 1.0,
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "hold_n": 12.0,
    }


# ---------------------------------------------------------------------
# 5. rise-start_kind sub-split (2026-09-14 flat-start-rise escalation:
# 21/21 cap/reward-price/reset-timing/leg-order levers null -- see
# module docstring). `_goal_mode_label` is the pure helper that turns
# a `rise` step into `"rise:<start_kind>"`; a tiny fake `model` object
# (no PPO needed) is enough to test it directly.
# ---------------------------------------------------------------------

class _FakeModel:
    def __init__(self, rise_start_kind):
        self.goal_mode_batch_split_rise_start_kind = rise_start_kind


def test_goal_mode_label_default_off_is_plain_mode():
    m = _FakeModel(False)
    assert _goal_mode_label(m, {"goal_mode": "rise",
                                "start_kind": "flat"}) == "rise"
    assert _goal_mode_label(m, {"goal_mode": "hold"}) == "hold"


def test_goal_mode_label_no_attr_at_all_is_plain_mode():
    # A model that never called attach_goal_mode_batch_split at all
    # (e.g. only goal_mode_adv_norm is armed) must never see the
    # composite label -- getattr(..., False) default.
    class _Bare:
        pass
    assert _goal_mode_label(_Bare(), {"goal_mode": "rise",
                                      "start_kind": "flat"}) == "rise"


def test_goal_mode_label_on_composes_rise_with_start_kind():
    m = _FakeModel(True)
    assert _goal_mode_label(
        m, {"goal_mode": "rise", "start_kind": "flat"}) == "rise:flat"
    assert _goal_mode_label(
        m, {"goal_mode": "rise", "start_kind": "bridge"}) == "rise:bridge"


def test_goal_mode_label_on_non_rise_modes_untouched():
    m = _FakeModel(True)
    assert _goal_mode_label(m, {"goal_mode": "hold",
                                "start_kind": "flat"}) == "hold"
    assert _goal_mode_label(m, {"goal_mode": "lower"}) == "lower"


def test_goal_mode_label_on_missing_start_kind_falls_back_to_plain_rise():
    m = _FakeModel(True)
    assert _goal_mode_label(m, {"goal_mode": "rise"}) == "rise"
    assert _goal_mode_label(
        m, {"goal_mode": "rise", "start_kind": None}) == "rise"
    assert _goal_mode_label(
        m, {"goal_mode": "rise", "start_kind": ""}) == "rise"


def test_attach_rise_start_kind_defaults_false():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4)
    assert m.goal_mode_batch_split_rise_start_kind is False


def test_attach_rise_start_kind_true_is_stored():
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 rise_start_kind=True)
    assert m.goal_mode_batch_split_rise_start_kind is True


_RISE_KINDS = ("flat", "bridge")


class _TinyRiseKindEnv(gym.Env):
    """Like `_TinyModeEnv`, but every instance is `goal_mode="rise"`
    with a fixed `start_kind` (alternating flat/bridge by env index),
    plus one plain `hold` instance -- enough to prove the composite
    `rise:<start_kind>` grouping actually forms disjoint minibatches
    when the sub-flag is on, and stays one merged `rise` group when
    it's off (bit-exact vs the pre-09-14 behavior)."""

    metadata = {}

    def __init__(self, env_idx: int):
        super().__init__()
        self.observation_space = spaces.Box(-10, 10, (_OBS_DIM,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (_N_ACT,), dtype=np.float32)
        if env_idx % 4 == 3:
            self._mode, self._kind = "hold", None
        else:
            self._mode = "rise"
            self._kind = _RISE_KINDS[env_idx % len(_RISE_KINDS)]
        self._t = 0

    def reset(self, *, seed=None, options=None):
        self._t = 0
        return np.zeros(_OBS_DIM, dtype=np.float32), {}

    def step(self, action):
        self._t += 1
        reward = -float(np.mean(np.asarray(action) ** 2))
        term = self._t >= 8
        info = {"goal_mode": self._mode}
        if self._kind is not None:
            info["start_kind"] = self._kind
        return (np.zeros(_OBS_DIM, dtype=np.float32), reward, term,
                False, info)


def _make_rise_kind_ppo(cls, n_envs=8, seed=0):
    venv = DummyVecEnv(
        [lambda i=i: _TinyRiseKindEnv(i) for i in range(n_envs)])
    m = cls("MlpPolicy", venv, n_steps=16, batch_size=32, n_epochs=2,
            seed=seed, device="cpu", policy_kwargs=dict(net_arch=[16]))
    m.set_random_seed(seed)
    return m


def test_rise_start_kind_off_keeps_rise_as_one_merged_group():
    """Default (rise_start_kind=False): flat/bridge rise ticks share
    ONE `rise` group -- matches every pre-09-14 run's behavior."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_rise_kind_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()
    # 2 groups total: plain "rise" (flat+bridge pooled) + "hold".
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 2
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "rise_n", 0) > 0
    assert (GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "rise_flat_n"
           ) not in fake_logger.name_to_value


def test_rise_start_kind_on_splits_flat_from_bridge():
    """Armed: `rise:flat` and `rise:bridge` each get their own
    disjoint minibatch group, on top of `hold` -- 3 groups total, and
    no minibatch this mechanism builds ever mixes flat with bridge (or
    either with hold)."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_rise_kind_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 rise_start_kind=True)
    assert m.goal_mode_batch_split_rise_start_kind is True
    m.set_logger(configure(None, ["stdout"]))
    _collect(m)

    labels_flat = _labels_to_flat(
        m._goal_mode_step_labels, m.rollout_buffer.buffer_size,
        m.rollout_buffer.n_envs)
    assert set(labels_flat.tolist()) == {"rise:flat", "rise:bridge",
                                         "hold"}
    seen_minibatch_label_sets = []
    orig_get_samples = m.rollout_buffer._get_samples

    def _spy_get_samples(batch_inds, env=None):
        seen_minibatch_label_sets.append(
            set(labels_flat[batch_inds].tolist()))
        return orig_get_samples(batch_inds, env=env)

    m.rollout_buffer._get_samples = _spy_get_samples
    m.train()

    assert seen_minibatch_label_sets
    for label_set in seen_minibatch_label_sets:
        assert len(label_set) == 1, (
            f"a minibatch mixed rise start_kinds: {label_set}")


def test_rise_start_kind_on_logs_sanitized_colon_free_keys():
    """W&B metric keys must not contain ':' (the composite label's
    internal grouping separator) -- `rise:flat` logs as `rise_flat_n`,
    not `rise:flat_n`."""
    cls = make_goal_mode_batch_split_ppo_class(PPO)
    m = _make_rise_kind_ppo(cls, n_envs=8)
    attach_goal_mode_batch_split(m, enabled=True, min_group=4,
                                 rise_start_kind=True)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value, **kw):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    _collect(m)
    m.train()
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups") == 3
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "rise_flat_n", 0) > 0
    assert fake_logger.name_to_value.get(
        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "rise_bridge_n", 0) > 0
    for key in fake_logger.name_to_value:
        assert ":" not in key, f"un-sanitized colon in W&B key: {key}"
