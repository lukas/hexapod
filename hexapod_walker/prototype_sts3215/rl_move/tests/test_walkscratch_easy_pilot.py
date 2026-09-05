"""WALKSCRATCH_EASY bank + mechanism tests (operator focus note 2026-09-05).

Operator-authorized bounded teacher-free walking restart: walkcurr is
reopened for ONE easy-simulation pilot cohort
(cw-walkscratch-easy0905-{base-s0,base-s1,sde-s0,halfgrav-s0}).  This
file is the pre-launch proof the focus note demands, against the EXACT
resolved recipe (mesh_mjx twin, 100 Hz, easy physics, no-hold forward
command, freeprog k=2/cap 0.06 income diet):

- the new ``goal.walk_cmd_hold_s``/``goal.walk_cmd_ramp_s`` keys are
  default-preserving (legacy 1 s hold + 1 s ramp bit-exact) and, at 0,
  put the full command on from tick 0 — killing the ~K_WALK/tick
  opening-stop windfall every prior from-scratch arm banked;
- the easy-physics overrides actually resolve: zero servo latency /
  deadband / sensor noise, 3x torque headroom, 360 deg/s velocity
  ceiling + 3.6 deg/tick slew (no hidden 35 deg/s cruise limiter),
  struct compliance off, degenerate DR = identical sampled dynamics,
  half gravity only in the halfgrav arm via ease.gravity_scale;
- the stance-centered action box has its center on the TRUE settled
  plant (bias 0/40/35 -> yaw 0 / hip 20 / knee_abs 100; the old
  bias-15 comment's knee 80 predates the 09-02 robot_abs frame
  unification and is ~20 deg off the real plant) and a zero-action
  reset is stable (no termination, no belly-sink, ~zero income);
- the reward bank ranks behaviors the way discovery needs: real travel
  out-earns every stationary form, stationary income is pose-invariant
  and ~0, wrong-way travel is charged below standing, dying is the
  strict floor, income is monotone in travel.

Teacher/scripted trajectories are used ONLY as offline reward-bank
comparators here (operator boundary), never as training input.

Runtime note: the bank steps the mesh twin on CPU; module-scoped
fixtures keep it to one rollout set. Mark: not in the calibrated
primitive suite's fast path — run explicitly before launching the
pilot arms.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD

SEEDS = (0, 1)
CMD_VX = 0.06
EPISODE_S = 10.0

# --- the EXACT pilot recipe (mirrors the launch --cfg-set list) -------
EASY_BASE = {
    ("env", "model_source"): "mesh_mjx",
    ("control", "hz"): 100,
    ("goal", "walk_pure"): 1.0,
    ("goal", "walk_speed_min_m_s"): CMD_VX,
    ("goal", "walk_speed_max_m_s"): CMD_VX,
    ("goal", "walk_heading_max_rad"): 0.0,
    ("goal", "walk_cmd_resample_s"): 0.0,
    ("goal", "walk_cmd_hold_s"): 0.0,
    ("goal", "walk_cmd_ramp_s"): 0.0,
    # reward diet: freeprog income (near-raw velocity, 0.1 s EMA),
    # fall termination, mild action-delta smoothness, nothing else
    ("reward", "k_walk_freeprog"): 2.0,
    ("reward", "walk_freeprog_cap_m_s"): CMD_VX,
    ("reward", "walk_kernel_vel_ema"): 1.0,
    ("reward", "walk_kernel_vel_tau_s"): 0.1,
    ("reward", "term_penalty"): 24.0,
    # tilt/safety trips are priced by THIS key (flat, default 10), not
    # term_penalty — pinned to the same 24 so dying is decisively bad
    ("reward", "safety_termination_penalty"): 24.0,
    ("reward", "k_track"): 0.0,
    ("reward", "k_roll"): 0.0,
    ("reward", "k_pitch"): 0.0,
    ("reward", "k_height"): 0.0,
    ("reward", "k_gyro"): 0.0,
    ("reward", "k_action"): 0.0,
    ("reward", "k_action_delta"): 0.01,
    ("reward", "k_current"): 0.0,
    ("reward", "k_walk_heading"): 0.0,
    ("reward", "k_step_event"): 0.0,
    ("reward", "k_park_duty"): 0.0,
    ("reward", "k_walk_idle_charge"): 0.0,
    ("reward", "k_loadslip_excess"): 0.0,
    # easy actuator/bus/safety: no latency/deadband/noise, generous
    # torque + speed, wide (but finite) tilt trip, current trip inert
    ("bus", "write_speed"): 4096.0,
    ("bus", "servo_vel_max_counts_s"): "write_speed",
    ("bus", "write_acc"): 1000.0,
    ("safety", "max_delta_q_deg"): 3.6,
    ("safety", "max_current_a"): 100.0,
    ("safety", "max_roll_deg"): 30.0,
    ("safety", "max_pitch_deg"): 30.0,
    ("struct_comp", "enabled"): 0.0,
    ("dr", "latency_scale"): (0.0, 0.0),
    ("dr", "deadband_scale"): (0.0, 0.0),
    ("dr", "torque_scale"): (3.0, 3.0),
    ("dr", "encoder_noise_deg"): 0.0,
    ("dr", "tilt_noise_deg"): 0.0,
    ("dr", "gyro_noise_deg_s"): 0.0,
}

# Stance-centered action box (mechanism-test only; the reward bank runs
# on the full-range mapping because reward semantics are action-
# coordinate independent apart from the 0.01 action-delta term).
EASY_BOX = {
    ("goal", "joint_action_bias_hip_deg"): 40.0,
    # knee bias 35, NOT the joint_task comment's 15: since the 09-02
    # robot_abs unification the axis frame is absolute-tibia, so the
    # canonical settled plant is knee_abs ~100 = center 65 + 35.
    # Empirically verified below (test_box_center_is_settled_plant).
    ("goal", "joint_action_bias_knee_deg"): 35.0,
    ("goal", "joint_action_box_yaw_deg"): 15.0,
    ("goal", "joint_action_box_hip_deg"): 20.0,
    ("goal", "joint_action_box_knee_deg"): 25.0,
}


def _make_env(seed: int, overrides: dict, episode_seconds: float = EPISODE_S,
              randomize: bool = True):
    import os

    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for (sec, leaf), val in overrides.items():
        cfg.setdefault(sec, {})[leaf] = val
    params = SimServoParams.from_cfg(cfg)
    # conftest.py pins HEXAPOD_MODEL_SOURCE=primitive for the calibrated
    # legacy suite, and the env var OVERRIDES cfg inside
    # resolve_model_source — without this scope the whole bank would
    # silently run on the wrong model family. The pilot trains on the
    # checked-in mesh twin, so that is what we prove against.
    prev = os.environ.get("HEXAPOD_MODEL_SOURCE")
    os.environ["HEXAPOD_MODEL_SOURCE"] = str(
        overrides.get(("env", "model_source"), "mesh_mjx"))
    try:
        env = SimHexapodJointWalkEnv(
            params=params, randomize=randomize, dr_scale=0.0,
            episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    finally:
        if prev is None:
            os.environ.pop("HEXAPOD_MODEL_SOURCE", None)
        else:
            os.environ["HEXAPOD_MODEL_SOURCE"] = prev
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


# ---------------------------------------------------------------------
# hold/ramp keys: default preservation + no-hold behavior
# ---------------------------------------------------------------------

def test_legacy_hold_ramp_default_bit_exact():
    base = {k: v for k, v in EASY_BASE.items()
            if k not in (("goal", "walk_cmd_hold_s"),
                         ("goal", "walk_cmd_ramp_s"))}
    legacy = dict(base)
    legacy[("goal", "walk_cmd_hold_s")] = -1.0
    legacy[("goal", "walk_cmd_ramp_s")] = -1.0
    e0 = _make_env(7, base)
    e1 = _make_env(7, legacy)
    e0.reset()
    e1.reset()
    t0, t1 = e0._goal_traj, e1._goal_traj
    assert np.array_equal(t0.vx, t1.vx) and np.array_equal(t0.vy, t1.vy), \
        "explicit -1 must be bit-exact with the absent-key legacy path"
    hold_n = int(round(1.0 / e0.dt))
    assert np.all(t0.vx[:hold_n] == 0.0), "legacy 1 s zero-hold missing"
    assert t0.vx[-1] == pytest.approx(CMD_VX), "legacy final command wrong"
    # the ramp is strictly between 0 and the target somewhere
    mid = t0.vx[hold_n:2 * hold_n]
    assert np.any((mid > 0.0) & (mid < CMD_VX)), "legacy 1 s ramp missing"


def test_easy_command_active_from_tick0():
    env = _make_env(0, EASY_BASE)
    env.reset()
    traj = env._goal_traj
    assert np.all(traj.vx == pytest.approx(CMD_VX)), \
        "hold_s=0/ramp_s=0 must put the full forward command on at tick 0"
    assert np.all(traj.vy == 0.0)


# ---------------------------------------------------------------------
# easy-physics mechanism resolution
# ---------------------------------------------------------------------

def test_easy_mechanisms_resolved():
    from rl_move.sim.servo_model import SimServoParams, motor_contract

    env = _make_env(0, EASY_BASE)
    env.reset()
    er = env._ep_rand
    assert er is not None, "dr-scale 0 must keep the randomizer alive"
    assert er.latency_scale == 0.0, "servo latency not removed"
    assert er.deadband_scale == 0.0, "servo deadband not removed"
    assert er.torque_scale == 3.0, "torque headroom override missing"
    assert er.encoder_noise_rad == 0.0
    assert er.tilt_noise_rad == 0.0
    assert er.gyro_noise_rad_s == 0.0
    # 3x torque reaches the actuator forcerange
    assert float(np.max(env.model.actuator_forcerange)) == pytest.approx(
        3.0 * 2.2, abs=1e-6)
    # gravity nominal in the base arms
    assert float(env.model.opt.gravity[2]) == pytest.approx(-9.80665,
                                                            abs=1e-6)
    # structural compliance off
    assert env._struct_comp is None
    # velocity ceiling lifted to the bus write speed (360 deg/s)
    cfg = load_config()
    for (sec, leaf), val in EASY_BASE.items():
        cfg.setdefault(sec, {})[leaf] = val
    c = motor_contract(cfg, params=SimServoParams.from_cfg(cfg))
    assert c["resolved_vel_max_deg_s_min"] == pytest.approx(360.0, abs=1.0)
    assert c["slew_limit_deg_s"] == pytest.approx(360.0, abs=1.0)
    # degenerate ranges: consecutive resets sample identical dynamics
    keys = ("latency_scale", "deadband_scale", "torque_scale",
            "friction_scale", "mass_scale", "contact_stiff_scale")
    first = {k: getattr(er, k) for k in keys}
    env.reset()
    er2 = env._ep_rand
    for k in keys:
        assert getattr(er2, k) == first[k], (
            f"episode dynamics not deterministic at dr-scale 0: {k}")


def test_halfgrav_arm_scales_gravity_only():
    hg = dict(EASY_BASE)
    hg[("ease", "gravity_scale")] = 0.5
    env = _make_env(0, hg)
    env.reset()
    assert float(env.model.opt.gravity[2]) == pytest.approx(
        -0.5 * 9.80665, rel=1e-6), "ease.gravity_scale=0.5 did not apply"
    # everything else identical to base
    assert env._ep_rand.latency_scale == 0.0
    assert env._ep_rand.torque_scale == 3.0


def test_easy_slew_no_hidden_cruise_limiter():
    env = _make_env(1, {**EASY_BASE, **EASY_BOX})
    env.reset()
    a = np.zeros(env.n_act)
    a[2::3] = 1.0          # all knees to the +box edge (+25 deg)
    qprev = env._state.joint_position.copy()
    max_dq_deg = 0.0
    for _ in range(20):
        env.step(a)
        q = env._state.joint_position
        max_dq_deg = max(max_dq_deg,
                         float(np.degrees(np.abs(q - qprev)).max()))
        qprev = q.copy()
    speed_deg_s = max_dq_deg / env.dt
    assert speed_deg_s > 150.0, (
        f"hidden velocity limiter: peak joint speed {speed_deg_s:.0f} "
        "deg/s (loaded-fit cruise is ~35-37 deg/s; easy recipe wants "
        "~360)")


# ---------------------------------------------------------------------
# stance-centered box + stable zero-action reset, windfall removal
# ---------------------------------------------------------------------

def test_box_center_is_settled_plant_and_zero_action_stable():
    env = _make_env(0, {**EASY_BASE, **EASY_BOX})
    env.reset()
    center_deg = np.degrees(env._joint_action_box_center)
    assert center_deg[0] == pytest.approx(0.0, abs=1e-6)
    assert center_deg[1] == pytest.approx(20.0, abs=1e-6)
    assert center_deg[2] == pytest.approx(100.0, abs=1e-6), (
        "knee center must be the robot_abs plant (~100), not the stale "
        "relative-frame 80")
    # center within ~15 deg of the actually settled stance (hip sags
    # under gravity with finite kp: ~8 deg on the 3.49 kg twin, ~12 deg
    # on the committed as-built 4.81 kg twin the pods actually load)
    q_nom_deg = np.degrees(env._q_nom)
    assert float(np.max(np.abs(center_deg - q_nom_deg))) < 15.0, (
        f"action center far from settled stance: center={center_deg[:3]} "
        f"settled={q_nom_deg[:3]}")
    # zero action = hold the stance: stable, no income, no termination
    z0 = float(env.data.xpos[env._chassis_bid, 2])
    tot, n = 0.0, 200
    for _ in range(n):
        obs, r, done, trunc, info = env.step(np.zeros(env.n_act))
        tot += r
        assert not (done or trunc), "zero-action reset terminated"
    z1 = float(env.data.xpos[env._chassis_bid, 2])
    assert abs(z1 - z0) < 0.03, f"zero-action height drift {z1 - z0:.3f} m"
    assert abs(tot / n) < 0.1, (
        f"zero-action stance is not income-neutral: {tot / n:+.3f}/tick")


def test_opening_stop_windfall_removed():
    """Under the legacy hold/ramp the K_WALK kernel pays ~2/tick for
    standing still during the opening stop; the pilot recipe must not."""
    legacy = dict(EASY_BASE)
    legacy[("goal", "walk_cmd_hold_s")] = -1.0
    legacy[("goal", "walk_cmd_ramp_s")] = -1.0

    def park_return_2s(overrides):
        env = _make_env(2, overrides)
        env.reset()
        tot = 0.0
        for _ in range(200):
            obs, r, done, trunc, info = env.step(np.zeros(env.n_act))
            tot += r
            if done or trunc:
                break
        return tot

    windfall = park_return_2s(legacy)
    easy = park_return_2s(EASY_BASE)
    assert windfall > 50.0, (
        f"legacy windfall probe broken (expected ~+200): {windfall:.1f}")
    assert easy < 5.0, (
        f"opening-stop windfall not removed: park still earns "
        f"{easy:.1f} in 2 s")


# ---------------------------------------------------------------------
# WALKSCRATCH_EASY reward bank (exact diet, mesh twin, easy physics)
# ---------------------------------------------------------------------

def _q_to_action(env, q_rad: np.ndarray) -> np.ndarray:
    from rl_move.sim.joint_task import q_rad_to_action
    if env._joint_action_box_active:
        return np.clip((np.asarray(q_rad, float)
                        - env._joint_action_box_center)
                       / env._joint_action_box_rad, -1.0, 1.0)
    return q_rad_to_action(q_rad)


def _easy_rollout(policy: str, seed: int, *, gait_scale: float = 1.0,
                  overrides: dict | None = None
                  ) -> tuple[float, float, int]:
    """(return, net forward travel m, steps) for a scripted behavior
    twin under the exact pilot diet. Twins mirror
    test_task_semantics._slipwalk_rollout (same poses, robot_abs)."""
    # Independent Codex review: env.step and WALK_PLANT use robot_abs;
    # the legacy sim_gait_compat wrapper returns relative knees.
    from hexapod_core.tripod_gait import TripodGait
    from rl_move.sim.probe_walk_income import WALK_PLANT

    env = _make_env(seed, overrides if overrides is not None else EASY_BASE)
    env.reset()
    traj = env._goal_traj
    assert np.all(traj.vx == pytest.approx(CMD_VX)), \
        "easy recipe must command full speed from tick 0"

    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(*WALK_PLANT)
    plant_rad = np.array([0.0, *WALK_PLANT] * 6) * DEG2RAD
    # -80/-80 front-pair fold: the legacy -50 fold only reaches ~21 deg
    # roll on the mesh twin under easy physics and NEVER trips the
    # widened 30 deg envelope (probe 09-05); -80 trips tilt_roll ~0.5 s.
    topple_rad = plant_rad.copy()
    for leg in (0, 1):
        topple_rad[3 * leg + 1] -= 80.0 * DEG2RAD
        topple_rad[3 * leg + 2] -= 80.0 * DEG2RAD
    bellysit_rad = np.array([0.0, 20.0, 175.0] * 6) * DEG2RAD

    x0 = float(env.data.xpos[env._chassis_bid, 0])
    total, step = 0.0, 0
    n = len(traj.vx)
    while True:
        t = step * env.dt
        i = min(step, n - 1)
        if policy in ("gait", "reverse", "sideways"):
            vx = float(traj.vx[i]) * gait_scale
            if policy == "reverse":
                gait.set_velocity(vx=-vx, vy=0.0)
            elif policy == "sideways":
                gait.set_velocity(vx=0.0, vy=vx)
            else:
                gait.set_velocity(vx=vx, vy=0.0)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "stall":
            gait.set_velocity(vx=0.0, vy=0.0)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "belly_sit":
            q = bellysit_rad
        elif policy == "topple":
            q = topple_rad
        elif policy == "sprint_fall":
            # The cw-walkscratch-easy0905-sdehalfgrav-{s0,s1} 40M
            # exploit twin (09-05 dig-in): ballistic forward lurch at
            # ~3x the command (observed v_along 0.19-0.29 m/s, income
            # capped at 2/tick) for ~0.7 s, then pitch over and
            # tilt-terminate — banking the burst income while paying
            # only the flat death price.
            if t < 0.7:
                gait.set_velocity(vx=float(traj.vx[i]) * gait_scale,
                                  vy=0.0)
                q = np.asarray(gait.desired_deg(t)) * DEG2RAD
            else:
                q = topple_rad
        else:                       # park
            q = plant_rad
        obs, r, done, trunc, info = env.step(_q_to_action(env, q))
        total += r
        step += 1
        if done or trunc:
            break
    dx = float(env.data.xpos[env._chassis_bid, 0]) - x0
    return total, dx, step


@pytest.fixture(scope="module")
def easy_returns() -> dict[str, float]:
    plan = {
        "fast": ("gait", 2.0),
        "gait": ("gait", 1.0),
        "creep": ("gait", 0.5),
        "crawl": ("gait", 0.25),
        "park": ("park", 1.0),
        "stall": ("stall", 1.0),
        "belly_sit": ("belly_sit", 1.0),
        "reverse": ("reverse", 1.0),
        "sideways": ("sideways", 1.0),
        "topple": ("topple", 1.0),
    }
    out = {}
    for name, (pol, scale) in plan.items():
        runs = [_easy_rollout(pol, s, gait_scale=scale) for s in SEEDS]
        out[name] = float(np.mean([r[0] for r in runs]))
        out[name + "_dx"] = float(np.mean([r[1] for r in runs]))
        out[name + "_steps"] = float(np.mean([r[2] for r in runs]))
    return out


def test_easy_travel_beats_every_stationary_form(easy_returns):
    gait = easy_returns["gait"]
    for still in ("park", "stall", "belly_sit"):
        assert gait > easy_returns[still] + 25.0, (
            f"stationary '{still}' competitive with walking under the "
            f"easy diet: {easy_returns}")
    assert easy_returns["gait_dx"] > 0.10, (
        "reference gait did not travel; bank probe broken")


def test_easy_no_stationary_pose_out_earns_park(easy_returns):
    """No statue shape may EARN more than holding the stance (a stray
    default-on term would show up here).  A statue being mildly CHARGED
    below park is fine and real: on the 4.81 kg twin the belly-sit twin
    drifts ~9 mm backward while sinking and pays the freeprog
    wrong-way charge (~-43/10 s) — that is priced motion, not a pose
    subsidy."""
    park = easy_returns["park"]
    for still in ("stall", "belly_sit"):
        assert easy_returns[still] < park + 10.0, (
            f"stationary '{still}' out-earns park: {easy_returns}")
        assert easy_returns[still] > park - 80.0, (
            f"stationary '{still}' absurdly charged: {easy_returns}")
    assert abs(park) < 25.0, (
        f"park income far from 0 under the no-windfall diet: {park:.1f}")


def test_easy_wrong_way_below_standing(easy_returns):
    floor = min(easy_returns["park"], easy_returns["stall"])
    for wrong in ("reverse", "sideways"):
        assert floor > easy_returns[wrong] + 10.0, (
            f"wrong-way '{wrong}' out-earns standing: {easy_returns}")


def test_easy_dying_is_priced_below_park(easy_returns):
    """Termination pricing (flat safety_termination_penalty=24):
    die-early must never beat standing.  MEASURED 09-05 on the
    committed 4.81 kg twin: NO static fold can exceed ~26.5 deg tilt
    (the chassis catches the ground first), so at the pilot's widened
    30 deg envelope static leans never terminate — only dynamic falls
    can.  The scripted topple twin therefore proves the trip + penalty
    pathway under a test-scoped 20 deg envelope (same diet otherwise);
    the pilot's own 30 deg headroom is an exploration choice, recorded
    in the launch notes.  Wrong-way marathons are not in the floor set:
    at k_freeprog=2 they are charged ~-2000/10 s, which no agent
    sustains — park > topple is what blocks escape-by-death."""
    ov = dict(EASY_BASE)
    ov[("safety", "max_roll_deg")] = 20.0
    ov[("safety", "max_pitch_deg")] = 20.0
    tot, dx, steps = _easy_rollout("topple", 0, overrides=ov)
    assert steps < 400, (
        f"topple twin did not terminate under the 20 deg probe "
        f"envelope: steps={steps}")
    assert tot < easy_returns["park"] - 15.0, (
        f"dying is not priced below park: topple={tot:.1f} "
        f"park={easy_returns['park']:.1f}")
    # at the pilot envelope the same fold survives as a charged lean
    assert easy_returns["topple_steps"] >= 400, (
        "expected the static fold to survive the 30 deg pilot envelope "
        f"(measured max ~26.5 deg): {easy_returns['topple_steps']}")


def test_easy_more_travel_earns_more_below_cap(easy_returns):
    """Income must be monotone in real travel BELOW the 0.06 m/s cap
    (the discovery gradient). ABOVE the cap it deliberately rolls off
    (along-income saturates while cross-sway/action-delta charges keep
    growing — measured 09-05: 0.058 m/s ~ +1480, 0.099 m/s ~ +1365,
    0.18 m/s ~ +960): the cap equals the command, so overspeed is
    mildly discouraged, never rewarded. What matters is that even the
    2x overspeed twin still earns hugely more than any stationary or
    wrong-way form — there is no rolloff path back to parking."""
    # below/at cap: crawl ~0.029 m/s, creep ~0.058 m/s (measured);
    # the 1.0x twin already overshoots the cap (~0.099 m/s) and lives
    # on the rolloff, so it is asserted via the overspeed floor below.
    assert (easy_returns["creep"] > easy_returns["crawl"]
            > easy_returns["park"] + 25.0), (
        f"below-cap travel income not monotone: {easy_returns}")
    for over in ("gait", "fast"):
        assert easy_returns[over] > easy_returns["park"] + 400.0, (
            f"overspeed rolloff approaches parking income: {easy_returns}")


def test_easy_box_gait_still_travels_and_out_earns_park():
    """The tight stance box must not strangle the reference gait: the
    same scripted tripod, expressed in box coordinates, still travels
    and still out-earns holding the stance."""
    ov = {**EASY_BASE, **EASY_BOX}
    g_tot, g_dx, _ = _easy_rollout("gait", 0, overrides=ov)
    p_tot, p_dx, _ = _easy_rollout("park", 0, overrides=ov)
    assert g_dx > 0.10, f"in-box gait barely travels: {g_dx:.3f} m"
    assert g_tot > p_tot + 25.0, (
        f"in-box gait does not out-earn park: gait={g_tot:.1f} "
        f"park={p_tot:.1f}")


# ---------------------------------------------------------------------
# SURVIVAL-DURATION pricing fix (09-05 dig-in: sdehalfgrav-{s0,s1}
# sprint-then-fall exploit — flat 24 death price is an order of
# magnitude below a capped-income burst's take)
# ---------------------------------------------------------------------
# Root-cause chain: the sde x halfgrav cell (2/4 seeds by 40M) learned
# a ~0.7 s ballistic lurch (v_along 0.19-0.29 m/s, freeprog income
# capped at 2/tick) into a tilt_pitch death: ep_len collapsed to a
# 65-84-tick plateau while per-episode reward climbed -222 -> -5.6 —
# the one-time -24 charge never outweighs the burst income, so death
# is a paid reset button.  Fix: reward.term_cost_per_remaining_s
# (08-15 mechanism, "a drag-then-fall cannot bank income a survivor
# would have kept earning") prices EARLY death in proportion to the
# survival time forfeited, with reward.term_cost_max bounding the
# terminal charge for critic sanity (08-17).  reward.alive is REJECTED
# for this diet: a per-tick alive bonus re-prices the park/statue
# basin (15+ walkcurr run classes converged there) from ~0 to strongly
# positive — the documented "freeze and collect" class.  Both keys are
# default-off and bit-exact for behaviors that survive to truncation.
#
# Sizing (training episodes 5 s / 500 ticks @ 100 Hz): death at t
# costs 24 + min(100*(5-t), 450).  Observed burst deaths (0.65-0.85 s)
# are charged ~444-464 vs a burst-take ceiling of 2/tick * ~85 = 170
# (>2.5x margin); the charge decays toward the flat 24 near
# truncation, so a stumble while genuinely walking out stays cheap.
EASY_REMCOST = {
    ("reward", "term_cost_per_remaining_s"): 100.0,
    ("reward", "term_cost_max"): 450.0,
}
# The 4.81 kg twin's static folds max out ~26.5 deg, so scripted twins
# can only terminate under a test-scoped 20 deg envelope (same pattern
# as test_easy_dying_is_priced_below_park; the learned exploit trips
# the pilot's 30 deg envelope DYNAMICALLY, which scripted poses cannot
# reproduce).  Pricing comparisons are envelope-consistent: every
# behavior in a test runs under the same envelope.
PROBE20 = {
    ("safety", "max_roll_deg"): 20.0,
    ("safety", "max_pitch_deg"): 20.0,
}


@pytest.fixture(scope="module")
def remcost_returns() -> dict[str, float]:
    base = {**EASY_BASE, **PROBE20}
    fix = {**base, **EASY_REMCOST}
    out: dict[str, float] = {}
    for diet, ov in (("base", base), ("fix", fix)):
        for pol, scale in (("sprint_fall", 3.0), ("park", 1.0)):
            runs = [_easy_rollout(pol, s, gait_scale=scale, overrides=ov)
                    for s in SEEDS]
            out[f"{pol}@{diet}"] = float(np.mean([r[0] for r in runs]))
            out[f"{pol}@{diet}_steps"] = float(
                np.mean([r[2] for r in runs]))
    return out


def test_easy_sprintfall_exploit_reproduced_at_flat24(remcost_returns):
    """Under the launched pilot diet (flat 24 death price) the scripted
    sprint-then-fall twin must OUT-EARN park — reproducing in-bank the
    exploit both sdehalfgrav 40M seeds learned.  If this fails, the
    bank does not model the observed behavior and the fix tests below
    prove nothing."""
    assert remcost_returns["sprint_fall@base_steps"] < 400, (
        "sprint_fall twin did not terminate under the 20 deg probe "
        f"envelope: {remcost_returns}")
    assert (remcost_returns["sprint_fall@base"]
            > remcost_returns["park@base"] + 15.0), (
        f"exploit not reproduced (sprint_fall should out-earn park "
        f"under flat 24): {remcost_returns}")


def test_easy_remcost_prices_sprintfall_below_park(remcost_returns):
    """With the survival-duration charge on, dying after a paid burst
    must fall DECISIVELY below just standing there — the exploit's
    income can never cover the forfeited-survival price."""
    assert remcost_returns["sprint_fall@fix_steps"] < 400, (
        f"fix changed the twin's termination: {remcost_returns}")
    assert (remcost_returns["sprint_fall@fix"]
            < remcost_returns["park@fix"] - 50.0), (
        f"survival-duration charge does not price out the burst: "
        f"{remcost_returns}")
    # park itself is untouched by the fix (survives to truncation)
    assert (abs(remcost_returns["park@fix"]
                - remcost_returns["park@base"]) < 1e-6), (
        f"fix keys changed a surviving behavior's return: "
        f"{remcost_returns}")


def test_easy_remcost_bit_exact_for_survivors():
    """At the pilot's own 30 deg envelope (where the campaign trains),
    the fix keys are bit-exact for behaviors that survive to
    truncation: gait and park earn IDENTICAL returns with and without
    the keys."""
    fix = {**EASY_BASE, **EASY_REMCOST}
    for pol in ("gait", "park"):
        t0, dx0, s0 = _easy_rollout(pol, 0, overrides=EASY_BASE)
        t1, dx1, s1 = _easy_rollout(pol, 0, overrides=fix)
        assert s0 == s1 and abs(t0 - t1) < 1e-9, (
            f"remcost keys not bit-exact for surviving '{pol}': "
            f"{t0} vs {t1} ({s0} vs {s1} steps)")


def test_easy_remcost_sizing_dominates_burst_ceiling():
    """Arithmetic guard on the chosen dose, against the THEORETICAL
    income ceiling (2/tick at cap), not just the measured twin: for
    every burst length in the plausible ballistic class (<=1.5 s — by
    ~1.8 s of sustained capped income the 'burst' is real locomotion
    whose gradient must not be nuked), the death charge under 5 s
    training episodes exceeds the burst's maximum possible take."""
    k_rem = EASY_REMCOST[("reward", "term_cost_per_remaining_s")]
    cap = EASY_REMCOST[("reward", "term_cost_max")]
    flat = EASY_BASE[("reward", "safety_termination_penalty")]
    for t in np.arange(0.1, 1.51, 0.1):
        charge = flat + min(k_rem * (5.0 - t), cap)
        ceiling = 2.0 * 100.0 * t
        assert charge > ceiling, (
            f"death at {t:.1f}s underpriced: charge {charge:.0f} <= "
            f"income ceiling {ceiling:.0f}")


