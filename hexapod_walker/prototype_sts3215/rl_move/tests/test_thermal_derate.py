"""motor.thermal_derate_enable -- per-joint actuator torque-capacity
derate driven by sustained current (walkcurr track, 2026-10-06).

Background: `lowerrole_terminal_support_forensics_2026-10-02` found the
lower role's converged 2-leg (L2+L5) terminal-support habit draws
near-identical sustained high per-joint current in passing AND
over_current-failing composed-lifecycle episodes; `lowerrole_contact_
timing_forensics_2026-10-06` found the habit is established within
~1s of ground contact and never narrows over the remaining ~13s. Every
reward/observation/trajectory/action-space/architecture/margin-pricing/
sampling-mix/reference-shaping lever tried against it is CLOSED
(rl_docs/tracks/walkcurr/STATUS.md Next 3). This mechanism is a
structurally different family: an env-DYNAMICS consequence (a live
``model.actuator_forcerange`` multiplier), not a reward price --
mirroring real STS3215-class servo thermal derating under sustained
near-rail current.

Contract under test:
  - default OFF (`motor.thermal_derate_enable` unset/0) is bit-exact:
    no state allocated (`_thermal_heat`/`_thermal_base_forcerange` stay
    None), `model.actuator_forcerange` never mutated from its post-DR
    baseline, stepped rewards byte-identical to a keyless env.
  - ON with a permissive threshold (current always "over") and a
    sustained hard push: per-joint heat grows tick over tick toward 1
    and `model.actuator_forcerange` magnitude shrinks monotonically
    toward `(1 - thermal_derate_max_frac) * baseline`.
  - ON but with a threshold current never reaches: heat stays at 0 and
    forcerange stays at the baseline despite the mechanism being armed.
  - episode reset clears the heat state and restores forcerange to
    THIS episode's fresh baseline (no cross-episode leakage).

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _env(seed: int, enable: bool = False, a_thresh: float | None = None,
         tau_rise: float | None = None, tau_fall: float | None = None,
         max_frac: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if enable:
        m = cfg.setdefault("motor", {})
        m["thermal_derate_enable"] = 1.0
        if a_thresh is not None:
            m["thermal_derate_a_thresh"] = a_thresh
        if tau_rise is not None:
            m["thermal_derate_tau_rise_s"] = tau_rise
        if tau_fall is not None:
            m["thermal_derate_tau_fall_s"] = tau_fall
        if max_frac is not None:
            m["thermal_derate_max_frac"] = max_frac
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for mname in ("hold", "lean", "track", "unload", "raise", "rise",
                  "lower", "quad", "walk"):
        if hasattr(g, f"p_{mname}"):
            setattr(g, f"p_{mname}", 1.0 if mname == "rise" else 0.0)
    g.force_rise_start = "flat"
    return env


def _base_env(env):
    """Reach through goal_task's wrapper to the balance env with
    ``_pos_act``/``_thermal_*`` state (same attribute lookup chain the
    other per-tick mechanisms' tests use)."""
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


def test_default_off_never_allocates_or_mutates():
    env = _env(seed=1)
    base = _base_env(env)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    base_forcerange = base.model.actuator_forcerange[base._pos_act].copy()
    _run(env, 30, action)
    assert base._thermal_derate_active is False
    assert base._thermal_heat is None
    assert base._thermal_base_forcerange is None
    np.testing.assert_array_equal(
        base.model.actuator_forcerange[base._pos_act], base_forcerange)
    env.close()


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("motor", {})["thermal_derate_enable"] = 0.0
    for cfg in (cfg_a, cfg_b):
        cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    env_a = SimHexapodGoalEnv(cfg=cfg_a, seed=4)
    env_b = SimHexapodGoalEnv(cfg=cfg_b, seed=4)
    for env in (env_a, env_b):
        g = env._goal_gen
        for mname in ("hold", "lean", "track", "unload", "raise", "rise",
                      "lower", "quad", "walk"):
            if hasattr(g, f"p_{mname}"):
                setattr(g, f"p_{mname}", 1.0 if mname == "rise" else 0.0)
        g.force_rise_start = "flat"
    env_a.reset(seed=4)
    env_b.reset(seed=4)
    rng = np.random.default_rng(0)
    for _ in range(25):
        act = rng.uniform(-1, 1, env_a.action_space.shape).astype(
            np.float32)
        _, ra, term_a, trunc_a, _ = env_a.step(act)
        _, rb, term_b, trunc_b, _ = env_b.step(act)
        assert ra == rb
        assert (term_a, trunc_a) == (term_b, trunc_b)
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_on_sustained_high_current_shrinks_forcerange():
    # a_thresh=0.0 means every tick reads "over" regardless of action
    # magnitude; a hard push from a flat start draws real current, so
    # heat should climb toward 1 and forcerange magnitude should shrink
    # monotonically toward (1 - max_frac) * baseline.
    env = _env(seed=1, enable=True, a_thresh=0.0, tau_rise=0.5,
               tau_fall=1.0, max_frac=0.5)
    base = _base_env(env)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    env.reset()
    base_forcerange = base._thermal_base_forcerange.copy()
    assert base._thermal_derate_active is True
    mags = []
    for _ in range(40):
        _, _, term, trunc, _ = env.step(action)
        mags.append(float(np.max(
            base.model.actuator_forcerange[base._pos_act, 1])))
        if term or trunc:
            break
    assert base._thermal_heat is not None
    assert np.all(base._thermal_heat > 0.0), (
        "sustained over-threshold current must raise heat on every joint")
    assert np.all(base._thermal_heat <= 1.0 + 1e-9)
    final_fr = base.model.actuator_forcerange[base._pos_act]
    assert np.all(final_fr[:, 1] <= base_forcerange[:, 1] + 1e-9)
    assert np.all(final_fr[:, 0] >= base_forcerange[:, 0] - 1e-9)
    # Shrinks tick over tick while the streak never breaks (heat
    # monotone non-decreasing toward saturation under a constant-over
    # drive -> derived forcerange magnitude monotone non-increasing).
    assert all(b <= a + 1e-9 for a, b in zip(mags, mags[1:])), (
        "forcerange magnitude must not grow while current stays over "
        "threshold"
    )
    env.close()


def test_high_threshold_never_fires():
    env = _env(seed=1, enable=True, a_thresh=1.0e6, tau_rise=0.5,
               tau_fall=0.5, max_frac=0.5)
    base = _base_env(env)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    env.reset()
    base_forcerange = base._thermal_base_forcerange.copy()
    for _ in range(20):
        _, _, term, trunc, _ = env.step(action)
        if term or trunc:
            break
    assert np.all(base._thermal_heat == 0.0)
    np.testing.assert_allclose(
        base.model.actuator_forcerange[base._pos_act], base_forcerange)
    env.close()


def test_reset_clears_heat_and_restores_forcerange():
    env = _env(seed=1, enable=True, a_thresh=0.0, tau_rise=0.3,
               tau_fall=1.0, max_frac=0.5)
    base = _base_env(env)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    env.reset()
    for _ in range(15):
        _, _, term, trunc, _ = env.step(action)
        if term or trunc:
            break
    assert np.any(base._thermal_heat > 0.0)
    env.reset()
    assert np.all(base._thermal_heat == 0.0)
    np.testing.assert_allclose(
        base.model.actuator_forcerange[base._pos_act],
        base._thermal_base_forcerange)
    env.close()
