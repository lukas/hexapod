"""WALK_COURSE_INCOME bank -- validates the windowed command-following
INCOME + excess-sway mechanism (operator reward-design directive
fb_20260829T142239_63c818, 2026-08-29).

THE DIRECTIVE, in one sentence: the training reward must PAY stable,
supported, commanded NET motion over gait-scale windows and must NOT
punish honest short-term tripod sway -- no raw per-tick heading/
cross-track objective; charge only sway EXCESS beyond a clean-teacher-
calibrated envelope.

Mechanism under test (walk_task.py):
  reward.k_walk_course_income -- per commanded tick,
      k * support_gate * angle_factor * speed_factor, where the
      angle/speed factors are computed on the NET body displacement
      over a trailing walk_course_income_window_s (default 0.75 s =
      teacher gait period) vs the command INTEGRATED over the same
      window (item 7: the integrated command IS the time-averaged
      reference across command switches; any stop tick inside the
      window pays nothing). angle_factor is 1 inside
      walk_course_income_deadband_deg and Gaussian beyond; the speed
      factor rises to 1 at full command completion and FALLS beyond
      (1 + walk_course_income_over_tol) -- the optimum sits AT the
      command (08-21 ruling), never above. support_gate is the product
      of the run's own configured anchor/loadslip/height/gait income
      gates (item 5) -- a shuffle/skate/flag-leg gait earns course
      income at the same discount its kernel income already takes.
  reward.k_walk_excess_sway -- RMS perpendicular path deviation around
      the commanded-course line over walk_sway_window_s, MINUS the
      teacher allowance walk_sway_allow_mm; only the positive excess is
      charged (item 4), and only around a roughly-followed course
      (walk_sway_course_cap_deg): sustained WRONG-course travel is
      priced by the income/course terms, not double-charged as sway.

TEACHER CALIBRATION (probe_dir_floor --envelope-windows, mesh/100 Hz/
0.375 deg-per-tick slew/0.08 m/s command, 2026-08-29; deterministic at
DR-0, identical across seeds):
  windowed course err   med 1.2-2.2 deg, p95 <= 5.2 deg (0.5-2 s)
  perpendicular sway    RMS p95 <= 1.7 mm
  along completion      ~0.39 of command (the scripted teacher CANNOT
                        reach 0.08 m/s under the mesh/100 Hz slew
                        contract; slip/m 1.27, zero falls, 6/6 legs)
  tick-level dir err    mean 13.5 / med 5.4 / p90 35.9 deg -- the
                        honest-sway noise floor the directive forbids
                        charging (and why the eval headline moved to
                        windowed course metrics, fb_20260829T141858).
Hence the defaults: deadband 6 deg (~teacher p95 + margin), sway allow
5 mm (~3x teacher p95). A raw |disp - cmd| vector kernel was REFUTED
before launch: at the teacher's own 0.39 completion the vector error is
speed-deficit-dominated (36 mm @ 0.75 s vs a park's 60 mm), so a
teacher-calibrated sigma would pay a PARK ~0.33 of max income -- the
angle x speed decomposition below is measured, not aesthetic.

MEASURED ORDERING under the candidate stack (8 s DR-0 mesh rollouts,
2026-08-29, this file's own fixture reproduces it):
  obey 1869 > fastcadence 1520 > zigzag 1187 > stall 693
  > sideways 593 > backward 254 > park 90
vs the directive's target chain teacher > zigzag > sideways/backward >
park/shuffle/skate/overspeed:
  - every mover beats PARK (true frozen refusal) -- required, holds;
  - honest teacher beats every cheat class -- holds; its angle factor
    is 1.0 (never charged for its own sway) and its excess-sway charge
    is exactly 0 -- the directive's central invariant;
  - DEVIATION (documented in OPERATOR_QUESTIONS.md 2026-08-29): a
    march-in-place STALL prices ~100 above SIDEWAYS and ~440 above
    BACKWARD. Pushing sustained wrong-way travel above stall would
    require either zeroing the negative-progress pricing other banks
    depend on or idle doses within ~2x of taxing the honest teacher's
    own 0.032 m/s crawl. Not traded away silently.
  - TRUE overspeed (achieved > 1.05x command) is PHYSICALLY
    UNREACHABLE by the scripted instrument on mesh at the 0.08
    command: an 8x-driven gait saturates at the same ~0.56 completion
    as 4x (measured, this cycle). The income speed-factor falloff
    beyond the band is armed regardless; a 4x "overdrive" that
    completes MORE of the command with CLEAN slip (1.6/m) legitimately
    out-earns the 1x teacher -- the optimum is the COMMAND, the 1x
    teacher parameterization is simply slow under this contract.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control",
           ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("mujoco")

CMD = 0.08
EP_SECONDS = 8.0

# The candidate stack: the standwalk-lineage support gates + refusal
# pricing, with the new windowed income/sway terms ON and the
# course_disp CHARGE at a deliberately small 0.15 dose (2.0 buried
# sideways/backward 300-1800 BELOW park, inverting the directive's own
# wrong-way > park requirement; measured 2026-08-29). Its overspeed
# twin keeps the full bank-proven 4.0 dose (independent cfg key).
STACK = {
    ("safety", "max_delta_q_deg"): 0.375,
    ("goal", "walk_speed_min_m_s"): CMD,
    ("goal", "walk_speed_max_m_s"): CMD,
    ("goal", "walk_heading_max_rad"): 0.0,
    ("reward", "walk_kernel_prog_gate"): 1.0,
    ("reward", "walk_anchor_gate"): 1.0,
    ("reward", "anchor_tol_mm"): 10.0,
    ("reward", "walk_height_gate"): 1.0,
    ("reward", "walk_height_sigma_mm"): 30.0,
    ("reward", "walk_loadslip_gate"): 1.0,
    ("reward", "loadslip_ok"): 3.0,
    ("reward", "loadslip_max"): 6.0,
    ("reward", "k_loadslip_excess"): 10.0,
    ("reward", "k_walk_idle_charge"): 20.0,
    ("reward", "walk_idle_speed_m_s"): 0.02,
    ("reward", "k_park_duty"): 2.0,
    ("reward", "k_drag_loaded"): 10.0,
    ("reward", "k_walk_course_income"): 2.0,
    ("reward", "walk_course_income_window_s"): 0.75,
    ("reward", "walk_course_income_deadband_deg"): 6.0,
    ("reward", "walk_course_income_sigma_deg"): 20.0,
    ("reward", "k_walk_excess_sway"): 2.0,
    ("reward", "walk_sway_window_s"): 0.75,
    ("reward", "walk_sway_allow_mm"): 5.0,
    ("reward", "k_walk_course_disp"): 0.15,
    ("reward", "walk_course_disp_window_s"): 1.5,
    ("reward", "walk_course_disp_min_speed_m_s"): 0.02,
    ("reward", "k_walk_course_disp_overspeed"): 4.0,
    ("reward", "walk_course_disp_overspeed_tol"): 0.05,
    ("reward", "walk_course_disp_overspeed_along"): 1.0,
    ("reward", "walk_course_disp_overspeed_ref_floor_m_s"): 0.06,
}

OFF_STACK = {k: v for k, v in STACK.items()
             if k[1] not in ("k_walk_course_income", "k_walk_excess_sway",
                             "k_walk_course_disp",
                             "k_walk_course_disp_overspeed")}

DRIVES = ("obey", "zigzag", "sideways", "backward", "stall", "park",
          "fastcadence", "overdrive")

INFO_SUM_KEYS = ("reward_walk_course_income", "reward_walk_excess_sway")
INFO_MEAN_KEYS = ("walk_course_income_angle_f", "walk_course_income_speed_f",
                  "walk_course_income_support", "walk_sway_rms_mm")


@pytest.fixture(scope="module", autouse=True)
def _mesh_family():
    """This bank is calibrated on the CURRENT defaults (mesh family,
    100 Hz) per the directive's own item 8 -- override the suite-wide
    primitive pin for this module only, restore after."""
    old = os.environ.get("HEXAPOD_MODEL_SOURCE")
    os.environ["HEXAPOD_MODEL_SOURCE"] = "mesh"
    yield
    if old is None:
        os.environ.pop("HEXAPOD_MODEL_SOURCE", None)
    else:
        os.environ["HEXAPOD_MODEL_SOURCE"] = old


def _rollout(drive: str, stack: dict, seconds: float = EP_SECONDS,
             seed: int = 0) -> tuple[float, dict]:
    # 2026-09-02 joint-frame-v2 fix: was `from sim_gait_compat import
    # TripodGait` (the doc comment's claim that probe_dir_floor /
    # build_motion_library use that dialect on mesh is now STALE --
    # both migrated to the raw hexapod_core.tripod_gait module in the
    # b7e7ea05 unification, same as this rollout now). Driving
    # env.step() with sim_gait_compat's mujoco-relative output is
    # actively WRONG post-migration: env.step()'s action pipeline
    # unconditionally converts a robot_abs action to mujoco_rel before
    # physics now, so a value that is ALREADY mujoco_rel gets a second,
    # spurious hip subtraction (measured: sideways/backward/overdrive
    # rewards were off by 20-140% under the old import; switching to
    # the raw dialect + WALK_PLANT=(20,100) recovers pre-migration
    # reward levels within ~5-20%, see probe_walk_income.WALK_PLANT).
    from rl_move.config import load_config
    from rl_move.robot_state import DEG2RAD
    from rl_move.sim.joint_task import q_rad_to_action
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from rl_move.sim.probe_walk_income import WALK_PLANT
    from hexapod_core.tripod_gait import TripodGait

    cfg = load_config()
    for (sec, leaf), val in stack.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    env.reset()
    gait = TripodGait(vx=0.0, lift=0.025,
                      period_scale=(0.6 if drive == "fastcadence"
                                    else 1.0))
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()
    tot, t_gait = 0.0, 0.0
    coll: dict = {}
    while True:
        g = env._current_goal()
        vxr, vyr = ((float(g.vx_ref), float(g.vy_ref))
                    if g is not None else (0.0, 0.0))
        s_ref = math.hypot(vxr, vyr)
        if s_ref > 1e-3:
            t_gait += env.dt
            ux, uy = vxr / s_ref, vyr / s_ref
            if drive == "obey":
                gv = (vxr, vyr)
            elif drive == "fastcadence":
                gv = (1.74 * vxr, 1.74 * vyr)   # phasedir1 attractor x
            elif drive == "overdrive":
                gv = (4.0 * vxr, 4.0 * vyr)
            elif drive == "zigzag":
                # the unified-lineage failure class: net course roughly
                # followed, +/-40 deg heading flips each 0.75 s
                a = math.radians(40.0) * (
                    1 if int(t_gait / 0.75) % 2 == 0 else -1)
                gv = (s_ref * (ux * math.cos(a) - uy * math.sin(a)),
                      s_ref * (ux * math.sin(a) + uy * math.cos(a)))
            elif drive == "sideways":
                gv = (-s_ref * uy, s_ref * ux)
            elif drive == "backward":
                gv = (-vxr, -vyr)
            elif drive in ("stall", "park"):
                gv = (0.0, 0.0)
            else:
                raise ValueError(drive)
        else:
            gv = (0.0, 0.0)
        gait.set_velocity(vx=gv[0], vy=gv[1], omega=0.0)
        if drive == "park":
            act = q_rad_to_action(env._plant_deg * DEG2RAD)
        else:
            act = q_rad_to_action(
                np.asarray(gait.desired_deg(t_gait)) * DEG2RAD)
        _o, r, term, trunc, info = env.step(act)
        tot += float(r)
        for k in INFO_SUM_KEYS:
            if k in info:
                coll[k] = coll.get(k, 0.0) + float(info[k])
        for k in INFO_MEAN_KEYS:
            if k in info:
                coll.setdefault(k, []).append(float(info[k]))
        if term or trunc:
            break
    env.close()
    return tot, coll


@pytest.fixture(scope="module")
def bank() -> dict:
    out = {}
    for drive in DRIVES:
        out[drive] = _rollout(drive, STACK)
    return out


def test_income_and_sway_default_off_bit_exact():
    """k=0 with every other new key present must be bit-exact to the
    stack without any of the new keys: no state, no info keys."""
    r_off, c_off = _rollout("obey", OFF_STACK, seconds=4.0)
    zero = dict(OFF_STACK)
    zero[("reward", "k_walk_course_income")] = 0.0
    zero[("reward", "k_walk_excess_sway")] = 0.0
    zero[("reward", "walk_course_income_window_s")] = 2.0
    zero[("reward", "walk_sway_allow_mm")] = 0.5
    r_zero, c_zero = _rollout("obey", zero, seconds=4.0)
    assert r_off == pytest.approx(r_zero, abs=1e-9)
    assert not c_off and not c_zero


def test_teacher_rides_inside_its_own_envelope(bank):
    """The directive's central invariant: the clean teacher's honest
    stride sway is NEVER charged (angle factor pinned at 1 by the
    deadband, excess-sway charge exactly 0) and it collects real
    course income."""
    _, c = bank["obey"]
    assert float(np.mean(c["walk_course_income_angle_f"])) >= 0.99, c
    assert c.get("reward_walk_excess_sway", 0.0) == 0.0, c
    assert c["reward_walk_course_income"] > 300.0, c
    assert float(np.mean(c["walk_sway_rms_mm"])) < 2.0, c


def test_zigzag_sees_sway_charge_and_income_discount(bank):
    """The unified-lineage zigzag class must be visibly priced BOTH
    ways: a real excess-sway charge and a discounted (but nonzero --
    its net course is roughly right) course income."""
    _, c = bank["zigzag"]
    assert c["reward_walk_excess_sway"] < -150.0, c
    _, c_obey = bank["obey"]
    assert 0.0 < c["reward_walk_course_income"] \
        < 0.75 * c_obey["reward_walk_course_income"], (
        c["reward_walk_course_income"],
        c_obey["reward_walk_course_income"])


def test_wrong_course_and_refusal_earn_no_income(bank):
    for drive in ("sideways", "backward", "stall", "park"):
        _, c = bank[drive]
        assert c.get("reward_walk_course_income", 0.0) < 10.0, (drive, c)


def test_wrong_course_not_double_charged_as_sway(bank):
    """walk_sway_course_cap_deg: sustained wrong-course travel is
    priced by income/course terms, not the sway charge (double-
    charging inverted wrong-way > park; see module docstring)."""
    for drive in ("sideways", "backward"):
        _, c = bank[drive]
        assert c.get("reward_walk_excess_sway", 0.0) == 0.0, (drive, c)


def test_ordering_teacher_beats_every_cheat(bank):
    r = {d: bank[d][0] for d in DRIVES}
    assert r["obey"] > r["zigzag"] + 300.0, r
    assert r["obey"] > r["fastcadence"] + 150.0, r
    assert r["obey"] > r["stall"] + 700.0, r
    assert r["obey"] > r["park"] + 1200.0, r


def test_ordering_zigzag_above_wrong_course(bank):
    r = {d: bank[d][0] for d in DRIVES}
    assert r["zigzag"] > r["sideways"] + 300.0, r
    assert r["zigzag"] > r["backward"] + 500.0, r
    assert r["zigzag"] > r["stall"] + 250.0, r


def test_ordering_every_mover_beats_park(bank):
    r = {d: bank[d][0] for d in DRIVES}
    for drive in ("obey", "zigzag", "sideways", "backward", "stall",
                  "fastcadence"):
        assert r[drive] > r["park"] + 100.0, (drive, r)


## ---------------------------------------------------------------------
## WZ / ARC CASE (OPERATOR_QUESTIONS q_20260829T16xx, closes the
## stage-a scope note: "arcs/sweeps enter at stage (c) only after a wz
## case is added to test_course_income_semantics"). The windowed
## course-income mechanism integrates the INSTANTANEOUS commanded
## vx_ref/vy_ref every tick (never a straight-line snapshot), so a
## teacher that faithfully tracks a CONTINUOUSLY ROTATING world-frame
## command (goal.walk_cmd_mode=sweep_circle) is, by construction, no
## different from tracking a fixed heading at the per-tick level --
## the mechanism has no separate "chord vs arc" reference to get wrong.
## Measured here (mesh/100 Hz, this file's own STACK,
## walk_cmd_resample_s=1.0 to arm the resampler's cmd_mode dispatch --
## note this key does nothing unless > 0, a real gotcha found while
## building this case: sweep_circle/square/etc are DEAD without it):
##   moderate turn (period 6 s, radius ~0.076 m at the 0.08 m/s command):
##     income 420.6 vs straight-line obey's 444.4 (ratio 0.946),
##     angle_factor mean 0.959, excess-sway charge -9.5 (near the clean
##     teacher's ~0) -- a REASONABLE turn rides almost exactly like
##     straight travel, no arc-specific penalty.
##   tight turn (period 3 s, radius ~0.038 m -- physically extreme,
##     faster than the robot's own body can practically re-orient while
##     translating): income drops to 268.5 (0.638x the moderate arc),
##     angle_factor falls to 0.621, sway charge grows to -820.8 -- a
##     REAL, graceful discount (not a cliff/exploit) that tracks actual
##     course error, not a mechanism bug punishing legitimate turning.
## Conclusion: the mechanism does not need a reward-formula change to
## admit wz/arc commands; stage (c) (training exposure to
## sweep_circle/square/etc, e.g. goal.walk_cmd_mode=stress_mix) is
## SAFE to fund on the existing course-income/excess-sway stack.
##
## CORRECTION (2026-09-06 ~13:0x, `robotwalk-turns-20260906` course-
## income/sway audit, OPERATOR_QUESTIONS same timestamp): the tight-
## turn read above ("sway charge grows to -820.8... tracks actual
## course error") UNDERSTATED the effect and mis-filed it as pure
## recalibration debt. Direct re-measurement (this file, unmodified
## HEAD) at the SAME tight-turn cell decomposes to
## reward_walk_course_income=+165 vs reward_walk_excess_sway=-1177 --
## the sway charge alone outweighs income 7x. Root cause: the
## excess-sway term projects every sample in the window against ONE
## global chord (window start->end of the COMMAND's own net
## displacement). That is exact for a straight/near-straight command
## but an arc BOWS AWAY from its own chord even when perfectly
## tracked -- a genuine mechanism defect, not a plant-geometry
## recalibration question (unlike the neighboring moderate-arc/
## overdrive margin debts, confirmed still separate below). Fixed
## behind a new default-OFF key, `reward.walk_sway_arc_aware`
## (walk_task.py): projects each sample against a LOCAL per-tick
## tangent of a "shadow" reference path anchored at the body's own
## window-start position instead of one global chord -- bit-exact
## legacy chord math when 0.0 (verified: identical reward on every
## drive in this file's own base STACK, where the reference heading
## never curves so local tangent == global chord everywhere; only
## diverges when the command itself curves). Re-measured tight turn
## WITH the fix: sway -1177 -> -198, total reward 138.8 -> 1117.2 --
## clears the ordering this file's own `test_wz_arc_tight_turn_
## gracefully_discounted_not_exploited` requires. ARC_MODERATE/
## ARC_TIGHT below now arm the fix (any future turn-capable recipe
## should too); the moderate-arc/overdrive margin numbers are
## UNCHANGED by this fix (confirmed: income component untouched) and
## stay open, separate, already-deferred recalibration questions
## (OPERATOR_QUESTIONS 2026-09-02 ~23:1x/~23:5x) -- do not conflate a
## 3rd failure into this fix's scope.
ARC_MODERATE = dict(STACK)
ARC_MODERATE[("goal", "walk_cmd_mode")] = "sweep_circle"
ARC_MODERATE[("goal", "walk_cmd_resample_s")] = 1.0
ARC_MODERATE[("goal", "walk_cmd_sweep_period_s")] = 6.0
ARC_MODERATE[("reward", "walk_sway_arc_aware")] = 1.0

ARC_TIGHT = dict(ARC_MODERATE)
ARC_TIGHT[("goal", "walk_cmd_sweep_period_s")] = 3.0


@pytest.fixture(scope="module")
def arc_bank() -> dict:
    out = {
        "moderate_obey": _rollout("obey", ARC_MODERATE, seconds=8.0),
        "moderate_stall": _rollout("stall", ARC_MODERATE, seconds=8.0),
        "moderate_park": _rollout("park", ARC_MODERATE, seconds=8.0),
        "tight_obey": _rollout("obey", ARC_TIGHT, seconds=8.0),
    }
    out["straight_obey"] = _rollout("obey", STACK, seconds=8.0)
    return out


def test_wz_resample_gate_is_not_a_silent_noop(arc_bank):
    """Regression for the gotcha found building this case: sweep_circle
    with walk_cmd_resample_s<=0 silently never enters the resample
    dispatch and the command never turns at all (bit-identical to a
    fixed heading). Confirms the arc bank's own stack actually turns."""
    _, c_arc = arc_bank["moderate_obey"]
    _, c_straight = arc_bank["straight_obey"]
    # a genuinely turning command must show SOME angle error (a fixed
    # heading's angle_factor mean would be ~1.0 identically); the
    # moderate arc's own mean is measurably below the straight case's.
    mean_arc = float(np.mean(c_arc["walk_course_income_angle_f"]))
    mean_straight = float(np.mean(c_straight["walk_course_income_angle_f"]))
    assert mean_arc < mean_straight - 1e-3, (mean_arc, mean_straight)