# ---------------------------------------------------------------------
# WALKSCRATCH_EASY heading-generalization bank (rung 2, 09-05)
# ---------------------------------------------------------------------
# STATUS.md names heading generalization as the campaign's next open
# gap once base/halfgrav close their fixed-forward rung (both did,
# 09-05), and explicitly requires a ranking bank proof BEFORE any
# heading-diet launch. Design follows the operator's OWN pre-existing
# staged-heading-curriculum ruling (fb_20260822T032514, walk_task.py
# _sample_walk comment): forward-only first, then a SMALL DISCRETE
# heading SET, never full +-180 from tick zero — so this rung uses
# goal.walk_heading_set = {0, +45, -45} deg, NOT a continuous/full
# range. goal.walk_cmd_resample_s=6 draws a fresh heading from that
# set every 6s inside the pilot's 20s episode (>=2 resamples per
# rollout), blended over the legacy 1s ramp; goal.walk_stop_frac=0 so
# this rung isolates heading-tracking from the (separately-covered)
# stop/hold behavior.
#
# The reward mechanism needs NO new keys: k_walk_freeprog's existing
# along/cross decomposition (walk_task.walk_freeprog_score) already
# projects onto whatever (vx_ref, vy_ref) is live THIS tick, so a
# policy that keeps re-aiming at the resampled heading is paid the
# same way the fixed-forward rung already validated; a policy that
# holds its ORIGINAL heading after a resample starts eating the same
# cross-track charge the existing WALKCURR_PF bank already prices
# 90-deg-off travel with (test_walkcurr_pf_stationary_beats_wrong_way:
# sideways must not beat park). This bank re-measures that same
# invariant under LIVE resampling instead of a single fixed offset.
EASY_HEADING = dict(EASY_BASE)
EASY_HEADING.update({
    ("goal", "walk_heading_set"): [0.0, math.pi / 4.0, -math.pi / 4.0],
    ("goal", "walk_cmd_resample_s"): 6.0,
    ("goal", "walk_stop_frac"): 0.0,
})
HEADING_EPISODE_S = 20.0  # matches the launched campaign's episode length


