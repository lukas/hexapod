"""Rung-4 reverse-handoff on the batched MJX path (assistfade, 09-07).

Interface-level bank for ``goal.walk_reverse_handoff_gate`` /
``goal.walk_reverse_handoff_s`` on the MJX vec envs — the batched twin
of the CPU bank in ``test_task_semantics.py`` (ASSISTFADE_RUNG4_*).
Deliberately implementation-agnostic (written by the coordination
cycle, operator focus note 20260907T055148Z, while the implementation
itself landed from a concurrent cycle — see
rl_docs/tracks/assistfade/STATUS.md 09-07 ~06:3x): every test drives
only the public cfg keys + VecEnv API, so it stays valid whichever
wiring (per-tick host loop, precomputed plan, vectorized teacher)
serves the choreography.

Contract under test:
  1. gate key present-but-zero is bit-exact on the batched path;
  2. gate ON leaves every env genuinely MOVING with an asymmetric
     (mid-gait) footprint at episode start — the positive control;
  3. the host-side teacher commands are the SAME plan the C env
     computes for the same seed (final commanded pose matches to
     float precision; physics may drift fp32 vs fp64, commands not);
  4. sharded env stays BIT-IDENTICAL to the in-process reference with
     the gate ON (incl. a pooled-reset pop of a handoff-minted entry);
  5. pooled resets of handoff entries are immediately steppable.

Skipped when mujoco-mjx / jax aren't installed. CPU-pinned like every
MJX suite (bit-exact contract is per-XLA-platform).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("JAX_PLATFORMS", "cpu")

import numpy as np
import pytest

_PROTO = Path(__file__).resolve().parents[2]
if str(_PROTO) not in sys.path:
    sys.path.insert(0, str(_PROTO))

pytest.importorskip("mujoco")

from rl_move.sim.mjx_backend import mjx_is_available  # noqa: E402

if not mjx_is_available():  # pragma: no cover
    pytest.skip("mujoco-mjx / jax not installed", allow_module_level=True)

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.mjx_vec_env import MjxVecEnv  # noqa: E402
from rl_move.sim.servo_model import SimServoParams  # noqa: E402
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402

B = 2

# walk_pure pins every episode to a walk goal (the rung-4 regime; also
# guarantees _current_goal() is never None, the only case where the CPU
# reference skips the handoff).
BASE = {("goal", "walk_pure"): 1.0}
GATE_ZERO = {("goal", "walk_reverse_handoff_gate"): 0.0,
             ("goal", "walk_reverse_handoff_s"): 2.0}
GATE_ON = {("goal", "walk_reverse_handoff_gate"): 1.0,
           ("goal", "walk_reverse_handoff_s"): 1.0}


def _cfg(over: dict):
    cfg = load_config()
    for (sec, leaf), val in over.items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _venv(over: dict, *, seed: int = 0, cls=MjxVecEnv, **kw):
    return cls(SimHexapodJointWalkEnv, B,
               env_kwargs=dict(cfg=_cfg(over), randomize=False,
                               dr_scale=0.0, episode_seconds=1.0,
                               params=SimServoParams.from_cfg(None)),
               seed=seed, pool_per_env=1, desync_episodes=False, **kw)


def _zero_acts(v):
    return np.zeros((B,) + v.action_space.shape, dtype=np.float32)


def test_gate_key_present_but_zero_is_bitexact():
    """cfg keys present with gate=0.0 must not change a single bit of
    the batched reset/step stream vs the keys being absent."""
    a = _venv(BASE, seed=3)
    b = _venv({**BASE, **GATE_ZERO}, seed=3)
    try:
        oa, ob = a.reset(), b.reset()
        assert np.array_equal(oa, ob), "reset obs differ with gate=0"
        for k in range(3):
            ra = a.step(_zero_acts(a))
            rb = b.step(_zero_acts(b))
            assert np.array_equal(ra[0], rb[0]), f"obs diverged @{k}"
            assert np.array_equal(ra[1], rb[1]), f"reward diverged @{k}"
            assert np.array_equal(ra[2], rb[2]), f"dones diverged @{k}"
    finally:
        a.close()
        b.close()


def test_gate_on_moving_asymmetric_start_batched():
    """Positive control, batched twin of the CPU bank: gate ON leaves
    every env with real body velocity AND a mid-gait (asymmetric) pad
    reference, where the gate-off twin is a level near-static stand."""
    off = _venv(BASE, seed=0)
    off.reset()
    v_off = [float(np.hypot(*e.data.qvel[0:2])) for e in off.envs]
    sp_off = [float(np.ptp(e._pad_z_ref)) for e in off.envs]
    off.close()

    on = _venv({**BASE, **GATE_ON}, seed=0)
    on.reset()
    v_on = [float(np.hypot(*e.data.qvel[0:2])) for e in on.envs]
    sp_on = [float(np.ptp(e._pad_z_ref)) for e in on.envs]
    on.close()

    for i in range(B):
        assert v_on[i] > v_off[i] + 1e-4, (
            f"env {i}: no measurable body velocity from the handoff "
            f"(off={v_off[i]} on={v_on[i]})")
        assert sp_on[i] > sp_off[i] + 1e-3, (
            f"env {i}: footprint not asymmetric/mid-gait "
            f"(off spread={sp_off[i]} on spread={sp_on[i]})")


def test_cpu_and_batched_handoff_share_the_exact_teacher_plan():
    """Same seed => same goal + phase draws => the final commanded pose
    (host float64 math) must match the C env's to float precision.
    venv.reset() with pool_per_env=1 runs TWO choreographies (one pool
    mint + one live), each consuming one (goal, phase) draw pair from
    env 0's stream — so the C twin resets twice to align streams."""
    cfg_over = {**BASE, **GATE_ON}
    cpu = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=1.0, seed=0, cfg=_cfg(cfg_over))
    cpu.reset()
    cpu.reset()          # align with the venv's pool-mint + live draws
    cmd_cpu = np.asarray(cpu._cmd, dtype=float).copy()
    v_cpu = float(np.hypot(*cpu.data.qvel[0:2]))
    cpu.close()

    on = _venv(cfg_over, seed=0)
    on.reset()
    shim = on.envs[0]
    cmd_mjx = np.asarray(shim._cmd, dtype=float).copy()
    v_mjx = float(np.hypot(*shim.data.qvel[0:2]))
    on.close()

    assert np.allclose(cmd_cpu, cmd_mjx, atol=1e-9), (
        "host-side teacher plan diverged between C env and MJX shim:\n"
        f"cpu={cmd_cpu}\nmjx={cmd_mjx}")
    assert v_cpu > 1e-3, f"C reference not moving after handoff: {v_cpu}"
    assert v_mjx > 1e-3, f"MJX env not moving after handoff: {v_mjx}"