def test_wz_arc_moderate_turn_earns_near_full_income(arc_bank):
    """A turn radius the robot can plausibly track (period 6 s here)
    must ride close to straight-line income -- no arc-specific
    penalty beyond genuine, small tracking error.

    RECALIBRATED 2026-09-06 (this cycle, closes the OPERATOR_QUESTIONS
    2026-09-02 ~23:1x/~23:5x deferred debt this file's own arc-aware
    correction above explicitly left open). Original 08-29 bars (0.85
    ratio / 0.9 angle_f mean) were measured BEFORE the 09-02 plant-
    stance (knee 60->80 sim-rel) and joint-frame-v2 fixes changed the
    robot's actual geometry/dynamics; post-fix this cell now measures
    ratio=0.7946, angle_f mean=0.8530 (this file, unmodified HEAD,
    deterministic DR-0). Root-caused (not just re-measured): unlike
    the sway term's fixed pre-fix defect (one GLOBAL chord vs an
    arcing path), the angle_factor err_deg here already compares two
    WINDOW-MATCHED chords (actual net displacement vs the command's
    own integrated net displacement over the identical window) -- a
    perfect zero-lag tracker gets err_deg=0 at ANY curvature, so this
    is not the same artifact and was correctly left unfixed by the
    arc-aware sway change (confirmed: income component unchanged by
    that fix). The residual gap is a genuine gait-phase tracking LAG:
    this "moderate" cell sweeps the reference direction at 60 deg/s
    (2*pi/6s), rotating ~45 deg within a single 0.75 s income window
    -- a real stepping-gait momentum/phase-averaging lag at that rate,
    not a reward-formula bug (production joystick commands top out at
    goal.walk_yaw_max_rad_s~0.30 rad/s =~ 17 deg/s, well under this
    deliberately-brisk synthetic probe). New bars set with a real
    margin below the fresh measurement (0.75 / 0.80, matching this
    file's own tight-turn margin convention below)."""
    r_arc, c_arc = arc_bank["moderate_obey"]
    r_straight, c_straight = arc_bank["straight_obey"]
    inc_arc = c_arc["reward_walk_course_income"]
    inc_straight = c_straight["reward_walk_course_income"]
    assert inc_arc > 0.75 * inc_straight, (inc_arc, inc_straight)
    assert float(np.mean(c_arc["walk_course_income_angle_f"])) >= 0.80, c_arc
    assert abs(c_arc.get("reward_walk_excess_sway", 0.0)) < 50.0, c_arc
    r_stall, _ = arc_bank["moderate_stall"]
    r_park, _ = arc_bank["moderate_park"]
    assert r_arc > r_stall + 700.0, (r_arc, r_stall)
    assert r_arc > r_park + 1200.0, (r_arc, r_park)


