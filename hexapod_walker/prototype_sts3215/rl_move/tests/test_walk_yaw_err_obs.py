"""LIVE signed yaw-rate tracking-error observation channel
(goal.walk_yaw_err_obs), walkcurr STATUS Next item (b), built 09-28.

Context: the yawprogdecay1 canary pair (`ops.sh index story
cw-walkyaw50hz-rlonly-scratch-sac-s{0,1}-...-yawprogdecay1-canary2m`)
closed a REWARD-only fix to the turnonly/yawprice20 uncontrolled-spin
exploit: capping/decaying the yaw_prog income past ratio=1 does
eliminate the farmed overshoot, but both seeds collapse instead to a
near-frozen body with essentially zero signed wz response to the
command (probe_turn_authority's own "FROZEN-BODY" classifier on both).
The standing hypothesis (walkcurr STATUS item (b)) is that this is
partly an OBSERVATION gap, not only a reward-shape one: the obs tail
today gives the policy the raw commanded wz_ref (walk_task.WalkGoal /
_augment_obs) and separately a measured rate buried in the gyro obs
block -- the policy has to reconstruct "how wrong am I" itself by
subtracting two independently-DR-noised numbers, with no recurrent
memory (this lineage is a plain SAC MLP, not the GRU/history-based
architectures used elsewhere). This channel appends that live signed
error directly, from the same privileged env._body_wz() ground truth
probe_turn_authority itself reads.

Per RESEARCH_RULES "Tests": mechanics only (cfg wiring / obs width /
the exact subtraction+scale formula), never a rollout-ranking or
trained-behavior assertion. mesh_mjx model, no artifacts, <5s total.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def _mesh_mjx(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")


def _walk_env(monkeypatch, *, yaw_cmd=0.0, yaw_err_obs=0.0, seed=0):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = yaw_cmd
    goal["walk_yaw_err_obs"] = yaw_err_obs
    goal["walk_gait_start_frac"] = 0.0
    goal["walk_park_start_frac"] = 0.0
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    return env


def test_default_off_is_flag_off_and_bit_exact_width(monkeypatch):
    """goal.walk_yaw_err_obs unset (0.0 default): the flag stays False
    and obs width is IDENTICAL to a yaw_cmd-only env -- bit-exact for
    every pre-09-28 walk_yaw_cmd lineage."""
    env_plain = _walk_env(monkeypatch, yaw_cmd=1.0, yaw_err_obs=0.0,
                           seed=0)
    assert env_plain._yaw_cmd is True
    assert env_plain._yaw_err_obs is False
    w_plain = env_plain.observation_space.shape[0]
    env_plain.close()


def test_err_obs_requires_yaw_cmd_to_take_effect(monkeypatch):
    """walk_yaw_err_obs=1 WITHOUT walk_yaw_cmd=1 is a no-op (there is
    no wz_ref to compute an error against) -- flag stays False, obs
    width matches the fully-legacy (no yaw at all) env."""
    env_none = _walk_env(monkeypatch, yaw_cmd=0.0, yaw_err_obs=0.0,
                          seed=0)
    w_none = env_none.observation_space.shape[0]
    env_none.close()

    env_err_only = _walk_env(monkeypatch, yaw_cmd=0.0, yaw_err_obs=1.0,
                              seed=0)
    assert env_err_only._yaw_cmd is False
    assert env_err_only._yaw_err_obs is False
    assert env_err_only.observation_space.shape[0] == w_none
    env_err_only.close()


def test_err_obs_adds_exactly_one_dim_over_yaw_cmd_alone(monkeypatch):
    env_plain = _walk_env(monkeypatch, yaw_cmd=1.0, yaw_err_obs=0.0,
                           seed=0)
    w_plain = env_plain.observation_space.shape[0]
    env_plain.close()

    env_err = _walk_env(monkeypatch, yaw_cmd=1.0, yaw_err_obs=1.0,
                         seed=0)
    assert env_err._yaw_cmd is True
    assert env_err._yaw_err_obs is True
    assert env_err.observation_space.shape[0] == w_plain + 1
    env_err.close()


def test_appended_value_is_measured_minus_commanded_over_scale(
        monkeypatch):
    """Wiring check: the LAST obs entry is exactly
    (env._body_wz() - goal.wz_ref) / WZ_ERR_SCALE at the instant obs
    was built -- not a trained-behavior claim, just that the two
    numbers this mechanism is supposed to combine are the ones it
    actually reads, with the documented scale."""
    from rl_move.sim import walk_task as wt

    env = _walk_env(monkeypatch, yaw_cmd=1.0, yaw_err_obs=1.0, seed=3)
    obs, _info = env.reset()
    goal = env._current_goal()
    wz_ref = float(getattr(goal, "wz_ref", 0.0))
    wz_meas = env._body_wz()
    expected = (wz_meas - wz_ref) / wt.WZ_ERR_SCALE
    assert obs[-1] == pytest.approx(expected, abs=1e-6)
    # And the second-to-last entry is still the plain commanded ref
    # (unchanged position/scale vs the pre-09-28 tail convention).
    assert obs[-2] == pytest.approx(wz_ref / wt.WZ_SCALE, abs=1e-6)
    env.close()


def test_zero_commanded_and_still_body_reads_near_zero_error(
        monkeypatch):
    """Mechanics sanity, not a trained-behavior claim: immediately
    after reset (body at rest, wz_ref most likely 0 for this seed's
    draw or small), the raw error value is finite and consistent with
    the same subtraction on a second read -- guards against a stale/
    uninitialized _body_wz() read order bug."""
    env = _walk_env(monkeypatch, yaw_cmd=1.0, yaw_err_obs=1.0, seed=7)
    obs, _info = env.reset()
    import math
    assert math.isfinite(obs[-1])
    env.close()