def _heading_rollout(policy: str, seed: int, *,
                     overrides: dict | None = None
                     ) -> tuple[float, float, int]:
    """(return, net planar travel m, along-command dist m, steps) for a
    scripted behavior twin under the heading-generalization diet.
    Unlike ``_easy_rollout`` the command (vx_ref, vy_ref) genuinely
    varies tick-to-tick, so twins here read BOTH components every
    step:
      - 'track': re-aims at the CURRENT commanded (vx_ref, vy_ref)
        every tick — perfect heading tracking.
      - 'fixedhead': aims at tick-0's command forever, ignoring every
        later resample — correct only until the first resample.
      - 'wronghead': aims at the exact NEGATIVE of the current
        command every tick — always 180 deg off, live.
      - 'park' / 'stall' / 'topple': same poses as the fixed-forward
        bank (direction-agnostic)."""
    from hexapod_core.tripod_gait import TripodGait
    from rl_move.sim.probe_walk_income import WALK_PLANT

    env = _make_env(seed, overrides if overrides is not None else
                    EASY_HEADING, episode_seconds=HEADING_EPISODE_S)
    env.reset()
    traj = env._goal_traj

    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(*WALK_PLANT)
    plant_rad = np.array([0.0, *WALK_PLANT] * 6) * DEG2RAD
    topple_rad = plant_rad.copy()
    for leg in (0, 1):
        topple_rad[3 * leg + 1] -= 80.0 * DEG2RAD
        topple_rad[3 * leg + 2] -= 80.0 * DEG2RAD

    vx0, vy0 = float(traj.vx[0]), float(traj.vy[0])
    x0 = float(env.data.xpos[env._chassis_bid, 0])
    y0 = float(env.data.xpos[env._chassis_bid, 1])
    total, step = 0.0, 0
    n = len(traj.vx)
    while True:
        t = step * env.dt
        i = min(step, n - 1)
        cvx, cvy = float(traj.vx[i]), float(traj.vy[i])
        if policy == "track":
            gait.set_velocity(vx=cvx, vy=cvy)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "fixedhead":
            gait.set_velocity(vx=vx0, vy=vy0)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "wronghead":
            gait.set_velocity(vx=-cvx, vy=-cvy)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "stall":
            gait.set_velocity(vx=0.0, vy=0.0)
            q = np.asarray(gait.desired_deg(t)) * DEG2RAD
        elif policy == "topple":
            q = topple_rad
        else:                       # park
            q = plant_rad
        obs, r, done, trunc, info = env.step(_q_to_action(env, q))
        total += r
        step += 1
        if done or trunc:
            break
    dx = float(env.data.xpos[env._chassis_bid, 0]) - x0
    dy = float(env.data.xpos[env._chassis_bid, 1]) - y0
    return total, math.hypot(dx, dy), step