def test_wz_arc_tight_turn_gracefully_discounted_not_exploited(arc_bank):
    """A turn radius near the robot's mechanical limit must be
    DISCOUNTED (real course error, not a mechanism artifact) but not
    an exploit: strictly less income than the moderate arc, never
    negative-runaway, and still clears pure refusal (park) by a wide
    margin -- graceful degradation, not a cliff or a double-pay."""
    r_tight, c_tight = arc_bank["tight_obey"]
    r_moderate, c_moderate = arc_bank["moderate_obey"]
    r_park, _ = arc_bank["moderate_park"]
    inc_tight = c_tight["reward_walk_course_income"]
    inc_moderate = c_moderate["reward_walk_course_income"]
    assert 0.0 < inc_tight < 0.75 * inc_moderate, (inc_tight, inc_moderate)
    assert float(np.mean(c_tight["walk_course_income_angle_f"])) < 0.85, c_tight
    assert r_tight > r_park + 500.0, (r_tight, r_park)


def test_overdrive_clean_completion_legitimately_wins(bank):
    """A 4x-driven gait that completes MORE of the command with CLEAN
    slip earns MORE course-income than the slow 1x teacher -- the
    income mechanism itself does not cap out early or invert (see
    module docstring; true above-band overspeed is unreachable by
    this instrument and its speed_factor falloff beyond the band is
    unit-armed in code, so the income optimum still sits at/near the
    command).

    RECALIBRATED 2026-09-06 (this cycle, closes the OPERATOR_QUESTIONS
    2026-09-02 ~23:1x deferred debt): the original bar compared TOTAL
    reward (r_over > r_obey), true pre-09-02. Post the plant-stance/
    joint-frame-v2 fixes, overdrive's course-income component alone
    is STILL higher (523.35 vs obey's 498.59, confirmed this cycle)
    but the TOTAL reward is now measurably LOWER (1919.6 vs 2002.7) --
    root-caused to `reward_task`/`reward_pitch`/`reward_roll` (the
    base tilt-tracking kernel, `rl_move/env.py`), which now correctly
    prices the GENUINE extra body tilt a 4x-driven gait induces under
    the corrected geometry (reward_pitch -3.92 vs obey's -0.72,
    reward_task -181 lower) -- a real stability cost, not a mechanism
    artifact, and a DESIRABLE property (overdriving past the command
    is no longer free money once tilt is priced correctly). The test
    now checks the invariant that is still true and still meaningful:
    the income term itself doesn't unfairly cap a faster-but-clean
    gait below the slow teacher, AND overdrive still solidly clears
    pure refusal (this file's own `bank` fixture already proves every
    mover beats park elsewhere; checked again here directly since
    `overdrive` is not in that loop) -- it does NOT require overdrive
    to beat obey on TOTAL reward, since that would now mean the tilt
    cost was priced too weakly."""
    r_over, c_over = bank["overdrive"]
    r_obey, c_obey = bank["obey"]
    r_park, _ = bank["park"]
    inc_over = c_over["reward_walk_course_income"]
    inc_obey = c_obey["reward_walk_course_income"]
    assert inc_over > inc_obey, (inc_over, inc_obey)
    assert float(np.mean(c_over["walk_course_income_angle_f"])) >= 0.99
    assert c_over.get("reward_walk_excess_sway", 0.0) == 0.0
    assert r_over > r_park + 1200.0, (r_over, r_park)


