"""Tests for the optional per-foot LOAD observation channel
(``obs.foot_contact_sense``, see ``rl_move/sim/walk_task.py::
foot_contact_sense_obs_dim`` / ``_augment_obs``).

2026-09-26 standwalk standing hypothesis (operator focus, RL_GOALS
169c555 lever (c)): the walker cannot ADAPT to per-leg miscalibration
because it cannot SENSE it -- no obs channel carries the DR draw. This
channel exposes the per-foot touch-sensor load (the same ground-truth
reading every duty/slip reward mechanism already consumes) as
``tanh(force_N / obs.foot_contact_scale)`` appended at the absolute
FRAME TAIL (kept last so ``--obs-pad-transplant 6`` is a per-frame
tail zero-pad on the transformer lineage). Default OFF and bit-exact
when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import load_config
from rl_move.sim.walk_task import (
    N_FOOT_CONTACT_OBS, SimHexapodJointWalkEnv, foot_contact_sense_obs_dim,
)


def test_dim_default_off():
    assert foot_contact_sense_obs_dim({}) == 0
    assert foot_contact_sense_obs_dim(
        {"obs": {"foot_contact_sense": 0.0}}) == 0


def test_dim_on():
    assert foot_contact_sense_obs_dim(
        {"obs": {"foot_contact_sense": 1.0}}) == N_FOOT_CONTACT_OBS


def _make_env(on: bool, *, scale: float | None = None):
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    if on:
        obs_cfg["foot_contact_sense"] = 1.0
        if scale is not None:
            obs_cfg["foot_contact_scale"] = scale
    return SimHexapodJointWalkEnv(cfg, seed=0)


def test_default_off_bit_exact():
    a = _make_env(False)
    obs_a, _ = a.reset(seed=0)
    b = _make_env(False)
    obs_b, _ = b.reset(seed=0)
    np.testing.assert_array_equal(obs_a, obs_b)
    assert a.observation_space.shape == b.observation_space.shape


def test_on_widens_frame_tail_by_six_and_prefix_identical():
    off = _make_env(False)
    obs_off, _ = off.reset(seed=0)
    on = _make_env(True)
    obs_on, _ = on.reset(seed=0)
    k = off._hist_n
    w_off = obs_off.shape[0] // k
    w_on = obs_on.shape[0] // k
    assert w_on == w_off + N_FOOT_CONTACT_OBS
    assert on.observation_space.shape[0] == obs_on.shape[0]
    # Every stacked frame: prefix identical to the off env's frame, the
    # 6 new dims at the frame TAIL.
    for f in range(k):
        np.testing.assert_allclose(
            obs_on[f * w_on:f * w_on + w_off],
            obs_off[f * w_off:(f + 1) * w_off], atol=0.0)


def test_tail_matches_touch_sensor_tanh():
    env = _make_env(True, scale=5.0)
    obs, _ = env.reset(seed=0)
    w = obs.shape[0] // env._hist_n
    tail = obs[w - N_FOOT_CONTACT_OBS:w]  # newest frame's tail
    want = []
    for adr in env._touch_adr:
        f = max(float(env.data.sensordata[adr]), 0.0) if adr >= 0 else 0.0
        want.append(np.tanh(f / 5.0))
    np.testing.assert_allclose(tail, np.asarray(want, dtype=np.float32),
                               atol=1e-6)
    # Bounded regardless of contact spikes.
    assert np.all(tail >= 0.0) and np.all(tail < 1.0)
    # At the settled plant stance all six feet are loaded -- the channel
    # must actually carry signal, not read zero.
    assert np.count_nonzero(tail > 0.05) >= 4


def test_step_keeps_tail_live():
    env = _make_env(True)
    obs, _ = env.reset(seed=1)
    w = obs.shape[0] // env._hist_n
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    obs, _, term, trunc, _ = env.step(a)
    tail = obs[w - N_FOOT_CONTACT_OBS:w]
    assert tail.shape == (N_FOOT_CONTACT_OBS,)
    assert np.all(tail >= 0.0) and np.all(tail <= 1.0)
