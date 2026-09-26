"""Task-space TURN-OFFSET mechanism (goal.walk_yaw_offset_set /
walk_reward_yaw.yaw_offset_kernel), walkcurr Next item.

Built 2026-09-26 per the design sketched in track STATUS.md 2026-09-25
~13:5x, after the rate-based tip_frac==0 "walk+curve specialist"
composition route CLOSED 0/2 seeds on the eased-cap contract
(`cw-walkyaw50hz-rlonly-scratch-sac-{s0,s1}-easedterm-tipfrac0-acq1`).
Every closed rate-based arm commands a continuous body-frame yaw-RATE
that is either pinned at exactly 0 or drawn from a wide band with an
instant flip at resample boundaries. This mechanism instead draws a
discrete relative-heading OFFSET to be reached and HELD -- a
position-tracking target, not a rate-tracking one -- so a 0-degree
offset is continuous with every other offset instead of a separate
bang-bang regime.

Per RESEARCH_RULES "Tests": mechanics, not measurements. The pure
reward-kernel math (Gaussian shape, hold-tolerance gate, default-off
bit-exactness, state accumulation) is tested against a minimal fake
env with no MuJoCo model at all (mirrors test_walk_persistence_bonus.
py's `_FakeGoal`/`_Env` pattern). A second, smaller group uses the
real env (mesh_mjx, mechanics only: cfg parsing / obs width / command
draw shape) to cover `walk_env_init.py`/`walk_task._sample_walk`
wiring that cannot be faked.
"""
from __future__ import annotations

import math

import pytest

from rl_move.sim import walk_reward_yaw as wry


class _FakeGoal:
    def __init__(self, yaw_offset_ref=0.0):
        self.yaw_offset_ref = yaw_offset_ref


def _make_env(cfg, dt=0.02, wz=0.0, yaw_offset_cmd=True):
    class _Env:
        pass
    e = _Env()
    e.cfg = cfg
    e.dt = dt
    e._yaw_offset_cmd = yaw_offset_cmd
    e._yaw_offset_achieved = 0.0
    e._body_wz = lambda: wz
    return e


# ---------------------------------------------------------------------
# Pure reward-kernel mechanics (no MuJoCo)
# ---------------------------------------------------------------------

def test_default_off_is_bit_exact_even_with_offset_cmd_flag():
    """Every reward key unset (k_walk_yaw_offset/_hold both 0.0/absent):
    reward is untouched and no info keys are written, EVEN THOUGH
    env._yaw_offset_cmd is True (the flag alone does not price
    anything -- only a nonzero k does)."""
    env = _make_env(cfg={}, wz=0.5)
    info = {}
    reward = wry.yaw_offset_kernel(env, _FakeGoal(0.3), info, 10.0)
    assert reward == pytest.approx(10.0 + 0.0)
    # the achieved accumulator still integrates (telemetry-only info
    # keys are written whenever the command flag is on); reward itself
    # gets no term from either gate.
    assert "reward_walk_yaw_offset" not in info
    assert "reward_walk_yaw_offset_hold" not in info


def test_yaw_offset_cmd_false_is_a_complete_noop():
    """env._yaw_offset_cmd False (the default): function returns
    reward unchanged instantly, no info keys, no state mutation --
    covers every pre-09-26 lineage."""
    env = _make_env(cfg={"reward": {"k_walk_yaw_offset": 5.0,
                                     "k_walk_yaw_offset_hold": 5.0}},
                     wz=0.5, yaw_offset_cmd=False)
    info = {}
    reward = wry.yaw_offset_kernel(env, _FakeGoal(0.3), info, 7.0)
    assert reward == 7.0
    assert info == {}
    assert env._yaw_offset_achieved == 0.0


def test_kernel_peaks_at_k_when_error_is_zero():
    """Achieved rotation exactly matches the target (err=0): the
    Gaussian kernel pays its full k (exp(0)=1)."""
    env = _make_env(cfg={"reward": {"k_walk_yaw_offset": 3.0}},
                     dt=1.0, wz=0.5)
    info = {}
    reward = wry.yaw_offset_kernel(env, _FakeGoal(0.5), info, 0.0)
    assert env._yaw_offset_achieved == pytest.approx(0.5)
    assert info["walk_yaw_offset_err"] == pytest.approx(0.0)
    assert reward == pytest.approx(3.0)
    assert info["reward_walk_yaw_offset"] == pytest.approx(3.0)


def test_kernel_decays_with_sigma_away_from_target():
    """A fixed remaining error pays less income at a NARROWER sigma
    (same shape as every other Gaussian kernel in this file)."""
    env_wide = _make_env(cfg={"reward": {
        "k_walk_yaw_offset": 1.0, "walk_yaw_offset_sigma_rad": 1.0}},
        dt=1.0, wz=0.0)
    info_wide = {}
    wry.yaw_offset_kernel(env_wide, _FakeGoal(1.0), info_wide, 0.0)

    env_narrow = _make_env(cfg={"reward": {
        "k_walk_yaw_offset": 1.0, "walk_yaw_offset_sigma_rad": 0.1}},
        dt=1.0, wz=0.0)
    info_narrow = {}
    wry.yaw_offset_kernel(env_narrow, _FakeGoal(1.0), info_narrow, 0.0)

    assert info_wide["walk_yaw_offset_err"] == pytest.approx(1.0)
    assert info_narrow["walk_yaw_offset_err"] == pytest.approx(1.0)
    assert (info_narrow["reward_walk_yaw_offset"]
            < info_wide["reward_walk_yaw_offset"])