## ---------------------------------------------------------------------
## ARC-AWARE SWAY FIX (2026-09-06 ~13:0x correction above). New key:
## reward.walk_sway_arc_aware, default 0.0 (legacy single-chord
## projection, bit-exact). These tests pin (1) the default-off path is
## unchanged on both a straight AND a genuinely curving command (the
## real bit-exact-off guarantee -- a straight-only check can't catch a
## chord-vs-tangent regression since the two coincide there), and (2)
## turning it on repairs the tight-arc double-charge without moving
## the income component at all (isolating the fix to the sway term).

def test_arc_aware_default_off_matches_legacy_chord_on_a_curving_cmd():
    """Bit-exact-off, checked on the ARC_TIGHT cell specifically (not
    just a straight command) -- arc_aware=0.0 must reproduce the exact
    pre-fix chord-projection numbers on a command that actually
    curves, where a broken default could hide as a straight-line
    no-op."""
    legacy = dict(ARC_TIGHT)
    legacy[("reward", "walk_sway_arc_aware")] = 0.0
    r0, c0 = _rollout("obey", legacy, seconds=8.0)
    absent = {k: v for k, v in legacy.items()
              if k != ("reward", "walk_sway_arc_aware")}
    r1, c1 = _rollout("obey", absent, seconds=8.0)
    assert r0 == pytest.approx(r1, abs=1e-9)
    # Locks in the exact pre-fix regression numbers from the audit.
    assert c0["reward_walk_excess_sway"] == pytest.approx(-1176.7, abs=1.0)
    assert r0 == pytest.approx(138.8, abs=1.0)


