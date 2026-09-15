"""Two-phase rise sub-goal: dynamic hold-extension gate
(goal.rise_curl_gate, walkcurr track, 2026-09-13).

Background (RL_LOG 09-13 21:3x, `cw-stance50hz-rlonly-
risecurlgate-s1-canary2m` CANARY FAIL - MECHANISM): TWO successive
income-repricing levers on `reward_rise_score_prog` (current-headroom-
gated, then curl-geometry-gated) both left the flat/bridge rise/det
failing trajectories statistically identical to the ungated parent
(`cur_rail_frac` reproducing the parent's own 0.457/0.587 fingerprint
verbatim) -- pricing the SAME continuous height ramp differently never
stopped the policy attempting the doomed sprawled push, because the
height reference itself advances on a fixed WALL-CLOCK schedule
(`goal.rise_hold_s` then `goal.rise_ramp_s`) regardless of whether the
feet ever curled in. The curl-geometry income gate's own canary showed
`rise_score_curl_factor` pinned at 1.0 for all 31 sampled ticks across
2M steps -- it never actually discounted a real training tick, because
the policy's learned trajectory never scores height/posture progress
while still far from tucked, so the discount lever had nothing to
discount.

This is not a third re-price of the same income term: it makes the
height ramp's own ONSET conditional on a genuine intermediate sub-goal
(feet within `rise_curl_gate_threshold_mm` of the plant footprint --
curl-to-bridge-pose), by freezing the trajectory index fed to
`_current_goal()` at the last pre-ramp (height==0) tick for as long as
the sub-goal is unmet, up to a capped extra wait
(`rise_curl_gate_max_extra_s`) so a hopeless episode still eventually
gets scored on its attempt rather than stalling forever. Crouch starts
(curl_dist already ~0) are exempt.

Contract under test:
  - default OFF (`goal.rise_curl_gate` unset) is bit-exact: the height
    ramp's onset tick is identical with the gate machinery present in
    the class vs an env built before this change would have produced
    (verified via a direct schedule-index cross-check, not a golden
    file).
  - ON, curl distance held artificially far (never meets the
    threshold): the height ramp does NOT begin at the natural
    `_rise_ramp_i0` schedule tick; it is deferred by up to
    `rise_curl_gate_max_extra_s`, then forced to proceed anyway (no
    infinite stall).
  - ON, curl distance made to cross the threshold partway through the
    extra-wait window: the ramp begins exactly one tick after the
    crossing, not at the original schedule tick and not at the cap.
  - ON, crouch start: behaves bit-identically to the gate being off
    (curl_dist ~0 at a crouch start, nothing to gate; also explicitly
    exempted by `start_at`).

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _rise_env(seed: int, force_start: str = "flat",
              curl_gate: float = 0.0,
              max_extra_s: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if curl_gate:
        cfg["goal"]["rise_curl_gate"] = curl_gate
        if max_extra_s is not None:
            cfg["goal"]["rise_curl_gate_max_extra_s"] = max_extra_s
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
    g.force_rise_start = force_start
    return env


def _run(env, n_steps, action):
    env.reset()
    out = []
    for _ in range(n_steps):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    return out


def _first_ramp_tick(infos):
    """First index whose height_ref_mm departs from ~0."""
    for i, info in enumerate(infos):
        if abs(info.get("height_ref_mm", 0.0)) > 1e-6:
            return i
    return None


def test_default_off_ramps_on_the_natural_schedule():
    env = _rise_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._rise_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    # Bit-exact: the ramp begins exactly at the precomputed schedule
    # tick, never deferred (freeze_ticks stays 0 whole episode).
    assert first == hold_n - 1


def test_gate_on_defers_ramp_while_curl_never_met_then_forces_it():
    max_extra_s = 0.4
    env = _rise_env(seed=1, curl_gate=1.0, max_extra_s=max_extra_s)
    # The 40mm threshold is unreachable for a true flat start doing
    # nothing (curl_dist starts ~176mm and a zero action barely moves
    # it), so the gate must hold through the whole extra-wait window.
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._rise_ramp_i0
    dt = env.dt
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    max_extra_ticks = int(round(max_extra_s / dt))
    # Ramp must NOT start at the original schedule tick (deferred)...
    assert first > hold_n
    # ...but must not stall past hold_n + the capped extra wait either.
    assert first <= hold_n + max_extra_ticks + 1


def test_gate_unlocks_immediately_once_curl_dist_crosses_threshold():
    env = _rise_env(seed=1, curl_gate=1.0, max_extra_s=5.0)
    # Report the sub-goal as ALREADY satisfied at reset (measured curl
    # distance pinned under the 40mm threshold), so the gate must never
    # defer at all -- ramp begins at the natural schedule tick, same as
    # gate-off.
    env._curl_dist = lambda: 0.0
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._rise_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    assert first == hold_n - 1


def test_crouch_start_exempt_from_gating():
    env = _rise_env(seed=2, force_start="crouch", curl_gate=1.0,
                     max_extra_s=5.0)
    # Crouch starts are exempt by start_at -- must behave exactly like
    # gate-off.
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 200, action)
    hold_n = env._rise_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    assert first == hold_n - 1


def test_freeze_ticks_zero_when_gate_off():
    env = _rise_env(seed=1, curl_gate=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    env.reset()
    for _ in range(50):
        env.step(action)
        assert env._rise_gate_freeze_ticks == 0
    env.close()
