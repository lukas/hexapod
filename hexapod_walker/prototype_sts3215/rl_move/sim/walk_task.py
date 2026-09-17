"""SimHexapodJointWalkEnv — velocity-command locomotion, raw joint actions.

The most ambitious task so far: a ``walk`` goal mode where the policy is
given a commanded planar body velocity (body-frame vx/vy, m/s) and must
discover a gait that tracks it. Built on the raw joint-space env because
the fixed-foot IK cannot express stepping at all — the same structural
ceiling that blocked flat rise blocked locomotion outright.

Goal obs grows by 2 (scaled vx/vy refs, zero for non-walk modes), so
obs = 59 proprio + 11 goal = 70. All other modes (hold/lean/track/
unload/raise/rise/lower) remain in the mix so the policy keeps its
balance/rise competence while learning to walk.

Reward for walk episodes: the shared kernel/regularizer stack (zero tilt
refs — stay level while moving) PLUS a Gaussian kernel on velocity
tracking error, same design language as the tilt/height kernels:
``k_walk * exp(-|v - v_ref|^2 / 2 sigma^2)``. Velocity is the chassis'
body-frame planar velocity from privileged sim state; hardware transfer
will need an estimator (or optical flow), which is acknowledged and
deferred — sim-first, like everything else in Phase 1.

v2 (post cw-walk, which plateaued at a ~0.04 m/s shuffle):

1. MEASURED body velocity appended to the obs (2 dims, obs 70 -> 72).
   v1 was open-loop on the exact quantity it was scored on — the policy
   could never correct speed error it cannot sense.
2. PROGRESS reward: k_prog * (v . u_ref)/s_ref, capped at 1.25. The
   kernel alone pays ~nothing until tracking is already close (sigma
   0.04 at 0.075 m/s error = 0.17), so "stand still and collect the
   level-body kernel" was a local optimum. The linear term pays every
   cm/s in the commanded direction from the very first step, and
   charges moving against it.
3. Walk mix 0.40 -> 0.70; kernel sigma widened to 0.05.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from rl_move.config import cfg_get
from rl_move.env import (GOAL_DIM, TaskGoal, current_sense_obs_dim,
                          height_err_sense_obs_dim,
                          height_vel_sense_obs_dim)
from rl_move.robot_state import DEG2RAD, N_JOINTS
from .joint_task import SimHexapodJointGoalEnv
from .goal_task import GoalTrajectory
from .sim_env import N_OBS

try:
    import gymnasium as _gym
except Exception:  # pragma: no cover
    _gym = None

WALK_GOAL_DIM = GOAL_DIM + 2
N_VEL_OBS = 2             # measured body-frame vx, vy appended to obs
VEL_SCALE = 0.15          # m/s; matches the max commanded speed
K_WALK = 2.0              # kernel peak, ~2x the tilt-tracking kernel
SIGMA_V = 0.05            # m/s; kernel width
# Linear progress shaping (v2 fix): measured velocity projected onto the
# commanded direction, as a fraction of the commanded speed, capped at
# 1.25. The kernel alone had no gradient from "standing" to "walking" —
# run cw-walk (5M) plateaued at a 0.04 m/s shuffle because standing
# still collected the level-body kernel risk-free while the walk kernel
# paid ~nothing until tracking was already good. Every cm/s toward the
# goal now pays immediately; moving against the command costs.
K_PROG = 1.0

# Explicit joystick command schedules. ``legacy`` preserves the historical
# independent resampler exactly; ``stress_mix`` selects one of the concrete
# schedules per episode.
WALK_CMD_SCHEDULES = (
    "random_hold", "flip_180", "sweep_circle", "square", "stop_go",
    "jitter",
)
WALK_CMD_MODE_IDS = {"legacy": 0, **{
    name: i + 1 for i, name in enumerate(WALK_CMD_SCHEDULES)
}}

# In-run command curriculum for stress_mix (08-17, operator-approved
# fb_20260817T005114 item 7): the from-scratch joystick recipe threw
# every schedule family at a newborn policy at once, four arms died
# without ever surviving takeoff. goal.walk_cmd_stage (default -1 =
# off, stress_mix draw-stream bit-exact) restricts which families
# stress_mix may draw, CUMULATIVE so earlier skills stay in the mix:
#   stage 0: forward/back stepping only (flip_180 + stop_go, heading
#            forced to 0) — learn to survive and reverse;
#   stage 1: + headings / circles / squares (random_hold,
#            sweep_circle, square), full heading scope;
#   stage >=2: the full stress_mix family set (adds jitter).
# Transitions inside an episode stay INSTANTANEOUS (blend cfg is
# untouched); ramp the stage with the sched.* in-run scheduler
# (sched.key=goal.walk_cmd_stage) so promotion is by global steps.
WALK_CMD_STAGE_FAMILIES = (
    ("flip_180", "stop_go"),
    ("random_hold", "sweep_circle", "square"),
    ("jitter",),
)


def walk_cmd_track_score(vx: float, vy: float, vx_ref: float,
                         vy_ref: float, stop_speed_m_s: float = 0.03
                         ) -> tuple[float, float, float]:
    """Normalized physical command score and its two components.

    At the requested speed and direction the score is +1. A parked body is
    -1, equal-speed cross-track motion is -2, and equal-speed motion exactly
    backward is -3. For a stop command, stillness is 0 and motion is charged
    by speed relative to ``stop_speed_m_s``.
    """
    s_ref = math.hypot(vx_ref, vy_ref)
    if s_ref <= 1e-6:
        speed = math.hypot(vx, vy)
        scale = max(float(stop_speed_m_s), 1e-6)
        return -speed / scale, 0.0, speed
    ux, uy = vx_ref / s_ref, vy_ref / s_ref
    along = vx * ux + vy * uy
    cross = abs(ux * vy - uy * vx)
    score = (along - abs(along - s_ref) - cross) / s_ref
    return score, along, cross


def walk_freeprog_score(vx: float, vy: float, vx_ref: float,
                        vy_ref: float, cap_m_s: float = 0.06
                        ) -> tuple[float, float, float]:
    """Direction-first command score with NO target speed.

    Operator order 2026-08-21 (from-scratch anti-slip walking): the
    policy must travel in the COMMANDED DIRECTION; it does not have to
    hit a commanded speed. So this score pays travel along the command
    direction, saturating at ``cap_m_s`` (faster earns the same, and is
    never charged here), and charges cross-track and backward travel on
    the same scale. +1 = along-command at or above the cap, 0 = parked,
    -1 = pure backward (or pure cross-track) at/above the cap. Unlike
    ``walk_cmd_track_score`` there is no ``|along - s_ref|`` band term:
    the commanded vector sets the DIRECTION only. For a stop command
    (``s_ref`` ~ 0) stillness is 0 and motion is charged up to -1.
    """
    cap = max(float(cap_m_s), 1e-6)
    s_ref = math.hypot(vx_ref, vy_ref)
    if s_ref <= 1e-6:
        speed = math.hypot(vx, vy)
        return -min(speed / cap, 1.0), 0.0, speed
    ux, uy = vx_ref / s_ref, vy_ref / s_ref
    along = vx * ux + vy * uy
    cross = abs(ux * vy - uy * vx)
    a = min(max(along / cap, -1.0), 1.0)
    c = min(cross / cap, 1.0)
    return a - c, along, cross


WALK_DIRECTION_MIN_SPEED_M_S = 0.01


def walk_direction_error_deg(
        vx: float, vy: float, vx_ref: float, vy_ref: float,
        min_speed_m_s: float = WALK_DIRECTION_MIN_SPEED_M_S,
) -> float | None:
    """Angle between actual and commanded planar velocity.

    Returns None for stop commands and near-stationary motion, where a
    velocity direction is undefined. Otherwise the result is in [0, 180].
    """
    cmd_speed = math.hypot(vx_ref, vy_ref)
    speed = math.hypot(vx, vy)
    if cmd_speed <= 1e-6 or speed < max(float(min_speed_m_s), 0.0):
        return None
    cos_err = (vx * vx_ref + vy * vy_ref) / (speed * cmd_speed)
    return math.degrees(math.acos(min(max(cos_err, -1.0), 1.0)))


def _add_walk_direction_info(
        info: dict, vx: float, vy: float, vx_ref: float, vy_ref: float,
        min_speed_m_s: float,
) -> None:
    """Emit active-command direction telemetry into an env info dict."""
    if math.hypot(vx_ref, vy_ref) <= 1e-3:
        return
    err = walk_direction_error_deg(
        vx, vy, vx_ref, vy_ref, min_speed_m_s=min_speed_m_s)
    info["walk_direction_valid"] = 1.0 if err is not None else 0.0
    if err is not None:
        info["walk_direction_err_deg"] = float(err)
        info["walk_direction_wrong_way"] = 1.0 if err > 90.0 else 0.0


# Curriculum tables (moved verbatim to walk_curriculum.py 2026-08-29;
# pure constants, see that module's docstring).
from .walk_curriculum import (  # noqa: F401
    LP_BUCKETS,
    WALKCURR_BUCKETS,
    WALKCURR_BUCKETS_V2,
    WALKCURR_BUCKETS_V3,
    WALKCURR_BUCKETS_V4,
    WALKCURR_BUCKETS_V5,
    WALKCURR_BUCKETS_V6,
    WALKCURR_BUCKETS_V7,
    WALKCURR_BUCKETS_V8,
    WALKCURR_BUCKETS_V9,
    WALKCURR_BUCKETS_V10,
    WALKCURR_GATE_V2_IGNITION,
    WALKCURR_GATE_V2_QUALITY,
    WALKCURR_GATE_V3_BRIDGE,
    WALKCURR_GATE_V4_BRIDGE,
    WALKCURR_GATE_V4_JOYSTICK,
    WALKCURR_GATE_V5_BRIDGE,
    WALKCURR_GATE_V5_FAST,
    WALKCURR_GATE_V6_BRIDGE,
    WALKCURR_GATE_V6_JOYSTICK,
    WALKCURR_MIX,
)
# Phase-based alternating-tripod reward (Siekmann-style periodic reward
# composition, plan §Walk item c; enabled by goal.walk_phase_obs=1 +
# reward.k_phase_contact>0). An internal clock at goal.walk_phase_hz
# advances while a walk velocity is commanded; the policy SEES the clock
# (sin/cos appended to obs, +2 dims) and a modest reward pays contact
# states that agree with alternating tripods: PHASE_TRIPOD_A expected in
# stance while sin(phase) >= 0, the complement otherwise. NO joint
# targets, NO trajectories, NO hard constraint — a parked or dragged leg
# scores 50% agreement = zero net reward; only clock-synchronized
# stepping pays. Rationale: three penalty-style levers failed because
# PPO paid the fine rather than restructure the gait (flag, flagw,
# speedhi); this term makes stepping itself the paid behavior, densely,
# every tick.
N_PHASE_OBS = 2
PHASE_TRIPOD_A = (0, 2, 4)      # alternating tripod around the body
PHASE_HZ_DEFAULT = 1.0          # ~stride rate of the 0.02-0.06 lineage

# Speed-coupled phase clock (2026-08-22, amp M2 speedrange root cause;
# same fingerprint as joystick phasedir9-seed17): the clock above
# advances at a FIXED rate whenever any linear velocity is commanded,
# so commanded speed can never reach the actor's cadence — a 3x
# command range compressed to ~0.10+/-0.02 m/s realized in BOTH the
# fastphase (hz 1.333->2.0) and fastphase-nostyle (style weight 0)
# probes: neither a faster constant clock nor removing AMP style
# widened it. With goal.walk_phase_speed_scale=k (default 0.0 = OFF,
# bit-exact legacy), the effective clock rate becomes
#   hz_eff = hz_base * (1 + k * (s_ref / s_nom - 1))
# i.e. k=1 -> cadence fully proportional to commanded speed, anchored
# so s_ref == s_nom reproduces hz_base exactly (the teacher's cadence
# at its natural ~0.08 m/s). goal.walk_phase_speed_nom sets the
# anchor speed; goal.walk_phase_hz_max (default 0 = no clamp) caps
# the rate so extreme commands cannot demand physically impossible
# stepping. Consumers stay consistent by construction: obs sin/cos,
# the k_phase_contact agreement reward, and (via sim_env's
# bc_anchor_phase_lock branch) the walk BC anchor all read the same
# advanced phase.
PHASE_SPEED_NOM_DEFAULT = 0.08   # m/s; teacher's natural speed


def phase_hz_effective(hz_base, s_ref, k_coup,
                       s_nom=PHASE_SPEED_NOM_DEFAULT, hz_max=0.0):
    """Effective phase-clock rate under speed coupling.

    k_coup <= 0 (the default) returns hz_base exactly — legacy
    fixed-rate clock, bit-exact. s_ref == s_nom also returns hz_base
    exactly for any k_coup (anchor point). hz_max > 0 clamps the top;
    the result is never negative.
    """
    if k_coup <= 0.0 or s_ref <= 0.0:
        return hz_base
    ratio = s_ref / max(float(s_nom), 1e-6)
    hz = hz_base * (1.0 + k_coup * (ratio - 1.0))
    if hz_max > 0.0:
        hz = min(hz, hz_max)
    return max(hz, 0.0)


WZ_SCALE = 0.5            # rad/s; obs scale for the commanded yaw rate

# Explicit mode/command one-hot (obs.mode_onehot=1; RL_PLAN queue 2.4,
# the flagship-unified-policy prerequisite). Today the policy must
# INFER the commanded skill from the reference trajectory's shape (a
# hold and a zero-command walk look identical; rise vs lower only
# differ in the height ramp's sign, ticks later). The flagship
# multitask MDP gives the policy the mode as a direct input instead:
# a 6-wide one-hot appended at the very TAIL of each obs frame (after
# vel/phase/wz extras — same tail-append convention as wz_ref, so
# --obs-pad-transplant can still warm-start from any narrower
# champion). Default OFF: obs layout of every existing checkpoint is
# bit-exact unchanged.
#
# Slot order is FROZEN (append-only, like checkpoints): goal-mix modes
# map onto skill FAMILIES — attitude/stillness goals (hold/lean/track/
# unload) all light "hold"; raise (small up-ramp from plant) rides
# with "rise"; "turn" is RESERVED (de-scoped 08-11, no camera = no
# front) and never lit today so a future re-scope needs no width
# change. The leg one-hot (unload/lift) and vx/vy/wz refs still carry
# the WITHIN-mode command exactly as before.
MODE_ONEHOT_ORDER = ("hold", "rise", "lower", "walk", "turn", "quad")
N_MODE_OBS = len(MODE_ONEHOT_ORDER)
_MODE_FAMILY = {
    "hold": "hold", "lean": "hold", "track": "hold", "unload": "hold",
    "raise": "rise", "rise": "rise",
    "lower": "lower",
    "walk": "walk",
    # getup carries a velocity command and its own state-based stand
    # score — command-wise it is the walk family (vx/vy refs already
    # in the goal obs carry the within-mode command).
    "getup": "walk",
    # recover (recover_to_plant, 08-15 operator directive
    # fb_20260815T165306_606974): reach a full-height quiet six-loaded
    # stand from any recoverable state, zero velocity command
    # throughout — command-wise it is the rise family.
    "recover": "rise",
    "quad": "quad",
    # quadwalk = quad-family locomotion (08-13, quad track "four-leg
    # WALKING" spec): the quad one-hot bit + non-zero vx/vy refs carry
    # the within-mode command, exactly the walk-vs-hold convention.
    "quadwalk": "quad",
    # "turn" (09-04, standwalk item-2 escalation: the whole open-loop
    # BC-anchor-dose/geometry-scale lever family closed 8/8 FAIL, every
    # cell showing the SAME shared-representation signature — winning
    # combined-tick wz always costs pure-turn wz on the ONE shared walk
    # core). This un-reserves the slot the 08-11 comment above named as
    # future-proofing: it is never produced by a real goal-trajectory
    # mode string (no generator sets .mode="turn"), only synthesized
    # per-tick by mode_onehot_turn_cmd below, so this entry is a pure
    # ADDITION with no effect on any existing mode string lookup.
    "turn": "turn",
}


def mode_onehot(mode: str) -> np.ndarray:
    """6-wide skill-family one-hot for a goal-trajectory mode string.

    Unknown/missing modes map to "hold" (the zero-reference balance
    family) so an unconditioned probe can never light a motion bit.
    """
    out = np.zeros(N_MODE_OBS, dtype=float)
    fam = _MODE_FAMILY.get(str(mode), "hold")
    out[MODE_ONEHOT_ORDER.index(fam)] = 1.0
    return out


@dataclass
class WalkGoal(TaskGoal):
    """TaskGoal + commanded body-frame planar velocity (+ yaw rate)."""
    vx_ref: float = 0.0
    vy_ref: float = 0.0
    wz_ref: float = 0.0   # rad/s, +CCW; only in obs when walk_yaw_cmd=1

    def as_obs(self, cfg: dict) -> np.ndarray:
        # NOTE: the commanded yaw rate (wz_ref, walk_yaw_cmd lineage) is
        # deliberately NOT here — it is appended at the obs TAIL by
        # _augment_obs so --obs-pad-transplant 1 can warm-start a yaw
        # run from any non-yaw champion (transplant pads tail columns).
        base = super().as_obs(cfg)
        return np.concatenate(
            [base, [self.vx_ref / VEL_SCALE, self.vy_ref / VEL_SCALE]])


@dataclass
class WalkTrajectory(GoalTrajectory):
    """Constant-velocity command, eased in after a settle hold."""
    vx: np.ndarray = None  # (n_steps,) m/s
    vy: np.ndarray = None
    wz: np.ndarray = None  # (n_steps,) rad/s; None = no yaw channel
    cmd_mode: str = "legacy"
    duration_steps: int | None = None
    command_changes: int = 0

    def at(self, step: int) -> WalkGoal:
        i = min(max(step, 0), len(self.roll) - 1)
        return WalkGoal(roll_ref=float(self.roll[i]),
                        pitch_ref=float(self.pitch[i]),
                        height_ref=float(self.height[i]),
                        unload_leg=self.unload_leg,
                        lift_legs=self.lift_legs,
                        vx_ref=float(self.vx[i]),
                        vy_ref=float(self.vy[i]),
                        wz_ref=float(self.wz[i])
                        if self.wz is not None else 0.0)


def walk_yaw_init_wz_decision(vx_ref: float, vy_ref: float, wz_ref: float,
                              frac: float, scale: float,
                              draw: float) -> float:
    """Shared gating + arithmetic for the walkyaw RSI-style initial-wz
    curriculum lever (``goal.walk_yaw_init_wz_frac``/``_scale``, both
    default 0.0 = OFF; 2026-09-17, `OPERATOR_QUESTIONS.md` ~20:1x
    candidate (c) -- see `sim_env.SimHexapodBalanceEnv.
    _apply_walk_yaw_init_wz`'s docstring for the full rationale).

    Pure function, no rng/env access -- all three execution engines
    (CPU ``sim_env.py``, in-process ``mjx_vec_env.MjxVecEnv``, sharded
    ``mjx_sharded_vec_env`` workers) call this with exactly the same
    semantics, so it only needs testing once, here.

    ``draw``: a single U[0,1) sample the CALLER already drew from its
    OWN rng stream -- this function never draws, so every caller's own
    bit-exact-off / rng-stream-preserving guarantee (no draw at all when
    ``frac<=0``) stays entirely in the caller's hands.

    Returns 0.0 (a safe "not selected" sentinel -- a genuinely selected
    value is always ``scale*wz_ref`` with ``abs(wz_ref)>1e-3`` and
    ``scale!=0``, so it can never legitimately read exactly 0.0) unless:
    ``frac>0``, ``scale!=0``, the episode is a genuine turn-in-place
    tick (``hypot(vx_ref,vy_ref)<=1e-3`` and ``abs(wz_ref)>1e-3`` --
    identical gating to ``reward.walk_turn_kernel_neutral``/
    ``goal.walk_turn_yaw_bias_deg``), and ``draw<frac``.
    """
    if frac <= 0.0 or scale == 0.0:
        return 0.0
    if math.hypot(vx_ref, vy_ref) > 1e-3 or abs(wz_ref) <= 1e-3:
        return 0.0
    if draw >= frac:
        return 0.0
    return scale * wz_ref


def _wrap_goal(goal: TaskGoal | None) -> WalkGoal | None:
    """Give non-walk goals the widened obs with zero velocity refs."""
    if goal is None or isinstance(goal, WalkGoal):
        return goal
    return WalkGoal(roll_ref=goal.roll_ref, pitch_ref=goal.pitch_ref,
                    height_ref=goal.height_ref, unload_leg=goal.unload_leg,
                    lift_legs=goal.lift_legs)


# ---------------------------------------------------------------------------
# TRANSITION-WINDOW slip-charge accounting (`reward.k_walk_transition_slip`,
# 2026-09-07). Extracted to plain functions on plain (int, list[float])
# state — no MuJoCo, no task object — so the touchdown/liftoff state
# machine can be unit-tested directly with synthetic tick sequences
# (`rl_move/tests/test_task_semantics.py`,
# `test_wts_*`/`test_walkcurr_transition_touchdown_*`). Corrected per
# accounting review fb_20260907T185803_c8af66
# (rl_docs/tracks/walkcurr/STATUS.md 2026-09-07 19:03 UTC) against the
# `d250ae55` version that trained the `...-transwin-c1` canary pair:
#
# 1. The old touchdown-tick charge measured the raw XY delta from the
#    LAST AIRBORNE sample to the first CONTACT sample and charged the
#    whole thing as "loaded skid" -- but that interval straddles the
#    airborne/contact boundary, so a clean landing (foot arrives at its
#    intended spot and then does not move again once loaded) still paid
#    for ordinary swing-approach motion. Fixed by never charging the
#    touchdown tick itself; the live window now starts at the first
#    tick that is unambiguously loaded-to-loaded (this stance's tick 1
#    vs tick 0), which is exactly what `transition_window_tick` prices
#    below. To keep the same NUMBER of live ticks charged (not weaken
#    the dose), the countdown is seeded at the full `td_ticks` instead
#    of `td_ticks - 1`.
# 2. The old continuing-contact bookkeeping advanced the touchdown
#    countdown and trimmed the liftoff ring buffer ONLY on ticks whose
#    force cleared `wts_contact_n` -- so a low-force contact gap (foot
#    still "on" per the coarse 0.5 N floor, but below the stricter
#    measurement threshold) paused the window instead of aging it,
#    letting a stale high-excess sample or an already-exhausted
#    countdown survive far past the configured tick count.
#    `transition_window_tick` now advances (decrements the countdown,
#    appends+trims the ring buffer) on EVERY on-tick, padding the ring
#    buffer with 0.0 when the tick isn't confidently measurable so the
#    trailing window still ages in TICK time, not "meaningful-tick"
#    time.
def transition_window_touchdown(td_ticks: int) -> tuple[list, int]:
    """New stance bout: fresh (empty) liftoff ring buffer + a full
    ``td_ticks``-tick live-window countdown. Deliberately charges
    nothing here -- see note (1) above."""
    return [], int(td_ticks)


def transition_window_tick(td_count: int, lo_buf: list, *,
                            meaningful: bool, ex_w: float,
                            lo_ticks: int) -> tuple[int, list, float | None]:
    """One continuing-contact (already-on, was-already-on) tick's
    bookkeeping. ``meaningful`` = this tick's (and the previous tick's)
    contact force both clear the mechanism's own confidence threshold;
    ``ex_w`` = this tick's measured tangential-velocity excess (only
    trusted when ``meaningful``). Returns
    ``(new_td_count, new_lo_buf, live_charge_or_None)`` -- advances
    every on-tick per note (2) above, regardless of ``meaningful``.
    """
    charged = None
    if td_count > 0:
        td_count -= 1
        if meaningful:
            charged = ex_w
    lo_buf = lo_buf + [ex_w if meaningful else 0.0]
    if len(lo_buf) > lo_ticks:
        lo_buf = lo_buf[-lo_ticks:]
    return td_count, lo_buf, charged


def transition_window_liftoff(lo_buf: list) -> float | None:
    """Retrospective liftoff charge: the mean of whatever trailing
    on-tick samples (real or 0.0-padded) survived in the ring buffer --
    no lookahead, everything in it already happened. Per fb_
    20260907T185803_c8af66's third check: this is intentionally blind
    to anything that happens AFTER liftoff (airborne motion is never
    fed into ``lo_buf``), so two stances with identical loaded history
    but different first-airborne motion give the same charge."""
    if not lo_buf:
        return None
    return float(sum(lo_buf) / len(lo_buf))


# Per-LEG minimum-duty TERMINATION tick update (`safety.walk_leg_duty_
# terminate_s`, 2026-09-07; relative-floor add-on `..._floor_rel_frac`,
# 2026-09-07 ~22:5x). Extracted to a plain function on plain
# (list[float], list[float]) state -- no MuJoCo, no task object -- so
# the EMA/low-seconds state machine (and the new relative-floor
# arithmetic) can be unit-tested directly with synthetic per-leg
# on/off sequences instead of a physics rollout, exactly the
# `transition_window_*` precedent above. See the design rationale
# (heading-relative starvation an absolute floor tuned not to
# false-positive on passing gaits cannot catch) in `sim_env.py`'s own
# call site.
def walk_legduty_term_tick(
        ema: list, low_s: list, *, on: list, dt: float, tau_s: float,
        floor: float, floor_rel_frac: float, in_grace: bool,
) -> tuple[list, list, float]:
    """One tick's bookkeeping for all 6 legs. ``ema``/``low_s`` are the
    PREVIOUS tick's state (length-6 lists); ``on`` is this tick's 6
    binary contact readings. Returns ``(new_ema, new_low_s,
    worst_low_s)`` -- ``worst_low_s`` is the max consecutive-seconds-
    below-floor across all 6 legs, for the caller to compare against
    its own ``walk_leg_duty_terminate_s`` bound. ``floor_rel_frac=0.0``
    reproduces the plain absolute-floor-only path exactly (bit-exact
    legacy when the relative add-on is off)."""
    new_ema = [e + (dt / tau_s) * (float(o) - e) for e, o in zip(ema, on)]
    effective_floor = floor
    if floor_rel_frac > 0.0:
        team_mean = sum(new_ema) / 6.0
        effective_floor = max(floor, floor_rel_frac * team_mean)
    new_low_s = []
    worst = 0.0
    for e, prev_low in zip(new_ema, low_s):
        if in_grace:
            low = 0.0
        elif e < effective_floor:
            low = prev_low + dt
        else:
            low = 0.0
        new_low_s.append(low)
        if low > worst:
            worst = low
    return new_ema, new_low_s, worst


# Per-LEG duty-RATIO reward CHARGE (`reward.walk_leg_duty_ratio_charge`,
# 2026-09-08 -- the "duty-balance reward TARGET" scoped since 09-07
# ~23:2x/~23:4x as the only lever left after BOTH the per-tick-price
# class (11 mechanisms: walk_duty_gate, walk_swing_gate,
# walk_duty_band_gate, walk_gait_gate+k_step_event -- every one an
# INCOME-MULTIPLYING factor in [0,1]) and the termination class
# (safety.walk_leg_duty_terminate_s, 8/8) closed FAIL against the
# base(1g)/crossgrav chronic front-pair-or-middle-pair leg sacrifice.
# Deliberately a DIFFERENT SHAPE from both closed classes: an
# independent ADDITIVE per-tick penalty (never multiplies r_walk/
# r_prog/r_cmd_track, so it cannot be "simply outbid" by a fatter
# income term the way every closed *_gate factor could be, per each
# of their own closure notes) and no episode cutoff (so it cannot be
# "paid as ambient cost then move on" the way the termination's own
# firing-rate-rises-not-falls signature showed). Uses the CALIBRATED
# peer-excluded-mean ratio (STATUS.md 2026-09-07 ~23:4x zero-spend
# finding, 288 real gate-report episodes, 12 arms across the whole
# front-pair-pathology campaign + one clean baseline): ratio_i =
# duty_ema_i / mean(the OTHER five legs' duty_ema) -- a threshold in
# 0.22-0.24 separates >=299/300 episodes (87 flagged-sacrifice
# episodes' own worst ratio: p90 0.179; 213 passing episodes' own
# worst-leg ratio: min 0.222, p10 0.302). Default target 0.30 sits at
# that passing-population's own p10 (a genuinely-walking gait's
# worst leg should clear it; a sacrificed leg should not). Adapts to
# whatever relative activity level the gait has established that
# tick -- no heading-conditioned per-leg role table needed, same
# rationale as the (already-closed, termination-only)
# `walk_leg_duty_terminate_floor_rel_frac` add-on, but here wired as
# the reward-shaping TARGET that add-on's own commit message named as
# the still-open next build. Own EMA state (`_legduty_ratio_ema`),
# NOT shared with the termination feature's `_walk_legduty_ema`
# (sim_env.py) so this arm's dose can be swept without perturbing it.
def walk_legduty_ratio_tick(ema: list, *, on: list, dt: float,
                            tau_s: float) -> list:
    """One tick's EMA update for all 6 legs' own ground-contact duty.
    Same exponential form as `walk_legduty_term_tick`'s EMA (kept as
    an independent state copy). ``ema``/``on`` are length-6."""
    return [e + (dt / tau_s) * (float(o) - e) for e, o in zip(ema, on)]


def walk_legduty_ratio_charge(ema: list, target: float,
                               swing_counts: list | None = None,
                               swing_min_count: float = 0.0,
                               agg: str = "min",
                               ) -> tuple[float, list]:
    """Peer-excluded-mean duty ratio per leg and the WORST (max)
    shortfall below ``target`` across all 6 legs (i.e. the shortfall
    of whichever leg has the smallest ratio -- the same MIN-over-legs
    "one bad leg drags the whole score" convention every other
    anti-sacrifice mechanism in this file uses, expressed as a
    shortfall instead of a multiplicative factor). ``peer_mean``
    excludes the leg itself (sharpens the cut ~2x vs an including-self
    mean, per the calibration finding); guarded against an all-zero
    team with a small epsilon (returns ratio 1.0-ish, no spurious
    charge, rather than a division blowup).

    OPTIONAL swing-count floor (2026-09-08, the "different pricing
    design" the 0.30/0.45-dose FAIL verdicts named as the only
    remaining open branch): the 0.30/0.45 dose escalations showed a
    repeatable within-episode trade -- a flagged leg's ratio recovers
    above target (gait_valid flips True) while that SAME episode's
    slip gets worse, consistent with the leg raising its ground-
    contact DUTY by dragging/planting longer rather than by actually
    picking up and placing its foot (a real step). ``swing_counts``
    (trailing-window qualifying-swing event count per leg, same
    stride-filtered definition every other anti-drag gate in this
    file uses) lets the caller ZERO a leg's effective ratio credit if
    it hasn't completed >= ``swing_min_count`` real swings recently,
    regardless of how high its duty ratio has climbed -- a dragging
    leg cannot buy its way to zero shortfall by raising duty alone,
    it must also actually swing. Bit-exact vs the original 2-arg form
    when ``swing_counts`` is None or ``swing_min_count<=0`` (the
    default): ``eff_ratios`` degenerates to plain ``ratios``, no
    behavior change for any existing caller/dose.

    OPTIONAL aggregation mode (2026-09-08, ``agg``, default ``"min"``
    reproduces every prior dose/target/swing-floor arm byte-for-byte --
    all of them, and the entire termination-class/per-tick-price class
    before them, are now closed with no efficacy on the chronic
    front-PAIR sacrifice fingerprint (STATUS.md 2026-09-08 ~19:1x)).
    ``agg="sum"`` is the literal untested half of the calibration
    finding's own actionable spec ("summed (not maxed) over legs so it
    prices the observed multi-leg (front-PAIR) starvation shape") that
    every closed MIN-over-legs arm never exercised: MIN charges exactly
    the worse of two simultaneously-starved legs' shortfall, identical
    to what a SINGLE starved leg would draw at the same charge weight --
    it cannot structurally distinguish "one bad leg" from "two bad legs
    together" the pathology's own name (front-PAIR) describes. SUM
    charges every leg's own shortfall and adds them, so a genuine
    two-leg simultaneous sacrifice draws roughly double the single-leg
    price at the identical per-leg weight -- a different reachable
    gradient, not just a bigger dose (a plain weight increase on MIN
    would inflate a single-leg shortfall too; SUM only inflates when
    MULTIPLE legs are jointly below target, which is the specific shape
    every prior arm's own gate reports show, e.g. duty_cycle vectors
    naming 2 simultaneously-low legs, not 1). Reduces to the MIN value
    whenever at most one leg is below target (both aggregations agree
    on a single-bad-leg episode), so this only changes behavior on the
    exact multi-leg case it targets."""
    ratios = []
    for i in range(6):
        others = [e for j, e in enumerate(ema) if j != i]
        peer_mean = sum(others) / len(others)
        if peer_mean < 1e-6:
            ratios.append(1.0)
        else:
            ratios.append(ema[i] / peer_mean)
    eff_ratios = ratios
    if swing_counts is not None and swing_min_count > 0.0:
        eff_ratios = [
            (0.0 if float(swing_counts[i]) < swing_min_count else ratios[i])
            for i in range(6)
        ]
    if agg == "sum":
        charge = sum(max(0.0, target - r) for r in eff_ratios)
    else:
        charge = max(0.0, target - min(eff_ratios))
    return charge, ratios


# Per-LEG load-SLIP reward CHARGE (`reward.walk_leg_loadslip_ratio_
# charge`, 2026-09-08 -- the "load-slip" half of the "price per-leg
# utilization/load-slip directly" concrete lead the assistfade
# TRACK-LEVEL FINDING (09-07 ~14:5x) and walkcurr's own duty-ratio-
# charge closure name. The utilization half (walk_leg_duty_ratio_
# charge, contact-TIME based) and its swing-count-floor add-on are
# both now CLOSED (walkcurr: 3/3 dose/lineage reproductions null;
# assistfade: 2/2 seeds FAIL -- a chronically-planted leg's duty
# ratio recovers without it ever actually cycling). This is a
# DIFFERENT physical quantity: not how LONG a leg stays in contact,
# but how FAST its foot slides while it IS in contact (the existing
# per-tick `tangent_vels` measurement every k_foot_slip_tangent/
# k_walk_transition_slip mechanism already uses, mean-aggregated and
# REFUTED for general slip reduction 09-06/09-07 -- see the k_tslip/
# k_wts comments above). A chronically-planted, non-swinging leg
# that the body is still translating past MUST be sliding under
# load every tick that translation happens (it cannot "hold" a fixed
# ground point while the body moves out from under it without
# swinging) -- so this prices exactly the drag symptom the swing-
# floor's binary swing-count gate tried and failed to fix, using a
# continuous, physically-direct measurement instead of a count
# threshold. Same peer-excluded-mean-ratio shape as the duty-ratio
# charge (own EMA/own state, not shared), but INVERTED: high
# relative slip is bad (duty-ratio charges a shortfall BELOW target;
# this charges an excess ABOVE target, i.e. the WORST -- max, not
# min -- leg's ratio is what pays). Default target 1.5 (a leg
# sliding 50% faster than the mean of its five peers while loaded)
# is a fresh assume-and-go pick, NOT a population-calibrated
# threshold like duty-ratio's 0.30 (no equivalent 200+-episode
# calibration corpus exists yet for this quantity) -- record as such
# in any launch note; refine empirically if a canary's own telemetry
# shows the target too loose/tight. Default 0.0 = off, no state
# read, legacy bit-exact.
def walk_legslip_ratio_tick(ema: list, *, tv: list, dt: float,
                            tau_s: float) -> list:
    """One tick's EMA update for all 6 legs' own tangential (skid)
    velocity while loaded. ``tv`` is this tick's per-leg measured
    tangential velocity (m/s), 0.0 for any leg not in a measured
    stance contact this tick (same "off ticks decay the EMA toward
    the off value" convention as `walk_legduty_ratio_tick`, here 0
    instead of 0/1 contact). Same exponential form, independent
    state (`ema`/`tv` length-6, never shared with the duty-ratio
    charge's own EMA)."""
    return [e + (dt / tau_s) * (float(v) - e) for e, v in zip(ema, tv)]


def walk_legslip_ratio_charge(ema: list, target: float
                               ) -> tuple[float, list]:
    """Peer-excluded-MEDIAN slip-velocity ratio per leg and the WORST
    (max) excess above ``target`` across all 6 legs -- the leg
    sliding fastest relative to its peers is the one that pays,
    mirroring `walk_legduty_ratio_charge`'s worst-leg convention but
    on the opposite side (excess, not shortfall, since high relative
    slip is the bad direction here). Deliberately MEDIAN, not MEAN,
    of the other five legs (unlike the duty-ratio charge's own
    peer-excluded MEAN) -- a real-physics bank probe (2026-09-08)
    caught the mean version FALSE-POSITIVE-charging the honest
    walking legs whenever one leg was genuinely near-zero-slip (e.g.
    raised off the ground, not touching): a single near-zero outlier
    drags the MEAN of the other five down, which INFLATES every one
    of THOSE legs' own ratio (their ema is now divided by an
    artificially small peer figure) even though they are walking
    honestly -- exactly backwards from the duty-ratio charge, where
    a low-duty outlier deflating its peers' mean makes their (already
    healthy) ratios look even healthier, never triggers a false
    charge, because duty-ratio charges the MIN not the MAX. Because
    this charge is worst-is-MAX, the same "peer mean dragged down by
    one outlier" effect is dangerous rather than harmless here, and a
    median is robust to exactly the single-outlier case this
    mechanism must tolerate (a raised/unloaded leg is correctly
    NOT this mechanism's job -- that is `walk_leg_duty_ratio_charge`'s
    -- and must not spuriously blame a different, honestly-loaded
    leg). Guarded against an all-near-zero team (every leg quietly
    planted with no slip) with a small epsilon -- returns ratio 1.0
    (neutral, no spurious charge against a genuinely clean stance)
    rather than a division blowup or a false-positive charge."""
    ratios = []
    for i in range(6):
        others = [e for j, e in enumerate(ema) if j != i]
        others_sorted = sorted(others)
        mid = len(others_sorted) // 2
        if len(others_sorted) % 2 == 1:
            peer_med = others_sorted[mid]
        else:
            peer_med = 0.5 * (others_sorted[mid - 1] + others_sorted[mid])
        if peer_med < 1e-6:
            ratios.append(1.0)
        else:
            ratios.append(ema[i] / peer_med)
    worst_excess = max(0.0, max(ratios) - target)
    return worst_excess, ratios


# Per-LEG swing-INITIATION reward INCOME (`reward.walk_leg_swing_
# initiation_income`, 2026-09-08 -- the OTHER concrete lead the
# loadslip-ratio-charge closure named alongside swing-gap-charge: "a
# positive swing-initiation income for the currently-most-loaded leg"
# (CURRENT_TRUTHS/walkcurr STATUS.md 2026-09-08 ~19:1x). Pulled out as
# its own pure helper (mirroring `walk_legduty_ratio_charge`/
# `walk_legslip_ratio_charge` above) so the "was this leg the single
# most-loaded of all six" decision at the heart of the mechanism is
# unit-testable without a full env rollout -- see
# `rl_move/tests/test_walk_task.py`.
def walk_leg_swing_initiation_maxload(loads: list) -> list:
    """Per-leg bool: was ``loads[i]`` the single highest of all 6?
    Strict ``> 0`` guards the degenerate all-zero snapshot (nobody
    loaded yet, e.g. right at episode reset) from awarding a spurious
    "most loaded" claim to every leg at once; ties AT the max are all
    flagged True (a `>=` comparison, matching the "pay whoever is
    tied for heaviest" convention -- a genuine simultaneous tie is
    rare with continuous EMA floats but should not silently pick an
    arbitrary winner if it ever happens)."""
    worst = max(loads) if loads else 0.0
    return [ld > 1e-6 and ld >= worst for ld in loads]


# The walk-mode reward stack of _post_step lives in these sibling modules.
# They import the module-level constants/helpers defined ABOVE this line
# from walk_task, so the import has to sit here (after those definitions)
# rather than at the top of the file.
from . import walk_reward_charges  # noqa: E402
from . import walk_reward_gates  # noqa: E402
from . import walk_reward_yaw  # noqa: E402
from . import walk_reward_course  # noqa: E402
from . import walk_reward_progress  # noqa: E402
from . import walk_reward_stepevent  # noqa: E402
from . import walk_reward_recover  # noqa: E402
from . import walk_env_init  # noqa: E402

class SimHexapodJointWalkEnv(SimHexapodJointGoalEnv):
    """Joint-action goal env + walk mode (obs 59 + 11 + 2 vel feedback)."""

    # Modes the periodic eval isolates for this env (train_ppo_sim reads
    # this class attribute; "lean" dropped to keep eval time bounded —
    # lean is a subset of track).
    EVAL_MODES = ("hold", "track", "unload", "raise", "rise", "walk")

    # Per-episode walk bookkeeping the batched MJX vec env must carry in
    # its pooled reset-state snapshots (see mjx_vec_env.py).
    MJX_SNAPSHOT_EXTRA = ("_foot_on", "_liftoff_xy", "_liftoff_step",
                          "_foot_prev_xy", "_foot_prev_force",
                          "_foot_tan_slip_m", "_duty_hist",
                          "_dgate_hist", "_swing_gate_hist", "_phase",
                          "_anchor_xy", "_anchor_prev_on",
                          "_walk_bucket", "_step_disp_bank",
                          "_ls_prev_xy", "_ls_prev_on",
                          "_ls_slip_m", "_ls_prog_m",
                          "_ls_slip_ema", "_ls_prog_ema",
                          "_yaw_still_ema", "_yaw_prog_ema", "_stance_slip_acc",
                          "_walk_idle_ema", "_walk_idle_low_s",
                          "_walk_stop_cmd_s",
                          "_walk_qvel_ema", "_walk_course_ema",
                          "_walk_course_disp_hist",
                          "_walk_course_win_hist", "_walk_course_win_cum",
                          "_walk_kernel_vema", "_walk_kernel_wz_ema",
                          "_gait_last_step", "_gait_cmd_tick",
                          "_gait_gate_qfactor", "_wp", "_vel_est",
                          "_trans_td_count", "_trans_lo_buf",
                          "_walk_legduty_ema", "_walk_legduty_low_s",
                          "_legduty_ratio_ema", "_legduty_ratio_ticks",
                          "_legduty_ratio_swing_hist",
                          "_legslip_ratio_ema", "_legslip_ratio_ticks",
                          "_swing_gap_s", "_liftoff_was_maxload",
                          "_swinit_load_ema")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Walk probability lives on the generator so the eval callback's
        # p_<mode> isolation mechanism works unchanged. 0.70: run 1's
        # 0.40 diluted the hard skill with tasks the lineage had solved.
        self._goal_gen.p_walk = 0.70
        # quadwalk (08-13, quad track): commanded walking on the four
        # support legs with goal.quad_lift_legs raised. Default 0 =
        # never sampled; the _sample_goal cdf gains an EMPTY interval
        # so every legacy rng stream is bit-exact unchanged. Enable
        # per-run via --goal-mix quadwalk=<p>. The attribute must
        # exist (not just a getattr default) so the eval harness's
        # p_<mode> forcing can isolate the mode.
        self._goal_gen.p_quadwalk = 0.0
        # recover_to_plant (08-15, operator directive fb_20260815T165306
        # _606974): universal recovery to a quiet six-loaded stand.
        # Default 0 = never sampled; the _sample_goal cdf gains an EMPTY
        # interval so every legacy rng stream is bit-exact unchanged.
        # Enable per-run via --goal-mix recover=<p>.
        self._goal_gen.p_recover = 0.0
        # Adaptive reset-bank curriculum state (recover mode only).
        # PERSISTENT across episodes (like _lp_weights, NOT in
        # SNAP_ATTRS).  _rec_stats is certification-only: stochastic
        # PPO rollouts are deliberately too noisy to certify the 0.5 s
        # six-foot hold, so they must never advance the ladder.
        # _rec_rollout_stats remains visible as diagnostic telemetry.
        self._rec_stats = {}
        self._rec_cert_rounds = {}
        self._rec_rollout_stats = {}
        self._rec_rollout_counts = {}
        # Global MJX training batches are folded into this per-bucket
        # terminal-shortfall EMA by the trainer callback.  It affects only
        # replay probability; deterministic certification remains the sole
        # authority for admission.
        self._rec_training_error_stats = {}
        self._rec_external_certification = bool(float(cfg_get(
            self.cfg, "goal", "recover_external_certification",
            default=0.0)))
        # Recovery must prove the easy six-foot correction before floor
        # starts enter the diet.  any1 started with families 1+2 and also
        # probed family 3, so there was no bucket-1 acquisition phase to
        # measure.
        # _rec_active_n is the MONOTONIC number of unlocked buckets.
        # _rec_focus_bucket is the hardest unlocked acquisition bucket;
        # _rec_weak_bucket is the weakest previously certified bucket and
        # receives extra spaced-replay pressure.  Keeping these concepts
        # separate prevents a noisy assay from deleting learned starts.
        self._rec_active_n = 1
        self._rec_focus_bucket = 0
        self._rec_weak_bucket = None
        walk_env_init.init_reward_bookkeeping(self)
        walk_env_init.init_charge_ramps(self)
        walk_env_init.init_gait_gate_and_curriculum_state(self)
        walk_env_init.init_obs_and_mode_flags(self)
        if _gym is not None:
            self.observation_space = self._obs_space_box(
                N_OBS - 6 + self.n_act + WALK_GOAL_DIM + N_VEL_OBS
                + (N_PHASE_OBS if self._phase_obs else 0)
                + (1 if self._yaw_cmd else 0)
                + (N_MODE_OBS if self._mode_obs else 0)
                + (N_JOINTS if self._recover_plant_q_obs else 0)
                + (N_JOINTS if self._fault_obs else 0)
                + current_sense_obs_dim(self.cfg)
                + height_err_sense_obs_dim(self.cfg)
                + height_vel_sense_obs_dim(self.cfg))

    def _augment_obs(self, obs: np.ndarray, *,
                     reset: bool = False) -> np.ndarray:
        # Per-tick walk extras, applied via the base-env hook so the
        # obs-history stack (obs.history_frames) includes them in every
        # frame. goal.walk_obs_body_vel selects the source of the
        # "measured" velocity entries (obs WIDTH unchanged in all modes,
        # so checkpoints stay warm-start compatible):
        #   1.0 (default) — privileged simulator body velocity;
        #   0.0 — zeroed (policy infers velocity from qdot/gyro);
        #   2.0 — meas := ref, EXACTLY what the hardware runner feeds
        #         (board has no velocity estimate; 08-09 walk deploy).
        #         Required for deployment-equivalence arms — zeroing is
        #         a DIFFERENT contract than the robot's ref-copy.
        #   3.0 — DEPLOYABLE leg-odometry estimator
        #         (rl_move.estimator.LegOdometryVelocity, the probe-
        #         validated board-safe module): fed the OBSERVED state
        #         (DR-corrupted encoders + gyro + tilt — the robot's own
        #         view), so training sees hardware-realistic estimate
        #         error. Built 08-20 (fb_20260820T000059 item 3c audit:
        #         mode 2 carries ZERO body-velocity information by
        #         construction — the fast-profile canary could not even
        #         observe its own 2.5x overspeed; before 08-20 a cfg
        #         value of 3 silently fell into the privileged branch).
        #         Same obs WIDTH as every other mode.
        vel_mode = float(cfg_get(self.cfg, "goal", "walk_obs_body_vel",
                                 default=1.0))
        if vel_mode == 0.0:
            v = np.zeros(N_VEL_OBS)
        elif vel_mode == 2.0:
            goal = self._current_goal()
            v = (np.array([float(getattr(goal, "vx_ref", 0.0)),
                           float(getattr(goal, "vy_ref", 0.0))])
                 / VEL_SCALE) if goal is not None else np.zeros(N_VEL_OBS)
        elif vel_mode == 3.0:
            if reset or self._vel_est is None:
                from rl_move.estimator import LegOdometryVelocity
                self._vel_est = LegOdometryVelocity(dt=self.dt)
            st = self._state
            if st is not None:
                v_est = self._vel_est.update(
                    st.joint_position, st.imu_gyro,
                    st.imu_roll, st.imu_pitch)
            else:
                v_est = np.zeros(N_VEL_OBS)
            v = np.asarray(v_est, dtype=float) / VEL_SCALE
        else:
            v = self._body_vel_xy() / VEL_SCALE
        obs = np.concatenate([obs, v])
        if self._phase_obs:
            # Phase clock advance lives here (post-physics, pre-obs) so
            # obs and the phase-agreement reward in step() see the same
            # value — behavior identical to the pre-hook code for the
            # legacy walk_phase_obs=1 runs (all refuted/retired).
            if not reset:
                goal = self._current_goal()
                s_ref = (float(np.hypot(goal.vx_ref, goal.vy_ref))
                         if goal is not None else 0.0)
                run = s_ref > 1e-3
                if not run and float(cfg_get(
                        self.cfg, "goal", "walk_phase_run_on_yaw",
                        default=0.0)) > 0.0:
                    # Turn-in-place clock fix (amp M2-yaw, 08-22): the
                    # clock above only ran while a LINEAR velocity was
                    # commanded, so during turn-in-place segments
                    # (vx=vy=0, wz!=0) the phase obs FROZE — a
                    # phase-locked policy (every BC-clone lineage) then
                    # has no time-base to step with and parks. Measured:
                    # yawcmd + tip50-r2 + tip90 all show tip err ==
                    # |wz_ref| exactly (zero rotation at vx=0) while yaw
                    # WHILE TRANSLATING (clock running) did improve —
                    # exposure 0.5/0.9 gave zero dose-response because
                    # the skill was unlearnable with a frozen clock, not
                    # under-exposed. goal.walk_phase_run_on_yaw=1 also
                    # advances the clock while a yaw rate is commanded
                    # (default 0 = off, bit-exact legacy; pure-park
                    # segments with wz_ref=0 still freeze the clock).
                    run = abs(float(getattr(goal, "wz_ref", 0.0))
                              if goal is not None else 0.0) > 1e-3
                if run:
                    hz = float(cfg_get(self.cfg, "goal", "walk_phase_hz",
                                       default=PHASE_HZ_DEFAULT))
                    # Speed-coupled clock (default OFF = bit-exact
                    # legacy fixed rate; see phase_hz_effective).
                    k_coup = float(cfg_get(
                        self.cfg, "goal", "walk_phase_speed_scale",
                        default=0.0))
                    if k_coup > 0.0:
                        hz = phase_hz_effective(
                            hz, s_ref, k_coup,
                            s_nom=float(cfg_get(
                                self.cfg, "goal",
                                "walk_phase_speed_nom",
                                default=PHASE_SPEED_NOM_DEFAULT)),
                            hz_max=float(cfg_get(
                                self.cfg, "goal", "walk_phase_hz_max",
                                default=0.0)))
                    self._phase = (self._phase
                                   + 2.0 * math.pi * hz * self.dt) \
                        % (2.0 * math.pi)
            obs = np.concatenate(
                [obs, [math.sin(self._phase), math.cos(self._phase)]])
        if self._yaw_cmd:
            # Commanded yaw rate at the obs TAIL (see WalkGoal.as_obs
            # note): measured yaw rate is already in the gyro obs, so
            # only the reference is appended. Zero for non-walk goals
            # and during the settle hold.
            goal = self._current_goal()
            wz_ref = float(getattr(goal, "wz_ref", 0.0)) \
                if goal is not None else 0.0
            obs = np.concatenate([obs, [wz_ref / WZ_SCALE]])
        if self._mode_obs:
            # Skill-family one-hot, constant per episode, re-derived
            # every tick from _goal_traj (already in mjx_host.SNAP_ATTRS
            # — pool-restore safe by construction, no new episode attr).
            mode = (getattr(self._goal_traj, "mode", "hold")
                    if self._goal_traj is not None else "hold")
            if (self._mode_cmd
                    and _MODE_FAMILY.get(str(mode), "hold") == "walk"):
                # Command-derived slot (obs.mode_onehot_cmd=1): follow
                # the LIVE blended command so the dual-core GRU routes
                # stop segments to the stance core. Derived per tick
                # from _current_goal() like the wz_ref tail above —
                # pool-restore safe by construction, no episode attr.
                # During the settle hold / ramp-from-zero the command
                # IS near zero, so those ticks route to the stance
                # core too — the commanded behavior there is standing.
                goal = self._current_goal()
                vx = float(getattr(goal, "vx_ref", 0.0)) \
                    if goal is not None else 0.0
                vy = float(getattr(goal, "vy_ref", 0.0)) \
                    if goal is not None else 0.0
                wz = float(getattr(goal, "wz_ref", 0.0)) \
                    if goal is not None else 0.0
                stopped = (abs(vx) <= 0.005 and abs(vy) <= 0.005
                           and abs(wz) <= 0.02)
                obs = np.concatenate(
                    [obs, mode_onehot("hold" if stopped else "walk")])
            elif (self._mode_turn_cmd
                    and _MODE_FAMILY.get(str(mode), "hold") == "walk"):
                # Pure-turn command-derived slot (obs.mode_onehot_
                # turn_cmd=1, see __init__ note): same _current_goal()
                # per-tick read as the branch above, but a DIFFERENT
                # partition — pure-turn ticks (not stop ticks) get
                # their own "turn" bit, matching sim_env.py's
                # _bc_pure_turn threshold exactly (1e-3, not the
                # 0.005 m/s / 0.02 rad/s stop thresholds, which are a
                # separate, coarser stop-detection tuned for the
                # hold/walk split above).
                goal = self._current_goal()
                vx = float(getattr(goal, "vx_ref", 0.0)) \
                    if goal is not None else 0.0
                vy = float(getattr(goal, "vy_ref", 0.0)) \
                    if goal is not None else 0.0
                wz = float(getattr(goal, "wz_ref", 0.0)) \
                    if goal is not None else 0.0
                pure_turn = (math.hypot(vx, vy) <= 1e-3
                             and abs(wz) > 1e-3)
                obs = np.concatenate(
                    [obs, mode_onehot("turn" if pure_turn else "walk")])
            else:
                obs = np.concatenate([obs, mode_onehot(mode)])
        if self._recover_plant_q_obs:
            mode = (getattr(self._goal_traj, "mode", "hold")
                    if self._goal_traj is not None else "hold")
            q_plant = np.zeros(N_JOINTS, dtype=float)
            if mode == "recover" and self._state is not None:
                qs = float(cfg_get(self.cfg, "obs", "q_scale",
                                   default=1.0))
                q_plant = ((self._state.joint_position
                            - self._plant_deg * DEG2RAD)
                           / max(qs, 1e-6))
            obs = np.concatenate([obs, q_plant])
        if self._fault_obs:
            er = getattr(self, "_ep_rand", None)
            fh = (er.fault_health() if er is not None
                  else np.ones(N_JOINTS, dtype=np.float32))
            obs = np.concatenate([obs, fh])
        return obs.astype(np.float32)

    def _reset_begin(self, seed: int | None = None):
        walk_env_init.reset_reward_bookkeeping(self)
        return super()._reset_begin(seed)

    def _reset_finalize(self):
        obs, info = super()._reset_finalize()
        if self.walk_probe_on:
            self._walk_probe_start()
        return obs, info

    # ------------------------------------------------------------------
    # In-env walk quality probe (walk_probe_on; measurement only).
    # Same formulas as train_ppo_transfer.eval_task's external loop,
    # with ONE sourcing difference: foot XY comes from the pad BODIES
    # (self._pad_bids — mirrored per tick into the MJX shims' FakeData,
    # exactly what the reward stack reads) instead of the foot sites
    # (which the batched backend does not mirror). Identical code runs
    # on the C env and both MJX vec envs, so cert numbers are directly
    # comparable across backends.

    def _walk_probe_start(self) -> None:
        self._wp = dict(
            tr=tuple(self._tilt_ref0),
            sat_limit=0.98 * self.safety.max_dq,
            prev_cmd=self.safety._last_safe.copy(),
            prev_on=None, prev_xy=[None] * 6,
            peak_roll=0.0, peak_pitch=0.0, peak_gyro=0.0,
            slip=0.0, sw=0, sat_jt=0, sat_all=0,
            sw_foot=[0] * 6, on_ticks=0,
            h0=float(self.data.xpos[self._chassis_bid, 2]),
            xy0=self.data.xpos[self._chassis_bid, :2].copy(),
            h_sum=0.0, vx_se=0.0, vy_se=0.0, wz_se=0.0, vx_n=0,
            cmd_dist=0.0, prog_m=0.0, cross_m=0.0,
            stop_v_sum=0.0, stop_ticks=0,
            stop_v_sum_settled=0.0, stop_ticks_settled=0,
            stop_v_sum_pure=0.0, stop_ticks_pure=0,
            stop_seg_s=0.0,
            head_ticks=int(round(2.0 / self.dt)),
            ret=0.0, n=0)

    def _walk_probe_tick(self, reward: float, term: bool, trunc: bool,
                         info: dict) -> None:
        w = self._wp
        w["ret"] += reward
        w["n"] += 1
        n = w["n"]
        st = self._state
        w["peak_roll"] = max(w["peak_roll"],
                             abs(st.imu_roll - w["tr"][0]))
        w["peak_pitch"] = max(w["peak_pitch"],
                              abs(st.imu_pitch - w["tr"][1]))
        w["peak_gyro"] = max(w["peak_gyro"],
                             float(np.max(np.abs(st.imu_gyro[:2]))))
        cmd = self.safety._last_safe
        n_sat = int(np.sum(np.abs(cmd - w["prev_cmd"])
                           >= w["sat_limit"]))
        w["sat_jt"] += n_sat
        w["sat_all"] += int(n_sat >= 6)
        w["prev_cmd"] = cmd.copy()
        on: list[bool] = []
        for f in range(6):
            adr = self._touch_adr[f]
            is_on = bool(adr >= 0
                         and float(self.data.sensordata[adr]) > 0.5)
            b = self._pad_bids[f]
            xy = self.data.xpos[b, :2].copy() if b >= 0 else None
            if w["prev_on"] is not None:
                if is_on != w["prev_on"][f]:
                    w["sw"] += 1
                    w["sw_foot"][f] += 1
                if (is_on and w["prev_on"][f] and xy is not None
                        and w["prev_xy"][f] is not None):
                    w["slip"] += float(np.hypot(*(xy - w["prev_xy"][f])))
            w["prev_xy"][f] = xy
            on.append(is_on)
            w["on_ticks"] += int(is_on)
        w["prev_on"] = on
        w["h_sum"] += float(self.data.xpos[self._chassis_bid, 2])
        vxr = getattr(self._goal_traj, "vx", None)
        if vxr is not None:
            j = min(max(n - 1, 0), len(vxr) - 1)
            vyr = getattr(self._goal_traj, "vy", None)
            wzr = getattr(self._goal_traj, "wz", None)
            vx_meas, vy_meas = self._body_vel_xy()
            vx_c = float(vxr[j])
            vy_c = float(vyr[j]) if vyr is not None else 0.0
            w["vx_se"] += (vx_c - float(vx_meas)) ** 2
            w["vy_se"] += (vy_c - float(vy_meas)) ** 2
            wz_c = float(wzr[j]) if wzr is not None else 0.0
            w["wz_se"] += (wz_c - float(self._body_wz())) ** 2
            w["vx_n"] += 1
            s_ref = float(np.hypot(vx_c, vy_c))
            w["cmd_dist"] += s_ref * self.dt
            if s_ref > 1e-6:
                w["prog_m"] += ((float(vx_meas) * vx_c
                                 + float(vy_meas) * vy_c) / s_ref
                                * self.dt)
                w["cross_m"] += ((float(vy_meas) * vx_c
                                  - float(vx_meas) * vy_c) / s_ref
                                 * self.dt)
                w["stop_seg_s"] = 0.0
            else:
                # Elapsed time already spent in THIS stop segment
                # before this tick (2026-08-24, joyfullcurr10
                # cert-methodology audit: the legacy `stop_v_sum`/
                # `stop_ticks` below count every stop tick from the
                # very first one, with no per-segment settle
                # exemption -- unlike the reward's own
                # `reward.walk_stop_grace_s`, which explicitly ramps
                # the stop charges' multiplier 0->1 over the first
                # grace window because that transient is an
                # unavoidable physical deceleration, not creep. That
                # asymmetry means dosing the reward charge can only
                # ever discipline the POST-grace ticks the cert
                # already weights identically to the pre-grace ones,
                # so a dose-insensitive `stop_speed_m_s` plateau does
                # not by itself prove the creep is unshapeable --
                # `goal.walk_stop_settle_s` (default 0.0, additive
                # metric only, legacy `stop_v_sum`/`stop_ticks` path
                # below is untouched) lets an offline read exclude the
                # first N seconds of each stop segment the same way,
                # surfacing `stop_speed_settled_m_s` for comparison.
                seg_s_before = w["stop_seg_s"]
                w["stop_seg_s"] = seg_s_before + self.dt
                if n > w["head_ticks"]:
                    w["stop_v_sum"] += float(np.hypot(vx_meas, vy_meas))
                    w["stop_ticks"] += 1
                    settle_s = float(cfg_get(
                        self.cfg, "goal", "walk_stop_settle_s",
                        default=0.0))
                    if seg_s_before >= settle_s:
                        w["stop_v_sum_settled"] += float(
                            np.hypot(vx_meas, vy_meas))
                        w["stop_ticks_settled"] += 1
                    # stop_speed_pure_m_s (2026-08-24, certfreeze-v8
                    # dig-in): the cert-time hold supervisor
                    # (_walk_stop_freeze_override) EXEMPTS any tick
                    # with wz_ref != 0 ("a nonzero turn IS the
                    # commanded motion") -- but a V7+ walkcurr bucket's
                    # stop_frac and wz_zero_frac draws are independent
                    # rng calls on the SAME resampled segment, so a
                    # "stop" segment (vx=vy=0) can also carry wz != 0
                    # about half the time in any bucket that trains
                    # the wz diet. The legacy stop_v_sum/stop_ticks
                    # above count every such tick uniformly, so the
                    # freeze can never bring their average under a
                    # cert bar the freeze itself only ever half-
                    # applies. This purely-additive metric (bit-exact
                    # equal to stop_speed_m_s whenever wz is never
                    # commanded nonzero during a stop, i.e. every
                    # pre-V7 table and every V7+ bucket with
                    # wz_max=0) excludes ticks where |wz_ref| exceeds
                    # the SAME 1e-3 threshold the freeze override
                    # uses, so a cert wired to this field agrees with
                    # the freeze about what counts as "commanded
                    # still."
                    if abs(wz_c) <= 1e-3:
                        w["stop_v_sum_pure"] += float(
                            np.hypot(vx_meas, vy_meas))
                        w["stop_ticks_pure"] += 1
        if term or trunc:
            info["walk_probe"] = self._walk_probe_summary(bool(term))

    def _walk_probe_summary(self, term: bool) -> dict:
        w, nan = self._wp, float("nan")
        n = max(w["n"], 1)
        rad2deg = 180.0 / math.pi
        xyN = self.data.xpos[self._chassis_bid, :2]
        vx_n = w["vx_n"]
        # Body-height telemetry vs the SAME anchor the reward gate uses
        # (z0 + goal.height_ref; walk_height_gate block below). Emitted
        # unconditionally so cert panels can show the crouch depth and
        # the income factor a gated run would keep, whether or not the
        # gate is enabled (operator order fb_20260818T085648_2a0a60:
        # body-height/height-factor on B0 cert + all W&B panels).
        goal = self._current_goal()
        h_ref = float(getattr(goal, "height_ref", 0.0))
        h_err_m = (w["h_sum"] / n - self._z0) - h_ref
        sig_m = float(cfg_get(self.cfg, "reward",
                              "walk_height_sigma_mm",
                              default=30.0)) / 1000.0
        height_factor = math.exp(
            -0.5 * (h_err_m / max(sig_m, 1e-6)) ** 2)
        return {
            "h_err_mm": h_err_m * 1000.0,
            "height_factor": height_factor,
            "return": w["ret"], "ep_len": float(w["n"]),
            "survival_s": float(w["n"] * self.dt),
            "command_changes": float(getattr(
                self._goal_traj, "command_changes", 0)),
            "early_term": float(term),
            "peak_roll_deg": w["peak_roll"] * rad2deg,
            "peak_pitch_deg": w["peak_pitch"] * rad2deg,
            "peak_gyro_dps": w["peak_gyro"] * rad2deg,
            "slip_m": w["slip"],
            "fwd_m": float(np.hypot(*(xyN - w["xy0"]))),
            "contact_sw_per_s": w["sw"] / max(w["n"] * self.dt, 1e-9),
            "slew_sat": w["sat_jt"] / max(w["n"] * 18, 1),
            "slew_sat_all": w["sat_all"] / n,
            "mean_h_m": w["h_sum"] / n,
            "dh_m": (float(self.data.xpos[self._chassis_bid, 2])
                     - w["h0"]),
            "vx_rmse": (float(np.sqrt(w["vx_se"] / vx_n))
                        if vx_n else nan),
            "vy_rmse": (float(np.sqrt(w["vy_se"] / vx_n))
                        if vx_n else nan),
            "wz_rmse_dps": (float(np.sqrt(w["wz_se"] / vx_n)) * rad2deg
                            if vx_n else nan),
            "cmd_prog_m": w["prog_m"],
            "cmd_prog_frac": (w["prog_m"] / w["cmd_dist"]
                              if w["cmd_dist"] > 0.01 else nan),
            "slip_per_m": w["slip"] / max(w["prog_m"], 0.05),
            "cross_track_frac": (abs(w["cross_m"]) / w["cmd_dist"]
                                 if w["cmd_dist"] > 0.01 else nan),
            "wrong_way": (float(w["prog_m"] < 0.0)
                          if w["cmd_dist"] > 0.01 else nan),
            "stop_speed_m_s": (w["stop_v_sum"] / w["stop_ticks"]
                               if w["stop_ticks"] else nan),
            "stop_speed_settled_m_s": (
                w["stop_v_sum_settled"] / w["stop_ticks_settled"]
                if w["stop_ticks_settled"] else nan),
            "stop_ticks_settled_frac": (
                w["stop_ticks_settled"] / w["stop_ticks"]
                if w["stop_ticks"] else nan),
            "stop_speed_pure_m_s": (
                w["stop_v_sum_pure"] / w["stop_ticks_pure"]
                if w["stop_ticks_pure"] else nan),
            "stop_ticks_pure_frac": (
                w["stop_ticks_pure"] / w["stop_ticks"]
                if w["stop_ticks"] else nan),
            "foot_sw_min_per_s": (min(w["sw_foot"])
                                  / max(w["n"] * self.dt, 1e-9)),
            # Per-leg switch-rate breakdown (2026-09-14, assistfade
            # per-leg residual-fade lever, STATUS.md 09-14 "fade per-
            # leg instead of one global blend"): the SAME per-foot
            # tallies foot_sw_min_per_s already reduces via min() --
            # additive, purely new key, does not change any existing
            # field. Leg order matches mirror.py's N_LEGS convention
            # (action index 3*leg + axis), the same order self.
            # _touch_adr/self._pad_bids already iterate in.
            "foot_sw_per_s": [s / max(w["n"] * self.dt, 1e-9)
                             for s in w["sw_foot"]],
            "duty_factor": w["on_ticks"] / max(w["n"] * 6, 1),
        }

    # ------------------------------------------------------------------
    # Adaptive competence+retention walk-command curriculum
    # (goal.walk_curriculum=1; WALKCURR_BUCKETS/WALKCURR_MIX above).
    # Same contract as the recover-mode ladder: sampling weights are
    # derived env-side from certification results, the trainer is the
    # only writer of those results (deterministic held-out assays,
    # broadcast to every env), stochastic rollouts can never move the
    # frontier, and locked future buckets are never trained.

    def _walkcurr_prepare_episode(self) -> None:
        gen = self._goal_gen
        if float(getattr(gen, "p_walk", 0.0)) != 1.0:
            raise ValueError(
                "goal.walk_curriculum=1 requires a pure walk diet "
                f"(p_walk=1.0, got {getattr(gen, 'p_walk', 0.0)}); the "
                "curriculum owns the whole command distribution")
        if float(cfg_get(self.cfg, "goal", "mode_seq",
                         default=0.0)) > 0.0:
            raise ValueError("goal.walk_curriculum is incompatible "
                             "with goal.mode_seq")
        force = getattr(self, "force_walk_curr_bucket", None)
        if force is not None:
            b = int(force)
            if not 0 <= b < len(self._wc_table):
                raise ValueError(f"force_walk_curr_bucket {b} out of "
                                 f"range 0..{len(self._wc_table) - 1}")
        else:
            b = self._walkcurr_draw_bucket()
        self._wc_bucket = b
        dr = float(self._wc_table[b]["dr"])
        self.randomizer = self._walkcurr_randomizer(dr)

    def _walkcurr_draw_bucket(self) -> int:
        w = self._walkcurr_weights()
        r = float(self.rng.random())
        return int(np.searchsorted(np.cumsum(w), r,
                                   side="right").clip(0, len(w) - 1))

    def _walkcurr_weights(self) -> np.ndarray:
        """Sampling mixture over UNLOCKED buckets only (operator spec):
        50% frontier, 25% weakest mastered, 15% uniform mastered, 10%
        the rung just prior to the frontier. With no mastered buckets
        every component folds back to the frontier. Locked buckets
        (index >= active_n) get exactly zero mass by construction."""
        n = max(1, int(self._wc_active_n))
        frontier = n - 1
        w = np.zeros(n, dtype=float)
        w[frontier] += WALKCURR_MIX["frontier"]
        mastered = list(range(frontier))
        if mastered:
            weakest = min(
                mastered,
                key=lambda b: self._wc_results.get(
                    b, {}).get("score", float("inf")))
            w[weakest] += WALKCURR_MIX["weakest"]
            for b in mastered:
                w[b] += WALKCURR_MIX["uniform"] / len(mastered)
            w[frontier - 1] += WALKCURR_MIX["prior"]
        else:
            w[frontier] += (WALKCURR_MIX["weakest"]
                            + WALKCURR_MIX["uniform"]
                            + WALKCURR_MIX["prior"])
        return w / w.sum()

    def _walkcurr_randomizer(self, scale: float):
        """Per-bucket DomainRandomizer (cached), with the same cfg
        dr.* absolute-override semantics as sim_env.__init__."""
        key = round(float(scale), 6)
        r = self._wc_randomizers.get(key)
        if r is None:
            from .domain_rand import DomainRandomizer
            r = DomainRandomizer.from_params(self.params, scale=key)
            for _k, _v in (self.cfg.get("dr") or {}).items():
                if not hasattr(r.ranges, _k):
                    raise ValueError(f"unknown DR override dr.{_k}")
                if isinstance(_v, str):
                    _parts = tuple(float(x) for x in _v.split(","))
                    _v = _parts[0] if len(_parts) == 1 else _parts
                setattr(r.ranges, _k, _v)
            self._wc_randomizers[key] = r
        return r

    def apply_walkcurr_certification(self, bucket: int, passed: bool,
                                     score: float,
                                     cert_round: int) -> dict:
        """Record one bucket's deterministic held-out assay (trainer
        broadcast; the ONLY write path into the curriculum). ``score``
        is a continuous competence proxy (cert cmd_prog_frac) used only
        to pick the weakest mastered bucket for replay pressure."""
        bucket = int(bucket)
        if not 0 <= bucket < len(self._wc_table):
            raise ValueError(f"unknown walkcurr bucket {bucket}")
        self._wc_results[bucket] = {
            "passed": bool(passed), "score": float(score),
            "cert_round": int(cert_round)}
        return dict(self._wc_results[bucket], bucket=bucket)

    def walkcurr_update_admission(self, cert_round: int) -> dict:
        """Promote ONLY if the frontier AND every retained bucket
        passed a FRESH assay of this cert round. Never time-based."""
        n = int(self._wc_active_n)
        frontier = n - 1
        rows = {}
        for b in range(n):
            row = self._wc_results.get(b)
            fresh = (row is not None
                     and row.get("cert_round") == int(cert_round))
            rows[b] = {"passed": bool(fresh and row["passed"]),
                       "fresh": bool(fresh),
                       "score": (float(row["score"]) if row is not None
                                 else float("nan"))}
        frontier_passed = rows[frontier]["passed"]
        retained_failed = [b for b in range(frontier)
                           if not rows[b]["passed"]]
        retention_passed = not retained_failed
        promoted = False
        if (frontier_passed and retention_passed
                and self._wc_active_n < len(self._wc_table)):
            self._wc_active_n += 1
            promoted = True
        return {
            "cert_round": int(cert_round),
            "frontier_bucket": frontier,
            "frontier_passed": bool(frontier_passed),
            "retention_passed": bool(retention_passed),
            "retained_failed_buckets": retained_failed,
            "promoted": bool(promoted),
            "active_n": int(self._wc_active_n),
            "buckets": rows,
        }

    def walkcurr_state(self) -> dict:
        """Serializable telemetry snapshot (weights + results)."""
        w = self._walkcurr_weights()
        frontier = self._wc_active_n - 1
        mastered = list(range(frontier))
        weakest = (min(mastered,
                       key=lambda b: self._wc_results.get(
                           b, {}).get("score", float("inf")))
                   if mastered else -1)
        return {
            "total_buckets": len(self._wc_table),
            "active_n": int(self._wc_active_n),
            "frontier_bucket": int(frontier),
            "weakest_mastered": int(weakest),
            "sample_probabilities": {str(b): float(p)
                                     for b, p in enumerate(w)},
            "results": {str(b): dict(r)
                        for b, r in self._wc_results.items()},
        }

    def apply_drag_allow_frac(self, frac: float) -> dict:
        """Move the live drag_stance allowance to ``frac`` of the ramp
        (0 = loose/noisy-safe start, 1 = the cfg target allowance);
        trainer-driven — see the ``reward.drag_stance_allow_ramp_steps``
        block in ``__init__``. Mirrors ``apply_profile_ramp_frac``'s
        contract exactly: raises when the ramp is not armed, so a
        broadcast that silently no-ops is never a hidden failure mode.
        """
        if self._drag_allow_ramp is None:
            raise RuntimeError(
                "apply_drag_allow_frac called but reward."
                "drag_stance_allow_ramp_steps is not set (>0) in this "
                "env's cfg — the drag-allow ramp is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        s = self._drag_allow_ramp["start_m"]
        t = self._drag_allow_ramp["target_m"]
        self._drag_allow_override_m = s + f * (t - s)
        self._drag_allow_ramp["frac"] = f
        return {"frac": f, "allow_mm": self._drag_allow_override_m * 1000.0}

    def apply_walk_charge_frac(self, frac: float) -> dict:
        """Move the live dense-walk-charge scale to ``frac`` of the
        ramp (0 = walk_charge_ramp_min_frac of every scaled charge,
        1 = the full bank-proven dose); trainer-driven — see the
        ``reward.walk_charge_ramp_steps`` block in ``__init__``.
        Mirrors ``apply_drag_allow_frac``'s contract exactly:
        raises when the ramp is not armed, so a broadcast that
        silently no-ops is never a hidden failure mode.
        """
        if self._walk_charge_ramp is None:
            raise RuntimeError(
                "apply_walk_charge_frac called but reward."
                "walk_charge_ramp_steps is not set (>0) in this "
                "env's cfg — the walk-charge ramp is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        m = self._walk_charge_ramp["min_frac"]
        self._walk_charge_override = m + f * (1.0 - m)
        self._walk_charge_ramp["frac"] = f
        return {"frac": f, "charge_scale": self._walk_charge_override}

    def _walk_charge_scale(self) -> float:
        """Live scale on the three discovery-friction walk charges
        (k_park_duty, k_walk_idle_charge, k_walk_heading — see the
        walk-charge ramp block in ``__init__``; k_loadslip_excess is
        excluded and never scaled): 1.0 (bit-exact legacy / full
        bank-proven dose) unless the trainer has broadcast a ramp
        frac."""
        ov = self._walk_charge_override
        return 1.0 if ov is None else ov

    def apply_loadslip_bootstrap_frac(self, frac: float) -> dict:
        """Move the live k_loadslip_excess scale to ``frac`` of the
        bootstrap (0 = walk_loadslip_bootstrap_min_frac of the
        bank-proven charge, 1 = full dose); trainer-driven — see the
        ``reward.walk_loadslip_bootstrap_steps`` block in ``__init__``.
        Mirrors ``apply_walk_charge_frac``'s contract exactly: raises
        when the bootstrap is not armed, so a broadcast that silently
        no-ops is never a hidden failure mode."""
        if self._ls_bootstrap is None:
            raise RuntimeError(
                "apply_loadslip_bootstrap_frac called but reward."
                "walk_loadslip_bootstrap_steps is not set (>0) in "
                "this env's cfg — the loadslip bootstrap is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        m = self._ls_bootstrap["min_frac"]
        self._ls_bootstrap_override = m + f * (1.0 - m)
        self._ls_bootstrap["frac"] = f
        return {"frac": f, "excess_scale": self._ls_bootstrap_override}

    def _loadslip_excess_scale(self) -> float:
        """Live scale on k_loadslip_excess (see the loadslip-bootstrap
        block in ``__init__``): 1.0 (bit-exact legacy / full
        bank-proven dose) unless the trainer has broadcast a bootstrap
        frac."""
        ov = self._ls_bootstrap_override
        return 1.0 if ov is None else ov

    def walkcurr_checkpoint_state(self) -> dict:
        """State paired with a promotion checkpoint (rollback/resume)."""
        return {"active_n": int(self._wc_active_n),
                "results": {str(b): dict(r)
                            for b, r in self._wc_results.items()}}

    def restore_walkcurr_checkpoint_state(self, state: dict) -> None:
        active_n = int(state["active_n"])
        if not 1 <= active_n <= len(self._wc_table):
            raise ValueError(f"invalid walkcurr active_n {active_n}")
        self._wc_active_n = active_n
        self._wc_results = {
            int(b): {"passed": bool(r["passed"]),
                     "score": float(r["score"]),
                     "cert_round": int(r["cert_round"])}
            for b, r in dict(state["results"]).items()}

    def _sample_walk_curr(self) -> WalkTrajectory:
        """Curriculum walk episode: the stashed bucket's spec fully
        defines the command distribution (legacy goal.walk_cmd_* keys
        are ignored while the curriculum owns sampling). Command
        grammar matches the legacy sampler: 1 s zero hold + 1 s ramp,
        then optional resampled segments with blends and stops."""
        b = self._wc_bucket
        if b is None:
            raise RuntimeError("walkcurr episode without a prepared "
                               "bucket (reset ordering bug)")
        spec = self._wc_table[b]
        n = self.episode_steps + 1
        rng = self.rng
        duration_steps = int(round(float(spec.get(
            "duration_s", self.episode_steps * self.dt)) / self.dt))
        command_n = min(n, duration_steps + 1)
        command_changes = 0

        def draw_cmd() -> tuple[float, float]:
            speed = float(rng.uniform(spec["s_lo"], spec["s_hi"]))
            if spec["head_hi"] <= 0.0:
                ang = 0.0
            else:
                mag = float(rng.uniform(spec["head_lo"],
                                        spec["head_hi"]))
                ang = mag if rng.random() < 0.5 else -mag
            return speed * math.cos(ang), speed * math.sin(ang)

        vx_t, vy_t = draw_cmd()
        hold_n = max(1, int(round(1.0 / self.dt)))
        ramp_n = max(1, int(round(1.0 / self.dt)))
        vx = np.full(n, vx_t)
        vy = np.full(n, vy_t)
        vx[:hold_n] = 0.0
        vy[:hold_n] = 0.0
        end = min(hold_n + ramp_n, n)
        vx[hold_n:end] = np.linspace(0.0, vx_t, end - hold_n)
        vy[hold_n:end] = np.linspace(0.0, vy_t, end - hold_n)
        rs_s = float(spec["resample_s"])
        # V7 stress-diet extras (walk_task.py WALKCURR_BUCKETS_V7
        # banner): missing on every V1-V6 bucket, so `.get` defaults
        # keep this branch a true no-op (zero extra rng draws) for
        # every pre-existing table.
        wz_max = float(spec.get("wz_max", 0.0))
        wz_zero_frac = float(spec.get("wz_zero_frac", 1.0))
        reversal_frac = float(spec.get("reversal_frac", 0.0))
        wz = np.zeros(n) if wz_max > 0.0 else None
        if rs_s > 0.0:
            jit = float(spec["jitter"])
            bl_lo, bl_hi = float(spec["blend_lo"]), float(spec["blend_hi"])

            def seg_len() -> int:
                s = rs_s if jit <= 0.0 \
                    else rs_s * float(rng.uniform(1.0 - jit, 1.0 + jit))
                return max(1, int(round(max(s, self.dt) / self.dt)))

            def blend_len() -> int:
                bl = bl_lo if bl_hi <= bl_lo \
                    else float(rng.uniform(bl_lo, bl_hi))
                if bl <= 0.0:
                    return 0
                return max(1, int(round(max(bl, self.dt) / self.dt)))

            cvx, cvy, cwz = vx_t, vy_t, 0.0
            i = hold_n + ramp_n + seg_len()
            while i < command_n:
                if rng.random() < float(spec["stop_frac"]):
                    nvx = nvy = 0.0
                elif reversal_frac > 0.0 and rng.random() < reversal_frac:
                    # Bucket-diet analogue of stress_mix's flip_180: an
                    # instantaneous full reversal of the current
                    # command (the joygate's dominant held-out failure
                    # mode, over_current on stop/reverse, is never
                    # PRACTICED by the plain V6 sampler).
                    nvx, nvy = -cvx, -cvy
                else:
                    nvx, nvy = draw_cmd()
                n_blend = blend_len()
                end_b = min(i + n_blend, command_n)
                if n_blend:
                    vx[i:end_b] = np.linspace(cvx, nvx, end_b - i)
                    vy[i:end_b] = np.linspace(cvy, nvy, end_b - i)
                vx[end_b:command_n] = nvx
                vy[end_b:command_n] = nvy
                cvx, cvy = nvx, nvy
                if wz is not None:
                    nwz = (0.0 if rng.random() < wz_zero_frac
                          else float(rng.uniform(-wz_max, wz_max)))
                    if n_blend:
                        wz[i:end_b] = np.linspace(cwz, nwz, end_b - i)
                    wz[end_b:command_n] = nwz
                    cwz = nwz
                command_changes += 1
                i += seg_len()
        zeros = np.zeros(n)
        self._walk_bucket = None
        traj = WalkTrajectory(mode="walk", roll=zeros, pitch=zeros,
                              height=zeros, unload_leg=None,
                              start_at="plant", vx=vx, vy=vy, wz=wz,
                              cmd_mode="walkcurr",
                              duration_steps=duration_steps,
                              command_changes=command_changes)
        return traj

    def set_walk_bucket_weights(self, w) -> None:
        """LP-curriculum hook (called via VecEnv.env_method)."""
        w = np.clip(np.asarray(w, dtype=float), 0.0, None)
        s = float(w.sum())
        self._lp_weights = (w / s) if s > 0 else None

    def _sample_walk(self) -> WalkTrajectory:
        if self._wc_on:
            # Adaptive curriculum owns the whole command distribution
            # (bucket stashed by _walkcurr_prepare_episode pre-DR).
            return self._sample_walk_curr()
        n = self.episode_steps + 1
        rng = self.rng
        # Command range is configurable for speed curricula: cw-walk2-gait
        # doubled stride but plateaued at ~0.045 m/s while commands ran to
        # 0.12 — mostly-unreachable commands mean the tracking kernel never
        # engages. A narrowed range makes tracking learnable first.
        s_lo = float(cfg_get(self.cfg, "goal", "walk_speed_min_m_s",
                             default=0.03))
        s_hi = float(cfg_get(self.cfg, "goal", "walk_speed_max_m_s",
                             default=0.12))
        self._walk_bucket = None
        if float(cfg_get(self.cfg, "goal", "walk_lp_curriculum",
                         default=0.0)) == 1.0:
            # Bucketed command sampling; weights come from the LP
            # callback via set_walk_bucket_weights (uniform until the
            # first update, and always uniform in the eval harness).
            w = self._lp_weights
            if w is None:
                w = np.full(len(LP_BUCKETS), 1.0 / len(LP_BUCKETS))
            b = int(rng.choice(len(LP_BUCKETS), p=w))
            self._walk_bucket = b
            speed = float(rng.uniform(*LP_BUCKETS[b]))
        else:
            speed = float(rng.uniform(s_lo, s_hi))
        # Command-heading scope (operator rulings 2026-08-09 §2/§5:
        # rear hemisphere DEFERRED; current phase is forward /
        # forward-diagonal only). goal.walk_heading_max_rad >= 0 caps
        # |heading| at that angle (0 = pure forward; pi/4 = the ruled
        # fwd-diagonal promotion scope). Default -1 = legacy 60% fwd /
        # 20% +-45deg / 20% anywhere mix, draw-stream exact.
        h_max = float(cfg_get(self.cfg, "goal", "walk_heading_max_rad",
                              default=-1.0))
        # Discrete commanded-heading SET (operator staged-curriculum
        # order 2026-08-22, fb_20260822T032514: forward-only first,
        # then a SMALL HEADING SET, then full fixed headings — never
        # full +-180 from tick zero). goal.walk_heading_set, a JSON
        # list of radians (--cfg-set 'goal.walk_heading_set=[0,0.7854,
        # -0.7854]') or a comma-separated string, draws the episode
        # heading uniformly FROM THE SET and overrides
        # walk_heading_max_rad; mid-episode resamples (draw_heading
        # below) use the same set. Default "" = off: no draw happens,
        # every legacy rng stream is bit-exact.
        h_set_raw = cfg_get(self.cfg, "goal", "walk_heading_set",
                            default="")
        if isinstance(h_set_raw, (list, tuple)):
            h_set = [float(x) for x in h_set_raw]
        elif isinstance(h_set_raw, str) and h_set_raw.strip():
            h_set = [float(x) for x in h_set_raw.split(",")]
        else:
            h_set = []
        if h_set:
            ang = h_set[int(rng.integers(len(h_set)))]
        elif h_max >= 0.0:
            ang = 0.0 if h_max == 0.0 \
                else float(rng.uniform(-h_max, h_max))
        else:
            r = rng.random()
            if r < 0.60:
                ang = 0.0                               # forward
            elif r < 0.80:
                ang = float(rng.uniform(-math.pi / 4, math.pi / 4))
            else:
                ang = float(rng.uniform(-math.pi, math.pi))  # anywhere
        cmd_mode = str(cfg_get(self.cfg, "goal", "walk_cmd_mode",
                               default="legacy")).strip().lower()
        # goal.walk_cmd_stage curriculum (see WALK_CMD_STAGE_FAMILIES
        # above): only shapes stress_mix draws; default -1 keeps the
        # legacy uniform family choice draw-stream bit-exact.
        stage_f = float(cfg_get(self.cfg, "goal", "walk_cmd_stage",
                                default=-1.0))
        stage0 = False
        if cmd_mode == "stress_mix":
            if stage_f >= 0.0:
                s = min(int(stage_f), len(WALK_CMD_STAGE_FAMILIES) - 1)
                fams = tuple(f for tier in WALK_CMD_STAGE_FAMILIES[:s + 1]
                             for f in tier)
                cmd_mode = str(rng.choice(fams))
                if s == 0:
                    stage0 = True
                    ang = 0.0    # pure forward/back stepping first
            else:
                cmd_mode = str(rng.choice(WALK_CMD_SCHEDULES))
        elif cmd_mode != "legacy" and cmd_mode not in WALK_CMD_SCHEDULES:
            raise ValueError(
                f"unknown goal.walk_cmd_mode={cmd_mode!r}; expected "
                f"legacy, stress_mix, or one of {WALK_CMD_SCHEDULES}")
        vx_t, vy_t = speed * math.cos(ang), speed * math.sin(ang)
        # Opening-command shape (2026-09-05 operator walkscratch pilot):
        # the legacy hardcoded 1 s zero-hold + 1 s ramp lets the K_WALK
        # Gaussian kernel pay ~K_WALK/tick for STANDING STILL during the
        # opening stop (freeprog only replaces the kernel when
        # s_ref > 1e-3), a ~200-reward windfall at 100 Hz that every
        # from-scratch walkcurr arm banked before earning its first
        # movement income. goal.walk_cmd_hold_s / goal.walk_cmd_ramp_s
        # make both durations configurable; 0 means the full command is
        # active from tick 0 (no stop segment, no kernel windfall, the
        # freeprog/kernel income prices motion immediately). Default
        # -1.0 = the legacy max(1, round(1/dt)) shape, bit-exact for
        # every existing lineage (no rng is drawn either way).
        _hold_s = float(cfg_get(self.cfg, "goal", "walk_cmd_hold_s",
                                default=-1.0))
        _ramp_s = float(cfg_get(self.cfg, "goal", "walk_cmd_ramp_s",
                                default=-1.0))
        hold_n = (max(0, int(round(_hold_s / self.dt))) if _hold_s >= 0.0
                  else max(1, int(round(1.0 / self.dt))))
        ramp_n = (max(0, int(round(_ramp_s / self.dt))) if _ramp_s >= 0.0
                  else max(1, int(round(1.0 / self.dt))))
        vx = np.full(n, vx_t)
        vy = np.full(n, vy_t)
        vx[:hold_n] = 0.0
        vy[:hold_n] = 0.0
        end = min(hold_n + ramp_n, n)
        vx[hold_n:end] = np.linspace(0.0, vx_t, end - hold_n)
        vy[hold_n:end] = np.linspace(0.0, vy_t, end - hold_n)
        zeros = np.zeros(n)
        # Yaw-rate command (goal.walk_yaw_cmd=1; all draws gated so
        # legacy rng streams are untouched). Per segment: zero with
        # p=walk_yaw_zero_frac (heading-hold — the drift fix pays it),
        # else uniform +-walk_yaw_max_rad_s. Drawn independently of the
        # linear command, so stop segments with wz != 0 are TURN IN
        # PLACE episodes for free.
        wz = None
        wz_max = float(cfg_get(self.cfg, "goal", "walk_yaw_max_rad_s",
                               default=0.3))
        wz_zero_frac = float(cfg_get(self.cfg, "goal", "walk_yaw_zero_frac",
                                     default=0.5))

        def draw_wz() -> float:
            if rng.random() < wz_zero_frac:
                return 0.0
            return float(rng.uniform(-wz_max, wz_max))

        if self._yaw_cmd:
            wz_t = draw_wz()
            wz = np.full(n, wz_t)
            wz[:hold_n] = 0.0
            wz[hold_n:end] = np.linspace(0.0, wz_t, end - hold_n)
        # Mid-episode command resampling (operator wishlist 2026-08-09:
        # "walking around and changing direction"; default 0 = off, rng
        # stream unchanged). Every walk_cmd_resample_s seconds draw a
        # new (speed, heading) within the same scope and blend to it
        # over 1 s; with walk_stop_frac probability a segment is a full
        # stop — the policy learns start/steer/stop transitions instead
        # of one frozen command per episode.
        rs_s = float(cfg_get(self.cfg, "goal", "walk_cmd_resample_s",
                             default=0.0))
        if rs_s > 0.0:
            stop_frac = float(cfg_get(self.cfg, "goal", "walk_stop_frac",
                                      default=0.15))

            def draw_heading() -> float:
                if stage0:
                    return 0.0   # stage-0 curriculum: fwd/back only
                if h_set:
                    return h_set[int(rng.integers(len(h_set)))]
                if h_max >= 0.0:
                    return 0.0 if h_max == 0.0 \
                        else float(rng.uniform(-h_max, h_max))
                r = rng.random()
                if r < 0.60:
                    return 0.0
                if r < 0.80:
                    return float(rng.uniform(-math.pi / 4, math.pi / 4))
                return float(rng.uniform(-math.pi, math.pi))

            # Joystick realism (operator, 08-09): a human on a stick flips
            # commands at IRREGULAR intervals with near-INSTANT transitions.
            # walk_cmd_resample_jitter j draws each segment length uniform
            # in [rs_s*(1-j), rs_s*(1+j)]; walk_cmd_blend_s_min/max draw
            # each transition's blend time (default 1.0/1.0 = legacy fixed
            # 1 s ramp; set min 0.1 for flick-like flips). Defaults leave
            # every existing lineage's rng stream unchanged.
            jit = float(cfg_get(self.cfg, "goal", "walk_cmd_resample_jitter",
                                default=0.0))
            bl_lo = float(cfg_get(self.cfg, "goal", "walk_cmd_blend_s_min",
                                  default=1.0))
            bl_hi = float(cfg_get(self.cfg, "goal", "walk_cmd_blend_s_max",
                                  default=1.0))

            def seg_len() -> int:
                s = rs_s if jit <= 0.0 \
                    else rs_s * float(rng.uniform(1.0 - jit, 1.0 + jit))
                return max(1, int(round(max(s, self.dt) / self.dt)))

            def blend_len() -> int:
                b = bl_lo if bl_hi <= bl_lo \
                    else float(rng.uniform(bl_lo, bl_hi))
                if b <= 0.0:
                    return 0
                return max(1, int(round(max(b, self.dt) / self.dt)))

            cvx, cvy = vx_t, vy_t
            cwz = float(wz[min(end, n - 1)]) if wz is not None else 0.0
            if cmd_mode == "sweep_circle":
                period_s = max(float(cfg_get(
                    self.cfg, "goal", "walk_cmd_sweep_period_s",
                    default=12.0)), self.dt)
                sweep_sign = -1.0 if rng.random() < 0.5 else 1.0
                idx = np.arange(max(n - end, 0), dtype=float)
                theta = ang + sweep_sign * 2.0 * math.pi * (
                    idx * self.dt / period_s)
                vx[end:] = speed * np.cos(theta)
                vy[end:] = speed * np.sin(theta)
            else:
                square_sign = None
                if cmd_mode == "square":
                    square_sign = -1.0 if rng.random() < 0.5 else 1.0
                stop_next = True
                i = hold_n + ramp_n + seg_len()
                while i < n:
                    if cmd_mode in ("legacy", "random_hold"):
                        if rng.random() < stop_frac:
                            nvx = nvy = 0.0
                        else:
                            s2 = float(rng.uniform(s_lo, s_hi))
                            a2 = draw_heading()
                            nvx = s2 * math.cos(a2)
                            nvy = s2 * math.sin(a2)
                    elif cmd_mode == "flip_180":
                        nvx, nvy = -cvx, -cvy
                    elif cmd_mode == "square":
                        a2 = math.atan2(cvy, cvx) + (
                            square_sign * math.pi / 2.0)
                        s2 = max(math.hypot(cvx, cvy), s_lo)
                        nvx = s2 * math.cos(a2)
                        nvy = s2 * math.sin(a2)
                    elif cmd_mode == "stop_go":
                        if stop_next:
                            nvx = nvy = 0.0
                        else:
                            s2 = float(rng.uniform(s_lo, s_hi))
                            a2 = draw_heading()
                            nvx = s2 * math.cos(a2)
                            nvy = s2 * math.sin(a2)
                        stop_next = not stop_next
                    else:  # jitter
                        a2 = math.atan2(cvy, cvx) + float(rng.uniform(
                            -float(cfg_get(
                                self.cfg, "goal", "walk_cmd_jitter_rad",
                                default=0.25)),
                            float(cfg_get(
                                self.cfg, "goal", "walk_cmd_jitter_rad",
                                default=0.25))))
                        s2 = float(rng.uniform(s_lo, s_hi))
                        nvx = s2 * math.cos(a2)
                        nvy = s2 * math.sin(a2)
                    n_blend = blend_len()
                    end_b = min(i + n_blend, n)
                    if n_blend:
                        vx[i:end_b] = np.linspace(cvx, nvx, end_b - i)
                        vy[i:end_b] = np.linspace(cvy, nvy, end_b - i)
                    vx[end_b:] = nvx
                    vy[end_b:] = nvy
                    cvx, cvy = nvx, nvy
                    if wz is not None:
                        nwz = draw_wz()
                        if n_blend:
                            wz[i:end_b] = np.linspace(
                                cwz, nwz, end_b - i)
                        wz[end_b:] = nwz
                        cwz = nwz
                    i += seg_len()
        # Commanded gait height (operator wishlist 2026-08-09: walk in a
        # HIGHER or LOWER stance; default 0 = today's nominal walk).
        # goal.walk_height_off_mm ramps the height ref alongside the
        # velocity ramp; the shared height kernel already rewards
        # tracking it (same machinery as raise/rise/lower).
        h_off = float(cfg_get(self.cfg, "goal", "walk_height_off_mm",
                              default=0.0)) / 1000.0
        height = zeros
        if h_off != 0.0:
            height = np.full(n, h_off)
            height[:hold_n] = 0.0
            height[hold_n:end] = np.linspace(0.0, h_off, end - hold_n)
        # Park-basin reset diversity (goal.walk_park_start_frac, default
        # 0.0 = feature off): with probability f the episode STARTS in
        # a tripod-park posture (three hips lifted; pose built env-side
        # in sim_env reset). Rationale (cycle 24): the sto park persisted
        # at the SAME seed index through lowent->h15b->c1->kgate even
        # after kernel gating cut the park's return ~1250 -> 274/ep —
        # pricing is refuted; park-adjacent states are simply too RARE
        # (1/6 episodes, entered at t~1 s) for PPO's gradient to teach an
        # exit. Making them common at reset densifies exactly that
        # gradient. The draw is taken unconditionally so the rng stream
        # shifts identically whether or not the feature is enabled at
        # the same frac.
        park_frac = float(cfg_get(self.cfg, "goal", "walk_park_start_frac",
                                  default=0.0))
        start_at = "park" if rng.random() < park_frac else "plant"
        # Turn-in-place curriculum (operator direction 08-10: the fix
        # for the structural left drift is COMMAND EXPOSURE, not more
        # price tuning). Under independent sampling, turn-in-place
        # states are ~7.5% of segments — too rare for PPO to learn
        # the skill it is being scored on. goal.walk_turn_in_place_frac
        # (default 0 = off, rng stream unchanged): with probability f
        # the WHOLE episode becomes a dedicated turn — zero linear
        # command, guaranteed non-trivial yaw command with a 50/50
        # sign draw (both directions get equal exposure by
        # construction; the drift direction can never dominate the
        # curriculum). Applied LAST so it overrides resample segments.
        tip_frac = float(cfg_get(self.cfg, "goal",
                                 "walk_turn_in_place_frac", default=0.0))
        if self._yaw_cmd and tip_frac > 0.0 and rng.random() < tip_frac:
            vx[:] = 0.0
            vy[:] = 0.0
            # Keep the head-replacement targets consistent: a gait
            # spawn drawn below must CONTINUE this turn-in-place
            # command, not resurrect the discarded linear draw
            # (pre-existing latent interaction — no prior config ran
            # tip_frac and gait_start_frac together).
            vx_t = 0.0
            vy_t = 0.0
            mag = float(rng.uniform(0.5 * wz_max, wz_max))
            wz_t = mag if rng.random() < 0.5 else -mag
            wz = np.full(n, wz_t)
            wz[:hold_n] = 0.0
            wz[hold_n:end] = np.linspace(0.0, wz_t, end - hold_n)
            start_at = "plant"
        # Mid-stride reset diversity (TALL LADDER T6: RSI-for-walk,
        # 08-11 eve). Five reward-side arms (ref ladder, income gate,
        # gate+budget, k_height 3x/10x, speed relief) all left the
        # mid-gait posture pinned at −72..−75 mm below spawn — while
        # every episode already SPAWNS tall at the plant. The policy
        # knows tall STANDING; it has never been inside a tall
        # mid-stride WALKING state, so no pricing can select for one
        # (same shape as the park persistence above: pricing refuted →
        # densify the missing states at reset). goal.walk_gait_start_frac
        # (default 0 = off, conditional draw keeps legacy rng streams
        # bit-exact): with prob f the episode spawns MID-STRIDE in the
        # scripted tripod gait's tall pose (built env-side in sim_env
        # reset from this trajectory's command) and the walk command is
        # active from the start (0.3 s ramp, no hold — the point is
        # CONTINUING a tall walk, not re-entering it from a stand).
        gait_frac = float(cfg_get(self.cfg, "goal",
                                  "walk_gait_start_frac", default=0.0))
        if (gait_frac > 0.0 and start_at == "plant"
                and rng.random() < gait_frac):
            start_at = "gait"
            # Replace only the hold+ramp HEAD (any resampled segments
            # after it are preserved).
            ramp_fast = max(1, int(round(0.3 / self.dt)))
            head = min(max(end, ramp_fast), n)
            vx[:head] = vx_t
            vy[:head] = vy_t
            vx[:ramp_fast] = np.linspace(0.0, vx_t, ramp_fast)
            vy[:ramp_fast] = np.linspace(0.0, vy_t, ramp_fast)
            # Turn-state reset densification (08-23): when
            # goal.walk_gait_spawn_wz > 0 (default 0 = off, legacy
            # commands and rng streams bit-exact) the yaw command is
            # ALSO live from the start (same 0.3 s fast ramp), matching
            # the mid-rotation spawn pose sim_env builds from traj.wz —
            # otherwise the policy would wake up turning under a zero
            # yaw command it is then scored against.
            spawn_wz = float(cfg_get(self.cfg, "goal",
                                     "walk_gait_spawn_wz", default=0.0))
            if spawn_wz > 0.0 and wz is not None:
                wz_tgt = float(wz[min(head, n - 1)])
                wz[:head] = wz_tgt
                wz[:ramp_fast] = np.linspace(0.0, wz_tgt, ramp_fast)
            if h_off != 0.0:
                height[:head] = h_off
                height[:ramp_fast] = np.linspace(0.0, h_off, ramp_fast)
        return WalkTrajectory(mode="walk", roll=zeros, pitch=zeros,
                              height=height, unload_leg=None,
                              start_at=start_at, vx=vx, vy=vy, wz=wz,
                              cmd_mode=cmd_mode)

    def _sample_quadwalk(self) -> WalkTrajectory:
        """QUADWALK mode (quad track, 08-13 spec): commanded planar
        walking on the four support legs with the front pair
        (goal.quad_lift_legs) raised as hands.

        Command interface = walk's (vx/vy refs + the goal one-hot
        lighting the lift legs; obs width unchanged, mode one-hot
        family "quad"). The walk reward block prices it with lift-leg
        exemptions (park-duty window and step/swing credit skip the
        lift legs) PLUS the quad clear/plant income, so an honest
        rear-four gait out-earns a six-leg walk, a fronts-down drag
        and a freeze — pinned by the QUADWALK semantics bank.

        Fixed command shape: slower command band than walk (0.02-0.05
        m/s; four feet, smaller support polygon), forward only, a 2 s
        settle head (the fronts must lift before the ramp — matches
        goal.quad_grace_s + ramp), heading-hold yaw, no mid-episode
        resample.
        """
        n = self.episode_steps + 1
        rng = self.rng
        vx_t = float(rng.uniform(0.02, 0.05))
        vy_t = 0.0
        hold_n = max(1, int(round(2.0 / self.dt)))
        ramp_n = max(1, int(round(1.0 / self.dt)))
        vx = np.full(n, vx_t)
        vy = np.full(n, vy_t)
        vx[:hold_n] = 0.0
        vy[:hold_n] = 0.0
        end = min(hold_n + ramp_n, n)
        vx[hold_n:end] = np.linspace(0.0, vx_t, end - hold_n)
        vy[hold_n:end] = np.linspace(0.0, vy_t, end - hold_n)
        zeros = np.zeros(n)
        wz = np.zeros(n) if self._yaw_cmd else None
        # Spawn kind (08-13, quad track, after cw-quadwalk1/2/3): from
        # the legacy six-foot "plant" start the warm-started six-leg
        # walk basin survives both 3x lift income AND a live per-tick
        # ground-contact charge worth ~40% of episode return (verdict
        # chain in rl_docs/runs/cw-quadwalk{1,2,3}.md) — pricing is an
        # exhausted lever class; the blocker is exploration. "quad"
        # spawns the episode ALREADY IN the fronts-tucked four-leg
        # stance (built env-side in sim_env._reset_begin, kind
        # "quadstance") so rear-four stepping is the natural thing to
        # try and six-leg walking requires actively planting the
        # charged fronts. Default "plant" = legacy bit-exact (same
        # start_at literal, no extra rng draw).
        start = str(cfg_get(self.cfg, "goal", "quadwalk_start",
                            default="plant"))
        if start not in ("plant", "quad"):
            raise ValueError(
                f"goal.quadwalk_start must be 'plant' or 'quad', "
                f"got {start!r}")
        return WalkTrajectory(mode="quadwalk", roll=zeros, pitch=zeros,
                              height=zeros, unload_leg=None,
                              lift_legs=tuple(getattr(
                                  self._goal_gen, "quad_legs", (0, 5))),
                              start_at=("quadstance" if start == "quad"
                                        else "plant"),
                              vx=vx, vy=vy, wz=wz)

    # GETUP start-kind mix (see _sample_getup): random legal tangle,
    # belly-zero, partial curl, crouch, plant, tripod park. The pose
    # itself is built env-side in sim_env._reset_begin ("any" branch).
    GETUP_START_KINDS = (("tangle", 0.30), ("zero", 0.20),
                         ("partial", 0.20), ("crouch", 0.10),
                         ("plant", 0.10), ("park", 0.10))

    def _sample_getup(self) -> WalkTrajectory:
        """GETUP mode (operator 08-11: "from any position I want the
        robot to get to zero pose, stand up and walk around").

        One episode = one unified recover→stand→walk MDP: spawn
        ANYWHERE along the pipeline (GETUP_START_KINDS above), a
        quiet command head (recover + stand first), then a
        joystick-style velocity schedule with stops. There are NO
        tilt/height references and no ramp schedule — all pricing is
        the state-based staged stand score in _post_step (REWARD.md
        §4b). Falls are recoverable states: runs enabling this mode
        must widen safety.max_roll/pitch_deg (e.g. 60°).

        Hooks (bank/canary only, not cfg keys): force_getup_start
        pins the start kind; force_getup_cmd=(vx, vy) replaces the
        command schedule with a constant command after a 0.5 s head.
        All draws happen regardless, so rng streams are identical
        whether or not a hook is armed.
        """
        n = self.episode_steps + 1
        rng = self.rng
        dt = self.dt
        r = rng.random()
        kind = self.GETUP_START_KINDS[-1][0]
        acc = 0.0
        for k, p in self.GETUP_START_KINDS:
            acc += p
            if r < acc:
                kind = k
                break
        force = getattr(self, "force_getup_start", None)
        if force is not None:
            kind = str(force)
        vx = np.zeros(n)
        vy = np.zeros(n)
        forced_cmd = getattr(self, "force_getup_cmd", None)
        if forced_cmd is not None:
            head = max(1, int(round(0.5 / dt)))
            vx[head:] = float(forced_cmd[0])
            vy[head:] = float(forced_cmd[1])
        else:
            # Quiet head: long enough to recover + stand from the worst
            # starts (a belly rise alone takes ~5-8 s through the servo
            # profile). Commands arriving before the robot is up simply
            # earn nothing (the S gate), so an early head is not fatal.
            q_lo, q_hi = 4.0, 8.0
            s_lo, s_hi = 0.03, 0.08
            stop_frac = 0.35
            seg_lo, seg_hi = 3.0, 6.0
            i = max(1, int(round(float(rng.uniform(q_lo, q_hi)) / dt)))
            cvx = cvy = 0.0
            blend_n = max(1, int(round(1.0 / dt)))
            while i < n:
                if rng.random() < stop_frac:
                    tvx = tvy = 0.0
                else:
                    sp = float(rng.uniform(s_lo, s_hi))
                    ang = (0.0 if rng.random() < 0.60
                           else float(rng.uniform(-math.pi / 4,
                                                  math.pi / 4)))
                    tvx, tvy = sp * math.cos(ang), sp * math.sin(ang)
                end_b = min(i + blend_n, n)
                vx[i:end_b] = np.linspace(cvx, tvx, end_b - i)
                vy[i:end_b] = np.linspace(cvy, tvy, end_b - i)
                vx[end_b:] = tvx
                vy[end_b:] = tvy
                cvx, cvy = tvx, tvy
                i += max(1, int(round(float(
                    rng.uniform(seg_lo, seg_hi)) / dt)))
        zeros = np.zeros(n)
        traj = WalkTrajectory(mode="getup", roll=zeros, pitch=zeros,
                              height=zeros, unload_leg=None,
                              start_at="any", vx=vx, vy=vy, wz=None)
        traj.start_kind = kind
        return traj

    # ---- recover_to_plant (08-15, operator directive
    # fb_20260815T165306_606974): reach a full-height, level, quiet
    # standing pose with ALL SIX feet loaded, from any recoverable
    # start, then HOLD it 0.5 s — the episode ends on held success.
    # Zero velocity command throughout (this is the recovery
    # specialist; walking is another mode's job). Start-state
    # curriculum = difficulty FAMILIES of start kinds, unlocked
    # monotonically from per-kind deterministic certification fractions
    # (bucket 0 alone first), with bucket-level spaced replay forever.
    # Reward is a potential DIFFERENCE (PBRS) on
    # bounded [0,1] features + one-shot success bonus + a
    # rate-normalized time tax — no occupancy/hold income, no alive
    # bonus (see _recover_reward / REWARD.md §4c).
    #
    # Backward curriculum from the goal boundary.  Buckets are
    # zero-indexed in telemetry and forced eval:
    #   B0 plant_catch: nominal plant + <=2 deg joint noise; hold it.
    #   B1 onefoot_micro: one foot perturbed 3-8 deg.
    #   B2 onefoot_mid:   one foot perturbed 8-15 deg.
    #   B3 onefoot:       one foot perturbed 15-30 deg.
    #   B4 park:          a full alternating tripod is lifted.
    #   B5-B7 shallow/medium/deep all-feet crouches.
    #   B8-B10 high/mid/low partial curls toward the belly-zero pose.
    #   B11 zero: belly-zero with small joint jitter.
    #   B12-B13 25/50% blends toward random legal tangles.
    #   B14-B15 full-height terminal repairs with one/two badly misplaced
    #   legs. These explicitly teach the failure seen at the old B14:
    #   upright and quiet, but parked forever on only four/five feet.
    #   B16-B20 60/70/80/90/100% random-legal tangle blends.
    #   B21 harvested on-path bank states; B22 side/back/upside-down drops.
    #   Sub-90-degree
    #   constructor tilts roll back upright during limp settle, so they
    #   are deliberately not represented as fake curriculum rungs.
    # Keeping the one-foot severities separate matters: the original
    # bucket 1 mixed a 12-30 deg single-foot correction with a tripod
    # park, and produced zero success despite millions of steps.
    RECOVER_FAMILIES = (("plant_catch",),
                        ("onefoot_micro",),
                        ("onefoot_mid",),
                        ("onefoot",),
                        ("park",),
                        ("crouch_shallow",),
                        ("crouch_mid",),
                        ("crouch_deep",),
                        ("partial_high",),
                        ("partial_mid",),
                        ("partial_low",),
                        ("zero",),
                        ("tangle_mild",),
                        ("tangle_mid",),
                        ("repair_one",),
                        ("repair_two",),
                        ("tangle_60",),
                        ("tangle_70",),
                        ("tangle_80",),
                        ("tangle_90",),
                        ("tangle",),
                        ("bank",),
                        ("flip",))
    RECOVER_KIND_IDS = {
        kind: i for i, kind in enumerate(
            kind for family in RECOVER_FAMILIES for kind in family)
    }
    RECOVER_KIND_BUCKETS = {
        kind: bucket for bucket, family in enumerate(RECOVER_FAMILIES)
        for kind in family
    }

    def _recover_family_kinds(self, bucket: int) -> list:
        """Available kinds in one bucket (bank requires a configured file)."""
        has_bank = cfg_get(self.cfg, "goal", "recover_start_bank",
                           default=None) is not None
        return [k for k in self.RECOVER_FAMILIES[bucket]
                if k != "bank" or has_bank]

    def _recover_active_kinds(self) -> list:
        """Kinds in every monotonically unlocked family."""
        kinds = []
        for bucket in range(self._rec_active_n):
            kinds += self._recover_family_kinds(bucket)
        return kinds

    def _recover_bucket_certification(self, bucket: int) -> dict | None:
        """Latest complete deterministic assay for one bucket."""
        kinds = self._recover_family_kinds(bucket)
        stats = [self._rec_stats.get(k, (0, 0)) for k in kinds]
        if not stats or any(episodes <= 0 for _successes, episodes in stats):
            return None
        successes = sum(v[0] for v in stats)
        episodes = sum(v[1] for v in stats)
        fractions = [s / n for s, n in stats]
        return {
            "success_fraction": successes / episodes,
            # Multi-kind buckets promote and remediate on their weakest
            # kind so an easy bank cannot hide a failing random tangle.
            "gate_fraction": min(fractions),
            "successes": successes,
            "episodes": episodes,
        }

    def _recover_refresh_weak_bucket(self) -> None:
        """Point replay pressure at the weakest certified old bucket."""
        candidates = []
        for bucket in range(self._rec_focus_bucket):
            row = self._recover_bucket_certification(bucket)
            if row is not None:
                candidates.append((row["gate_fraction"], -bucket, bucket))
        self._rec_weak_bucket = min(candidates)[2] if candidates else None

    def _recover_training_error_distribution(
            self, n: int | None = None) -> np.ndarray | None:
        """Evidence-weighted replay priority from training shortfall.

        Raw stochastic recovery success is a deliberately strict and noisy
        signal (exploration can break the continuous six-foot hold).  The
        sampler therefore uses terminal goal-potential shortfall instead,
        with safety terminations recorded as maximum error.  This signal can
        allocate a bounded replay slice but can never certify a bucket.
        """
        n = max(1, int(self._rec_active_n if n is None else n))
        min_episodes = 8
        power = 2.0
        priority = np.zeros(n, dtype=float)
        for bucket in range(n):
            error, episodes = self._rec_training_error_stats.get(
                bucket, (0.0, 0))
            if episodes < min_episodes:
                continue
            confidence = min(float(episodes) / min_episodes, 1.0)
            priority[bucket] = confidence * max(float(error), 0.0) ** power
        total = float(priority.sum())
        return priority / total if total > 0.0 else None

    def apply_recover_training_error_batch(self, rows: dict) -> None:
        """Fold global non-RSI training outcomes into sampler-only EMAs."""
        beta = 0.25
        for raw_bucket, values in rows.items():
            bucket = int(raw_bucket)
            if not 0 <= bucket < len(self.RECOVER_FAMILIES):
                continue
            error_sum, episodes = values
            episodes = int(episodes)
            if episodes <= 0:
                continue
            batch_error = float(np.clip(
                float(error_sum) / episodes, 0.0, 1.0))
            old_error, old_n = self._rec_training_error_stats.get(
                bucket, (batch_error, 0))
            updated = (batch_error if old_n == 0 else
                       (1.0 - beta) * old_error + beta * batch_error)
            self._rec_training_error_stats[bucket] = (
                float(updated), int(old_n) + episodes)

    def _recover_bucket_weights(self) -> np.ndarray:
        """Spaced-replay probabilities over unlocked recovery buckets.

        The mass is assigned by BUCKET, not by start kind: 50% to the
        acquisition frontier, 25% geometrically over its three immediate
        predecessors, 15% to the weakest certified old bucket, and 10%
        uniformly over all remaining unlocked buckets. Empty components
        fall back to the frontier. A multi-kind family splits its bucket
        probability later, so adding a bank never doubles that level's
        training share.  Once enough terminal evidence exists, a bounded
        sampler-only slice is redistributed toward buckets with the largest
        terminal goal-potential shortfall.
        """
        n = max(1, int(self._rec_active_n))
        focus = min(max(int(self._rec_focus_bucket), 0), n - 1)
        w = np.zeros(n, dtype=float)
        focus_mass = float(cfg_get(
            self.cfg, "goal", "recover_focus_mix", default=0.50))
        recent_mass = float(cfg_get(
            self.cfg, "goal", "recover_recent_mix", default=0.25))
        weak_mass = float(cfg_get(
            self.cfg, "goal", "recover_weak_mix", default=0.15))
        uniform_mass = float(cfg_get(
            self.cfg, "goal", "recover_uniform_mix", default=0.10))
        masses = np.maximum(
            np.asarray([focus_mass, recent_mass, weak_mass, uniform_mass],
                       dtype=float), 0.0)
        if float(masses.sum()) <= 0.0:
            masses[0] = 1.0
        masses /= masses.sum()
        focus_mass, recent_mass, weak_mass, uniform_mass = masses
        w[focus] += focus_mass

        recent = [focus - d for d in range(1, 4) if focus - d >= 0]
        if recent:
            shape = np.asarray((0.50, 0.30, 0.20)[:len(recent)],
                               dtype=float)
            shape /= shape.sum()
            for bucket, share in zip(recent, shape):
                w[bucket] += recent_mass * share
        else:
            w[focus] += recent_mass

        weak = self._rec_weak_bucket
        if weak is not None and 0 <= int(weak) < n and int(weak) != focus:
            w[int(weak)] += weak_mass
        else:
            w[focus] += weak_mass

        reserved = {focus, *recent}
        if weak is not None and 0 <= int(weak) < n:
            reserved.add(int(weak))
        others = [bucket for bucket in range(n) if bucket not in reserved]
        if others:
            for bucket in others:
                w[bucket] += uniform_mass / len(others)
        else:
            w[focus] += uniform_mass
        w /= w.sum()
        error_distribution = self._recover_training_error_distribution(n)
        error_mix = 0.10
        if error_distribution is not None:
            w = (1.0 - error_mix) * w + error_mix * error_distribution
        return w / w.sum()

    def _recover_kind_weights(self, kinds: list) -> np.ndarray:
        """Map bucket replay mass to kinds, splitting families evenly."""
        bucket_w = self._recover_bucket_weights()
        w = []
        for kind in kinds:
            bucket = self.RECOVER_KIND_BUCKETS[kind]
            family_n = len(self._recover_family_kinds(bucket))
            w.append(bucket_w[bucket] / max(family_n, 1))
        w = np.asarray(w, dtype=float)
        return w / w.sum()

    def _recover_admission_status(self,
                                  cert_round: int | None = None) -> dict:
        """Return the frontier and retention-suite gate state."""
        self._rec_focus_bucket = self._rec_active_n - 1
        admit_n = int(float(cfg_get(
            self.cfg, "goal", "recover_admit_n", default=4)))
        threshold = 0.8
        bucket_rows = {}
        for bucket in range(self._rec_active_n):
            kinds = self._recover_family_kinds(bucket)
            passed = bool(kinds)
            fresh = bool(kinds)
            fractions = []
            for kind in kinds:
                successes, episodes = self._rec_stats.get(kind, (0, 0))
                fraction = successes / episodes if episodes else 0.0
                fractions.append(fraction)
                passed = (passed and episodes >= admit_n
                          and fraction >= threshold)
                if cert_round is not None:
                    fresh = (fresh and self._rec_cert_rounds.get(kind)
                             == int(cert_round))
            bucket_rows[bucket] = {
                "passed": bool(passed and fresh),
                "score_passed": bool(passed),
                "fresh": bool(fresh),
                "gate_fraction": (min(fractions) if fractions else 0.0),
            }
        focus = self._rec_focus_bucket
        frontier_passed = bool(bucket_rows.get(
            focus, {}).get("passed", False))
        retention = [bucket_rows[b] for b in range(focus)]
        retention_passed = all(row["passed"] for row in retention)
        failed = [bucket for bucket, row in bucket_rows.items()
                  if not row["passed"]]
        retention_failed = [bucket for bucket in range(focus)
                            if not bucket_rows[bucket]["passed"]]
        return {
            "cert_round": (-1 if cert_round is None else int(cert_round)),
            "frontier_bucket": int(focus),
            "frontier_passed": frontier_passed,
            "retention_passed": bool(retention_passed),
            "suite_passed": bool(frontier_passed and retention_passed),
            "retention_bucket_count": int(focus),
            "failed_buckets": failed,
            "retention_failed_buckets": retention_failed,
            "retention_min_gate_fraction": min(
                (row["gate_fraction"] for row in retention), default=1.0),
            "min_gate_fraction": min(
                (row["gate_fraction"] for row in bucket_rows.values()),
                default=0.0),
            "buckets": bucket_rows,
        }

    def _recover_update_admission(
            self, cert_round: int | None = None) -> dict:
        """Unlock only after frontier plus retention suite pass."""
        status = self._recover_admission_status(cert_round)
        before = self._rec_active_n
        if (self._rec_active_n < len(self.RECOVER_FAMILIES)
                and status["suite_passed"]):
            self._rec_active_n += 1
            self._rec_focus_bucket = self._rec_active_n - 1
        self._recover_refresh_weak_bucket()
        status.update({
            "active_before": int(before),
            "active_after": int(self._rec_active_n),
            "promoted": bool(self._rec_active_n > before),
        })
        return status

    def recover_score_state(self) -> dict:
        """Serializable deterministic curriculum/scoreboard snapshot."""
        self._recover_refresh_weak_bucket()
        bucket_w = self._recover_bucket_weights()
        error_priority = self._recover_training_error_distribution()
        if error_priority is None:
            error_priority = np.zeros(self._rec_active_n, dtype=float)
        buckets = {}
        for bucket in range(len(self.RECOVER_FAMILIES)):
            row = self._recover_bucket_certification(bucket)
            if row is not None:
                buckets[str(bucket)] = row
        return {
            "total_buckets": len(self.RECOVER_FAMILIES),
            "max_unlocked_bucket": self._rec_active_n - 1,
            "focus_bucket": self._rec_focus_bucket,
            "weakest_bucket": (-1 if self._rec_weak_bucket is None
                                else int(self._rec_weak_bucket)),
            "buckets": buckets,
            "sample_probabilities": {
                str(bucket): float(probability)
                for bucket, probability in enumerate(bucket_w)
            },
            "training_errors": {
                str(bucket): {
                    "ema": float(self._rec_training_error_stats.get(
                        bucket, (0.0, 0))[0]),
                    "episodes": int(self._rec_training_error_stats.get(
                        bucket, (0.0, 0))[1]),
                    "priority": float(error_priority[bucket]),
                }
                for bucket in range(self._rec_active_n)
            },
        }

    def recover_curriculum_checkpoint_state(self) -> dict:
        """State paired with a policy snapshot at a proven promotion."""
        return {
            "active_n": int(self._rec_active_n),
            "focus_bucket": int(self._rec_focus_bucket),
            "stats": dict(self._rec_stats),
            "cert_rounds": dict(self._rec_cert_rounds),
        }

    def restore_recover_curriculum_checkpoint_state(self,
                                                    state: dict) -> None:
        """Restore promotion-time curriculum state, retaining error debt."""
        active_n = int(state["active_n"])
        if not 1 <= active_n <= len(self.RECOVER_FAMILIES):
            raise ValueError(f"invalid recovery active_n {active_n}")
        self._rec_active_n = active_n
        self._rec_focus_bucket = active_n - 1
        self._rec_stats = {
            str(kind): (int(values[0]), int(values[1]))
            for kind, values in dict(state["stats"]).items()
        }
        self._rec_cert_rounds = {
            str(kind): int(cert_round)
            for kind, cert_round in dict(state["cert_rounds"]).items()
        }
        self._recover_refresh_weak_bucket()

    def apply_recover_certification(self, kind: str,
                                    outcomes: list[bool],
                                    update_admission: bool = True,
                                    cert_round: int | None = None) -> dict:
        """Apply deterministic same-backend outcomes to the curriculum.

        The MJX trainer calls this on every training env after a held-out
        deterministic certification pass.  Keeping this mutation here
        makes the admission contract identical for C, MJX and sharded
        host envs while ensuring ordinary stochastic rollout terminals
        cannot move the frontier.
        """
        kind = str(kind)
        if kind not in self.RECOVER_KIND_BUCKETS:
            raise ValueError(f"unknown recover certification kind {kind!r}")
        ys = [bool(v) for v in outcomes]
        if not ys:
            raise ValueError("recover certification needs at least one outcome")
        successes = sum(1 for ok in ys if ok)
        n = len(ys)
        fraction = successes / n
        # A certification is a fixed-size held-out assay. Store exactly
        # this batch, rather than blending it into an EMA whose numerator
        # and denominator cannot be interpreted from a chart.
        self._rec_stats[kind] = (successes, n)
        if cert_round is not None:
            self._rec_cert_rounds[kind] = int(cert_round)
        before = self._rec_active_n
        focus_before = self._rec_focus_bucket
        if update_admission:
            self._recover_update_admission(cert_round)
        return {"kind": kind, "success_fraction": float(fraction),
                "successes": int(successes), "episodes": int(n),
                "active_before": int(before),
                "active_after": int(self._rec_active_n),
                "focus_before": int(focus_before),
                "focus_after": int(self._rec_focus_bucket)}

    def _sample_recover(self) -> WalkTrajectory:
        """One recover_to_plant episode: adaptive start-kind draw, zero
        commands, mode 'recover', env-side 'any' spawn branch builds
        the pose (start_kind rides the trajectory, same contract as
        getup). Hook (bank/eval only, not a cfg key):
        force_recover_start pins the kind — the weight computation and
        the draw still happen, so rng streams are identical whether or
        not the hook is armed."""
        if float(cfg_get(self.cfg, "goal", "mode_seq",
                         default=0.0)) > 0.0:
            # The mode-seq frame probes call _place_at_plant before the
            # episode placement and would consume the flip-spawn
            # pending quat; the combination is also semantically
            # meaningless (recover episodes are single-goal). Refuse
            # loudly instead of training a corrupted diet.
            raise ValueError("goal.mode_seq is incompatible with the "
                             "recover mode (frame probes vs flip "
                             "spawns); run recover as a single-mode "
                             "diet")
        if not self._rec_external_certification:
            self._recover_update_admission()
        kinds = self._recover_active_kinds()
        w = self._recover_kind_weights(kinds)
        r = float(self.rng.random())
        kind = kinds[int(np.searchsorted(np.cumsum(w), r,
                                         side="right").clip(
                                             0, len(kinds) - 1))]
        force = getattr(self, "force_recover_start", None)
        if force is not None:
            kind = str(force)
        n = self.episode_steps + 1
        zeros = np.zeros(n)
        traj = WalkTrajectory(mode="recover", roll=zeros.copy(),
                              pitch=zeros.copy(), height=zeros.copy(),
                              unload_leg=None, start_at="any",
                              vx=zeros.copy(), vy=zeros.copy(), wz=None)
        traj.start_kind = kind
        # RECOVER RSI (08-16, zero-family mechanism fix after
        # cw-recover-any8/any9 both stalled on B11): with probability
        # goal.recover_rsi_frac, an episode whose kind was NATURALLY
        # drawn as "zero" spawns ON
        # the demonstrated belly->plant path instead of the family
        # pose (sim_env._reset_begin builds the waypoint — the same
        # proven goal.rise_rsi_frac lever, extended to recover). The
        # decision lives HERE, goal-side, because only the sampler
        # knows whether the kind was FORCED: force_recover_start is
        # the deterministic CERT/eval path and must stay pure, so a
        # forced episode never carries the flag. Default 0.0 = off,
        # bit-exact (no extra rng draw).
        traj.recover_rsi = False
        _rsi_f = float(cfg_get(self.cfg, "goal", "recover_rsi_frac",
                               default=0.0))
        if _rsi_f > 0.0 and force is None:
            if kind == "zero" and float(self.rng.random()) < _rsi_f:
                traj.recover_rsi = True
        # RECOVER RSI, HARVESTED-BANK variant (08-16, tangle-wall
        # mechanism fix after any7/any11/any12's 3rd matching miss on
        # curriculum-weight): the ref-path mechanism above is
        # hardcoded to the belly->plant rise trajectory (a single
        # monotonic-height reference), which has no equivalent for
        # tangle's non-monotonic untangling motion. This second,
        # independent axis instead samples a spawn pose from a
        # harvested bank of ON-PATH states from a checkpoint's OWN
        # successful recoveries of the target kind
        # (harvest_recover_rsi_bank.py), so a policy stuck on a hard
        # kind practices from states partway through the motion that
        # is already known to work sometimes, not just the family's
        # raw start pose. Fully independent cfg keys/kind-list from
        # the ref-path axis above (no interaction when the target
        # kinds don't overlap); default frac 0.0 = off, bit-exact (no
        # extra rng draw). `not traj.recover_rsi` keeps the two
        # mechanisms mutually exclusive on a single episode if a kind
        # is ever listed in both.
        traj.recover_rsi_bank = False
        _rsi_bank_f = float(cfg_get(self.cfg, "goal",
                                    "recover_rsi_bank_frac", default=0.0))
        if _rsi_bank_f > 0.0 and force is None and not traj.recover_rsi:
            _rsi_bank_kinds = [k.strip() for k in str(cfg_get(
                self.cfg, "goal", "recover_rsi_bank_kinds",
                default="")).split(",") if k.strip()]
            if (kind in _rsi_bank_kinds
                    and float(self.rng.random()) < _rsi_bank_f):
                traj.recover_rsi_bank = True
        return traj

    # ---- mode sequencing (goal.mode_seq; TRANSITIONS_DIRECTIVE item 1)
    #
    # Episode = K back-to-back mode segments following the operator's
    # command grammar rise -> {hold|walk} -> {walk|lower} -> (rise ...).
    # At each switch the env installs the new segment family's CANONICAL
    # settled frame (q_nom/_z0/pad refs from sim_env._seq_capture_frames
    # — the eval_handoff/reanchor_to() semantics; see the trans-dagger2
    # fix note on sim_env._seq_maybe_switch) and regenerates the refs;
    # this side samples the plan and
    # builds each segment's schedule. goal.mode_seq=0 (default) is
    # bit-exact legacy: no plan, no extra rng draws, no per-tick work
    # beyond one attr check. Keys:
    #   goal.mode_seq                sequence-episode probability
    #                                (0 = off/legacy, 1 = every episode,
    #                                0<p<1 = mixed diet; joint_walk only)
    #   goal.mode_seq_segment_s_min  segment length draw lo (s, 6.0)
    #   goal.mode_seq_segment_s_max  segment length draw hi (s, 8.0)
    #   goal.mode_seq_blend_s_min    per-switch ref blend lo (s, 0.5)
    #   goal.mode_seq_blend_s_max    per-switch ref blend hi (s, 1.0)
    #   goal.mode_seq_max_segments   plan length cap (5)
    #   goal.mode_seq_forced_plan    "" (off) or a deterministic
    #                                "mode[:seconds],..." override plan
    #                                (eval-only DONE-gate session tool,
    #                                09-01 — see _sample_mode_seq)
    # First segment uses the LEGACY samplers (full start-kind diversity:
    # rise keeps its flat/bridge/crouch mix, walk its park/gait spawn
    # draws, lower its belly-start draw) so a sequence may begin at any
    # start kind, compatibly by construction. Mid-sequence spawns
    # (sequence-RSI) are deliberately NOT in v1 (pre-registered
    # follow-up lever).
    SEQ_NEXT = {"rise": ("hold", "walk"), "hold": ("walk", "lower"),
                "walk": ("lower",), "lower": ("rise",)}
    # goal.mode_seq_stress=1 (default 0 = bit-exact legacy SEQ_NEXT):
    # transition-stress grammar for the smooth universal-command
    # directive (operator fb_20260904T074505) — adds the mid-transition
    # switches the product must survive but the legacy grammar never
    # samples: rise->lower (interrupted/reversed rise), walk->hold
    # (stop/hold/restart mid-walk). Pair with short
    # goal.mode_seq_segment_s_min/max draws to interrupt transitions
    # before they settle. lower->rise unchanged (a short lower segment
    # followed by rise IS the interrupted-lower reversal).
    SEQ_NEXT_STRESS = {
        "rise": ("hold", "walk", "lower"),
        "hold": ("walk", "lower"),
        "walk": ("lower", "hold"),
        "lower": ("rise",),
    }

    def _sample_mode_seq(self):
        gen = self._goal_gen
        rng = self.rng
        dt = self.dt
        n = self.episode_steps + 1
        seg_lo = float(cfg_get(self.cfg, "goal", "mode_seq_segment_s_min",
                               default=6.0))
        seg_hi = float(cfg_get(self.cfg, "goal", "mode_seq_segment_s_max",
                               default=8.0))
        bl_lo = float(cfg_get(self.cfg, "goal", "mode_seq_blend_s_min",
                              default=0.5))
        bl_hi = float(cfg_get(self.cfg, "goal", "mode_seq_blend_s_max",
                              default=1.0))
        max_seg = int(cfg_get(self.cfg, "goal", "mode_seq_max_segments",
                              default=5))
        # goal.mode_seq_forced_plan (09-01, standwalk DONE-gate session
        # tool): default "" = bit-exact legacy random plan below. When
        # set, a comma-separated "mode[:seconds]" spec (e.g.
        # "rise:10,walk:60,lower:10") REPLACES the random SEQ_NEXT walk
        # + uniform segment-length draw with this EXACT deterministic
        # sequence/duration — the one thing the random sampler can't
        # give an eval harness: a guaranteed single sit->rise->walk->
        # lower cycle with a full-length (e.g. 60 s) walk segment
        # instead of the training-diet's uniform 6-12 s segments. Omit
        # ":seconds" to fall back to the midpoint of the segment-length
        # cfg (matches the random sampler's own scale). Eval-only lever
        # (no rng draws consumed beyond what building the plan needs);
        # never used by any training recipe today. First segment still
        # goes through the legacy start-kind samplers below, same as
        # the random path.
        forced = str(cfg_get(self.cfg, "goal", "mode_seq_forced_plan",
                             default="") or "").strip()
        if forced:
            specs: list[tuple[str, float]] = []
            for part in forced.split(","):
                part = part.strip()
                if not part:
                    continue
                m, _, d = part.partition(":")
                dur = float(d) if d else (seg_lo + seg_hi) / 2.0
                specs.append((m.strip(), dur))
            if not specs:
                raise ValueError(
                    "goal.mode_seq_forced_plan set but parsed to zero "
                    "segments — expected 'mode[:seconds],...'")
            mode = specs[0][0]
            plan = [{"mode": mode, "tick": 0, "blend": 0}]
            t = specs[0][1]
            for m, dur in specs[1:]:
                tk = int(round(t / dt))
                if tk >= self.episode_steps:
                    break  # doesn't fit this episode length — drop it
                bn = max(1, int(round(float(rng.uniform(bl_lo, bl_hi))
                                     / dt)))
                plan.append({"mode": m, "tick": tk, "blend": bn})
                t += dur
        else:
            # First mode: the configured goal mix restricted to the
            # four sequence modes (renormalized; uniform fallback) —
            # --goal-mix keeps steering what sequences train on.
            modes4 = ("rise", "walk", "hold", "lower")
            p = np.array([gen.p_rise, float(getattr(gen, "p_walk", 0.0)),
                          gen.p_hold, gen.p_lower], dtype=float)
            p = (p / p.sum()) if p.sum() > 0 else np.full(4, 0.25)
            mode = str(modes4[int(rng.choice(4, p=p))])
            # Segment boundaries: cumulative U(seg_lo, seg_hi) draws
            # until the tail can no longer hold a useful (>=3 s)
            # segment; the last segment runs to the episode end.
            # Guarantee >= 2 segments (a 1-segment "sequence" tests
            # nothing) by splitting at the middle if the draw left no
            # boundary.
            min_tail = int(round(3.0 / dt))
            ticks = [0]
            t = 0.0
            while len(ticks) < max_seg:
                t += float(rng.uniform(seg_lo, seg_hi))
                tk = int(round(t / dt))
                if tk > self.episode_steps - min_tail:
                    break
                ticks.append(tk)
            if len(ticks) == 1:
                ticks.append(max(1, self.episode_steps // 2))
            seq_next = (self.SEQ_NEXT_STRESS
                        if float(cfg_get(self.cfg, "goal",
                                         "mode_seq_stress",
                                         default=0.0)) > 0.0
                        else self.SEQ_NEXT)
            plan = [{"mode": mode, "tick": 0, "blend": 0}]
            for tk in ticks[1:]:
                mode = str(rng.choice(seq_next[mode]))
                bn = max(1, int(round(float(rng.uniform(bl_lo, bl_hi))
                                     / dt)))
                plan.append({"mode": mode, "tick": tk, "blend": bn})
        self._seq_plan = plan
        self._seq_idx = 0
        self._seq_seg_end = (int(plan[1]["tick"]) if len(plan) > 1
                             else int(self.episode_steps))
        # First segment through the legacy samplers (start-kind
        # diversity lives there; reset() uses its start_at).
        first = str(plan[0]["mode"])
        if first == "walk":
            return self._sample_walk()
        return gen.sample(rng, n, dt, force_mode=first)

    def _seq_segment_traj(self, mode: str, tick: int):
        """Mid-episode segment schedule on the EPISODE clock: arrays are
        full-length with [0:tick] padded (never read again) so every
        existing _step_i-indexed consumer (goal reads, ref_quiet, the
        BC lookahead, end-posture) works unchanged. Heights are
        relative to the CANONICAL family _z0 the caller installs
        BEFORE calling (settled plant for walk/hold/lower, settled
        belly for rise — sim_env._seq_capture_frames). Returns
        (traj, h_target, ramp_i0)."""
        n = self.episode_steps + 1
        m = n - tick
        if mode == "walk":
            base = self._sample_walk()
            for name in ("roll", "pitch", "height", "vx", "vy", "wz"):
                arr = getattr(base, name, None)
                if arr is None:
                    continue
                arr = np.asarray(arr, dtype=float)
                out = np.empty(n, dtype=float)
                out[:tick] = arr[0]
                out[tick:] = arr[:m]
                setattr(base, name, out)
            base.start_at = "plant"    # reset-only hint, unused here
            return base, 0.0, 0
        # rise/hold/lower segment schedules moved to the shared base
        # (goal_task.SimHexapodGoalEnv._seq_segment_traj, 08-15,
        # stance-only sequencing) — identical statements, identical rng
        # draw order, so walk-task sequence streams are unchanged.
        return super()._seq_segment_traj(mode, tick)

    def _seq_reset_mode_state(self, mode: str, ramp_i0: int,
                              h_target: float) -> None:
        super()._seq_reset_mode_state(mode, ramp_i0, h_target)
        # Fresh-segment walk bookkeeping: every accumulator _reset_begin
        # zeroes gets a fresh segment (income/charge baselines must
        # never leak across a mode switch); prev-XY/contact latches go
        # back to None/False and re-latch on the next loaded tick.
        self._liftoff_step = [0] * 6
        self._foot_prev_xy = [None] * 6
        self._foot_prev_force = [0.0] * 6
        self._foot_tan_slip_m = [0.0] * 6
        self._duty_hist = []
        self._dgate_hist = []
        self._swing_gate_hist = []
        self._anchor_xy = [None] * 6
        self._anchor_prev_on = [False] * 6
        self._step_disp_bank = 0.0
        self._yaw_still_ema = 0.0
        self._yaw_prog_ema = 0.0
        self._ls_prev_xy = [None] * 6
        self._ls_prev_on = [False] * 6
        self._ls_slip_m = 0.0
        self._ls_prog_m = 0.0
        # Windowed (EMA) loaded-slip rate bookkeeping
        # (reward.walk_loadslip_window_s, default 0 = off, see the
        # walk_loadslip_gate block in step()). Separate from the
        # cumulative _ls_slip_m/_ls_prog_m above so the legacy
        # episode-cumulative ratio stays bit-exact when off.
        self._ls_slip_ema = 0.0
        self._ls_prog_ema = 0.0
        # Anti-park travel-floor EMA (reward.k_walk_idle_charge);
        # per-episode/per-segment, snapshot via MJX_SNAPSHOT_EXTRA.
        self._walk_idle_ema = 0.0
        # Sustained-idle termination counter + its OWN mean-
        # |joint-velocity| EMA (safety.walk_idle_terminate_s):
        # deliberately NOT body speed (a real dragging/skating
        # gait can sit near-zero BODY speed while its legs
        # cycle hard, and cutting that short was measured to
        # rob it of the full-episode loadslip charge the bank
        # relies on; a body-speed version also flagged genuine
        # wrong-direction travel as "idle"). Mean |qvel| across
        # the 18 actuated joints cleanly separates a literally
        # FROZEN policy output (park/belly-sit/tripod-lock:
        # ~5e-5 rad/s, pure settle jitter) from every other
        # scripted behavior including skate/stall (>=0.1 rad/s,
        # ~35x higher) -- see the WALKCURR_PF_IDLE_TERM bank.
        # Seconds low, consecutively; reset to 0 the instant
        # the EMA clears the floor.
        self._walk_idle_low_s = 0.0
        self._walk_qvel_ema = 0.0
        # Per-LEG minimum-duty termination (safety.walk_leg_duty_
        # terminate_s, 2026-09-07): own per-leg EMA of ground-contact
        # duty (own contact sensor, same on=force>0.5 convention used
        # throughout this file) + seconds each leg has stayed below the
        # floor, consecutively. Seeded at 1.0 (not 0.0) because stance
        # episodes begin at the plant with all six feet loaded (same
        # "begins loaded" convention as _pad_z_ref) -- a 0.0 seed would
        # start every leg mid-way toward a false trigger before any
        # real contact data accumulates. See the walk_leg_duty_
        # terminate block in sim_env.step() for the mechanism itself
        # and its full design rationale (widen8/widenbis/widenrear180
        # role-aware-mechanism gap, CURRENT_TRUTHS 09-05 ~22:3x /
        # 09-07 ~04:4x).
        self._walk_legduty_ema = [1.0] * 6
        self._walk_legduty_low_s = [0.0] * 6
        # Per-leg duty-RATIO reward-charge EMA (reward.walk_leg_duty_
        # ratio_charge, 2026-09-08); own state, independent of the
        # termination feature's _walk_legduty_ema above. Seeded at 1.0
        # for the same "begins loaded at the plant" reason. Tick
        # counter gates the charge off until the EMA has had a chance
        # to reflect real contact data (mirrors the window-must-fill
        # grace every other gate in this file uses).
        self._legduty_ratio_ema = [1.0] * 6
        self._legduty_ratio_ticks = 0
        self._legduty_ratio_swing_hist: list = []
        # Per-leg load-SLIP reward-charge EMA (reward.walk_leg_
        # loadslip_ratio_charge, 2026-09-08); own state, independent
        # of every other slip/duty mechanism's EMA/history above.
        # Seeded at 0.0 (assume no slip until measured), unlike the
        # duty-ratio EMA's 1.0 seed, since "no slip yet observed" is
        # the correct neutral starting assumption for a velocity
        # quantity (0 contact-time exists trivially at reset; 0 slip
        # is also the trivially-true value before any foot has
        # touched down). Tick counter gates the charge off until the
        # EMA has had a chance to reflect real contact data (same
        # grace convention as every other gate in this file).
        self._legslip_ratio_ema = [0.0] * 6
        self._legslip_ratio_ticks = 0
        # Per-leg swing-GAP reward-charge state (reward.walk_leg_
        # swing_gap_charge, 2026-09-08): seconds elapsed since each
        # leg's last qualifying swing event -- see the mechanism's
        # own comment block in step() for the full design rationale
        # (the "duration-since-last-swing PATTERN price" lead named
        # by the loadslip-ratio-charge closure). Seeded at 0.0 (a leg
        # is trivially "just swung" at the plant-start reset, mirroring
        # the loadslip EMA's own 0-seed rationale). Independent of
        # every other slip/duty mechanism's state above.
        self._swing_gap_s = [0.0] * 6
        # Per-leg swing-INITIATION income state (reward.walk_leg_
        # swing_initiation_income, 2026-09-08): the OTHER concrete
        # lead named alongside swing-gap-charge by the loadslip-ratio-
        # charge closure ("a positive swing-initiation income for the
        # currently-most-loaded leg" -- CURRENT_TRUTHS/STATUS.md
        # 2026-09-08 ~19:1x). Tracks, per leg, whether THAT leg was
        # the single most heavily loaded of all six at the instant it
        # left the ground (set at liftoff, consumed/reset at the next
        # touchdown once the swing either qualifies for credit or
        # doesn't -- see the mechanism's own comment block in step()).
        # Seeded False (no leg has swung yet at reset, so none can
        # claim credit for the reset-pose's own trivial "liftoff").
        self._liftoff_was_maxload = [False] * 6
        # Trailing EMA of per-leg raw contact force (own state,
        # own units -- N, not a peer-ratio -- so the mechanism
        # can rank legs by ARGMAX directly), used instead of the
        # single-instant `_foot_prev_force` to decide "most
        # loaded" at liftoff: a raw last-tick snapshot is
        # dominated by the natural pre-liftoff UNLOADING
        # transient every smooth gait already does (a leg sheds
        # load in the ticks just before it lifts, by ordinary
        # weight-transfer kinematics, not misbehavior) -- an
        # empirical check during this mechanism's own bank-test
        # development found the raw-instant version NEVER fires
        # on the honest scripted gait for exactly this reason.
        # The EMA (tau `walk_leg_swing_initiation_load_tau_s`)
        # instead reflects how loaded this leg has BEEN over its
        # current/recent stance, which the brief pre-liftoff dip
        # cannot erase. Seeded 0.0 (no leg has been loaded yet
        # at reset).
        self._swinit_load_ema = [0.0] * 6
        # Seconds since the current commanded-stop segment began
        # (reward.walk_stop_grace_s); 0 whenever s_ref > 1e-3
        # (walking commanded), increments by dt each stop tick.
        # Used only to ramp the stop-speed charge in over the
        # unavoidable deceleration transient -- see the charge
        # site below. Same lifecycle as _walk_idle_ema.
        self._walk_stop_cmd_s = 0.0
        # Structural stop-hold timer (goal.walk_stop_freeze_s);
        # same lifecycle as _walk_stop_cmd_s -- see
        # sim_env._walk_stop_freeze_override.
        self._walk_stop_freeze_cmd_s = 0.0
        # Commanded-course EMA (reward.k_walk_course); same lifecycle.
        self._walk_course_ema = [0.0, 0.0]
        # Commanded-course NET-DISPLACEMENT ring buffer
        # (reward.k_walk_course_disp, the k_walk_course EMA-
        # cancellation fix-lever (b), 08-29 standwalk DIG-IN); lazily
        # (re)allocated in the reward step once the window size is
        # known, so a plain reset just drops any prior buffer.
        self._walk_course_disp_hist = None
        # Windowed course-following INCOME + excess-sway ring buffer
        # (reward.k_walk_course_income / reward.k_walk_excess_sway,
        # operator reward-design directive fb_20260829T142239_63c818):
        # deque of (x, y, cum_cmd_x, cum_cmd_y, cum_active_ticks) with
        # the running totals in _walk_course_win_cum; lazily
        # (re)allocated in the reward step once the window sizes are
        # known. Same lifecycle as _walk_course_disp_hist.
        self._walk_course_win_hist = None
        self._walk_course_win_cum = [0.0, 0.0, 0]
        # Stride-EMA velocity for the tracking kernel
        # (reward.walk_kernel_vel_ema); same lifecycle.
        self._walk_kernel_vema = [0.0, 0.0]
        # Stride-EMA yaw-rate for the yaw tracking kernel
        # (reward.walk_kernel_yaw_ema); same lifecycle.
        self._walk_kernel_wz_ema = 0.0
        self._stance_slip_acc = [0.0] * 6
        self._trans_td_count = [0] * 6
        self._trans_lo_buf = [[] for _ in range(6)]
        self._gait_last_step = [0] * 6
        self._gait_cmd_tick = 0
        self._gait_gate_qfactor = 1.0
        self._walk_bucket = None
        self._phase = 0.0

    def _sample_goal(self):
        # goal.mode_seq semantics (08-14, Arm 2 recipe: "retain ~25%
        # single-mode episodes"): 0 = off (bit-exact legacy, no draw),
        # 1 = every episode a sequence (bit-exact prior behavior, no
        # draw), 0<p<1 = this episode is a sequence with prob p, else
        # falls through to the legacy single-mode samplers (one extra
        # rng draw ONLY in the fractional case, so both endpoints keep
        # their historical rng streams).
        p_seq = float(cfg_get(self.cfg, "goal", "mode_seq",
                              default=0.0))
        if float(cfg_get(self.cfg, "goal", "mode_seq_stance",
                         default=0.0)) > 0.0:
            # The stance-only planner (goal_task, 08-15) belongs to the
            # joint_goal task; on joint_walk the base-mode fallback
            # below would start stance sequences mid-draw — refuse
            # loudly instead of training a misconfigured diet.
            raise ValueError(
                "goal.mode_seq_stance is a joint_goal-task key; use "
                "goal.mode_seq on the joint_walk task")
        if p_seq >= 1.0 or (p_seq > 0.0 and self.rng.random() < p_seq):
            return self._sample_mode_seq()
        gen = self._goal_gen
        p_walk = float(getattr(gen, "p_walk", 0.0))
        p_getup = float(getattr(gen, "p_getup", 0.0))
        p_qw = float(getattr(gen, "p_quadwalk", 0.0))
        p_rec = float(getattr(gen, "p_recover", 0.0))
        p_base = (gen.p_hold + gen.p_lean + gen.p_track + gen.p_unload
                  + gen.p_raise + gen.p_rise + gen.p_lower
                  + getattr(gen, "p_quad", 0.0))
        tot = p_walk + p_getup + p_qw + p_rec + p_base
        if tot <= 0:
            return self._sample_walk()
        # Single draw, walk-first cdf: with p_getup == p_quadwalk ==
        # p_recover == 0 (default) the draw and its use are
        # bit-identical to the legacy two-way split, so every existing
        # lineage's rng stream is unchanged (a zero-probability mode is
        # an empty interval).
        r = self.rng.random() * tot
        if r < p_walk:
            return self._sample_walk()
        if r < p_walk + p_getup:
            return self._sample_getup()
        if r < p_walk + p_getup + p_qw:
            return self._sample_quadwalk()
        if r < p_walk + p_getup + p_qw + p_rec:
            return self._sample_recover()
        return super()._sample_goal()

    def _current_goal(self):
        return _wrap_goal(super()._current_goal())

    def _body_vel_xy(self) -> np.ndarray:
        """Chassis planar velocity in the body frame (privileged)."""
        v_world = self.data.qvel[:3]
        R = self.data.xmat[self._chassis_bid].reshape(3, 3)
        return (R.T @ v_world)[:2]

    def _body_wz(self) -> float:
        """Chassis yaw rate about the body z axis (rad/s, +CCW)."""
        w_world = self.data.qvel[3:6]
        R = self.data.xmat[self._chassis_bid].reshape(3, 3)
        return float((R.T @ w_world)[2])

    def _post_step(self, result):
        # Walk-mode shaping — in the _post_step hook (not a step()
        # wrapper) so the batched MJX vec env, which drives the
        # begin/tick/finish halves directly, applies it too. Behavior
        # identical to the historical step() override, including on the
        # rejected-action early return.
        obs, reward, term, trunc, info = super()._post_step(result)
        if self._step_i >= self._active_episode_steps():
            trunc = True
        if (self._goal_traj is not None
                and getattr(self._goal_traj, "mode", "")
                in ("walk", "quadwalk")):
            # quadwalk (08-13, quad track) shares the entire walk
            # pricing stack — kernel, progress, every income gate and
            # slip/drag charge — with exactly two lift-leg exemptions
            # below (park-duty window, step/swing credit) plus the
            # quad clear/plant income at the end. `lift` is empty in
            # walk mode, so walk pricing is bit-exact unchanged.
            mode_q = (getattr(self._goal_traj, "mode", "")
                      == "quadwalk")
            goal = self._current_goal()
            lift = (tuple(goal.lift_legs)
                    if (mode_q and goal.lift_legs) else ())
            v = self._body_vel_xy()
            err = float(np.hypot(v[0] - goal.vx_ref, v[1] - goal.vy_ref))
            along, err, r_prog, r_walk, s_ref = (
                walk_reward_progress.velocity_kernel_and_progress(
                    self, err, goal, info, v))
            along, r_free_pen, r_prog, r_walk = (
                walk_reward_progress.freeprog_income(
                    self, along, goal, info, r_prog, r_walk, s_ref, v))
            along, cmd_cross, k_cmd_track, r_cmd_track = (
                walk_reward_progress.cmd_track_objective(
                    self, along, goal, v))
            reward = walk_reward_yaw.yaw_rate_kernel(self,
                along, goal, info, reward, s_ref)
            reward = walk_reward_yaw.anti_drift_yaw_pricing(self,
                goal, info, reward)
            r_walk, support_gate = walk_reward_gates.kernel_progress_gate(self,
                along, info, r_walk, s_ref)
            r_walk, r_freeze = (
                walk_reward_yaw.turn_in_place_kernel_gate_and_freeze(
                    self, goal, info, r_walk, s_ref))
            r_prog, r_walk, support_gate = (
                walk_reward_gates.anchored_stance_gate(
                    self, info, r_prog, r_walk, s_ref, support_gate))
            r_prog, r_walk, reward, support_gate = (
                walk_reward_gates.loaded_slip_gate(
                    self, along, info, r_prog, r_walk, reward, s_ref,
                    support_gate))
            r_prog, r_walk, support_gate = walk_reward_gates.height_gate(self,
                goal, info, r_prog, r_walk, s_ref, support_gate)
            g_gait, r_cmd_track, r_prog, r_walk, support_gate = (
                walk_reward_gates.gait_gate(
                    self, info, lift, r_cmd_track, r_prog, r_walk, s_ref,
                    support_gate))
            g_duty, r_cmd_track, r_prog, r_walk, support_gate = (
                walk_reward_gates.leg_duty_gate(
                    self, info, lift, r_cmd_track, r_prog, r_walk, s_ref,
                    support_gate))
            g_swing, r_cmd_track, r_prog, r_walk, support_gate = (
                walk_reward_gates.leg_swing_rate_gate(
                    self, info, lift, r_cmd_track, r_prog, r_walk, s_ref,
                    support_gate))
            g_ratio, g_ratio_swingfloor, r_ratio = (
                walk_reward_gates.leg_duty_ratio_charge(
                    self, info, s_ref))
            g_lsratio, r_lsratio = (
                walk_reward_gates.leg_loadslip_ratio_charge(
                    self, info, s_ref))
            g_swinggap, r_gap = walk_reward_gates.leg_swinggap_charge(self,
                info, s_ref)
            g_swinit = walk_reward_gates.swing_initiation_income_gain(self)
            r_prog, r_walk = walk_reward_yaw.turn_kernel_neutral(self,
                goal, info, r_prog, r_walk, s_ref)
            reward = float(reward) + r_walk + r_prog + r_cmd_track \
                + r_free_pen + r_ratio + r_lsratio + r_gap + r_freeze
            if r_free_pen != 0.0:
                info["reward_walk_freeprog_pen"] = r_free_pen
            info["reward_walk"] = r_walk
            info["reward_walk_prog"] = r_prog
            if k_cmd_track > 0.0:
                info["reward_walk_cmd_track"] = r_cmd_track
            info["walk_vel_err"] = err
            info["walk_speed"] = float(np.hypot(*v))
            reward = walk_reward_charges.fast_profile_tracking_charges(self,
                goal, info, reward, s_ref, v)
            reward = walk_reward_charges.idle_travel_floor_charge(self,
                along, info, reward, s_ref)
            reward = walk_reward_charges.stop_charges(self,
                goal, info, reward, s_ref, v)
            reward = walk_reward_charges.move_current_charge(self,
                info, reward, s_ref)
            reward = walk_reward_course.course_charge(self,
                goal, info, reward, s_ref, v)
            reward = walk_reward_course.course_displacement_charge(self,
                goal, info, reward, s_ref)
            reward = walk_reward_course.course_increment_and_sway_charges(self,
                goal, info, reward, s_ref, support_gate)
            walk_reward_progress.direction_telemetry(self,
                along, cmd_cross, goal, info, k_cmd_track, s_ref, v)
            reward = walk_reward_stepevent.phase_contact_agreement(self,
                info, reward, s_ref)
            reward = walk_reward_stepevent.step_event_package(self,
                along, g_duty, g_gait, g_lsratio, g_ratio, g_ratio_swingfloor,
                g_swing, g_swinggap, g_swinit, goal, info, lift, reward, s_ref)
            reward = walk_reward_charges.effort_charge(self, info, reward)
            reward = walk_reward_yaw.hip_yaw_margin_charge(self, info, reward)
            if mode_q:
                # quadwalk: the lifted-fronts income (clear/plant,
                # same cfg keys and grace as quad hold) rides on top
                # of the walk stack — fronts-down forfeits it by
                # construction, which is what makes the six-leg and
                # drag cheats under-earn (QUADWALK semantics bank).
                reward, info = self._quad_income(float(reward), info)
        elif (self._goal_traj is not None
                and getattr(self._goal_traj, "mode", "") == "quad"):
            reward, info = self._quad_income(float(reward), info)
        elif getattr(self, "_is_getup", False):
            reward, info = self._getup_reward(float(reward), info)
        elif getattr(self, "_is_recover", False):
            reward, term, info = self._recover_reward(
                float(reward), term, trunc, info)
        # reward.term_penalty (2026-08-18, fb_20260818T065930_03b422):
        # cfg-gated in-env twin of train_ppo_transfer's TRAINING-ONLY
        # _term_penalty_wrapper (one-time charge on early termination,
        # the dynrep pilots' anti-suicide term) so the batched MJX
        # trainers — which construct shim envs internally and cannot
        # wrap them — can train on the exact walkcurr2 reward contract.
        # Default 0.0 = bit-exact legacy. Eval/cert envs leave it 0
        # (evals run the raw reward, same rule as the transfer trainer).
        if term and not trunc:
            _tp = float(cfg_get(self.cfg, "reward", "term_penalty",
                                default=0.0))
            # reward.walk_idle_terminate_penalty (2026-08-24): the
            # sustained-idle boundary (safety.walk_idle_terminate_s)
            # fires on the SAME code path as every other termination,
            # which by default pays the full anti-suicide term_penalty
            # (sized, correctly, to make a fast tilt-death the worst
            # outcome in the bank). Reusing that same large lump for
            # idle-eviction was measured to collapse the fine per-tick
            # ranking the WALKCURR_PF bank requires among the
            # non-progressing behaviors (park/stall/reverse/sideways/
            # skate) -- once ALL of them also pay the ~1200 lump, only
            # their few pre-termination ticks of charge differ, and
            # a slow idle death can end up cheaper than the fast
            # topple death purely by paying fewer accumulated ticks,
            # inverting the required floor. A distinct, independently
            # sized penalty (default -1 sentinel = fall back to
            # reward.term_penalty, bit-exact unless set) lets a
            # walkcurr rung price "keep failing to progress" as
            # strictly worse than every live behavior WITHOUT
            # swamping the graded ranking among the live ones.
            if info.get("termination_reason") == "walk_idle_terminate":
                _tp_idle = float(cfg_get(
                    self.cfg, "reward", "walk_idle_terminate_penalty",
                    default=-1.0))
                if _tp_idle >= 0.0:
                    _tp = _tp_idle
            # reward.walk_leg_duty_terminate_penalty (2026-09-07): same
            # independent-sizing rationale as walk_idle_terminate_
            # penalty directly above -- a chronic single-leg-parked
            # death should rank on the same fine per-tick scale as
            # every other non-progressing behavior (park/stall/
            # reverse/sideways/skate), not swamp it with the full
            # anti-suicide term_penalty lump. Sentinel -1.0 = fall back
            # to reward.term_penalty, bit-exact unless set.
            if info.get("termination_reason") == "walk_leg_duty_terminate":
                _tp_ldt = float(cfg_get(
                    self.cfg, "reward", "walk_leg_duty_terminate_penalty",
                    default=-1.0))
                if _tp_ldt >= 0.0:
                    _tp = _tp_ldt
            if _tp > 0.0:
                reward = float(reward) - _tp
        if self.walk_probe_on and self._wp is not None:
            # Measurement-only walk quality probe (walkcurr MJX cert,
            # fb_20260818T065930_03b422): accumulate AFTER the full
            # reward stack so per-episode return matches what the
            # trainer sees; on the terminal tick the summary rides the
            # info dict. Zero effect on obs/reward/rng.
            self._walk_probe_tick(float(reward), bool(term),
                                  bool(trunc), info)
        # Adaptive/adversarial struct-DR feedback (dr.struct_dr_adaptive,
        # 2026-09-14 speed track — see domain_rand.DomainRandomizer.
        # record_struct_outcome/struct_story_weights): track this
        # episode's own peak roll and, on its last tick, report it back
        # to the SAME randomizer instance that drew the struct overlay,
        # tagged with the story that instance actually used — the only
        # write path into its regret state. Guarded on the cfg flag
        # (default off): this whole block is then one getattr check and
        # a no-op every tick, zero effect on obs/reward/rng in the
        # default (off) path.
        _rnd = self.randomizer
        if _rnd is not None and bool(
                getattr(_rnd.ranges, "struct_dr_adaptive", False)):
            self._struct_ep_peak_roll_deg = max(
                getattr(self, "_struct_ep_peak_roll_deg", 0.0),
                abs(float(info.get("roll_deg", 0.0))))
            if term or trunc:
                _er = self._ep_rand
                _story = (getattr(_er, "struct_dr_story", "")
                         if _er is not None else "")
                if _story:
                    _rnd.record_struct_outcome(
                        _story, self._struct_ep_peak_roll_deg)
                self._struct_ep_peak_roll_deg = 0.0
        return obs, reward, term, trunc, info

    def _quad_income(self, reward: float, info: dict) -> tuple:
        """Quad-family lifted-fronts shaping, shared by the quad HOLD
        mode and quadwalk (08-13; pure code motion from the quad elif
        in _post_step — behavior identical for quad mode).

        Quad-hold shaping (feasibility GO, c57; all cfg-gated,
        default 0 = mode earns only the base kernels). Two income
        terms, no new charges — the level kernel, current charge
        and tilt trip already price the failure modes:
          k_quad_clear: pay each LIFT leg's height above its
            episode-start pad z, clipped at 30 mm,
            and only while that foot is OFF the ground (a loaded
            "lifted" leg earns nothing by construction).
          k_quad_plant: pay the loaded fraction of the four
            support legs — the four-planted half of the task.
        A grace window (quad_grace_s) keeps the settle + lift
        transient unpaid so income starts only once the hold
        could actually be happening.

        k_quad_still (08-13, quad track: the turn1-r1 dig-in measured
        the learned quad HOLD stance creeping ~0.33 m/15 s — stillness
        was never priced; hold_still_gate is scoped hold/track and
        exempts quad by design): per-tick charge on body planar speed
        above a 5 mm/s floor, applied ONLY while no velocity is
        commanded (s_ref ~ 0) so it can never fight a quadwalk
        command. Default 0 = off, legacy exact.

        k_quad_lift_contact (08-13, quad track, after cw-quadwalk1/2:
        pure lift-INCOME pricing is a closed lever — 3x clear/plant
        income moved front-leg tail contact duty only 1.0 -> 0.62/0.32,
        never under the 0.15 fronts_lifted bar; six-leg walking from
        the warm start pays too well to abandon for a side bonus):
        per-tick CHARGE on the fraction of commanded LIFT legs in
        ground contact after the grace window. Makes keeping the
        fronts down strictly unprofitable instead of merely less
        profitable; the honest lifted form pays ~0 by construction.
        Applies to the whole quad family (quad hold's honest form has
        the fronts off the ground, so it is uncharged). Default 0 =
        off, legacy exact.
        """
        goal = self._current_goal()
        lift = tuple(goal.lift_legs) if goal.lift_legs else ()
        grace_n = int(round(float(cfg_get(
            self.cfg, "goal", "quad_grace_s", default=1.5)) / self.dt))
        k_qc = float(cfg_get(self.cfg, "reward", "k_quad_clear",
                             default=0.0))
        k_qp = float(cfg_get(self.cfg, "reward", "k_quad_plant",
                             default=0.0))
        if lift and self._step_i > grace_n and (k_qc > 0.0
                                                or k_qp > 0.0):
            cap_m = 30.0 / 1000.0
            clear_sum = 0.0
            clear_mm = 0.0
            fronts_off = 0
            for f in lift:
                adr = self._touch_adr[f]
                on = (adr >= 0 and
                      float(self.data.sensordata[adr]) > 0.5)
                z_ref = (self._pad_z_ref[f]
                         if self._pad_z_ref is not None else 0.0)
                clear = float(
                    self.data.xpos[self._pad_bids[f], 2]) - z_ref
                clear_mm += clear * 1000.0
                if not on:
                    fronts_off += 1
                    clear_sum += min(max(clear / cap_m, 0.0), 1.0)
            support = [f for f in range(6) if f not in lift]
            n_on = sum(
                1 for f in support
                if self._touch_adr[f] >= 0
                and float(self.data.sensordata[
                    self._touch_adr[f]]) > 0.5)
            # walk_gait_gate (08-13): on commanded quadwalk ticks the
            # clear/plant income rides the SAME all-support-legs
            # factor as the kernel — otherwise "sit fronts-up and
            # scoot" keeps its ~2.25/tick sitting income while the
            # gate zeroes only transport pay (quadwalk4/5's cheat was
            # funded by exactly this stream). Quad HOLD mode and
            # quadwalk stillness segments are untouched (the factor
            # is reset to 1.0 on every non-commanded tick and the
            # mode check below skips hold outright); gate off =
            # factor 1.0 = bit-exact.
            qgt = 1.0
            if getattr(self._goal_traj, "mode", "") == "quadwalk":
                qgt = float(getattr(self, "_gait_gate_qfactor", 1.0))
            r_qc = k_qc * clear_sum / max(len(lift), 1) * qgt
            r_qp = k_qp * n_on / max(len(support), 1) * qgt
            reward = float(reward) + r_qc + r_qp
            info["reward_quad_clear"] = r_qc
            info["reward_quad_plant"] = r_qp
            info["quad_clear_mm"] = clear_mm / max(len(lift), 1)
            info["quad_fronts_off"] = fronts_off / max(len(lift), 1)
            info["quad_planted_frac"] = n_on / max(len(support), 1)
        k_ql = float(cfg_get(self.cfg, "reward", "k_quad_lift_contact",
                             default=0.0))
        if lift and k_ql > 0.0 and self._step_i > grace_n:
            n_lift_on = sum(
                1 for f in lift
                if self._touch_adr[f] >= 0
                and float(self.data.sensordata[self._touch_adr[f]]) > 0.5)
            if n_lift_on:
                r_ql = -k_ql * n_lift_on / max(len(lift), 1)
                reward = float(reward) + r_ql
                info["reward_quad_lift_contact"] = r_ql
        k_qs = float(cfg_get(self.cfg, "reward", "k_quad_still",
                             default=0.0))
        if lift and k_qs > 0.0 and self._step_i > grace_n:
            s_ref = float(np.hypot(getattr(goal, "vx_ref", 0.0),
                                   getattr(goal, "vy_ref", 0.0)))
            if s_ref <= 1e-3:
                sp = float(np.hypot(*self._body_vel_xy()))
                r_qs = -k_qs * max(sp - 0.005, 0.0)
                reward = float(reward) + r_qs
                info["reward_quad_still"] = r_qs
                info["quad_body_speed"] = sp
        return reward, info

    # ------------------------------------------------------------------
    # GETUP mode reward (08-11, from-scratch redesign; REWARD.md §4b).
    #
    # Design constraints inherited from the whole stand campaign:
    #  - the flag-leg/tripod-at-height cheat beat every height-income
    #    mechanism on warm starts; the sanctioned unexplored lever is a
    #    STRUCTURAL coupling between height and MEASURED foot contact
    #    (RL_PLAN queue 2b) — here, height only counts through the
    #    supported-stand score S = f_height * f_feet(loaded)^2 *
    #    f_level * f_footprint (fades, not hard zeros: the holdstill1
    #    zero-gradient lesson);
    #  - freezing must earn ~0 (no kernel income in this mode at all —
    #    a level belly-rest satisfies the tilt kernel for free);
    #  - income is a ONE-SHOT staged ratchet (pays only new bests of
    #    the pipeline potential P) plus GATED steady pay, so neither
    #    regressing nor re-farming a partial rise is a living;
    #  - falling is not terminal (runs widen the tilt trip): after a
    #    fall the ratchet stays banked and the incentive to get back
    #    up is the restoration of the S-gated hold/walk income.
    # ------------------------------------------------------------------

    def _getup_geom(self) -> tuple[float, float]:
        """(z_plant, weight_n): chassis height at the plant stance
        (the f_height ceiling, same construction as _place_at_plant's
        base_z) and the robot's total weight in newtons (the
        load-stage denominator). Model constants — cached once, not
        episode state."""
        if not hasattr(self, "_getup_geom_cache"):
            import mujoco_prototype as MP
            from rl_move.body_ik import fk_all_feet
            deg2rad = math.pi / 180.0
            q_p = self._plant_deg * deg2rad
            feet_p = fk_all_feet(q_p)
            z_plant = (MP.YAW_OUTPUT_HEIGHT
                       - float(np.min(feet_p[:, 2])) + MP.FOOT_R)
            weight_n = float(np.sum(self.model.body_mass)) * 9.81
            self._getup_geom_cache = (z_plant, weight_n)
        return self._getup_geom_cache

    def _getup_reward(self, reward: float, info: dict
                      ) -> tuple[float, dict]:
        # 1) Strip the base kernel + tilt shaping. The tracking kernel
        #    pays a LEVEL body ~1/tick and a flat belly-rest is level —
        #    that is an alive bonus in disguise here. The quadratic
        #    tilt shaping would likewise charge every recovery tick at
        #    the widened envelope. Regularizers (gyro/action/current)
        #    stay: they price physics, not task shape.
        return walk_reward_recover.getup_reward(self, reward, info)

    @staticmethod
    def _rec_gate(x: float) -> float:
        """Smooth gate g(x): smoothstep on [0,1] — C1, monotone, g(0)=0,
        g(1)=1. The directive requires smooth gates (no hard
        thresholds inside the potential)."""
        x = min(max(x, 0.0), 1.0)
        return x * x * (3.0 - 2.0 * x)

    def _recover_reward(self, reward: float, term: bool, trunc: bool,
                        info: dict) -> tuple[float, bool, dict]:
        """recover_to_plant pricing (08-15 directive
        fb_20260815T165306_606974; REWARD.md §4c).

        r = kP*(gamma*Phi(s') - Phi(s)) + B*first_held_success
            - c_time*dt (until termination, incl. the success hold)
            - fail_cost at timeout/safety termination without success
        plus the base regularizers (gyro/action/current — physics
        pricing stays; the tracking kernel + tilt shaping are stripped
        like getup ticks). Phi uses bounded [0,1] features with smooth
        gates:
          U  uprightness ((1+cos(tilt))/2 — full gradient from
             upside-down)
          L  mean six-foot load saturation
          H  supported stand-height progress (belly->z_full, the
             compliance-calibrated real stand height; overshoot above
             the FK plant fades to 0 like getup — stilt pops price
             themselves)
          M  SMOOTH-MIN per-foot load — one unloaded foot stays
             visible; the getup3-c2/getup4 mean-average plateau cannot
             recur by construction
          P  nominal-footprint closeness (the getup f_footprint fade)
          Phi = wU*U + wL*g(U)*L + wH*g(U)*L*H + wM*g(U)*g(H)*M
                + wP*g(U)*g(H)*P            (weights .15/.15/.30/.30/.10)
        Success = 0.5 s CONTINUOUS hold of: |z - z_full| <= 15 mm,
        tilt <= 6 deg, every foot's load fraction >= 0.35 AND
        pad spread small (all six near the ground and loaded — no
        mean-only loophole), footprint closeness >= 0.5 (support
        proxy), low joint/body velocity, and no current violation.
        Falls are NOT terminal; the episode ends only on held success
        (one-shot bonus, term=True), timeout, or the safety envelope.
        A non-success termination pays 1.25x the full-episode time
        tax, so early abort can never out-earn trying.
        PBRS telescopes over the episode, so the spawn potential is
        never income and re-farming a feature pays 0 by construction.
        """
        return walk_reward_recover.recover_reward(self,
            reward, term, trunc, info)