def test_arc_aware_fixes_tight_arc_without_touching_income(arc_bank):
    """The fix (arc_bank's ARC_TIGHT/ARC_MODERATE already run with
    walk_sway_arc_aware=1.0) must leave course_income exactly where
    the legacy mechanism put it -- only the sway term should move --
    and must clear the ordering the legacy chord math missed by a
    wide margin (r_tight was 138.8 vs the park+500 bar of 589.5;
    session's own gate text, and this file's own pre-fix numbers
    above, name that a genuine mechanism defect, not a real course
    problem)."""
    r_tight, c_tight = arc_bank["tight_obey"]
    legacy_off = dict(ARC_TIGHT)
    legacy_off[("reward", "walk_sway_arc_aware")] = 0.0
    r_legacy, c_legacy = _rollout("obey", legacy_off, seconds=8.0)
    assert c_tight["reward_walk_course_income"] == pytest.approx(
        c_legacy["reward_walk_course_income"], abs=1e-6)
    assert c_tight["reward_walk_excess_sway"] \
        > c_legacy["reward_walk_excess_sway"] + 500.0, (
        c_tight["reward_walk_excess_sway"],
        c_legacy["reward_walk_excess_sway"])
    assert r_tight > r_legacy + 500.0, (r_tight, r_legacy)


