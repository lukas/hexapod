"""Walk command-curriculum tables (moved verbatim from walk_task.py 2026-08-29).

Nine generations of certification-gated command-curriculum buckets
(WALKCURR_BUCKETS .. _V9), their promotion gates, the LP speed buckets
and the frontier sampling mixture. Pure constants — no imports, no env
code. The selection/promotion machinery that CONSUMES these tables
(walkcurr_update_admission, apply_walkcurr_certification, the _wc_table
version dispatch) stays in walk_task.py; certification helpers live in
walkcurr_cert.py. Ledger/doc references to "walk_task.WALKCURR_*" refer
to these tables; walk_task re-imports them so both names stay live.
"""
import math

# Learning-progress curriculum (goal.walk_lp_curriculum=1): commanded
# speed is drawn from one of these buckets instead of a single global
# uniform range. Bucket weights start uniform and are re-weighted during
# training by the LP callback in train_ppo_sim (sample where tracking is
# IMPROVING, not where it is solved or currently impossible — the manual
# global widenings to 0.07/0.08 both regressed). Default off = legacy.
LP_BUCKETS = ((0.02, 0.03), (0.03, 0.04), (0.04, 0.05), (0.05, 0.06),
              (0.06, 0.07), (0.07, 0.08), (0.08, 0.10), (0.10, 0.12))