@pytest.fixture(scope="module")
def easy_heading_returns() -> dict[str, float]:
    plan = ("track", "fixedhead", "wronghead", "park", "stall", "topple")
    out = {}
    for name in plan:
        runs = [_heading_rollout(name, s, overrides=EASY_HEADING)
                for s in SEEDS]
        out[name] = float(np.mean([r[0] for r in runs]))
        out[name + "_dx"] = float(np.mean([r[1] for r in runs]))
        out[name + "_steps"] = float(np.mean([r[2] for r in runs]))
    return out


def test_easy_heading_command_actually_varies():
    """Wiring check: under EASY_HEADING the commanded (vx_ref, vy_ref)
    must take on at least 2 distinct headings across one 20s episode
    (proves walk_heading_set + walk_cmd_resample_s actually resolve
    together, not silently ignored / stuck at the tick-0 draw)."""
    env = _make_env(0, EASY_HEADING, episode_seconds=HEADING_EPISODE_S)
    env.reset()
    traj = env._goal_traj
    angs = sorted({round(math.atan2(vy, vx), 2)
                   for vx, vy in zip(traj.vx, traj.vy)
                   if math.hypot(vx, vy) > 1e-6})
    assert len(angs) >= 2, (
        f"heading command never changed across the episode: {angs} "
        "— walk_heading_set/walk_cmd_resample_s not wired as expected")


