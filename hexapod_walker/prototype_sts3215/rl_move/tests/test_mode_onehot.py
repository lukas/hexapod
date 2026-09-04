"""Explicit mode/command one-hot tests (obs.mode_onehot; RL_PLAN 2.4).

The flagship unified-policy MDP gives the policy the commanded skill
FAMILY as a direct input: a 6-wide one-hot (hold/rise/lower/walk/
turn/quad) appended at the tail of every obs frame. These tests lock:

1. default OFF = the obs contract of every existing checkpoint is
   untouched (width bit-exact);
2. ON = +6 dims, the right family bit for every goal-mix mode,
   constant across the episode, present in every history frame;
3. the mirror maps treat the one-hot as mirror-invariant and stay
   involutions at the widened layout.
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

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.mirror import (  # noqa: E402
    FRAME_WALK, frame_perm_sign, obs_perm_sign,
)
from rl_move.sim.walk_task import (  # noqa: E402
    MODE_ONEHOT_ORDER, N_MODE_OBS, SimHexapodJointWalkEnv, mode_onehot,
)

ALL_MODES = ("hold", "lean", "track", "unload", "raise",
             "rise", "lower", "walk", "quad")


def _make_env(mode: str | None = None, *, onehot: bool = True,
              hist: int = 1, seed: int = 0) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    if onehot:
        obs_cfg["mode_onehot"] = 1.0
    if hist != 1:
        obs_cfg["history_frames"] = hist
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    if mode is not None:
        g = env._goal_gen
        for m in ALL_MODES:
            if hasattr(g, f"p_{m}"):
                setattr(g, f"p_{m}", 0.0)
        setattr(g, f"p_{mode}", 1.0)
    return env


# ---------------------------------------------------------------------------
# The helper itself
# ---------------------------------------------------------------------------

def test_mode_onehot_families():
    exp = {"hold": "hold", "lean": "hold", "track": "hold",
           "unload": "hold", "raise": "rise", "rise": "rise",
           "lower": "lower", "walk": "walk", "quad": "quad"}
    for mode, fam in exp.items():
        v = mode_onehot(mode)
        assert v.sum() == 1.0
        assert v[MODE_ONEHOT_ORDER.index(fam)] == 1.0
    # unknown / missing -> hold (never lights a motion bit)
    assert mode_onehot("no_such_mode")[0] == 1.0
    # "turn" slot is reserved: no goal-mix mode maps onto it today
    turn = MODE_ONEHOT_ORDER.index("turn")
    for mode in ALL_MODES:
        assert mode_onehot(mode)[turn] == 0.0


# ---------------------------------------------------------------------------
# Env obs contract
# ---------------------------------------------------------------------------

def test_default_off_width_unchanged():
    env = _make_env(onehot=False)
    obs, _ = env.reset(seed=0)
    assert obs.shape == (FRAME_WALK,)
    assert env.observation_space.shape == (FRAME_WALK,)


def test_on_width_plus_six():
    env = _make_env("walk")
    obs, _ = env.reset(seed=0)
    assert obs.shape == (FRAME_WALK + N_MODE_OBS,)
    assert env.observation_space.shape == (FRAME_WALK + N_MODE_OBS,)


@pytest.mark.parametrize("mode,fam", [
    ("hold", "hold"), ("track", "hold"), ("unload", "hold"),
    ("raise", "rise"), ("rise", "rise"), ("lower", "lower"),
    ("walk", "walk"), ("quad", "quad"),
])
def test_mode_bit_matches_episode_mode(mode, fam):
    env = _make_env(mode, seed=1)
    obs, _ = env.reset(seed=1)
    want = np.zeros(N_MODE_OBS)
    want[MODE_ONEHOT_ORDER.index(fam)] = 1.0
    assert np.array_equal(obs[-N_MODE_OBS:], want), \
        f"reset obs tail wrong for mode {mode}"
    assert env._goal_traj.mode == mode
    # constant across the episode (the command, not a measurement)
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(5):
        obs, _, term, trunc, _ = env.step(a)
        assert np.array_equal(obs[-N_MODE_OBS:], want)
        if term or trunc:
            break


def test_history_frames_carry_mode_in_every_frame():
    env = _make_env("walk", hist=3, seed=2)
    obs, _ = env.reset(seed=2)
    w = FRAME_WALK + N_MODE_OBS
    assert obs.shape == (3 * w,)
    want = np.zeros(N_MODE_OBS)
    want[MODE_ONEHOT_ORDER.index("walk")] = 1.0
    for k in range(3):
        frame = obs[k * w:(k + 1) * w]
        assert np.array_equal(frame[-N_MODE_OBS:], want)


# ---------------------------------------------------------------------------
# Command-derived one-hot (obs.mode_onehot_cmd=1) — the multitask x arch
# transplant: on walk-family ticks the lit slot follows the LIVE blended
# command so DualGruActorCriticPolicy routes stop segments to the stance
# core on a walk-only command recipe.
# ---------------------------------------------------------------------------

HOLD_BIT = MODE_ONEHOT_ORDER.index("hold")
WALK_BIT = MODE_ONEHOT_ORDER.index("walk")


def _cmd_env(speed: float, *, cmd_flag: bool = True, yaw: bool = False,
             wz_max: float = 0.15, seed: int = 0):
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    obs_cfg["mode_onehot"] = 1.0
    if cmd_flag:
        obs_cfg["mode_onehot_cmd"] = 1.0
    g = cfg.setdefault("goal", {})
    g["walk_speed_min_m_s"] = speed
    g["walk_speed_max_m_s"] = speed
    g["walk_heading_max_rad"] = 0.0
    if yaw:
        g["walk_yaw_cmd"] = 1.0
        g["walk_yaw_zero_frac"] = 0.0
        g["walk_yaw_max_rad_s"] = wz_max
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    gen = env._goal_gen
    for m in ALL_MODES:
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_walk = 1.0
    return env


def _cmd_tail_tracks_goal(env, n_steps: int = 220):
    # 220 (not 80): the settle hold is 1.0/dt ticks (100 at the
    # mesh-era 100 Hz default, see walk_task.py hold_n) — 80 steps
    # never leaves the hold at all, a pre-existing gap from before the
    # 08-24 25->100 Hz default flip found while adding the
    # mode_onehot_turn_cmd tests below (same helper shape, same fix).
    """Step and assert the tail matches the stopped-predicate per tick.

    Returns (saw_hold, saw_walk) so callers can assert both routes
    were exercised.
    """
    eps_v, eps_w = 0.005, 0.02
    saw_hold = saw_walk = False
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    obs, _ = env.reset(seed=0)
    for _ in range(n_steps):
        goal = env._current_goal()
        vx = float(getattr(goal, "vx_ref", 0.0)) if goal else 0.0
        vy = float(getattr(goal, "vy_ref", 0.0)) if goal else 0.0
        wz = float(getattr(goal, "wz_ref", 0.0)) if goal else 0.0
        stopped = (abs(vx) <= eps_v and abs(vy) <= eps_v
                   and abs(wz) <= eps_w)
        tail = obs[-N_MODE_OBS:]
        want = np.zeros(N_MODE_OBS)
        want[HOLD_BIT if stopped else WALK_BIT] = 1.0
        assert np.array_equal(tail, want), \
            f"cmd ({vx:.4f},{vy:.4f},{wz:.4f}) stopped={stopped}, " \
            f"tail={tail}"
        saw_hold |= stopped
        saw_walk |= not stopped
        obs, _, term, trunc, _ = env.step(a)
        if term or trunc:
            break
    return saw_hold, saw_walk


def test_cmd_flag_off_walk_bit_constant_during_settle():
    # Bit-exact-off contract: without obs.mode_onehot_cmd a walk
    # episode lights "walk" from the very first (zero-command settle)
    # tick — the pre-change behavior.
    env = _cmd_env(0.05, cmd_flag=False)
    obs, _ = env.reset(seed=0)
    assert obs[-N_MODE_OBS:][WALK_BIT] == 1.0


def test_cmd_flag_routes_settle_to_hold_then_ramp_to_walk():
    env = _cmd_env(0.05)
    saw_hold, saw_walk = _cmd_tail_tracks_goal(env)
    # Settle hold (1 s at zero command) must route to the stance slot,
    # the ramped command to the locomotion slot.
    assert saw_hold and saw_walk


def test_cmd_flag_zero_command_stays_hold():
    env = _cmd_env(0.0)
    saw_hold, saw_walk = _cmd_tail_tracks_goal(env)
    assert saw_hold and not saw_walk


def test_cmd_flag_turn_in_place_routes_to_walk():
    # Zero linear speed but a live yaw command: turn-in-place is a
    # locomotion-core behavior (walk/turn/quad are all core A).
    env = _cmd_env(0.0, yaw=True)
    saw_hold, saw_walk = _cmd_tail_tracks_goal(env)
    assert saw_hold and saw_walk


def test_cmd_flag_non_walk_modes_unchanged():
    for mode, fam in (("hold", "hold"), ("rise", "rise"),
                      ("lower", "lower")):
        cfg = load_config()
        obs_cfg = cfg.setdefault("obs", {})
        obs_cfg["mode_onehot"] = 1.0
        obs_cfg["mode_onehot_cmd"] = 1.0
        env = SimHexapodJointWalkEnv(cfg, seed=3)
        gen = env._goal_gen
        for m in ALL_MODES:
            if hasattr(gen, f"p_{m}"):
                setattr(gen, f"p_{m}", 0.0)
        setattr(gen, f"p_{mode}", 1.0)
        obs, _ = env.reset(seed=3)
        want = np.zeros(N_MODE_OBS)
        want[MODE_ONEHOT_ORDER.index(fam)] = 1.0
        assert np.array_equal(obs[-N_MODE_OBS:], want)


# ---------------------------------------------------------------------------
# Mirror maps at the widened layout
# ---------------------------------------------------------------------------

def test_mirror_maps_mode_onehot():
    perm, sign = frame_perm_sign(walk=True, mode_onehot=True)
    assert len(perm) == FRAME_WALK + N_MODE_OBS
    # tail block: identity perm, +1 sign (mirror-invariant command)
    tail = np.arange(FRAME_WALK, FRAME_WALK + N_MODE_OBS)
    assert np.array_equal(perm[FRAME_WALK:], tail)
    assert np.all(sign[FRAME_WALK:] == 1.0)
    # still an involution, incl. with yaw/phase/history composed
    for kw in (dict(), dict(yaw_cmd=True, phase_obs=True)):
        p, s = obs_perm_sign(walk=True, mode_onehot=True,
                             history_frames=4, **kw)
        x = np.random.default_rng(3).normal(size=len(p))
        y = s * x[p]
        assert np.allclose(s * y[p], x)


# ---------------------------------------------------------------------------
# Pure-turn command-derived slot (obs.mode_onehot_turn_cmd=1; 09-04,
# standwalk item-2 escalation). Un-reserves MODE_ONEHOT_ORDER's "turn"
# slot: on a walk-family tick, a LIVE command with |vx_ref|,|vy_ref|
# <=1e-3 and |wz_ref|>1e-3 lights "turn" instead of "walk". Independent
# knob from mode_onehot_cmd (which only ever distinguishes hold/walk).
# ---------------------------------------------------------------------------

TURN_BIT = MODE_ONEHOT_ORDER.index("turn")


def _turn_cmd_env(*, turn_flag: bool = True, cmd_flag: bool = False,
                  seed: int = 0):
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    obs_cfg["mode_onehot"] = 1.0
    if turn_flag:
        obs_cfg["mode_onehot_turn_cmd"] = 1.0
    if cmd_flag:
        obs_cfg["mode_onehot_cmd"] = 1.0
    g = cfg.setdefault("goal", {})
    g["walk_yaw_cmd"] = 1.0
    g["walk_turn_in_place_frac"] = 1.0  # every episode: whole-episode
                                        # pure turn after the settle hold
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    gen = env._goal_gen
    for m in ALL_MODES:
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_walk = 1.0
    return env


def _turn_cmd_tail_tracks_goal(env, n_steps: int = 220):
    saw_turn = saw_walk = False
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    obs, _ = env.reset(seed=0)
    for _ in range(n_steps):
        goal = env._current_goal()
        vx = float(getattr(goal, "vx_ref", 0.0)) if goal else 0.0
        vy = float(getattr(goal, "vy_ref", 0.0)) if goal else 0.0
        wz = float(getattr(goal, "wz_ref", 0.0)) if goal else 0.0
        import math as _math
        pure_turn = (_math.hypot(vx, vy) <= 1e-3 and abs(wz) > 1e-3)
        tail = obs[-N_MODE_OBS:]
        want = np.zeros(N_MODE_OBS)
        want[TURN_BIT if pure_turn else WALK_BIT] = 1.0
        assert np.array_equal(tail, want), \
            f"cmd ({vx:.4f},{vy:.4f},{wz:.4f}) pure_turn={pure_turn}, " \
            f"tail={tail}"
        saw_turn |= pure_turn
        saw_walk |= not pure_turn
        obs, _, term, trunc, _ = env.step(a)
        if term or trunc:
            break
    return saw_turn, saw_walk


def test_turn_cmd_flag_off_bit_exact():
    # Bit-exact-off: without mode_onehot_turn_cmd a dedicated
    # turn-in-place episode still lights plain "walk" throughout
    # (the pre-change behavior) and the "turn" bit is never lit.
    env = _turn_cmd_env(turn_flag=False)
    obs, _ = env.reset(seed=0)
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(220):
        assert obs[-N_MODE_OBS:][TURN_BIT] == 0.0
        obs, _, term, trunc, _ = env.step(a)
        if term or trunc:
            break


def test_turn_cmd_flag_lights_turn_during_turn_in_place():
    env = _turn_cmd_env(turn_flag=True)
    saw_turn, saw_walk = _turn_cmd_tail_tracks_goal(env)
    # settle hold (zero command) reads pure_turn=False (wz==0) -> walk;
    # once the turn-in-place ramp reaches nonzero wz -> turn.
    assert saw_turn and saw_walk


def test_turn_cmd_flag_non_walk_modes_unchanged():
    for mode, fam in (("hold", "hold"), ("rise", "rise"),
                      ("lower", "lower")):
        cfg = load_config()
        obs_cfg = cfg.setdefault("obs", {})
        obs_cfg["mode_onehot"] = 1.0
        obs_cfg["mode_onehot_turn_cmd"] = 1.0
        env = SimHexapodJointWalkEnv(cfg, seed=3)
        gen = env._goal_gen
        for m in ALL_MODES:
            if hasattr(gen, f"p_{m}"):
                setattr(gen, f"p_{m}", 0.0)
        setattr(gen, f"p_{mode}", 1.0)
        obs, _ = env.reset(seed=3)
        want = np.zeros(N_MODE_OBS)
        want[MODE_ONEHOT_ORDER.index(fam)] = 1.0
        assert np.array_equal(obs[-N_MODE_OBS:], want)


def test_turn_cmd_flag_combined_tick_stays_walk():
    # Both a nonzero linear command AND a nonzero yaw command lit at
    # once (a "combined" tick, the bc_anchor_walk_combined_dose family's
    # own tick class) must NOT light "turn" -- only PURE turn does.
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    obs_cfg["mode_onehot"] = 1.0
    obs_cfg["mode_onehot_turn_cmd"] = 1.0
    g = cfg.setdefault("goal", {})
    g["walk_speed_min_m_s"] = 0.08
    g["walk_speed_max_m_s"] = 0.08
    g["walk_heading_max_rad"] = 0.0
    g["walk_yaw_cmd"] = 1.0
    g["walk_yaw_zero_frac"] = 0.0
    g["walk_yaw_max_rad_s"] = 0.25
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    gen = env._goal_gen
    for m in ALL_MODES:
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_walk = 1.0
    obs, _ = env.reset(seed=0)
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    saw_combined = False
    for _ in range(220):
        goal = env._current_goal()
        vx = float(getattr(goal, "vx_ref", 0.0)) if goal else 0.0
        vy = float(getattr(goal, "vy_ref", 0.0)) if goal else 0.0
        wz = float(getattr(goal, "wz_ref", 0.0)) if goal else 0.0
        import math as _math
        if _math.hypot(vx, vy) > 1e-3 and abs(wz) > 1e-3:
            saw_combined = True
            assert obs[-N_MODE_OBS:][TURN_BIT] == 0.0
            assert obs[-N_MODE_OBS:][WALK_BIT] == 1.0
        obs, _, term, trunc, _ = env.step(a)
        if term or trunc:
            break
    assert saw_combined, "test setup never produced a combined tick"


def test_turn_cmd_flag_precedence_under_mode_onehot_cmd():
    # Documented precedence when BOTH flags are set: mode_onehot_cmd's
    # hold/walk stop-detection takes priority (checked first), so the
    # turn bit is never lit in that combination today -- no run in
    # this family sets both, but pin the behavior so a future change
    # is a deliberate decision, not a silent reshuffle.
    env = _turn_cmd_env(turn_flag=True, cmd_flag=True)
    obs, _ = env.reset(seed=0)
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(220):
        assert obs[-N_MODE_OBS:][TURN_BIT] == 0.0
        obs, _, term, trunc, _ = env.step(a)
        if term or trunc:
            break