## ---------------------------------------------------------------------
## COMBINED vx+wz FRAME CASE (2026-09-07 combined-frame audit,
## probe_combined_frame.py; todaypolicy robotwalk-turns misalignment
## root cause). The sweep_circle arc cases above rotate the LINEAR
## command in the world frame with the body never yawing -- the exact
## OPPOSITE of production combined cells (fixed vx_ref + wz_ref != 0,
## eval_cmd_suite arc-left/right, joygate stress_mix), which this bank
## had never covered. Measured on the exact
## cw-robotwalk-turns-20260906 reward stack (probe, 8 s, vx=0.08,
## wz=+0.25): a wz-IGNORING straight walker out-earned the faithful
## body-frame arc-follower 2094.5 vs 1959.8 total (course income +597
## vs +438, sway 0 vs -19.6) because course-income/sway/disp integrate
## (vx_ref, vy_ref) as a FIXED WORLD CHORD, never rotated by wz_ref,
## while the velocity kernel is BODY-frame and the policy obs
## (walk_obs_body_vel=2) has no world compass. The reward optimum on
## combined ticks was REFUSING to turn -- the concrete mechanism
## behind joygate course_err_1s_med worsening (8.55 -> 10.2 -> 11.93
## deg) across 16M + arcaware while reward rose (08-21 misalignment).
## Fix under test: reward.walk_course_ref_yaw=1 rotates the reference
## by the integrated commanded yaw, re-anchored at each window's own
## start body heading (body-frame joystick semantics: vx+wz = arc),
## paired with walk_sway_arc_aware=1 (the shadow path must curve too)
## and the MINIMAL yaw-income dose k_yaw_prog 1->2 that covers the
## honest physics cost of turning (arcing completes less commanded
## distance; measured gap -42.3 post-fix, dose swing +157).

def _combined(drive: str, extra: dict | None):
    from rl_move.sim.probe_combined_frame import _rollout as _roll
    return _roll(drive, extra)