def test_sharded_bitwise_matches_inprocess_gate_on():
    """The training-path env (MjxShardedVecEnv) must stay BIT-IDENTICAL
    to the in-process reference with the handoff armed — including a
    pooled-reset pop of a handoff-minted entry (the dominant reset form
    during real training)."""
    import jax

    if jax.default_backend() != "cpu":  # pragma: no cover
        pytest.skip("bit-exact contract is per-XLA-platform; rerun "
                    "with JAX_PLATFORMS=cpu")

    import rl_move.sim.mjx_sharded_vec_env as sharded_mod
    if '"handoff_tick"' not in Path(sharded_mod.__file__).read_text():
        # The quoted literal is the worker protocol message — present
        # only once BOTH halves (worker handler + parent tick loop) of
        # the sharded wiring have landed; the half-landed state (shm
        # layout + reset_begin reply only) silently ignores the handoff
        # and would fail this test for a known, in-flight reason.
        pytest.skip("sharded reverse-handoff wiring not landed yet "
                    "(in flight — assistfade STATUS 09-07 ~06:3x); "
                    "this skip self-removes when it lands")

    cfg_over = {**BASE, **GATE_ON}
    a = _venv(cfg_over, seed=7)
    b = _venv(cfg_over, seed=7, cls=sharded_mod.MjxShardedVecEnv,
              host_workers=2)
    try:
        oa, ob = a.reset(), b.reset()
        assert np.array_equal(oa, ob), "reset obs differ"
        rng = np.random.default_rng(0)
        for k in range(6):
            act = rng.uniform(-0.3, 0.3,
                              (B,) + a.action_space.shape).astype(
                                  np.float32)
            if k == 2:
                act[0] = np.nan   # rejected action → pooled pop
            ra = a.step(act)
            rb = b.step(act)
            assert np.array_equal(ra[0], rb[0]), f"obs diverged @{k}"
            assert np.array_equal(ra[1], rb[1]), f"reward diverged @{k}"
            assert np.array_equal(ra[2], rb[2]), f"dones diverged @{k}"
    finally:
        a.close()
        b.close()


def test_pooled_reset_with_handoff_entries_is_steppable():
    """Pool entries minted with the gate ON inject a mid-gait state;
    the pop must hand SB3 a finite obs and an immediately steppable
    env (boundary for the device-state inject path)."""
    v = _venv({**BASE, **GATE_ON}, seed=1)
    try:
        v.reset()
        act = _zero_acts(v)
        act[0] = np.nan                    # SafetyLayer rejects → pop
        obs, rews, dones, infos = v.step(act)
        assert dones[0]
        assert np.all(np.isfinite(obs))
        obs, rews, dones, infos = v.step(_zero_acts(v))
        assert np.all(np.isfinite(obs))
        assert np.all(np.isfinite(rews))
    finally:
        v.close()