def test_hold_bonus_pays_only_within_tolerance():
    """k_walk_yaw_offset_hold pays a flat bonus only while |err| <=
    the tolerance; outside it, nothing."""
    cfg = {"reward": {"k_walk_yaw_offset_hold": 4.0,
                       "walk_yaw_offset_tol_rad": 0.05}}
    # inside tolerance
    env_in = _make_env(cfg=cfg, dt=1.0, wz=0.0)
    info_in = {}
    r_in = wry.yaw_offset_kernel(env_in, _FakeGoal(0.02), info_in, 1.0)
    assert r_in == pytest.approx(5.0)
    assert info_in["reward_walk_yaw_offset_hold"] == pytest.approx(4.0)
    # outside tolerance
    env_out = _make_env(cfg=cfg, dt=1.0, wz=0.0)
    info_out = {}
    r_out = wry.yaw_offset_kernel(env_out, _FakeGoal(0.5), info_out, 1.0)
    assert r_out == pytest.approx(1.0)
    assert "reward_walk_yaw_offset_hold" not in info_out


def test_achieved_accumulates_across_ticks():
    """The privileged achieved-rotation accumulator is a running
    integral of env._body_wz()*dt across repeated calls (mirrors the
    _yaw_still_ema/_yaw_prog_ema EMA pattern's per-episode state)."""
    env = _make_env(cfg={"reward": {"k_walk_yaw_offset": 1.0}},
                     dt=0.5, wz=0.2)
    goal = _FakeGoal(1.0)
    for _ in range(3):
        wry.yaw_offset_kernel(env, goal, {}, 0.0)
    assert env._yaw_offset_achieved == pytest.approx(0.3)


def test_wrong_direction_rotation_widens_error_not_negative_kernel():
    """Rotating AWAY from the target grows |err|; the Gaussian kernel
    (never negative by construction) simply pays less, matching every
    other kernel term's shape in this file."""
    env = _make_env(cfg={"reward": {"k_walk_yaw_offset": 2.0}},
                     dt=1.0, wz=-0.3)
    info = {}
    reward = wry.yaw_offset_kernel(env, _FakeGoal(0.5), info, 0.0)
    assert info["walk_yaw_offset_err"] == pytest.approx(0.8)
    assert 0.0 <= reward < 2.0


# ---------------------------------------------------------------------
# Real-env wiring (cfg parsing, obs width, command draw) -- mesh_mjx,
# mechanics only, no rollout/measurement assertions.
# ---------------------------------------------------------------------

@pytest.fixture
def _mesh_mjx(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")


def _offset_env(monkeypatch, offset_set="", frac=0.0, seed=0):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    if offset_set:
        goal["walk_yaw_offset_set"] = offset_set
        goal["walk_yaw_offset_frac"] = frac
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


def test_default_unset_leaves_flag_off_and_obs_width_unchanged(
        monkeypatch):
    env_off = _offset_env(monkeypatch, offset_set="", seed=0)
    assert env_off._yaw_offset_cmd is False
    assert env_off._yaw_offset_set_rad == []
    w_off = env_off.observation_space.shape[0]
    env_off.close()

    env_on = _offset_env(monkeypatch, offset_set="15,30,45,90",
                          frac=0.0, seed=0)
    assert env_on._yaw_offset_cmd is True
    assert len(env_on._yaw_offset_set_rad) == 4
    assert env_on._yaw_offset_set_rad[0] == pytest.approx(
        math.radians(15))
    w_on = env_on.observation_space.shape[0]
    env_on.close()
    assert w_on == w_off + 2


def test_full_frac_draws_a_pure_offset_episode(monkeypatch):
    """walk_yaw_offset_frac=1.0: every reset zeroes the linear command
    and draws a nonzero target from the set (mechanics of the draw,
    not a trained-behavior measurement)."""
    env = _offset_env(monkeypatch, offset_set="30,-30", frac=1.0,
                       seed=1)
    for _ in range(3):
        env.reset()
        goal = env._current_goal()
        assert abs(float(goal.vx_ref)) < 1e-9
        assert abs(float(goal.vy_ref)) < 1e-9
        assert abs(float(goal.yaw_offset_ref)) == pytest.approx(
            math.radians(30))
    env.close()


def test_zero_frac_never_draws_despite_configured_set(monkeypatch):
    """A configured set with frac=0.0 never actually fires the draw
    (short-circuited by rng.random() < 0.0 always False) -- every
    episode's yaw_offset_ref stays at the WalkGoal default 0.0."""
    env = _offset_env(monkeypatch, offset_set="45", frac=0.0, seed=2)
    for _ in range(3):
        env.reset()
        goal = env._current_goal()
        assert float(goal.yaw_offset_ref) == 0.0
    env.close()