def test_easy_heading_track_beats_fixed_after_resample(easy_heading_returns):
    """Re-aiming at the live command must decisively out-earn holding
    the stale tick-0 heading through later resamples — the exact
    'directions actually followed' bar the track's DONE gate names."""
    assert (easy_heading_returns["track"]
            > easy_heading_returns["fixedhead"] + 15.0), (
        f"stale-heading twin is competitive with live tracking: "
        f"{easy_heading_returns}")
    assert easy_heading_returns["track_dx"] > 0.5, (
        f"tracking twin did not actually travel: {easy_heading_returns}")


def test_easy_heading_track_beats_standing(easy_heading_returns):
    """Correct heading-tracking must out-earn both refusal (park) and
    marching in place (stall) by a wide margin."""
    for still in ("park", "stall"):
        assert (easy_heading_returns["track"]
                > easy_heading_returns[still] + 25.0), (
            f"standing '{still}' competitive with heading-tracking: "
            f"{easy_heading_returns}")


def test_easy_heading_standing_beats_wrong_heading(easy_heading_returns):
    """Live wrong-heading travel (always 180 deg off the CURRENT
    command, never just a stale offset) must not out-earn — or even
    tie — standing still, mirroring the existing WALKCURR_PF invariant
    that wrong-way travel must lose to park/stall."""
    floor = min(easy_heading_returns["park"], easy_heading_returns["stall"])
    assert floor > easy_heading_returns["wronghead"] + 15.0, (
        f"wronghead out-earns (or ties) standing still: "
        f"{easy_heading_returns} — live heading direction is not priced")


