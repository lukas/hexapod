"""``run_episode``'s ``trace_sink`` param + ``_save_rollout_trace``
(2026-09-03, standwalk rise-stall redesign spec item: "dump a real
qpos/action trace from a fresh stalling rollout and rebuild the
rise-stall twin as a faithful replay" -- no such tool existed).

Diagnostic-only, no-effect-when-unused mechanism: ``trace_sink=None``
(the default, every pre-existing call site) must leave ``run_episode``
byte-identical to before this change; passing a list appends one dict
per tick with the fields the redesign needs (qpos/qvel/action/
servo_current/height/mode/reward/terminated) WITHOUT altering the
returned ep dict, reward, or frames. ``_save_rollout_trace`` packs that
list into an .npz any future dig-in can load without re-running the
checkpoint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("mujoco")

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.eval_checkpoint import (  # noqa: E402
    run_episode, _save_rollout_trace)
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402

N_ACT = 18


class _ZeroModel:
    def predict(self, obs, deterministic=True):
        return np.zeros(N_ACT), None


def _rise_only_env(*, episode_seconds: float = 8.0):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=episode_seconds)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "walk", "lower"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_rise = 1.0
    return env


def test_trace_sink_none_is_a_pure_no_op():
    """Default (no trace_sink) must return the exact same ep dict as
    passing trace_sink=None explicitly -- this is the bit-exact-off
    contract every other diagnostic knob in this file follows."""
    env = _rise_only_env()
    env.reset(seed=0)
    ep_default, _ = run_episode(env, _ZeroModel(), deterministic=True,
                                video=False, annotate=None)
    env.close()
    env2 = _rise_only_env()
    env2.reset(seed=0)
    ep_explicit, _ = run_episode(env2, _ZeroModel(), deterministic=True,
                                 video=False, annotate=None,
                                 trace_sink=None)
    env2.close()
    assert ep_default == ep_explicit


def test_trace_sink_records_one_row_per_tick_without_changing_ep():
    env = _rise_only_env(episode_seconds=8.0)
    env.reset(seed=0)
    sink: list = []
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None, trace_sink=sink)
    env.close()
    n_ticks = len(sink)
    assert n_ticks > 0
    # one row per env.step() call
    assert n_ticks == pytest.approx(8.0 / env.dt, abs=1)
    row0 = sink[0]
    assert row0["qpos"].shape == env.data.qpos.shape
    assert row0["qvel"].shape == env.data.qvel.shape
    assert row0["action"].shape == (N_ACT,)
    assert row0["mode"] == "rise"
    # ep summary dict is untouched by tracing (same fields as the
    # no-trace call -- reuse the no-op test's contract).
    env3 = _rise_only_env(episode_seconds=8.0)
    env3.reset(seed=0)
    ep_notrace, _ = run_episode(env3, _ZeroModel(), deterministic=True,
                                video=False, annotate=None)
    env3.close()
    assert ep == ep_notrace


def test_save_rollout_trace_roundtrips_through_npz(tmp_path):
    env = _rise_only_env(episode_seconds=8.0)
    env.reset(seed=0)
    sink: list = []
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None, trace_sink=sink)
    env.close()
    out = tmp_path / "trace.npz"
    _save_rollout_trace(sink, out, ep)
    assert out.exists()
    d = np.load(out, allow_pickle=True)
    assert len(d["step"]) == len(sink)
    assert d["qpos"].shape == (len(sink), env.data.qpos.shape[0])
    assert d["action"].shape == (len(sink), N_ACT)
    loaded_ep = json.loads(str(d["ep_json"]))
    assert loaded_ep["mode"] == "rise"
    assert loaded_ep == ep


def test_save_rollout_trace_empty_sink_does_not_crash(tmp_path):
    out = tmp_path / "empty.npz"
    _save_rollout_trace([], out, {"mode": "rise"})
    assert not out.exists()
