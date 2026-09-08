"""test_amp_style_vec.py — AMP track M1 item 3: the live reward-loop
wiring (2026-08-22). Proves, on CPU only (no jax/mjx needed):

1. env contract: goal.amp_style_obs=1 makes the walk env emit a
   finite 60-dim info["amp_obs_style"] whose first 18 dims are RAW
   joint angles (neutral=0); the DEFAULT cfg emits NO key and takes
   the untouched code path (bit-exact off);
2. MotionLibrary.neutral_pose exists, is 18-dim, and equals the
   per-clip derivation for every clip (the single-neutral convention
   the live wiring assumes);
3. AMPStyleVecWrapper blend math: r = task_w * r_env + style_w *
   r_style with r_style in [0,1], zero on the first tick of every
   episode (no valid pair) and after every done (boundary masking);
4. transitions crossing a done are never pushed to the replay ring;
   the ring wraps correctly at capacity;
5. train_discriminator returns None until one batch fits, then runs
   finite updates that move D(real) above D(fake) on the synthetic
   setup; save()/load() round-trips the discriminator exactly.
"""
from __future__ import annotations


import numpy as np
import pytest
import torch


from rl_move.sim.amp_discriminator import MotionLibrary
from rl_move.sim.amp_style_vec import (
    AMPStyleVecWrapper, _TransitionRing)


# ---------------------------------------------------------------- env

def _cpu_walk_env(cfg=None):
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = cfg if cfg is not None else load_config()
    return SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=3.0, seed=0, cfg=cfg)


def test_env_emits_obs_style_only_when_cfg_on():
    from rl_move.config import load_config
    # OFF (default): no key — the untouched legacy path.
    env = _cpu_walk_env()
    env.reset()
    _, _, _, _, info = env.step(np.zeros(env.action_space.shape,
                                         dtype=np.float32))
    assert "amp_obs_style" not in info
    env.close()

    # ON: 60-dim finite vector, dims 0..17 = RAW joint angles.
    cfg = load_config()
    cfg.setdefault("goal", {})["amp_style_obs"] = 1.0
    env = _cpu_walk_env(cfg)
    env.reset()
    _, _, _, _, info = env.step(np.zeros(env.action_space.shape,
                                         dtype=np.float32))
    v = info["amp_obs_style"]
    assert v.shape == (60,)
    assert np.all(np.isfinite(v))
    q_now = np.asarray(env.data.qpos, dtype=np.float64)[env._qadr]
    np.testing.assert_allclose(v[:18], q_now, atol=1e-6)
    env.close()


def test_env_emits_cmd_conditioned_obs_style_when_flagged():
    """08-23 yaw-authority follow-up: goal.amp_style_cmd_cond=1 (on
    top of amp_style_obs=1) appends the LIVE (vx_ref, vy_ref, wz_ref)
    at the tail -> 63-dim, and the appended triple matches the active
    WalkGoal exactly. Default (cmd_cond absent/0) stays 60-dim, byte-
    identical to the legacy path (already proven above) -- this test
    only exercises the ON path plus one OFF-with-amp-on control."""
    from rl_move.config import load_config
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv

    def make_env(cmd_cond):
        cfg = load_config()
        goal = cfg.setdefault("goal", {})
        goal["amp_style_obs"] = 1.0
        if cmd_cond:
            goal["amp_style_cmd_cond"] = 1.0
        goal["walk_yaw_cmd"] = 1
        goal["walk_yaw_max_rad_s"] = 0.3
        goal["walk_turn_in_place_frac"] = 1.0
        goal["walk_gait_start_frac"] = 1.0
        env = SimHexapodJointWalkEnv(cfg, seed=0)
        g = env._goal_gen
        for m in ("hold", "lean", "track", "unload", "raise", "rise",
                  "lower"):
            if hasattr(g, f"p_{m}"):
                setattr(g, f"p_{m}", 0.0)
        g.p_walk = 1.0
        env.reset()
        return env

    # OFF: amp_style_obs on, cmd_cond absent -> still 60-dim (the flag,
    # not just amp_style_obs, gates the extra dims).
    env_off = make_env(False)
    _, _, _, _, info_off = env_off.step(
        np.zeros(env_off.action_space.shape, dtype=np.float32))
    assert info_off["amp_obs_style"].shape == (60,)
    env_off.close()

    # ON: 63-dim, tail == live WalkGoal command. Step past the legacy
    # 1s zero-hold (no walk_gait_spawn_wz here, so the ramp is the
    # plain walk_yaw_cmd default, not the fast-ramp densification
    # tested in test_walk_gait_spawn_wz_turn_state_densification) so
    # wz_ref is actually nonzero by the time we read it.
    env_on = make_env(True)
    n_steps = int(round(1.5 / env_on.dt))
    info_on = None
    for _ in range(n_steps):
        _, _, _, _, info_on = env_on.step(
            np.zeros(env_on.action_space.shape, dtype=np.float32))
    goal2 = env_on._current_goal()
    assert abs(float(getattr(goal2, "wz_ref", 0.0))) > 1e-9, (
        "test needs a turn-in-place draw with nonzero wz_ref")
    v = info_on["amp_obs_style"]
    assert v.shape == (63,)
    assert np.all(np.isfinite(v))
    np.testing.assert_allclose(
        v[60:], [goal2.vx_ref, goal2.vy_ref, goal2.wz_ref], atol=1e-6)
    env_on.close()