def test_easy_heading_dying_is_the_floor(easy_heading_returns):
    """Falling must sit below every walking/standing/wrong-heading
    behavior. Per the already-measured 09-05 finding
    (test_easy_dying_is_priced_below_park): the static topple fold
    never exceeds ~26.5 deg tilt on the committed 4.81 kg twin, so it
    SURVIVES (never terminates) at the pilot's real 30 deg envelope —
    reproduced here under EASY_HEADING too (steps == full episode) —
    and this bank instead proves the trip+penalty pathway under the
    same test-scoped 20 deg probe envelope the fixed-forward bank
    uses."""
    assert easy_heading_returns["topple_steps"] >= 1900, (
        "expected the static fold to survive the 30 deg pilot "
        f"envelope under EASY_HEADING too: {easy_heading_returns}")
    ov = dict(EASY_HEADING)
    ov[("safety", "max_roll_deg")] = 20.0
    ov[("safety", "max_pitch_deg")] = 20.0
    runs = [_heading_rollout("topple", s, overrides=ov) for s in SEEDS]
    tot = float(np.mean([r[0] for r in runs]))
    steps = float(np.mean([r[2] for r in runs]))
    assert steps < 400, (
        f"topple twin did not terminate under the 20 deg probe "
        f"envelope: steps={steps}")
    # Sustained wrong-heading/fixed-stale-heading marathons are not in
    # the floor set (same caveat as the fixed-forward bank's
    # test_easy_dying_is_priced_below_park): at k_freeprog=2 a full
    # 20 s of live 180-deg-off travel is self-punishing (~-4000) far
    # below any plausible escape-by-death payoff — park/stall are the
    # only realistic competitors death needs to beat.
    floor = min(easy_heading_returns["park"], easy_heading_returns["stall"])
    assert tot < floor - 15.0, (
        f"dying (topple@20deg={tot:.1f}) is not priced below standing "
        f"still ({floor:.1f}): {easy_heading_returns}")
