"""Two-phase rise sub-goal: attitude-stability hold-extension gate
(goal.rise_stability_gate, standwalk track, 2026-09-23).

Background (STATUS.md standwalk ~14:3x/~14:4x, second-rise-gap
dig-in): the composed rise->walk->lower->rise->walk baseline
(`eval_modeseq.py`) falls the SECOND (post-lower-reanchor) rise almost
every time on tilt_roll/tilt_pitch, and three independent doses of
direct exposure to the exact settled post-lower pose
(`goal.rise_start_bank`, 15/20/30% frac) all failed to move it. Direct
measurement (`eval_modeseq.py` + a one-off `DEBUG_TILT_REF` probe)
showed the restored physical attitude at the reanchor tick itself is
already level (~0.0-0.02deg from the episode's own tilt reference),
and a hidden-state-reset ablation (`DEBUG_RESET_STAND_STATE`) showed
the GRU stand model's carried-over recurrent state from the prior
`lower` segment is NOT the driver either (2/12 vs 1/12 second-rise
success, statistically unchanged) — so the instability genuinely
DEVELOPS during the first ~1.5s of the rise attempt, not at the
switch instant. This gate generalizes `_rise_gate_tick`'s existing
curl sub-goal freeze mechanism (`goal.rise_curl_gate`,
test_rise_curl_gate_hold.py) to a second, independent sub-goal: hold
the height ramp's onset until measured attitude (relative to this
episode's own `_tilt_ref0`, the SAME reference the safety trip uses)
settles within `rise_stability_gate_max_deg`, up to a capped extra
wait (`rise_stability_gate_max_extra_s`), so the policy gets a
dedicated stay-level grace window to arrest whatever attitude state
an unfamiliar pose leaves it in before also being asked to climb.

Contract under test:
  - default OFF (`goal.rise_stability_gate` unset) is bit-exact: the
    ramp's onset tick is identical to the gate machinery being absent
    (same convention as the curl gate's own bit-exactness test).
  - ON, attitude held artificially far from `_tilt_ref0` (never
    settles): the ramp is deferred by up to
    `rise_stability_gate_max_extra_s`, then forced to proceed anyway
    (no infinite stall) -- mirrors the curl gate's own "never met"
    test.
  - ON, attitude already at `_tilt_ref0` (trivially settled, the
    common case for every cold flat/bridge/crouch start): behaves
    bit-identically to the gate being off -- confirms the gate is a
    true no-op for ordinary cold starts and can only ever extend the
    genuinely-flagged post-lower-reanchor case.
  - ON both `rise_curl_gate` and `rise_stability_gate` together, with
    only ONE sub-goal artificially unmet: the ramp still defers --
    locks the AND (both-must-be-met) combination, not an OR.
  - freeze counter never advances when both gates are off.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _rise_env(seed: int, force_start: str = "flat",
              stability_gate: float = 0.0,
              curl_gate: float = 0.0,
              max_extra_s: float | None = None,
              max_deg: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if stability_gate:
        cfg["goal"]["rise_stability_gate"] = stability_gate
        if max_extra_s is not None:
            cfg["goal"]["rise_stability_gate_max_extra_s"] = max_extra_s
        if max_deg is not None:
            cfg["goal"]["rise_stability_gate_max_deg"] = max_deg
    if curl_gate:
        cfg["goal"]["rise_curl_gate"] = curl_gate
        cfg["goal"]["rise_curl_gate_max_extra_s"] = (
            max_extra_s if max_extra_s is not None else 2.0)
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
    assert first == hold_n - 1


def test_gate_on_defers_while_tilt_never_settles_then_forces_it():
    max_extra_s = 0.4
    env = _rise_env(seed=1, stability_gate=1.0, max_extra_s=max_extra_s)
    env.reset()
    # Force the sub-goal permanently unmet: offset the episode's own
    # tilt reference far from the actual (near-level) attitude, same
    # spirit as the curl gate test's "curl_dist starts far and a zero
    # action barely moves it" -- here we directly control the
    # reference so the mismatch cannot close by construction.
    roll_ref, pitch_ref = env._tilt_ref0
    env._tilt_ref0 = (roll_ref + math.radians(30.0), pitch_ref)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    out = []
    for _ in range(300):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    hold_n = env._rise_ramp_i0
    dt = env.dt
    env.close()
    first = _first_ramp_tick(out)
    assert first is not None
    max_extra_ticks = int(round(max_extra_s / dt))
    assert first > hold_n
    assert first <= hold_n + max_extra_ticks + 1


def test_gate_is_noop_when_attitude_already_at_reference():
    # The common case: attitude already matches _tilt_ref0 (true for
    # every ordinary cold flat/bridge/crouch start) -- must ramp on
    # the natural schedule, identical to gate-off.
    env = _rise_env(seed=1, stability_gate=1.0, max_extra_s=5.0,
                     max_deg=6.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._rise_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    assert first == hold_n - 1


def test_both_gates_and_combine_not_or():
    # curl sub-goal trivially met (crouch start), stability sub-goal
    # forced permanently unmet -- must still defer (AND, not OR).
    max_extra_s = 0.4
    env = _rise_env(seed=2, force_start="crouch", curl_gate=1.0,
                     stability_gate=1.0, max_extra_s=max_extra_s)
    env.reset()
    roll_ref, pitch_ref = env._tilt_ref0
    env._tilt_ref0 = (roll_ref + math.radians(30.0), pitch_ref)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    out = []
    for _ in range(300):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    hold_n = env._rise_ramp_i0
    dt = env.dt
    env.close()
    first = _first_ramp_tick(out)
    assert first is not None
    max_extra_ticks = int(round(max_extra_s / dt))
    assert first > hold_n
    assert first <= hold_n + max_extra_ticks + 1


def test_freeze_ticks_zero_when_both_gates_off():
    env = _rise_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    env.reset()
    for _ in range(50):
        env.step(action)
        assert env._rise_gate_freeze_ticks == 0
    env.close()