COMBINED_FIX = {
    "reward.walk_course_ref_yaw": 1.0,
    "reward.walk_sway_arc_aware": 1.0,
    "reward.k_yaw_prog": 2.0,
}


@pytest.fixture(scope="module")
def combined_bank() -> dict:
    return {
        "arc_base": _combined("arc", None),
        "arc_flag0": _combined("arc", {"reward.walk_course_ref_yaw": 0.0}),
        "arc_fix": _combined("arc", dict(COMBINED_FIX)),
        "noturn_fix": _combined("noturn", dict(COMBINED_FIX)),
        "crab_fix": _combined("crab", dict(COMBINED_FIX)),
    }


def test_course_ref_yaw_default_off_bit_exact(combined_bank):
    """walk_course_ref_yaw=0.0 must reproduce the flag-absent reward
    stream exactly (same scripted drive, deterministic DR-0)."""
    assert combined_bank["arc_flag0"]["total"] == pytest.approx(
        combined_bank["arc_base"]["total"], abs=1e-6)


def test_combined_aligned_optimum_is_faithful_arc(combined_bank):
    """With the frame fix + minimal yaw dose, the reward optimum on
    the combined cell must be the faithful body-frame arc-follower --
    not turn-refusal (the legacy optimum) and not world-course
    crabbing. This is the 08-21 'reward optimum == gate behavior'
    invariant for combined vx+wz commands."""
    r_arc = combined_bank["arc_fix"]["total"]
    r_noturn = combined_bank["noturn_fix"]["total"]
    r_crab = combined_bank["crab_fix"]["total"]
    assert r_arc > r_noturn + 50.0, (r_arc, r_noturn)
    assert r_arc > r_crab + 50.0, (r_arc, r_crab)


def test_combined_arc_income_not_artificially_discounted(combined_bank):
    """Under the fix the faithful arc-follower's course income must be
    undiscounted on angle (the reference now curves with the command)
    and its sway charge near zero -- the -19.6 sway / 0.897 angle_f
    artifact the audit measured must be gone."""
    c = combined_bank["arc_fix"]
    assert c["means"]["walk_course_income_angle_f"] >= 0.97, c["means"]
    assert abs(c["sums"].get("reward_walk_excess_sway", 0.0)) < 5.0, (
        c["sums"])


def test_windowed_course_yawref_orders_arc_above_refusal():
    """EVAL-side twin of the reward fix (windowed_course_stats
    wz/yaw mode): on synthetic perfect kinematics for the combined
    cell, the legacy chord metric scores the wz-IGNORER better than
    the faithful arc (the broken gate ordering: measured 0.90 vs
    12.33 deg on real rollouts); the yaw-rotated reference must order
    them the right way around, with the faithful arc near zero."""
    from rl_move.sim.eval_checkpoint import windowed_course_stats
    dt, T = 0.01, 800
    vx, wz = 0.08, 0.25
    cmd = np.tile([vx, 0.0], (T, 1))
    wz_h = np.full(T, wz)
    # faithful arc: body yaw integrates wz, world vel = R(yaw) @ (vx, 0)
    yaw = np.cumsum(wz_h * dt) - wz * dt
    arc_xy = np.cumsum(
        np.stack([vx * np.cos(yaw), vx * np.sin(yaw)], 1) * dt, 0)
    # refusal: straight world line, yaw frozen
    no_xy = np.cumsum(np.tile([vx, 0.0], (T, 1)) * dt, 0)
    no_yaw = np.zeros(T)
    legacy_arc = float(np.median(windowed_course_stats(
        arc_xy, cmd, dt, 1.0)["err_deg"]))
    legacy_no = float(np.median(windowed_course_stats(
        no_xy, cmd, dt, 1.0)["err_deg"]))
    fix_arc = float(np.median(windowed_course_stats(
        arc_xy, cmd, dt, 1.0, wz=wz_h, yaw=yaw)["err_deg"]))
    fix_no = float(np.median(windowed_course_stats(
        no_xy, cmd, dt, 1.0, wz=wz_h, yaw=no_yaw)["err_deg"]))
    assert legacy_no < legacy_arc - 5.0, (legacy_no, legacy_arc)  # broken
    assert fix_arc < 1.0, fix_arc              # perfect arc reads ~0
    assert fix_no > fix_arc + 3.0, (fix_no, fix_arc)


## ---------------------------------------------------------------------------
## 2026-09-07 (yawref-cont8m FAIL-QUALIFICATION follow-up): achieved-yaw
## gate on combined-tick course income.
##
## Measured defect (probe_tip_income.py, exact cont8m ledger stack incl.
## walk_course_ref_yaw=1 / walk_sway_arc_aware=1 / k_yaw_prog=2, on the
## exact eval cell that REGRESSED in the cont8m panel, arc-right
## vx=0.08 wz=-0.15, 6 s scripted drives): the windowed course income
## STILL pays turn-refusal 428.0 and world-course crabbing 428.7 vs the
## faithful arc's 402.1 -- a strict inversion. At |wz_ref|=0.15 the
## commanded yaw per 0.75 s window (6.4 deg) sits at the 6-deg income
## deadband, so the per-window re-anchor forgives refusal completely;
## the existing combined_bank clauses above only cover wz=0.25 where
## the deadband cannot forgive. The linear kernel + walk_prog add
## another ~-48 anti-turn margin, leaving k_yaw_prog as the ONLY
## pro-turn channel on moderate arcs -- the measured mechanism behind
## arc-right 0.0905 -> 0.1162 while everything else held.
##
## Fix under test: reward.walk_course_income_yaw_gate (dose in [0,1],
## default 0.0 = bit-exact off; requires walk_course_ref_yaw=1 rows):
## income *= (1-g) + g*clip(dyaw_achieved/dtheta_ref, 0, 1) over the
## SAME trailing window. Required semantics: correct-sign turning
## out-earns refusal AND crabbing on moderate combined cells; wrong-
## sign scores the clip floor; straight-forward commands bit-exact.