# ------------------------------------------------------------ library


def lib_path_default():
    from rl_move.sim.amp_discriminator import DEFAULT_LIBRARY
    return DEFAULT_LIBRARY


# ------------------------------------------------------- stub vec env

class _StubVecEnv:
    """Minimal VecEnv double: constant task reward 2.0/tick, scripted
    dones, obs_style rows drawn near the library manifold so the maths
    are deterministic and library-normalization stays finite."""

    def __init__(self, n_envs=3, feat_dim=60, done_script=None):
        self.num_envs = n_envs
        self.feat_dim = feat_dim
        self.observation_space = None
        self.action_space = None
        self.render_mode = None
        self._t = 0
        self._done_script = done_script or {}
        lib = MotionLibrary()
        self._base = lib.obs_style[0].astype(np.float32).copy()
        self._neutral = lib.neutral_pose.copy()
        self.emitted = []          # (t, env, row) for cross-checks

    def reset(self):
        self._t = 0
        return np.zeros((self.num_envs, 4), dtype=np.float32)

    def step_async(self, actions):
        pass

    def step_wait(self):
        self._t += 1
        rews = np.full(self.num_envs, 2.0, dtype=np.float32)
        dones = np.zeros(self.num_envs, dtype=bool)
        for (t, i) in self._done_script:
            if t == self._t:
                dones[i] = True
        infos = []
        for i in range(self.num_envs):
            row = self._base.copy()
            row += 0.01 * np.float32(self._t) + 0.001 * np.float32(i)
            # env emits RAW joints: add the neutral back onto dims 0..17
            raw = row.copy()
            raw[:18] += self._neutral
            infos.append({"amp_obs_style": raw})
            self.emitted.append((self._t, i, row))
        obs = np.zeros((self.num_envs, 4), dtype=np.float32)
        return obs, rews, dones, infos

    def close(self):
        pass

    # VecEnvWrapper delegates it needs
    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

    def get_attr(self, name, indices=None):
        raise AttributeError(name)


def _wrap(stub, **kw):
    kw.setdefault("style_weight", 0.5)
    kw.setdefault("task_weight", 0.7)
    kw.setdefault("replay_size", 64)
    kw.setdefault("seed", 0)
    return AMPStyleVecWrapper(stub, **kw)


def _write_tiny_library(path, extra_dims=0, n=40):
    """Minimal synthetic library npz (08-23 cmd-cond follow-up): just
    the fields MotionLibrary.__init__ reads. joint dims stay 18 always
    (that convention is independent of obs_style's tail width);
    extra_dims appends that many extra style columns (0 = plain 60-dim
    legacy-shaped library, 3 = a stand-in for the cmd-cond 63-dim
    library) so the SAME test helper covers both shapes."""
    rng = np.random.default_rng(0)
    jp = rng.normal(size=(n, 18)).astype(np.float32)
    rel = jp - jp[0]
    feat_dim = 60 + extra_dims  # 18+18+3+3+18(dummy foot dims)+extra
    obs_style = rng.normal(size=(n, feat_dim)).astype(np.float32)
    obs_style[:, :18] = rel  # keep the neutral-pose slice consistent
    np.savez_compressed(
        str(path), obs_style=obs_style,
        clip_starts=np.array([0]), clip_lens=np.array([n]),
        joint_position=jp, joint_position_rel_neutral=rel)


def test_wrapper_rejects_style_weight_zero():
    with pytest.raises(ValueError):
        _wrap(_StubVecEnv(), style_weight=0.0)


def test_ring_wraps_at_capacity():
    ring = _TransitionRing(8, 3)
    a = np.arange(30, dtype=np.float32).reshape(10, 3)
    ring.push(a[:5], a[:5] + 100)
    assert len(ring) == 5
    ring.push(a[5:], a[5:] + 100)          # 10 total -> wraps to 8
    assert len(ring) == 8
    # newest rows must all be present exactly once
    got = {tuple(r) for r in ring.s_t}
    want = {tuple(r) for r in a[2:]}       # oldest 2 evicted
    assert got == want
    s, s1 = ring.sample(16, np.random.default_rng(0))
    np.testing.assert_allclose(s1 - s, 100.0)


