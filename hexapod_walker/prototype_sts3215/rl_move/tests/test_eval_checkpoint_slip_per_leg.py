"""slip_per_m_per_leg (09-28, standwalk loadslip-pricing dose10 canary
follow-up): the "still inert" additive-aggregate-charge verdict names
a per-leg-targeted mechanism as the next lever, which first needs to
know WHERE the slip concentrates. `run_episode` already computed a
per-leg loaded-foot-travel array (`slips_w`) and only ever summed it
into the aggregate `slip_per_m` -- this purely additive field exposes
the per-leg breakdown with the identical guard/denominator, so it must
always reconstruct the aggregate up to rounding and never fire when
the aggregate itself is None.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.eval_checkpoint import run_episode
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

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


def test_slip_per_m_per_leg_has_six_legs_and_sums_to_aggregate():
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
    assert ep["slip_per_m"] is not None
    per_leg = ep["slip_per_m_per_leg"]
    assert per_leg is not None
    assert len(per_leg) == 6
    assert all(isinstance(v, float) for v in per_leg)
    # Both sides independently rounded-to-3dp -- loose tolerance.
    assert sum(per_leg) == pytest.approx(ep["slip_per_m"], abs=0.02)


def test_slip_per_m_per_leg_none_when_aggregate_none():
    """No commanded distance (e.g. no walk segment at all) -> the
    per-leg breakdown must stay None exactly when slip_per_m does,
    never fire on its own."""
    env = _walk_only_env(episode_seconds=5.0, mode_seq=1.0,
                         mode_seq_forced_plan="rise:2,hold:2")
    env.reset(seed=0)
    ep, _ = run_episode(env, _ZeroModel(), deterministic=True,
                        video=False, annotate=None)
    env.close()
    assert ep.get("slip_per_m") is None
    assert ep.get("slip_per_m_per_leg") is None
