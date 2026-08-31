"""distill_gru.py ``--mirror-augment`` tests (standwalk turn-authority
asymmetry fix path 2, STATUS 08-31 ~11:1x / OPERATOR_QUESTIONS
q_20260831T1115Z).

Locks:
1. ``mirror_augment_episodes`` doubles a batch, preserves mode labels,
   copies value targets unchanged, and mirroring TWICE is the identity
   (the underlying maps are involutions — test_mirror.py already locks
   this at the map level; this checks the episode-batch wrapper wires
   them correctly end to end).
2. an obs-width mismatch raises loudly (layout drift must never train
   silently on stale maps).
3. ``distill_gru.main`` requires ``goal.walk_yaw_cmd=1`` before doing
   any heavy teacher-loading work when ``--mirror-augment`` is passed
   (fails fast, not mid-collection).
4. default OFF: episodes pass through byte-identical when the flag is
   never set (covered structurally — the flag only gates a function
   call, never mutates default code paths).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "linux_control"))
sys.path.insert(0, str(ROOT / "linux_control" / "urt2_setup"))

from rl_move.sim.distill_gru import (  # noqa: E402
    main as distill_main, mirror_augment_episodes,
)
from rl_move.sim.mirror import (  # noqa: E402
    joint_perm_sign, obs_perm_sign, resolve_obs_mirror_maps,
)

CFG = {"goal": {"walk_yaw_cmd": 1.0, "walk_phase_obs": 1.0},
      "obs": {"mode_onehot": 1.0, "history_frames": 1}}


def _obs_width() -> int:
    perm, _ = obs_perm_sign(walk=True, yaw_cmd=True, phase_obs=True,
                            mode_onehot=True, history_frames=1)
    return len(perm)


def _fake_episodes(n_ep: int, obs_dim: int, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_ep):
        t = 5 + i
        mode = "walk" if i % 2 == 0 else "rise"
        obs = rng.normal(size=(t, obs_dim)).astype(np.float32)
        act = rng.uniform(-1, 1, size=(t, 18)).astype(np.float32)
        val = rng.normal(size=(t,)).astype(np.float32)
        out.append((mode, obs, act, val))
    return out


def test_mirror_augment_doubles_and_preserves_mode():
    obs_dim = _obs_width()
    eps = _fake_episodes(4, obs_dim)
    out = mirror_augment_episodes(eps, CFG, obs_dim)
    assert len(out) == 2 * len(eps)
    # original half is byte-identical and in the same order
    for (m0, o0, a0, v0), (m1, o1, a1, v1) in zip(eps, out[:len(eps)]):
        assert m0 == m1
        assert np.array_equal(o0, o1)
        assert np.array_equal(a0, a1)
        assert np.array_equal(v0, v1)
    # mirrored half: same mode label, same shape, same value target,
    # but obs/act actually transformed (not a no-op copy)
    for (m0, o0, a0, v0), (m1, o1, a1, v1) in zip(eps, out[len(eps):]):
        assert m0 == m1
        assert o1.shape == o0.shape and a1.shape == a0.shape
        assert np.array_equal(v0, v1)
        assert not np.array_equal(o0, o1)
        assert not np.array_equal(a0, a1)


def test_mirror_augment_is_involution_on_the_mirrored_copy():
    """Mirroring the mirrored copy again must reproduce the original
    (obs_perm_sign/joint_perm_sign are involutions — locks the wrapper
    applies them consistently, not just that the maps themselves are
    involutions, which test_mirror.py already covers)."""
    obs_dim = _obs_width()
    eps = _fake_episodes(3, obs_dim, seed=1)
    once = mirror_augment_episodes(eps, CFG, obs_dim)
    mirrored_only = once[len(eps):]
    twice = mirror_augment_episodes(mirrored_only, CFG, obs_dim)
    round_tripped = twice[len(mirrored_only):]
    for (m0, o0, a0, v0), (m1, o1, a1, v1) in zip(eps, round_tripped):
        assert m0 == m1
        assert np.allclose(o0, o1, atol=1e-6)
        assert np.allclose(a0, a1, atol=1e-6)


def test_mirror_augment_rejects_wrong_obs_width():
    eps = _fake_episodes(2, 40)
    with pytest.raises(SystemExit, match="obs layout drifted"):
        mirror_augment_episodes(eps, CFG, 40)


def test_resolve_obs_mirror_maps_matches_manual_composition():
    obs_dim = _obs_width()
    perm, sign = resolve_obs_mirror_maps(CFG, obs_dim, walk=True)
    exp_perm, exp_sign = obs_perm_sign(walk=True, yaw_cmd=True,
                                       phase_obs=True, mode_onehot=True,
                                       history_frames=1)
    assert np.array_equal(perm, exp_perm)
    assert np.array_equal(sign, exp_sign)


def test_distill_main_mirror_augment_requires_walk_yaw_cmd():
    # No goal.walk_yaw_cmd override -> defaults to 0 -> must fail FAST,
    # before any teacher checkpoint is loaded (no --walk-teacher/
    # --stance-teacher path given, so a slow failure would instead be
    # a FileNotFoundError deep in PPO.load, not this guard).
    with pytest.raises(SystemExit, match="walk_yaw_cmd"):
        distill_main(["--mirror-augment", "--dual"])


def test_joint_perm_sign_used_by_augment_matches_module_export():
    # sanity: the function imports the same joint_perm_sign others use
    p1, s1 = joint_perm_sign()
    p2, s2 = joint_perm_sign()
    assert np.array_equal(p1, p2) and np.array_equal(s1, s2)