# Adaptive competence+retention walk-command curriculum
# (goal.walk_curriculum=1; operator order 2026-08-18, run
# cw-dynrep-criticD-walkcurr1). Replaces the FIXED broad command
# sampling with a certification-gated frontier ladder: episodes draw a
# BUCKET (50% frontier / 25% weakest mastered / 15% uniform mastered /
# 10% the rung just prior to the frontier), never a locked future
# bucket, and never promote on time — only on a deterministic held-out
# certification pass of the frontier AND every retained bucket
# (apply_walkcurr_certification / walkcurr_update_admission, driven by
# the trainer exactly like the recover-mode ladder). Default 0 = off,
# bit-exact legacy: no rng draws, no randomizer swap, no cfg reads
# beyond __init__.
#   fields: s_lo/s_hi commanded speed band (m/s); head_lo/head_hi
#   heading magnitude band (rad, sign drawn ±; 0/0 = pure forward);
#   resample_s mid-episode command resampling period (0 = one command
#   held the whole episode = "long holds"); jitter/stop_frac/blend as
#   the legacy goal.walk_cmd_* keys; dr = this bucket's DR scale (the
#   env swaps its DomainRandomizer per episode); stop_gate = cert-time
#   max mean measured speed (m/s) during commanded-stop ticks (None =
#   bucket has no stop segments to gate).
WALKCURR_BUCKETS = (
    # B0 slow forward, long holds, DR0
    dict(name="fwd_slow", s_lo=0.04, s_hi=0.05, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None),
    # B1 forward speed band widens
    dict(name="fwd_band", s_lo=0.03, s_hi=0.06, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None),
    # B2-B4 heading cones open ±15/±30/±45 deg
    dict(name="head15", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(15.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None),
    dict(name="head30", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(30.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None),
    dict(name="head45", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None),
    # B5 blended front-cone transitions (no stops yet)
    dict(name="front_blend", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=6.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None),
    # B6 the joystick mix: 4s segments + jitter + stop/restart
    dict(name="stop_restart", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=0.015),
    # B7/B8 same commands under DR 0.1 then 0.3
    dict(name="dr01", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.1,
         stop_gate=0.015),
    dict(name="dr03", s_lo=0.03, s_hi=0.06, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.3,
         stop_gate=0.015),
    # B9/B10 lateral then rear/reverse — locked until every earlier
    # rung certifies AND retains (operator: "lateral/rear/reverse only
    # after retained passes").
    dict(name="lateral", s_lo=0.03, s_hi=0.06,
         head_lo=math.radians(45.0), head_hi=math.radians(90.0),
         resample_s=4.0, jitter=0.5, stop_frac=0.15, blend_lo=1.0,
         blend_hi=1.0, dr=0.3, stop_gate=0.015),
    dict(name="rear", s_lo=0.03, s_hi=0.06,
         head_lo=math.radians(90.0), head_hi=math.pi,
         resample_s=4.0, jitter=0.5, stop_frac=0.15, blend_lo=1.0,
         blend_hi=1.0, dr=0.3, stop_gate=0.015),
)

# WALKCURR_BUCKETS_V2 (walkcurr2, operator MCP note fb_20260818T060044,
# "figure out how to make a great run and then launch it"): corrects
# two root causes the matched walkcurr1-vs-40m1 data exposed in V1's
# B0/B1 (see cw-dynrep-criticD-40m1 triage + walkcurr1 in-flight reads).
#
# Root cause 1: V1's B0 command band (0.04-0.05 m/s, dead ahead) sits
# ENTIRELY inside SIGMA_V=0.05 (walk_task's velocity-tracking kernel
# width) of a PARKED (zero-output) robot — standing still nets
# exp(-(0.045/0.05)^2/2) = ~67% of peak reward, so PPO has little
# incentive to ever start walking before B0 can certify. V2's B0
# ("ignition") instead commands 0.08-0.12 m/s with a small heading
# spread from the very first bucket (a parked policy is now 1.6-2.4
# sigma off target, i.e. <15% of peak reward) — command diversity from
# step 0, not deferred to later rungs.
#
# Root cause 2: V1's gate (WALKCURR_GATE, train_ppo_transfer.py)
# applies slew_sat<=0.5 as a hard admission check on every bucket. The
# best real evidence of what a good policy at this budget looks like —
# cw-dynrep-criticD-40m1's retained 6M-best checkpoint, matched task,
# matched budget-ish, matched everything but curriculum — runs
# slew_sat~0.925, i.e. it would FAIL V1's own admission gate outright.
# A hard bar the best known-good policy cannot clear is not a quality
# floor, it is a wall between "parked" (low slew) and "walking" (high
# slew, because directional command changes cost joint-speed). V2
# raises slew_sat_max to 0.95 (WALKCURR_GATE_V2_*, monitored/
# selection-relevant like every other quality metric here, not
# vetoing) and otherwise keeps V1's floors (progress/slip/roll) intact
# — tightened, if anything, on later buckets via the per-bucket "gate"
# key (walkcurr_bucket_pass reads spec["gate"] when present).
#
# Buckets B2+ reuse V1's heading/resample/DR ladder verbatim (proven
# shape, not the thing that broke); only B0/B1 (ignition speed +
# immediate heading spread) and the gate calibration change.
WALKCURR_GATE_V2_IGNITION = dict(
    cmd_prog_frac_min=0.65, slip_per_m_max=2.5, peak_roll_deg_max=8.0,
    slew_sat_max=0.95, cross_track_frac_max=0.30,
    contact_sw_per_s_min=3.0, foot_sw_min_per_s_min=0.5)
WALKCURR_GATE_V2_QUALITY = dict(
    cmd_prog_frac_min=0.75, slip_per_m_max=2.0, peak_roll_deg_max=6.0,
    slew_sat_max=0.95, cross_track_frac_max=0.30,
    contact_sw_per_s_min=3.0, foot_sw_min_per_s_min=0.5)
WALKCURR_BUCKETS_V2 = (
    # B0 ignition: real speed + heading spread from step 0 (root cause 1)
    dict(name="ignition", s_lo=0.08, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(15.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_IGNITION),
    # B1 speed band widens toward the legacy range, heading unchanged
    dict(name="quality_band", s_lo=0.06, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(15.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_QUALITY),
    dict(name="full_band_head15", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(15.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_QUALITY),
    dict(name="head30", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(30.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_QUALITY),
    dict(name="head45", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_QUALITY),
    # B5 blended front-cone transitions (no stops yet)
    dict(name="front_blend", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=6.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V2_QUALITY),
    # B6 the joystick mix: 4s segments + jitter + stop/restart
    dict(name="stop_restart", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V2_QUALITY),
    # B7/B8 same commands under DR 0.1 then 0.3
    dict(name="dr01", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.1,
         stop_gate=0.015, gate=WALKCURR_GATE_V2_QUALITY),
    dict(name="dr03", s_lo=0.03, s_hi=0.12, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=1.0, blend_hi=1.0, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V2_QUALITY),
    # B9/B10 lateral then rear/reverse — locked until every earlier
    # rung certifies AND retains
    dict(name="lateral", s_lo=0.03, s_hi=0.12,
         head_lo=math.radians(45.0), head_hi=math.radians(90.0),
         resample_s=4.0, jitter=0.5, stop_frac=0.15, blend_lo=1.0,
         blend_hi=1.0, dr=0.3, stop_gate=0.015,
         gate=WALKCURR_GATE_V2_QUALITY),
    dict(name="rear", s_lo=0.03, s_hi=0.12,
         head_lo=math.radians(90.0), head_hi=math.pi,
         resample_s=4.0, jitter=0.5, stop_frac=0.15, blend_lo=1.0,
         blend_hi=1.0, dr=0.3, stop_gate=0.015,
         gate=WALKCURR_GATE_V2_QUALITY),
)
# WALKCURR_BUCKETS_V3 ("bridge" ladder, operator order
# fb_20260818T102844_116d4c, walkcurr4 evidence-based correction):
# ignition must be ADJACENT TO THE TRANSPLANTED SOURCE SKILL, not to a
# park-proof speed band. The gaitinit canaries showed the two failure
# directions of V2's ignition on an actor-init recipe: a scratch actor
# reaches cmd_prog 0.74 but crouches/falls (canB-r1 at 2.1M), while the
# proven tall-walk actor keeps posture/safety but LOSES commanded
# travel chasing V2's 0.08-0.12 m/s band it never walked at
# (gaitinit-bcinit final cert: cmd_prog_frac 0.0575, height_factor
# 0.5847). V3's first two rungs are a SHORT BRIDGE at the source
# checkpoint's own operating point (ppo_goal_cw_dep_bcgait1_hard1
# walks ~0.05 m/s straight, height -12.7mm, slip 1.3, zero falls):
# B0 = straight forward 0.05-0.06 m/s, NO heading jitter / resampling /
# stops, DR0; B1 widens speed to 0.05-0.10 still dead straight; every
# later rung is V2's own direction/heading/stop/DR ladder verbatim, so
# the eventual multi-direction joystick goal is preserved. NOTE
# V3 B0 deliberately sits near the SIGMA_V park zone V2 removed — that
# is safe ONLY on an actor-init recipe whose init already walks
# (pre-PPO deterministic cert required: --walkcurr-cert-at-init), and
# is why V3 is not a scratch-acquisition ladder.
WALKCURR_GATE_V3_BRIDGE = dict(
    cmd_prog_frac_min=0.60, slip_per_m_max=2.0, peak_roll_deg_max=8.0,
    slew_sat_max=0.95, cross_track_frac_max=0.30,
    contact_sw_per_s_min=3.0, foot_sw_min_per_s_min=0.5)
WALKCURR_BUCKETS_V3 = (
    # B0 bridge: the source gait's own command, held all episode, DR0
    dict(name="bridge_fwd", s_lo=0.05, s_hi=0.06, head_lo=0.0,
         head_hi=0.0, resample_s=0.0, jitter=0.0, stop_frac=0.0,
         blend_lo=1.0, blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V3_BRIDGE),
    # B1 bridge: speed band widens upward, still dead straight
    dict(name="bridge_band", s_lo=0.05, s_hi=0.10, head_lo=0.0,
         head_hi=0.0, resample_s=0.0, jitter=0.0, stop_frac=0.0,
         blend_lo=1.0, blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V3_BRIDGE),
) + WALKCURR_BUCKETS_V2[2:]   # V2 direction/heading/stop/DR ladder

# WALKCURR_BUCKETS_V4: sustained joystick curriculum. V3 spends its
# first five rungs on one fixed command per 10-second episode, even
# though the observed deployment failure is falling only after several
# direction changes. V4 keeps one short source-skill bridge, introduces
# command changes immediately at B1, then holds the command distribution
# fixed while extending continuous survival to 20/40/60 seconds. Only
# after the 60-second joystick task is retained does it widen speed, add
# DR, and open lateral/rear travel. ``duration_s`` controls both training
# episode truncation and the deterministic certification horizon;
# ``min_command_changes`` is a fail-closed check that a cert actually
# exercised the intended joystick transitions.
WALKCURR_GATE_V4_BRIDGE = dict(
    cmd_prog_frac_min=0.60, cmd_prog_frac_p10_min=0.50,
    slip_per_m_max=2.0, peak_roll_deg_max=8.0, slew_sat_max=0.95,
    cross_track_frac_max=0.30, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)
WALKCURR_GATE_V4_JOYSTICK = dict(
    cmd_prog_frac_min=0.65, cmd_prog_frac_p10_min=0.50,
    slip_per_m_max=2.0, peak_roll_deg_max=8.0, slew_sat_max=0.95,
    cross_track_frac_max=0.30, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)

WALKCURR_BUCKETS_V4 = (
    # B0: prove the imported gait survives at its own operating point.
    dict(name="bridge_10s", duration_s=10.0, min_command_changes=0,
         s_lo=0.05, s_hi=0.06, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V4_BRIDGE),
    # B1-B4: joystick changes happen immediately, then only duration grows.
    dict(name="joystick_10s", duration_s=10.0, min_command_changes=2,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    dict(name="joystick_20s", duration_s=20.0, min_command_changes=4,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    dict(name="joystick_40s", duration_s=40.0, min_command_changes=10,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    dict(name="joystick_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    # B5: widen speed and make joystick timing less predictable.
    dict(name="full_band_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.03, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    # B6/B7: retain the full 60-second joystick task under DR.
    dict(name="dr01_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.03, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.1,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    dict(name="dr03_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.03, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    # B8/B9: lateral and rear commands remain locked behind retained
    # 60-second front-cone competence under DR0.3.
    dict(name="lateral_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.03, s_hi=0.10, head_lo=math.radians(45.0),
         head_hi=math.radians(90.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
    dict(name="rear_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.03, s_hi=0.10, head_lo=math.radians(90.0),
         head_hi=math.pi, resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V4_JOYSTICK),
)

# WALKCURR_BUCKETS_V5 ("fast anti-skate" ladder, operator order
# fb_20260820T075230_4a90c6, recreated on the controller because the
# desktop commit 2cb2a7b7 could not be pushed): the fast-gait
# profile-headroom fork (steer6-fasttrack1 full-dose, steer7-middose1
# half-dose) FAILED on skating/slip and non-monotone speed control —
# both kept a single weakly-scaling cadence and paid slip 1.6-5.1/m.
# V5 is a fast-profile ladder ADJACENT to the proven tall-walk source
# (ppo_goal_cw_dep_bcgait1_hard1, walks ~0.05-0.06 m/s straight):
# B0 is a strict 10s bridge at the source's own operating point, B1/B2
# push the commanded band up to 0.08-0.10 / 0.06-0.10 with a small
# heading cone, B3-B5 are the V4-style joystick task (3s resamples,
# jitter, stops, partial blends) at 20/40/60 s, and only after the
# 60-second fast joystick task retains do B6/B7 add DR 0.1/0.3 and
# B8/B9 open lateral/rear. Gates are deliberately STRICT on
# direction/slip/height (the exact axes both steer forks failed):
# fast rungs demand cmd_prog>=0.70 (p10>=0.55), slip_per_m<=1.6,
# cross_track<=0.20, peak_roll<=8 deg, height_factor>=0.80 plus the
# usual all-feet contact/switch minima; the B0 bridge is slightly
# softer (cmd_prog>=0.65, p10>=0.50, slip<=1.8, cross_track<=0.22)
# so the warm start can certify at its own operating point before the
# band moves. V5 pairs with reward.k_loadslip_excess (direct loaded-
# slip charge, below) so skating is punished in training, not merely
# complained about at cert time.
# 2026-08-20 ~08:5x UTC alignment (q_20260820T0830Z review): the
# desktop branch (origin/codex/recover-retention @ 2cb2a7b7) is now
# fetchable. Diffed verbatim against the controller reconstruction
# above/below: the B0 bridge_10s bucket + WALKCURR_GATE_V5_BRIDGE the
# canaries actually exercised are BIT-IDENTICAL (confirming the
# fastnoslip1/midnoslip1 precert FAILs are genuine, not a
# reconstruction artifact) — but slew_sat_max was 0.95 here vs the
# authored 0.98, and B6-B9's min_command_changes/resample_s/jitter/
# stop_frac/blend/s_lo/head_hi diverged from the authored ladder.
# Realigned to the exact authored values below (never exercised by
# either canary — both died at B0 — so no in-flight run is affected).
WALKCURR_GATE_V5_BRIDGE = dict(
    cmd_prog_frac_min=0.65, cmd_prog_frac_p10_min=0.50,
    slip_per_m_max=1.8, peak_roll_deg_max=8.0, slew_sat_max=0.98,
    cross_track_frac_max=0.22, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)
WALKCURR_GATE_V5_FAST = dict(
    cmd_prog_frac_min=0.70, cmd_prog_frac_p10_min=0.55,
    slip_per_m_max=1.6, peak_roll_deg_max=8.0, slew_sat_max=0.98,
    cross_track_frac_max=0.20, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)

WALKCURR_BUCKETS_V5 = (
    # B0: prove the imported gait survives at its own operating point.
    dict(name="bridge_10s", duration_s=10.0, min_command_changes=0,
         s_lo=0.05, s_hi=0.06, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V5_BRIDGE),
    # B1/B2: the fast band opens — straight first, then a small cone.
    dict(name="fast_08_10_10s", duration_s=10.0, min_command_changes=0,
         s_lo=0.08, s_hi=0.10, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V5_FAST),
    dict(name="fast_06_10_head15", duration_s=20.0, min_command_changes=0,
         s_lo=0.06, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(15.0), resample_s=0.0, jitter=0.0,
         stop_frac=0.0, blend_lo=1.0, blend_hi=1.0, dr=0.0,
         stop_gate=None, gate=WALKCURR_GATE_V5_FAST),
    # B3-B5: fast joystick task, duration grows 20/40/60 s.
    dict(name="fast_joystick_20s", duration_s=20.0, min_command_changes=4,
         s_lo=0.06, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(30.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    dict(name="fast_joystick_40s", duration_s=40.0, min_command_changes=10,
         s_lo=0.06, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(30.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    dict(name="fast_joystick_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.06, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(30.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    # B6/B7: retain the 60-second fast joystick task under DR, the
    # heading cone opening to ±45 and the band widening down to 0.04.
    dict(name="fast_dr01_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.05, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.1,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    dict(name="fast_dr03_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.05, s_hi=0.10, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    # B8/B9: lateral and rear stay locked behind retained front-cone
    # competence under DR0.3.
    dict(name="lateral_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.04, s_hi=0.10, head_lo=math.radians(45.0),
         head_hi=math.radians(90.0), resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
    dict(name="rear_60s", duration_s=60.0, min_command_changes=9,
         s_lo=0.04, s_hi=0.10, head_lo=math.radians(90.0),
         head_hi=math.pi, resample_s=4.0, jitter=0.5,
         stop_frac=0.15, blend_lo=0.25, blend_hi=0.75, dr=0.3,
         stop_gate=0.015, gate=WALKCURR_GATE_V5_FAST),
)

# WALKCURR_BUCKETS_V6 ("hist16 full-circle joystick" ladder, operator
# order fb_20260823T220651_5c66e3): teach the hist16-dep1/c1 learned
# gait (16-frame deployment-contract walker, front-cone joystick only,
# heading_max 45 deg in training) to follow joystick commands in EVERY
# direction. Structure mirrors V4/V5: B0 is a strict 10-second bridge
# at the source checkpoint's own operating point
# (ppo_goal_cw_arch_hist16_dep1_c1 walks 0.05-0.06 m/s, front cone,
# DR0.5-trained), then the heading envelope opens in bands — front
# cone +-45 (20/60 s), side band 45-90 (20/60 s), rear bands 90-135
# (40 s) and 135-180 (60 s) — before B6 draws uniformly over the FULL
# CIRCLE for 60 s and B7/B8 retain the full-circle task under DR 0.2
# then DR 0.5 (the lineage's own training DR). One command
# distribution (3 s resamples, jitter, stops, partial blends) is held
# fixed across every joystick rung; only heading band, sustained
# horizon, and DR move. Gates are the V4 joystick bars (slip<=2.0 —
# inside the joystick-track slip band <=2.9 — cmd_prog>=0.65,
# all-feet cycling minima), bridge slightly softer, so promotion
# demands real command following in the newly opened band, not just
# survival.
WALKCURR_GATE_V6_BRIDGE = dict(
    cmd_prog_frac_min=0.60, cmd_prog_frac_p10_min=0.50,
    slip_per_m_max=2.0, peak_roll_deg_max=8.0, slew_sat_max=0.95,
    cross_track_frac_max=0.30, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)
WALKCURR_GATE_V6_JOYSTICK = dict(
    cmd_prog_frac_min=0.65, cmd_prog_frac_p10_min=0.50,
    slip_per_m_max=2.0, peak_roll_deg_max=8.0, slew_sat_max=0.95,
    cross_track_frac_max=0.30, contact_sw_per_s_min=3.0,
    foot_sw_min_per_s_min=0.5, height_factor_min=0.80)

WALKCURR_BUCKETS_V6 = (
    # B0: prove the transplanted hist16 gait survives at its own
    # operating point (0.05-0.06 m/s straight, DR0) before anything
    # moves.
    dict(name="bridge_10s", duration_s=10.0, min_command_changes=0,
         s_lo=0.05, s_hi=0.06, head_lo=0.0, head_hi=0.0,
         resample_s=0.0, jitter=0.0, stop_frac=0.0, blend_lo=1.0,
         blend_hi=1.0, dr=0.0, stop_gate=None,
         gate=WALKCURR_GATE_V6_BRIDGE),
    # B1/B2: the front cone the lineage already knows (+-45 deg),
    # joystick churn immediately, horizon 20 then 60 s.
    dict(name="front45_20s", duration_s=20.0, min_command_changes=4,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V6_JOYSTICK),
    dict(name="front45_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.radians(45.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V6_JOYSTICK),
    # B3/B4: the side band opens (45-90 deg), 20 then 60 s.
    dict(name="side90_20s", duration_s=20.0, min_command_changes=4,
         s_lo=0.04, s_hi=0.08, head_lo=math.radians(45.0),
         head_hi=math.radians(90.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V6_JOYSTICK),
    dict(name="side90_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.04, s_hi=0.08,
         head_lo=math.radians(45.0), head_hi=math.radians(90.0),
         resample_s=3.0, jitter=0.2, stop_frac=0.10, blend_lo=0.5,
         blend_hi=0.9, dr=0.0, stop_gate=0.015,
         gate=WALKCURR_GATE_V6_JOYSTICK),
    # B5/B6: rear bands 90-135 (40 s) then 135-180 (60 s).
    dict(name="rear135_40s", duration_s=40.0, min_command_changes=10,
         s_lo=0.04, s_hi=0.08, head_lo=math.radians(90.0),
         head_hi=math.radians(135.0), resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V6_JOYSTICK),
    dict(name="rear180_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.04, s_hi=0.08, head_lo=math.radians(135.0),
         head_hi=math.pi, resample_s=3.0, jitter=0.2,
         stop_frac=0.10, blend_lo=0.5, blend_hi=0.9, dr=0.0,
         stop_gate=0.015, gate=WALKCURR_GATE_V6_JOYSTICK),
    # B7: the goal task — uniform full-circle joystick, 60 s.
    dict(name="fullcircle_60s", duration_s=60.0, min_command_changes=15,
         s_lo=0.04, s_hi=0.08, head_lo=0.0, head_hi=math.pi,
         resample_s=3.0, jitter=0.2, stop_frac=0.10, blend_lo=0.5,
         blend_hi=0.9, dr=0.0, stop_gate=0.015,
         gate=WALKCURR_GATE_V6_JOYSTICK),
    # B8/B9: retain the full-circle task under DR 0.2 then the
    # lineage's own training DR 0.5.
    dict(name="fullcircle_dr02_60s", duration_s=60.0,
         min_command_changes=15, s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.pi, resample_s=3.0, jitter=0.2, stop_frac=0.10,
         blend_lo=0.5, blend_hi=0.9, dr=0.2, stop_gate=0.015,
         gate=WALKCURR_GATE_V6_JOYSTICK),
    dict(name="fullcircle_dr05_60s", duration_s=60.0,
         min_command_changes=15, s_lo=0.04, s_hi=0.08, head_lo=0.0,
         head_hi=math.pi, resample_s=3.0, jitter=0.2, stop_frac=0.10,
         blend_lo=0.5, blend_hi=0.9, dr=0.5, stop_gate=0.015,
         gate=WALKCURR_GATE_V6_JOYSTICK),
)

# WALKCURR_BUCKETS_V7 ("stress-diet" ladder, 08-24 assume-and-go
# repair): same heading/duration/DR/gate ladder as V6 (the certfreeze
# dig-in's own pre-registered if-false branch — "the damage is the
# b2+ practice diet itself... next lever is mixing stress_mix
# commands into bucket training, not freeze mechanics" — B2-B9's
# held-out joygate falls (over_current, 1/48 parent -> 6-7/48 across
# 3 independent freeze/no-freeze arms) never moved with the freeze
# mechanism, so the fix targets the DIET, not the supervisor). V6's
# own command sampler never draws an in-place turn (wz) or a full
# reversal — the held-out joygate's stress_mix family (flip_180,
# sweep_circle, square, jitter) does both every episode. V7 adds
# per-bucket `wz_max`/`wz_zero_frac` (in-place turning, same
# semantics as goal.walk_yaw_max_rad_s/walk_yaw_zero_frac) and
# `reversal_frac` (probability a resampled segment is a full
# instantaneous reversal, the bucket-diet analogue of flip_180) from
# front45_20s onward; the bridge rung (B0, proving the transplanted
# gait survives at all) stays untouched at 0/1.0/0.0. `_sample_walk_
# curr` reads these with `.get(..., 0.0)` defaults, so V1-V6 tables
# (missing the keys) are bit-exact unchanged.
WALKCURR_BUCKETS_V7 = tuple(
    (dict(b, wz_max=0.0, wz_zero_frac=1.0, reversal_frac=0.0)
     if b["name"] == "bridge_10s" else
     dict(b, wz_max=0.3, wz_zero_frac=0.5, reversal_frac=0.15))
    for b in WALKCURR_BUCKETS_V6
)

# WALKCURR_BUCKETS_V8 (08-24 scope-fix respec of V7, cw-arch-hist16-
# dep1-c1-joyfullcurr13-certfreeze-v7 FAIL): V7's own banner names the
# damage source as "the b2+ [heading-]widening practice diet", but its
# implementation applied the new wz-turn/reversal diet "from
# front45_20s onward" — i.e. INCLUDING front45_20s/front45_60s, which
# are still front-cone (not widened-heading) rungs and were the
# already-clean, already-certifying B1 in V6. Training-side audit of
# the certfreeze-v7 run confirms the resulting defect precisely: with
# the diet also baked into front45_20s, walkcurr/frontier never left
# bucket 1 for the ENTIRE 40M-step run (pre_b1_pass stuck False every
# cert round after round 1; b1's own stop_speed_m_s sits at
# 0.020-0.033 vs the 0.015 stop_gate for all 80 cert rounds — a full
# reversal inside the SAME 20s bucket that must also settle to a stop
# leaves residual momentum the window can't absorb) — the wide-heading
# buckets (side90+) the diet was actually meant to harden never trained
# at all, and reward fell across training (694->641->525->438 by
# quarter) instead of rising. V8 is the scope fix: identical to V7
# except the stress-diet extras start at side90_20s (the first
# heading-WIDENED rung) instead of front45_20s, so bridge_10s AND both
# front45 rungs stay byte-identical to V6 (clean cert path preserved)
# while every side/rear/full-circle rung still gets the full wz-turn +
# reversal diet V7 intended. `.get(..., 0.0)` defaults keep V1-V7
# unaffected.
_V8_CLEAN_NAMES = frozenset(("bridge_10s", "front45_20s", "front45_60s"))
WALKCURR_BUCKETS_V8 = tuple(
    (dict(b, wz_max=0.0, wz_zero_frac=1.0, reversal_frac=0.0)
     if b["name"] in _V8_CLEAN_NAMES else
     dict(b, wz_max=0.3, wz_zero_frac=0.5, reversal_frac=0.15))
    for b in WALKCURR_BUCKETS_V6
)

# WALKCURR_BUCKETS_V9 (08-24, certfreeze-v8 dig-in — cert-metric fix,
# NOT another bucket-scope respec): certfreeze-v8 confirmed the V8
# scope fix works (frontier leaves b1, reaches b3/side90) but then
# plateaus AT b3 for the rest of the run with the identical stuck-
# stop-cert signature v7 showed at b1 — root-caused to a semantics
# mismatch, not a bucket-placement or policy-quality gap: the
# cert-time hold supervisor (_walk_stop_freeze_override) exempts any
# tick with wz_ref != 0, but a wz-diet bucket's stop_frac and
# wz_zero_frac draws are independent rng calls on the SAME resampled
# segment, so ~half of its nominal "stop" segments also carry wz != 0
# and are exempt from the very freeze meant to clear the bar, while
# the legacy stop_speed_m_s counts every such tick anyway — the
# freeze/cert-off average is bracketed almost exactly by b1's known
# frozen (0.0133) / unfrozen (0.0326) numbers. V9 is byte-identical to
# V8 (same wz_max/wz_zero_frac/reversal_frac diet, same scope) except
# every bucket also carries `stop_metric="stop_speed_pure_m_s"`, the
# purely-additive metric (walk_task._walk_probe_tick) that excludes
# ticks where |wz_ref| exceeds the SAME 1e-3 threshold the freeze
# uses — bit-exact equal to stop_speed_m_s for any bucket that never
# commands wz during a stop (bridge_10s, front45_20s/60s, and every
# V1-V8 table with no wz key at all), differing only where a stop
# segment can also carry a turn. `walkcurr_cert.walkcurr_bucket_pass`
# reads `spec.get("stop_metric", "stop_speed_m_s")`, so omitting the
# key (every pre-V9 table) is bit-exact unchanged.
WALKCURR_BUCKETS_V9 = tuple(
    dict(b, stop_metric="stop_speed_pure_m_s")
    if b.get("stop_gate") is not None else b
    for b in WALKCURR_BUCKETS_V8
)

# Sampling mixture over unlocked buckets (operator spec): 50% frontier,
# 25% weakest mastered, 15% uniform over mastered, 10% the rung just
# prior to the frontier. Empty components fold back to the frontier.
WALKCURR_MIX = dict(frontier=0.50, weakest=0.25, uniform=0.15,
                    prior=0.10)
