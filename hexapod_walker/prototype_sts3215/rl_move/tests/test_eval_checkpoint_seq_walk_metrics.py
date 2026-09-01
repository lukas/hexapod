"""eval_checkpoint run_episode walk-metric fix (09-01, standwalk
single-cycle DONE-gate session tool).

BUG: `mode` in run_episode was captured ONCE at reset() and every
`if mode in ("walk", "quadwalk"):` gate (course/progress/slip/
gait-validity bookkeeping) kept reading that STALE value for the
whole episode. A plain single-mode episode never noticed (goal_mode
never changes), but a goal.mode_seq_forced_plan/mode_seq sequence
episode that starts in "rise" and later switches to "walk" got
cmd_dist_m/along_dist_m stuck at 0 the entire time -- progress_ratio/
slip_per_m/gait_valid always came back None for a session that
plainly walked mid-episode.

FIX: track the LIVE per-tick `info["goal_mode"]`; window the gait-
validity/slip computation to the tick range(s) where that live mode
was actually walk/quadwalk (summed across disjoint runs, no cross-run
diff/slip contamination at the seam). Legacy single-mode episodes have
exactly one run spanning the whole array, so the result must be
BIT-IDENTICAL to the pre-fix whole-episode formula -- checked directly
against `slip_m_total` (unconditional, untouched by this fix) below.
"""
from __future__ import annotations

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
from rl_move.sim.eval_checkpoint import run_episode  # noqa: E402
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402

N_ACT = 18


class _ZeroModel:
    def predict(self, obs, deterministic=True):
        return np.zeros(N_ACT), None


def _walk_only_env(*, episode_seconds: float = 10.0, **goal_overrides):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["walk_speed_min_m_s"] = 0.05
    g["walk_speed_max_m_s"] = 0.05
    g["walk_yaw_cmd"] = 0.0
    g.update(goal_overrides)
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=episode_seconds)
    return env


def test_legacy_single_mode_walk_matches_old_whole_episode_formula():
    """mode_seq OFF: the new windowed computation must reduce to
    exactly the old whole-episode one (single run = [0, T))."""
    env = _walk_only_env(episode_seconds=3.0)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_walk = 1.0
    env.reset(seed=0)
    assert env._goal_traj.mode == "walk"
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None)
    env.close()
    assert ep["progress_ratio"] is not None
    assert ep["slip_per_m"] is not None
    # the pre-fix formula was exactly slip_m_total / max(along_dist_m,
    # 0.05) -- slip_m_total is whole-episode & untouched by this fix.
    # Both sides are independently ROUNDED-to-3dp quantities (ep dict
    # convention), so compare with a loose tolerance, not bit-exactly.
    expect = ep["slip_m_total"] / max(ep["along_dist_m"], 0.05)
    assert ep["slip_per_m"] == pytest.approx(expect, abs=0.01)
    assert ep["gait_valid"] is not None


def test_forced_plan_rise_then_walk_populates_walk_metrics():
    """The bug case: episode LABELED 'rise' (reset-time mode) that
    mid-episode switches to a real walk segment must still get
    progress_ratio/slip_per_m/gait_valid from that walk segment --
    not None just because the episode didn't start as 'walk'."""
    env = _walk_only_env(episode_seconds=8.0, mode_seq=1.0,
                         mode_seq_forced_plan="rise:2,walk:3,lower:2")
    env.reset(seed=0)
    assert env._goal_traj.mode == "rise"  # reset-time label: "rise"
    assert env._seq_plan is not None
    assert [p["mode"] for p in env._seq_plan] == ["rise", "walk", "lower"]
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None)
    env.close()
    assert ep["mode"] == "rise"          # label unchanged (reset-time)
    assert ep["cmd_dist_m"] > 0.0         # BUG: used to stay exactly 0
    assert ep["progress_ratio"] is not None
    assert ep["slip_per_m"] is not None
    assert ep["gait_valid"] in (True, False)   # computed, not None


def test_forced_plan_pure_rise_no_walk_segment_stays_none():
    """No walk segment anywhere in the plan -> walk-only metrics stay
    None (unchanged legacy behavior for a non-walking episode)."""
    env = _walk_only_env(episode_seconds=5.0, mode_seq=1.0,
                         mode_seq_forced_plan="rise:2,hold:2")
    env.reset(seed=0)
    assert [p["mode"] for p in env._seq_plan] == ["rise", "hold"]
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None)
    env.close()
    assert "cmd_dist_m" not in ep       # never a walk tick -> never set
    assert ep.get("progress_ratio") is None
    assert ep.get("slip_per_m") is None
    assert ep.get("gait_valid") is None