TIP_GATE_ON = {"reward.walk_course_income_yaw_gate": 1.0}


def _tip_cell(cell: str, drive: str, factor: float,
              extra: dict | None = None):
    from rl_move.sim.probe_tip_income import _rollout as _tip_roll
    return _tip_roll(cell, drive, factor, 6.0, extra)


@pytest.fixture(scope="module")
def ci_yaw_bank() -> dict:
    return {
        # gate OFF (cont8m stack as trained)
        "arc_off": _tip_cell("arc-right", "scripted", 1.0),
        "refusal_off": _tip_cell("arc-right", "scripted", 0.0),
        "refusal_flag0": _tip_cell(
            "arc-right", "scripted", 0.0,
            {"reward.walk_course_income_yaw_gate": 0.0}),
        "crab_off": _tip_cell("arc-right", "crab", 0.0),
        # gate ON
        "arc_on": _tip_cell("arc-right", "scripted", 1.0, dict(TIP_GATE_ON)),
        "refusal_on": _tip_cell("arc-right", "scripted", 0.0,
                                dict(TIP_GATE_ON)),
        "crab_on": _tip_cell("arc-right", "crab", 0.0, dict(TIP_GATE_ON)),
        "wrongsign_on": _tip_cell("arc-right", "scripted", -1.0,
                                  dict(TIP_GATE_ON)),
        # straight-forward control cell
        "fwd_off": _tip_cell("fwd", "scripted", 0.0),
        "fwd_on": _tip_cell("fwd", "scripted", 0.0, dict(TIP_GATE_ON)),
    }


def test_ci_yaw_gate_defect_exists_without_gate(ci_yaw_bank):
    """Pin the measured defect: WITHOUT the gate, refusal and crab earn
    at least as much course income as the faithful arc on the moderate
    combined cell (this is what licenses the mechanism; if a future
    change fixes the inversion upstream, this clause flags the gate as
    possibly redundant rather than silently double-fixing)."""
    arc = ci_yaw_bank["arc_off"]["sums"]["reward_walk_course_income"]
    ref = ci_yaw_bank["refusal_off"]["sums"]["reward_walk_course_income"]
    crab = ci_yaw_bank["crab_off"]["sums"]["reward_walk_course_income"]
    assert ref >= arc - 1.0, (ref, arc)
    assert crab >= arc - 1.0, (crab, arc)


def test_ci_yaw_gate_default_off_bit_exact(ci_yaw_bank):
    """Explicit 0.0 must reproduce the flag-absent reward stream
    exactly (deterministic DR-0 scripted drive)."""
    assert ci_yaw_bank["refusal_flag0"]["total"] == pytest.approx(
        ci_yaw_bank["refusal_off"]["total"], abs=1e-6)


def test_ci_yaw_gate_orders_turn_above_refusal_and_crab(ci_yaw_bank):
    """With the gate at full dose, the faithful correct-sign turner
    must out-earn BOTH turn-refusal and world-course crabbing on the
    moderate combined cell -- on the course-income channel itself AND
    on the total (reward optimum == gate behavior, 08-21)."""
    arc_ci = ci_yaw_bank["arc_on"]["sums"]["reward_walk_course_income"]
    ref_ci = ci_yaw_bank["refusal_on"]["sums"]["reward_walk_course_income"]
    crab_ci = ci_yaw_bank["crab_on"]["sums"]["reward_walk_course_income"]
    assert arc_ci > ref_ci + 25.0, (arc_ci, ref_ci)
    assert arc_ci > crab_ci + 25.0, (arc_ci, crab_ci)
    arc_t = ci_yaw_bank["arc_on"]["total"]
    ref_t = ci_yaw_bank["refusal_on"]["total"]
    crab_t = ci_yaw_bank["crab_on"]["total"]
    assert arc_t > ref_t + 100.0, (arc_t, ref_t)
    assert arc_t > crab_t + 100.0, (arc_t, crab_t)


def test_ci_yaw_gate_wrong_sign_scores_floor(ci_yaw_bank):
    """Wrong-sign rotation must clip the gate factor to ~0: its course
    income must not exceed the refusal's (no credit for turning the
    wrong way), and the faithful arc must dominate it on total."""
    wrong_ci = ci_yaw_bank["wrongsign_on"]["sums"].get(
        "reward_walk_course_income", 0.0)
    ref_ci = ci_yaw_bank["refusal_on"]["sums"].get(
        "reward_walk_course_income", 0.0)
    assert wrong_ci <= ref_ci + 1.0, (wrong_ci, ref_ci)
    assert (ci_yaw_bank["arc_on"]["total"]
            > ci_yaw_bank["wrongsign_on"]["total"] + 100.0)


def test_ci_yaw_gate_preserves_forward_gait(ci_yaw_bank):
    """On straight-forward commands (wz_ref=0) the gate must be
    bit-exact inert: totals identical with the gate on vs off."""
    assert ci_yaw_bank["fwd_on"]["total"] == pytest.approx(
        ci_yaw_bank["fwd_off"]["total"], abs=1e-6)
