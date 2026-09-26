"""Construction-time state of SimHexapodJointWalkEnv (the __init__ blocks), moved out of SimHexapodJointWalkEnv.__init__.

Every function here is one contiguous block of the walk env constructor
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``__init__`` is a single call.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import math

from rl_move.config import cfg_get
from .walk_task import (
    WALKCURR_BUCKETS, WALKCURR_BUCKETS_V10, WALKCURR_BUCKETS_V2,
    WALKCURR_BUCKETS_V3, WALKCURR_BUCKETS_V4, WALKCURR_BUCKETS_V5,
    WALKCURR_BUCKETS_V6, WALKCURR_BUCKETS_V7, WALKCURR_BUCKETS_V8,
    WALKCURR_BUCKETS_V9,
)


def init_reward_bookkeeping(env):
    # Swing-bonus bookkeeping (see step()): per-foot contact state
    # and world XY at the moment of liftoff.
    env._pad_bids = [env.model.body(f"L{i}_pad").id
                      for i in range(6)]
    env._foot_on = [True] * 6
    env._liftoff_xy = [None] * 6
    env._liftoff_step = [0] * 6
    env._foot_prev_xy = [None] * 6
    env._foot_prev_force = [0.0] * 6
    env._foot_tan_slip_m = [0.0] * 6
    env._duty_hist: list = []
    # Per-leg contact-duty income gate history (09-05,
    # reward.walk_duty_gate): trailing window of six contact
    # booleans per commanded tick, SEPARATE from k_park's
    # _duty_hist so the two mechanisms cannot perturb each
    # other's windows. Rides MJX_SNAPSHOT_EXTRA.
    env._dgate_hist: list = []
    # Per-leg qualifying-swing-event history (09-05,
    # reward.walk_swing_gate): trailing window of six booleans per
    # commanded tick (True = this leg COMPLETED a real swing this
    # tick, same stride-filtered definition walk_gait_gate uses),
    # kept SEPARATE from _dgate_hist/_duty_hist so the three
    # mechanisms cannot perturb each other's windows.
    env._swing_gate_hist: list = []
    # Anchored-stance income gate bookkeeping (cycle 30): per-foot
    # world XY at touchdown ("anchor point") and its own prev-contact
    # state, kept SEPARATE from the step-event vars above so the two
    # mechanisms cannot perturb each other. prev_on starts False so
    # the first loaded tick registers as a touchdown and anchors the
    # initial stance feet where they stand.
    env._anchor_xy = [None] * 6
    env._anchor_prev_on = [False] * 6
    # Displacement budget for step-event credit (cycle 34, 0-c.2):
    # net body displacement (m) accrued along the commanded
    # direction and not yet spent on step credits.
    env._step_disp_bank = 0.0
    # Heading-hold drift EMA (reward.yaw_still_avg_s); per-episode,
    # reset in _reset_begin, snapshot via MJX_SNAPSHOT_EXTRA.
    env._yaw_still_ema = 0.0
    env._yaw_prog_ema = 0.0
    # Task-space turn-OFFSET cumulative achieved rotation
    # (goal.walk_yaw_offset_set lineage; walk_reward_yaw.
    # yaw_offset_kernel), integrated from env._body_wz() every walk
    # tick since episode/segment start. Per-episode, reset in
    # _reset_begin, snapshot via MJX_SNAPSHOT_EXTRA — same lifecycle
    # as _yaw_still_ema/_yaw_prog_ema above.
    env._yaw_offset_achieved = 0.0
    # Leg-odometry velocity estimator (goal.walk_obs_body_vel=3
    # only; None in every other mode = zero overhead). Per-episode
    # stateful — recreated on reset in _augment_obs, snapshot via
    # MJX_SNAPSHOT_EXTRA (instances deep-copy cleanly by design;
    # estimator.py docstring).
    env._vel_est = None
    # Loaded-slip income gate bookkeeping (operator ruling 2026-08-09
    # §3/WALK-SLIP): episode-accumulated loaded foot-XY travel and
    # along-command body progress. NEVER reset by touchdown — only
    # at episode reset — so cadence cannot re-buy an allowance.
    env._ls_prev_xy = [None] * 6
    env._ls_prev_on = [False] * 6
    env._ls_slip_m = 0.0
    env._ls_prog_m = 0.0
    # Windowed (EMA) loaded-slip rate bookkeeping
    # (reward.walk_loadslip_window_s, default 0 = off, see the
    # walk_loadslip_gate block in step()). Separate from the
    # cumulative _ls_slip_m/_ls_prog_m above so the legacy
    # episode-cumulative ratio stays bit-exact when off.
    env._ls_slip_ema = 0.0
    env._ls_prog_ema = 0.0
    # Anti-park travel-floor EMA (reward.k_walk_idle_charge);
    # per-episode/per-segment, snapshot via MJX_SNAPSHOT_EXTRA.
    env._walk_idle_ema = 0.0
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
    env._walk_idle_low_s = 0.0
    env._walk_qvel_ema = 0.0
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
    env._walk_legduty_ema = [1.0] * 6
    env._walk_legduty_low_s = [0.0] * 6
    # Per-leg duty-RATIO reward-charge EMA (reward.walk_leg_duty_
    # ratio_charge, 2026-09-08); own state, independent of the
    # termination feature's _walk_legduty_ema above. Seeded at 1.0
    # for the same "begins loaded at the plant" reason. Tick
    # counter gates the charge off until the EMA has had a chance
    # to reflect real contact data (mirrors the window-must-fill
    # grace every other gate in this file uses).
    env._legduty_ratio_ema = [1.0] * 6
    env._legduty_ratio_ticks = 0
    env._legduty_ratio_swing_hist: list = []
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
    env._legslip_ratio_ema = [0.0] * 6
    env._legslip_ratio_ticks = 0
    # Per-leg swing-GAP reward-charge state (reward.walk_leg_
    # swing_gap_charge, 2026-09-08): seconds elapsed since each
    # leg's last qualifying swing event -- see the mechanism's
    # own comment block in step() for the full design rationale
    # (the "duration-since-last-swing PATTERN price" lead named
    # by the loadslip-ratio-charge closure). Seeded at 0.0 (a leg
    # is trivially "just swung" at the plant-start reset, mirroring
    # the loadslip EMA's own 0-seed rationale). Independent of
    # every other slip/duty mechanism's state above.
    env._swing_gap_s = [0.0] * 6
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
    env._liftoff_was_maxload = [False] * 6
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
    env._swinit_load_ema = [0.0] * 6
    # Seconds since the current commanded-stop segment began
    # (reward.walk_stop_grace_s); 0 whenever s_ref > 1e-3
    # (walking commanded), increments by dt each stop tick.
    # Used only to ramp the stop-speed charge in over the
    # unavoidable deceleration transient -- see the charge
    # site below. Same lifecycle as _walk_idle_ema.
    env._walk_stop_cmd_s = 0.0
    # Structural stop-hold timer (goal.walk_stop_freeze_s);
    # same lifecycle as _walk_stop_cmd_s -- see
    # sim_env._walk_stop_freeze_override.
    env._walk_stop_freeze_cmd_s = 0.0
    # Commanded-course EMA (reward.k_walk_course); same lifecycle.
    env._walk_course_ema = [0.0, 0.0]
    # Commanded-course NET-DISPLACEMENT ring buffer
    # (reward.k_walk_course_disp, the k_walk_course EMA-
    # cancellation fix-lever (b), 08-29 standwalk DIG-IN); lazily
    # (re)allocated in the reward step once the window size is
    # known, so a plain reset just drops any prior buffer.
    env._walk_course_disp_hist = None
    # Windowed course-following INCOME + excess-sway ring buffer
    # (reward.k_walk_course_income / reward.k_walk_excess_sway,
    # operator reward-design directive fb_20260829T142239_63c818):
    # deque of (x, y, cum_cmd_x, cum_cmd_y, cum_active_ticks) with
    # the running totals in _walk_course_win_cum; lazily
    # (re)allocated in the reward step once the window sizes are
    # known. Same lifecycle as _walk_course_disp_hist.
    env._walk_course_win_hist = None
    env._walk_course_win_cum = [0.0, 0.0, 0]
    # Stride-EMA velocity for the tracking kernel
    # (reward.walk_kernel_vel_ema); same lifecycle.
    env._walk_kernel_vema = [0.0, 0.0]
    # Stride-EMA yaw-rate for the yaw tracking kernel
    # (reward.walk_kernel_yaw_ema); same lifecycle.
    env._walk_kernel_wz_ema = 0.0
    # Structural stance-slip charge (2026-08-11 charge-magnitude
    # audit, probe_drag_audit.py / GAIT.md P2): accumulated loaded
    # XY travel of the CURRENT stance period per foot. Reset at
    # touchdown (a new stance earns a fresh allowance), charged
    # continuously beyond reward.drag_stance_allow_mm. Audit truth:
    # per-TICK slip cannot separate skating from honest walking
    # (medians 0.40-0.47 vs 0.31 mm overlap; the 0.5 mm deadband
    # leaves 53-97% of skating free), but per-STANCE travel splits
    # them 3.3x (learned skaters median 9.8 mm vs scripted gait
    # 2.9 mm, p90 5.7) — charge the stroke, not the jitter.
    env._stance_slip_acc = [0.0] * 6
    # Touchdown/liftoff TRANSITION-WINDOW slip charge (2026-09-07,
    # walkcurr phase-binned slip audit follow-up: touchdown+liftoff
    # ticks carry ~50-60% more per-tick material slip than
    # mid-stance, see rl_docs/tracks/walkcurr/STATUS.md 09-07
    # ~18:2x). `_trans_td_count[f]` counts down the remaining
    # ticks of the touchdown window for leg f (0 = not in window);
    # `_trans_lo_buf[f]` is a small trailing ring (plain list,
    # truncated to reward.walk_transition_lo_ticks) of this
    # stance's most recent per-tick tangential slip velocities,
    # charged retrospectively at the moment leg f lifts off (the
    # tail of the buffer IS the liftoff window at that instant).
    env._trans_td_count = [0] * 6
    env._trans_lo_buf: list = [[] for _ in range(6)]


def init_charge_ramps(env):
    # Drag-stance allowance RAMP (08-22, phasedir9-seed-lottery
    # dig-in / pd8 regime-gap follow-up): the det-calibrated
    # drag_stance_allow_mm cannot separate honest walking from a
    # drag cheat while PPO's action-noise std is still high early
    # in training (pd8_digin_regime: at std 0.135 the honest
    # clone's own per-stance travel needs an allowance >=48mm to
    # stay untaxed while the det drag cheat pays zero past 36mm) —
    # a FIXED tight allowance (24mm) taxes noisy honest exploration
    # far harder than the cheat before basin selection happens,
    # which the log-std anneal alone cannot fix (mirrors
    # bus.profile_ramp_steps' construction exactly: cfg-armed,
    # trainer-driven, default OFF = bit-exact legacy). When armed
    # (reward.drag_stance_allow_ramp_steps > 0), the ALLOWANCE
    # starts loose (reward.drag_stance_allow_ramp_mm, meant to sit
    # above the noisy-honest tail) and anneals down to the normal
    # reward.drag_stance_allow_mm target over that many GLOBAL env
    # steps — armed but never broadcast (apply_drag_allow_frac)
    # sits at the TARGET allowance, so eval_checkpoint/play/the
    # periodic C-env evals always judge the calibrated final
    # pricing even when the training cfg carries ramp keys, exactly
    # like the profile ramp.
    env._drag_allow_ramp: dict | None = None
    env._drag_allow_override_m: float | None = None
    _da_ramp_steps = int(float(cfg_get(
        env.cfg, "reward", "drag_stance_allow_ramp_steps",
        default=0) or 0))
    if _da_ramp_steps > 0:
        _da_target_mm = float(cfg_get(
            env.cfg, "reward", "drag_stance_allow_mm", default=6.0))
        _da_start_mm = float(cfg_get(
            env.cfg, "reward", "drag_stance_allow_ramp_mm",
            default=48.0))
        if _da_start_mm < _da_target_mm:
            raise ValueError(
                "reward.drag_stance_allow_ramp_mm "
                f"({_da_start_mm:g}) must be >= the target "
                f"reward.drag_stance_allow_mm ({_da_target_mm:g}) "
                "— the ramp only ever loosens, never tightens, "
                "the allowance")
        env._drag_allow_ramp = {
            "steps": _da_ramp_steps,
            "start_m": _da_start_mm / 1000.0,
            "target_m": _da_target_mm / 1000.0,
            "frac": 1.0,
        }
    # Turn-in-place EXPOSURE-TIMING ramp (09-25, walkcurr turn-authority
    # Next-1 item: CURRENT_TRUTHS/STATUS.md 2026-09-24 ~21:2x closed the
    # STATIC command-mix fraction `goal.walk_turn_in_place_frac` (tried
    # at a fixed 0.5 from step 0, both `drramp` and `easedterm` SAC
    # bases, warm-started-from-a-turn-specialist and scratch, 4/4 FAIL —
    # "the interference is structural to the task mixture itself... not
    # the init distribution or the termination caps"). That closure
    # never varied WHEN in training the mixed exposure starts — every
    # arm commanded turn-in-place segments from tick 0, before either
    # walk-forward or turn-in-place is separately established. This
    # ramp is the untried TIMING axis its own closure names ("a
    # nonzero-wz-seeding curriculum"): with
    # goal.walk_turn_in_place_frac_ramp_steps > 0, the live turn-in-
    # place draw fraction starts at
    # goal.walk_turn_in_place_frac_ramp_start (default 0.0 = pure
    # walk-forward only) and anneals LINEARLY up to the cfg target
    # (goal.walk_turn_in_place_frac) over that many GLOBAL env steps,
    # letting the policy consolidate plain walking before the
    # turn-in-place command distribution is introduced. Same
    # cfg-armed / trainer-driven / default-OFF contract as every other
    # ramp in this file: default absent/0 is bit-exact legacy
    # (env._tip_frac_override stays None, the direct cfg read in
    # walk_task.py._sample_walk is unchanged); armed-but-unbroadcast
    # (trainer never calls apply_walk_tip_frac) sits at the FULL cfg
    # target because the override is only set once the trainer
    # broadcasts, so a train script that forgets to wire the callback
    # fails safe at the ALREADY-refuted static-mix behavior, never a
    # silently-diluted one. Tests:
    # rl_move/tests/test_walk_tip_frac_ramp.py.
    env._tip_frac_ramp: dict | None = None
    env._tip_frac_override: float | None = None
    _tip_ramp_steps = int(float(cfg_get(
        env.cfg, "goal", "walk_turn_in_place_frac_ramp_steps",
        default=0) or 0))
    if _tip_ramp_steps > 0:
        _tip_target = float(cfg_get(
            env.cfg, "goal", "walk_turn_in_place_frac", default=0.0))
        _tip_start = float(cfg_get(
            env.cfg, "goal", "walk_turn_in_place_frac_ramp_start",
            default=0.0))
        env._tip_frac_ramp = {
            "steps": _tip_ramp_steps,
            "start": _tip_start,
            "target": _tip_target,
            "frac": 0.0,
        }

    # Dense walk-charge RAMP (08-23, walkcurr fwd1/fwd2 dig-in):
    # from-scratch PPO froze into a tilt-safe splayed crouch for
    # 2M steps in three straight rung-1 arms because the dense
    # per-step walk charge flow (~-4.7/step, loadslip-dominated
    # via the 0.03 m travel floor) both makes freezing the best
    # REACHABLE policy and instantly punishes the flailing that
    # exploration must pass through, while every income channel
    # requires competent locomotion before it pays (walk_prog
    # identically 0.0 across all three runs); no bank-legal
    # income dose can compete (fwd2-swing/swingterm800 FAIL,
    # 08-23). When armed (reward.walk_charge_ramp_steps > 0) the
    # three DISCOVERY-FRICTION walk charges — k_park_duty,
    # k_walk_idle_charge, k_walk_heading — are scaled by
    # walk_charge_ramp_min_frac at frac 0 and anneal linearly UP
    # to the full bank-proven dose at frac 1. k_loadslip_excess is
    # DELIBERATELY EXCLUDED (bank finding, same day: ramping it
    # down at the shared min_frac=0.15 made 'skate'/'shuffle' beat
    # every wrong-way/standing behavior — see
    # test_walkcurr_chargeramp_min_ranking_holds) and always
    # charges at full dose; the ramp only loosens the charges that
    # make REFUSING to move look falsely cheap, never the
    # anti-skate/anti-fall floor. Same cfg-armed /
    # trainer-driven / default-OFF contract as the term-penalty
    # and drag-allow ramps: default absent/0 is bit-exact legacy,
    # and armed-but-unbroadcast sits at the FULL charges so
    # eval_checkpoint / play / the periodic C-env evals always
    # judge the bank-proven pricing even mid-ramp cfg.
    env._walk_charge_ramp: dict | None = None
    env._walk_charge_override: float | None = None
    _wc_ramp_steps = int(float(cfg_get(
        env.cfg, "reward", "walk_charge_ramp_steps",
        default=0) or 0))
    if _wc_ramp_steps > 0:
        # Default floor 0.40, MEASURED (08-23 chargeramp floor
        # bank): at 0.15 the loosened charges invert the required
        # ranking (skate +131 out-earns sideways +52/reverse -1.3
        # and shuffle +228 becomes a strong positive rest point);
        # 0.40 is the lowest floor that keeps skate/shuffle priced
        # below every honest behavior while the top of the
        # landscape stays positive-sum (gait > stall > park, all
        # positive); re-baseline against canonical v2 trajectories.
        # WALKCURR_PF_CHARGERAMP_MIN_OVERRIDES.
        _wc_min = float(cfg_get(
            env.cfg, "reward", "walk_charge_ramp_min_frac",
            default=0.40))
        if not 0.0 <= _wc_min <= 1.0:
            raise ValueError(
                "reward.walk_charge_ramp_min_frac "
                f"({_wc_min:g}) must be in [0, 1] — the ramp "
                "only ever anneals the charges UP to the "
                "bank-proven full dose")
        env._walk_charge_ramp = {
            "steps": _wc_ramp_steps, "min_frac": _wc_min,
            "frac": 1.0,
        }
    # Loaded-slip-excess BOOTSTRAP (08-23, walkcurr fwd4 dig-in
    # follow-up): fwd1-fwd4 (four straight rung-1 arms — plain,
    # swing-income x2, charge-ramp, wider-init-noise x2) all froze
    # into a static splayed crouch with env/walk_freeprog_score
    # flat/negative for the full 2M budget; the walk-charge ramp
    # deliberately EXCLUDED k_loadslip_excess (bank finding: ramping
    # it down TOGETHER with the other three charges at their shared
    # min_frac=0.15 made 'skate'/'shuffle' beat every honest
    # standing/wrong-way behavior). This is a SEPARATE, narrower
    # lever: soften ONLY k_loadslip_excess, ONLY for a short early
    # bootstrap window, ANNEALING BACK UP to the full bank-proven
    # dose — distinct from the rejected permanent-low-floor design.
    # Same cfg-armed / trainer-driven / default-OFF contract as the
    # three ramps above (bit-exact when reward.
    # walk_loadslip_bootstrap_steps is 0/absent). Re-proven at ITS
    # OWN schedule against the WALKCURR_PF bank held at the
    # bootstrap's min_frac (loadslip alone loosened, the other three
    # discovery-friction charges at full dose — the opposite
    # combination from the rejected chargeramp-min design) — see
    # This dose requires a fresh canonical v2 trajectory-bank baseline.
    # cfg: reward.walk_loadslip_bootstrap_steps (int, 0=off). The
    # 0.65 min fraction was MEASURED separately from the walk-charge
    # ramp's 0.40 floor: this charge, held alone at 0.40 while the
    # other three discovery-friction charges stay at FULL dose
    # (the least-favorable single-lever combination), lets
    # 'sideways' (-231) out-earn 'park' (-352) — a ranking
    # violation the bank catches
    # (test_walkcurr_loadslip_bootstrap_min_ranking_holds); 0.65
    # is the lowest floor in a 0.5-0.8 sweep that keeps
    # park/stall strictly above every wrong-way gait (margin
    # ~37) while still cutting the skate penalty by ~30% (-1339
    # -> -940) relative to the retired pre-v2 full dose.
    # WALKCURR_PF_LOADSLIP_BOOTSTRAP_MIN_OVERRIDES.
    env._ls_bootstrap: dict | None = None
    env._ls_bootstrap_override: float | None = None
    _lsb_steps = int(float(cfg_get(
        env.cfg, "reward", "walk_loadslip_bootstrap_steps",
        default=0) or 0))
    if _lsb_steps > 0:
        env._ls_bootstrap = {
            "steps": _lsb_steps, "min_frac": 0.65, "frac": 1.0,
        }


def init_gait_gate_and_curriculum_state(env):
    # All-support-legs gait gate bookkeeping (08-13, quad track,
    # reward.walk_gait_gate): per-leg COMMANDED-tick index of the
    # last completed real swing (liftoff -> >=2 ticks airborne ->
    # touchdown with XY stride >= gait_gate_stride_mm), plus the
    # commanded-tick clock itself and the per-tick factor stashed
    # for _quad_income's clear/plant gating. All three ride
    # MJX_SNAPSHOT_EXTRA (pool-restore lesson, commit 65edba7).
    env._gait_last_step = [0] * 6
    env._gait_cmd_tick = 0
    env._gait_gate_qfactor = 1.0
    # Learning-progress curriculum state: sampling weights over
    # LP_BUCKETS (None = uniform) and the bucket of the current
    # walk episode (surfaced in step info for the LP callback).
    env._lp_weights = None
    env._walk_bucket = None
    # Adaptive competence+retention walk-command curriculum state
    # (goal.walk_curriculum=1..4; see WALKCURR_BUCKETS*).
    # PERSISTENT across episodes like _lp_weights/_rec_* — never in
    # SNAP_ATTRS. _wc_results is certification-only: stochastic
    # rollouts must never move the frontier; the trainer broadcasts
    # deterministic held-out assay results via
    # apply_walkcurr_certification and promotes via
    # walkcurr_update_admission. version 2 (walkcurr2, operator MCP
    # note fb_20260818T060044) selects WALKCURR_BUCKETS_V2 (fixed
    # B0/B1 ignition band + per-bucket gate calibration) instead of
    # the original V1 table; version 1 stays bit-exact unchanged.
    wc_version = float(cfg_get(env.cfg, "goal", "walk_curriculum",
                               default=0.0))
    env._wc_on = wc_version in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
                                 9.0, 10.0)
    env._wc_version = int(wc_version) if env._wc_on else 0
    env._wc_table = (WALKCURR_BUCKETS_V10 if env._wc_version == 10
                      else WALKCURR_BUCKETS_V9 if env._wc_version == 9
                      else WALKCURR_BUCKETS_V8 if env._wc_version == 8
                      else WALKCURR_BUCKETS_V7 if env._wc_version == 7
                      else WALKCURR_BUCKETS_V6
                      if env._wc_version == 6
                      else WALKCURR_BUCKETS_V5
                      if env._wc_version == 5
                      else WALKCURR_BUCKETS_V4
                      if env._wc_version == 4
                      else WALKCURR_BUCKETS_V3
                      if env._wc_version == 3
                      else WALKCURR_BUCKETS_V2
                      if env._wc_version == 2
                      else WALKCURR_BUCKETS)
    if env._wc_version in (4, 5, 6, 7, 8, 9, 10):
        required_s = max(float(b["duration_s"])
                         for b in env._wc_table)
        available_s = env.episode_steps * env.dt
        if available_s + 0.5 * env.dt < required_s:
            raise ValueError(
                f"walk curriculum V{env._wc_version} requires "
                f"episode_seconds >= {required_s:g} (got "
                f"{available_s:g}); long-horizon certification "
                "must not be silently shortened")
    env._wc_active_n = 1
    env._wc_results: dict = {}   # bucket -> {passed, score, cert_round}
    env._wc_bucket = None        # this episode's curriculum bucket
    env._wc_randomizers: dict = {}   # dr scale -> DomainRandomizer
    if env._wc_on and float(cfg_get(
            env.cfg, "goal", "walk_lp_curriculum",
            default=0.0)) == 1.0:
        raise ValueError("goal.walk_curriculum and "
                         "goal.walk_lp_curriculum are mutually "
                         "exclusive command samplers")


def init_obs_and_mode_flags(env):
    # goal.walk_pure (2026-08-18, operator order
    # fb_20260818T065930_03b422): pure-walk diet fixed at
    # CONSTRUCTION time — every p_<mode> on the goal generator is
    # zeroed and p_walk set to 1.0 before the first reset, so the
    # batched MJX vec envs (which build their shim envs internally
    # and mint reset pools immediately) can never sample a mixed
    # diet before a post-construction set_goal_mix lands. Default
    # 0 = off, bit-exact legacy (no draws, no attribute writes).
    if float(cfg_get(env.cfg, "goal", "walk_pure",
                     default=0.0)) > 0.0:
        gen = env._goal_gen
        for _name in dir(gen):
            if (_name.startswith("p_")
                    and isinstance(getattr(gen, _name),
                                   (int, float))):
                setattr(gen, _name, 0.0)
        gen.p_walk = 1.0
    # In-env walk quality probe (measurement only, default OFF;
    # walkcurr MJX certification, fb_20260818T065930_03b422): when
    # walk_probe_on is set (VecEnv set_attr on cert envs), each
    # episode accumulates the eval_task quality metrics from the
    # same mirrored fields the reward stack reads (pad-body XY,
    # touch sensors, safety slew, IMU state, goal refs) and emits
    # them as info["walk_probe"] on the terminal tick. Never
    # affects obs, reward, termination or rng on any backend.
    env.walk_probe_on = bool(float(cfg_get(
        env.cfg, "goal", "walk_probe", default=0.0)) > 0.0)
    env._wp = None
    # Tripod phase clock (default OFF = legacy obs width; see module
    # docstring on the phase reward). Obs order: [base, vel, phase].
    env._phase_obs = float(cfg_get(env.cfg, "goal", "walk_phase_obs",
                                    default=0.0)) == 1.0
    env._phase = 0.0
    # Yaw-rate command channel (goal.walk_yaw_cmd=1): +1 goal obs
    # (scaled wz_ref via WalkGoal.as_obs). New-lineage flag — the
    # width change means no warm start from a non-yaw checkpoint.
    env._yaw_cmd = float(cfg_get(env.cfg, "goal", "walk_yaw_cmd",
                                  default=0.0)) == 1.0
    # Task-space turn-OFFSET curriculum (goal.walk_yaw_offset_set;
    # walk_task._sample_walk's yaw_offset block / walk_reward_yaw.
    # yaw_offset_kernel — the structurally-different, position-
    # tracking alternative to the closed rate-tracking walk_yaw_cmd
    # mechanism, see track STATUS.md 2026-09-25 ~13:5x design note).
    # A JSON list (`[15,30,45,90,-15,...]`) or comma-separated string
    # of DEGREES, parsed once here into radians; empty/absent (the
    # default) leaves env._yaw_offset_cmd False and every draw in
    # _sample_walk short-circuited — bit-exact legacy for every
    # existing lineage. New-lineage obs-width flag like walk_yaw_cmd
    # above (no warm start from a non-offset checkpoint without
    # --obs-pad-transplant).
    _yoff_raw = cfg_get(env.cfg, "goal", "walk_yaw_offset_set",
                         default="")
    if isinstance(_yoff_raw, (list, tuple)):
        _yoff_deg = [float(x) for x in _yoff_raw]
    elif isinstance(_yoff_raw, str) and _yoff_raw.strip():
        _yoff_deg = [float(x) for x in _yoff_raw.split(",")]
    else:
        _yoff_deg = []
    env._yaw_offset_set_rad = [math.radians(d) for d in _yoff_deg]
    env._yaw_offset_cmd = bool(env._yaw_offset_set_rad)
    # Explicit mode/command one-hot (obs.mode_onehot=1): +6 obs at
    # the frame TAIL (see module constants). New-lineage flag like
    # walk_yaw_cmd — the width change means no direct warm start
    # from a non-mode checkpoint (--obs-pad-transplant works).
    env._mode_obs = float(cfg_get(env.cfg, "obs", "mode_onehot",
                                   default=0.0)) == 1.0
    # Command-derived one-hot (obs.mode_onehot_cmd=1; the multitask
    # x arch transplant, 08-13). On the command-conditioned
    # generalist recipe every episode is mode "walk", so the
    # episode-constant one-hot above never routes the dual-core GRU
    # (gru_policy.DualGruActorCriticPolicy gates on the obs tail).
    # With this flag, walk-FAMILY ticks light the slot from the
    # LIVE blended command instead: a commanded stop (all of
    # |vx_ref|,|vy_ref| <= 0.005 m/s and |wz_ref| <= 0.02 rad/s)
    # lights "hold" (stance core), any
    # motion command lights "walk" (locomotion core). Non-walk
    # modes are untouched; no effect unless obs.mode_onehot=1.
    # Default OFF = bit-exact obs for every existing lineage.
    env._mode_cmd = float(cfg_get(env.cfg, "obs", "mode_onehot_cmd",
                                   default=0.0)) == 1.0
    # Pure-turn command-derived slot (obs.mode_onehot_turn_cmd=1;
    # 09-04, standwalk item-2 escalation, see MODE_ONEHOT_ORDER's
    # "turn" entry above). Independent of mode_onehot_cmd (may be
    # combined or used alone): on a walk-family tick, if the LIVE
    # command is a PURE turn (both |vx_ref| and |vy_ref| <= 1e-3 AND
    # |wz_ref| > 1e-3 — the EXACT same threshold sim_env.py's
    # ``_bc_pure_turn`` uses for the bc_anchor_walk_turn_skip /
    # bc_anchor_walk_combined_dose tick classification, so any
    # future architecture routed off this bit sees the identical
    # tick partition the BC-anchor levers already reason about),
    # light "turn" instead of "walk"; every other tick (combined,
    # straight-walk, non-walk families) is completely unaffected.
    # Default OFF = bit-exact obs for every existing lineage (no
    # effect unless obs.mode_onehot=1 too).
    env._mode_turn_cmd = float(cfg_get(
        env.cfg, "obs", "mode_onehot_turn_cmd", default=0.0)) == 1.0
    # Rise start-kind gate one-hot (obs.rise_start_kind_gate=1; standwalk
    # rise flat/bridge precision gap, 2026-09-24 ~21:3x). DISTINCT from
    # the already-closed `obs.rise_start_kind_sense` (removed 2026-09-24
    # ~19:1x): that fed the identical flat/bridge/crouch label as an
    # extra INPUT to one shared trunk and measurably changed nothing
    # (CANARY FAIL - MECHANISM, `startkind-canary2m`) -- the residual
    # was diagnosed as needing "a genuinely separate-WEIGHTS per-start-
    # kind mixture-of-experts rise head (distinct parameters per kind,
    # not a shared trunk fed a richer input)". This flag exists ONLY to
    # feed `gru_policy.RiseKindGruActorCriticPolicy`'s hard expert gate
    # (never mixed additively into a shared trunk's forward math) -- a
    # different mechanism SHAPE, not a re-dose of the closed one, so it
    # gets its own key rather than reviving the removed one. Requires
    # obs.mode_onehot=1 (appended immediately BEFORE the mode one-hot,
    # at the same fixed tail offset regardless of task-specific vel/
    # phase width upstream, so gru_policy's negative-index gate reads
    # stay reliable across every goal-task recipe — see module comment
    # on MODE_ONEHOT_ORDER for why that trailing slot is frozen).
    # Default OFF: 0 extra obs width, bit-exact for every existing
    # lineage.
    env._rise_kind_gate = float(cfg_get(
        env.cfg, "obs", "rise_start_kind_gate", default=0.0)) == 1.0
    # Recovery needs a task-stable pose frame.  q-q_nom is zero at
    # every reset because q_nom is the arbitrary settled bad pose, so
    # two very different tangles can otherwise begin with identical
    # joint-position observations.  Append q-q_plant at the frame tail
    # (recover ticks only); the pretrained dynamics adapter deliberately
    # consumes only the original first 59 proprio fields.
    env._recover_plant_q_obs = float(cfg_get(
        env.cfg, "obs", "recover_plant_q", default=0.0)) == 1.0
    # Fault-health obs (obs.fault_health=1; AMP brief sec8.2 M4
    # wiring — default OFF, bit-exact-when-off per every other obs
    # flag here). Appends EpisodeRandomization.fault_health() (18,
    # per-joint 1.0 healthy / 0.0 disabled-frozen / intermediate =
    # degraded strength) at the frame tail every tick, so the
    # policy can actually CONDITION ON a known joint fault instead
    # of only compensating blind (the faultsmoke1 pair's innate-
    # tolerance measurement). Same value all episode (fault draw is
    # per-reset, not per-tick) but recomputed every tick like
    # mode_onehot/wz_ref so it survives obs-history stacking and
    # pool-restore without a new SNAP_ATTRS entry — _ep_rand IS the
    # snapshotted state. All-ones (perfectly healthy) whenever
    # dr.fault_prob=0 or _ep_rand is unset (CPU C-path corner
    # before the first reset), so a fault-unaware DR-0 eval reads
    # as "everything healthy", the correct semantics.
    env._fault_obs = float(cfg_get(
        env.cfg, "obs", "fault_health", default=0.0)) == 1.0


def reset_reward_bookkeeping(env):
    # State the obs hook reads must be reset BEFORE _reset_finalize
    # builds the first observation. Done in the pre-physics reset
    # hook so both the C path (reset()) and the batched MJX vec env
    # (which drives _reset_begin directly) get it.
    env._foot_on = [True] * 6
    env._liftoff_xy = [None] * 6
    env._foot_prev_xy = [None] * 6
    env._foot_prev_force = [0.0] * 6
    env._foot_tan_slip_m = [0.0] * 6
    env._duty_hist = []
    env._dgate_hist = []
    env._swing_gate_hist = []
    env._anchor_xy = [None] * 6
    env._anchor_prev_on = [False] * 6
    env._step_disp_bank = 0.0
    env._ls_prev_xy = [None] * 6
    env._ls_prev_on = [False] * 6
    env._ls_slip_m = 0.0
    env._ls_prog_m = 0.0
    # Windowed (EMA) loaded-slip rate bookkeeping
    # (reward.walk_loadslip_window_s, default 0 = off, see the
    # walk_loadslip_gate block in step()). Separate from the
    # cumulative _ls_slip_m/_ls_prog_m above so the legacy
    # episode-cumulative ratio stays bit-exact when off.
    env._ls_slip_ema = 0.0
    env._ls_prog_ema = 0.0
    # Anti-park travel-floor EMA (reward.k_walk_idle_charge);
    # per-episode/per-segment, snapshot via MJX_SNAPSHOT_EXTRA.
    env._walk_idle_ema = 0.0
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
    env._walk_idle_low_s = 0.0
    env._walk_qvel_ema = 0.0
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
    env._walk_legduty_ema = [1.0] * 6
    env._walk_legduty_low_s = [0.0] * 6
    # Per-leg duty-RATIO reward-charge EMA (reward.walk_leg_duty_
    # ratio_charge, 2026-09-08); own state, independent of the
    # termination feature's _walk_legduty_ema above. Seeded at 1.0
    # for the same "begins loaded at the plant" reason. Tick
    # counter gates the charge off until the EMA has had a chance
    # to reflect real contact data (mirrors the window-must-fill
    # grace every other gate in this file uses).
    env._legduty_ratio_ema = [1.0] * 6
    env._legduty_ratio_ticks = 0
    env._legduty_ratio_swing_hist: list = []
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
    env._legslip_ratio_ema = [0.0] * 6
    env._legslip_ratio_ticks = 0
    # Per-leg swing-GAP reward-charge state (reward.walk_leg_
    # swing_gap_charge, 2026-09-08): seconds elapsed since each
    # leg's last qualifying swing event -- see the mechanism's
    # own comment block in step() for the full design rationale
    # (the "duration-since-last-swing PATTERN price" lead named
    # by the loadslip-ratio-charge closure). Seeded at 0.0 (a leg
    # is trivially "just swung" at the plant-start reset, mirroring
    # the loadslip EMA's own 0-seed rationale). Independent of
    # every other slip/duty mechanism's state above.
    env._swing_gap_s = [0.0] * 6
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
    env._liftoff_was_maxload = [False] * 6
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
    env._swinit_load_ema = [0.0] * 6
    # Seconds since the current commanded-stop segment began
    # (reward.walk_stop_grace_s); 0 whenever s_ref > 1e-3
    # (walking commanded), increments by dt each stop tick.
    # Used only to ramp the stop-speed charge in over the
    # unavoidable deceleration transient -- see the charge
    # site below. Same lifecycle as _walk_idle_ema.
    env._walk_stop_cmd_s = 0.0
    # Structural stop-hold timer (goal.walk_stop_freeze_s);
    # same lifecycle as _walk_stop_cmd_s -- see
    # sim_env._walk_stop_freeze_override.
    env._walk_stop_freeze_cmd_s = 0.0
    # Commanded-course EMA (reward.k_walk_course); same lifecycle.
    env._walk_course_ema = [0.0, 0.0]
    # Commanded-course NET-DISPLACEMENT ring buffer
    # (reward.k_walk_course_disp, the k_walk_course EMA-
    # cancellation fix-lever (b), 08-29 standwalk DIG-IN); lazily
    # (re)allocated in the reward step once the window size is
    # known, so a plain reset just drops any prior buffer.
    env._walk_course_disp_hist = None
    # Windowed course-following INCOME + excess-sway ring buffer
    # (reward.k_walk_course_income / reward.k_walk_excess_sway,
    # operator reward-design directive fb_20260829T142239_63c818):
    # deque of (x, y, cum_cmd_x, cum_cmd_y, cum_active_ticks) with
    # the running totals in _walk_course_win_cum; lazily
    # (re)allocated in the reward step once the window sizes are
    # known. Same lifecycle as _walk_course_disp_hist.
    env._walk_course_win_hist = None
    env._walk_course_win_cum = [0.0, 0.0, 0]
    # Stride-EMA velocity for the tracking kernel
    # (reward.walk_kernel_vel_ema); same lifecycle.
    env._walk_kernel_vema = [0.0, 0.0]
    # Stride-EMA yaw-rate for the yaw tracking kernel
    # (reward.walk_kernel_yaw_ema); same lifecycle.
    env._walk_kernel_wz_ema = 0.0
    env._stance_slip_acc = [0.0] * 6
    env._trans_td_count = [0] * 6
    env._trans_lo_buf = [[] for _ in range(6)]
    env._gait_last_step = [0] * 6
    env._gait_cmd_tick = 0
    env._gait_gate_qfactor = 1.0
    env._phase = 0.0
    env._yaw_still_ema = 0.0
    env._yaw_prog_ema = 0.0
    env._yaw_offset_achieved = 0.0
    env._vel_est = None
    if env._wc_on:
        # Bucket must be chosen BEFORE super() samples this
        # episode's DR (_ep_rand) so the bucket's dr scale applies
        # to the same episode. Off = zero rng draws, randomizer
        # untouched (bit-exact legacy).
        env._walkcurr_prepare_episode()
