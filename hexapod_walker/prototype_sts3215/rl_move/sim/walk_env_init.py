"""Construction-time state of SimHexapodJointWalkEnv (the __init__ blocks), moved out of SimHexapodJointWalkEnv.__init__.

Every function here is one contiguous block of the walk env constructor
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``__init__`` is a single call.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations


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
