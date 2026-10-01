# rl_only lower-role over_current: L1-hip JOINT-LIMIT vs LOAD root-cause (2026-10-01)

Scoped item: `lowerrole_overcurrent_systemid_2026-10-01/SUMMARY.md`'s own
named next step -- "is L1 hip being driven toward/against its JOINT
LIMIT during these hot windows (an architecture/bias artifact), or is
it fighting an asymmetric LOAD with room to move (a reward-pricing/
coordination artifact)? ... needs a per-tick qpos capture on L1 hip
during the hot window ... not yet built." Zero GPU spend for the
diagnosis (CPU MuJoCo eval only, same bus-fixed protocol/checkpoints/
seeds as every prior item in this chain); ends with a built+tested fix
and two training arms queued (GPU, not yet complete).

## Tool extension
`eval_lifecycle_handoff_rlonly.py`'s `lower_phase()` now also captures,
whenever `--current-trace-dir` is set (bit-exact no-op otherwise):
per-tick raw MuJoCo hinge `qpos` (the SAME coordinate `jnt_range`
bounds -- not the robot_abs logical convention) and per-tick per-leg
ground-contact (same `touch_N > 0.5` convention as
`sacrificed_legs()`/`eval_checkpoint.py`'s own gait-validity gate).
`trip_summary()` gained an optional `qpos_trace`/`joint_limit_rad` pair
(independent of the existing qvel/height pair) that reports, for
`final_joint` over the same trailing hot window: `hot_qpos_med_rad`,
the joint's own `(lo, hi)` range, `limit_margin_rad` (distance to the
NEARER bound) and `near_joint_limit` (margin < 0.05 rad ~= 2.9 deg).
9 new tests (`test_eval_lifecycle_handoff_rlonly.py`), all green; reran
the s1 (both seeds) + s0-seed0 arms of the exact n=18 protocol and
reproduced the stallclass item's own `lower_ok` counts bit-exactly
(s1_seed0 9/18, s1_seed100 7/18, s0_seed0 14/18) -- the new capture
changes nothing about episode outcomes.

## Finding 1 (decisive): EVERY L1-hip CORROBORATED_STALL is pinned past its own mechanical hinge limit, at a near-identical value -- an architecture/behavior artifact, not a load-fighting one
All 4/4 L1-hip CORROBORATED_STALL episodes (both s1 seeds) read
`near_joint_limit=True`, hip qpos **0.557 rad, 0.037 rad PAST the
0.52 rad upper hinge bound**, within 0.0004 rad of each other across
independent episodes/seeds -- not noise, a systematic saturation.
Every OTHER over_current episode this item re-captured with qpos
(24 RAIL_MOVING traces across s1's both seeds plus s0_seed0's own 3
over_current fails -- s0_seed100 not rerun, its stallclass-item
classification already reads 0/N CORROBORATED_STALL so it carries no
new question here) sits comfortably mid-range (margin >=0.52 rad,
`near_joint_limit=False`) -- including the one non-hip CORROBORATED_
STALL outlier (s1_seed100/direct_2, L2 knee, margin 0.73 rad). The
pinned-at-limit signature is EXCLUSIVE to the L1-hip corroborated-
stall class.

## Finding 2 (decisive): the pinned leg is airborne the ENTIRE episode -- a permanently sacrificed leg, not a transient stumble
Per-leg contact trace on the same 4 episodes: leg 1's foot never
touches the ground during the hot window (0/23-0/88 ticks, depending
on episode) AND its duty over the FULL 15s lower episode is
**0.019-0.06** -- below the 0.10 "permanently airborne" floor
`sacrificed_legs()` already uses elsewhere in this codebase to flag a
parked flag leg. The mechanism is: the lower-role policy permanently
lifts (sacrifices) one leg during the ENTIRE descent, commands its hip
toward full retraction, and that hip simply rails against its own
mechanical stop under sustained torque while the other 5 legs carry
the body -- the SAME family of pathology the joystick track's closed
`k_walk_move_current` lever already named ("locked-leg-tripod
exploit", pinned ~2.64A), here in the lower role instead of walk.

## Root cause located: an EXISTING, matched termination never fires during `lower` mode
The lower-role recipe's own cfg (`cfg_recipe_stance50hz_rlonly_
lowerrole_scratch_sac_drramp.py`, copied from the sibling stance/hold
recipe) ALREADY sets `safety.hold_min_load_terminate_{s,n,grace_s}` =
`1.0/0.3/1.0` -- the exact "per-foot min-load termination" mechanism
built 2026-08-25 under the op ruling "absorbing states beat prices;
must come WITH a termination, never instead of one" for this SAME
permanently-unloaded-foot pathology in HOLD mode. It never fires here
because `hold_minload_termination`'s mode gate only ever matched
`env._goal_traj.mode == "hold"`, and this recipe trains pure `lower`
(`--goal-mix hold=0.0,rise=0.0,lower=1.0`) -- the termination's own
state (`_hold_minload_ema`/`_hold_minload_low_s`) is already generic
(initialized for every joint_goal env, not walk/hold-specific), so the
gap is purely the mode string, not missing machinery.

## Fix built: `safety.hold_min_load_apply_lower` (new cfg key, default 0 = legacy bit-exact)
`balance_terminations.py`'s `hold_minload_termination` now also
matches `mode == "lower"` when this new flag is set, reusing the SAME
already-configured floor/grace values -- no new reward math, no new
state, a one-line mode-gate generalization of an already-validated
mechanism. Default off: no existing config sets this key (grepped),
so every prior checkpoint/eval is bit-exact-unaffected. 3 new tests
(`test_hold_minload_apply_lower.py`, mode_seq hand-plan harness
mirroring `test_mode_seq_grace_windows.py`'s own hold-switch test):
default-off never fires during a `lower` segment even with an
impossibly-strict floor; enabled, it fires during `lower` (respecting
its own grace window) and NOT during the preceding `rise` segment.
Full suite `ops.sh testdiff` clean (2 known_failures, unrelated) both
before and after this change.

## What this does and does not change
Does NOT itself raise `lower_ok` or alter any existing verdict --
no checkpoint has trained under this key yet. DOES close the open
"pinned-at-limit vs load-fighting" DIG-IN question decisively (pinned-
at-limit, specifically because of a permanently sacrificed leg) and
turns it into a concrete, narrowly-targeted, already-precedented fix
instead of a new reward-shaping guess. This is NOT a re-dose of the
CLOSED `k_torque_headroom`/`k_current_hot` levers (those price current
MAGNITUDE broadly, continuously, and both regressed training
outright); this reuses a discrete TERMINATION already proven to evict
an absorbing "permanently unloaded foot" state in the sibling hold
task, applied to a mode gap, not a new price.

## Next: two from-scratch retrains queued (GPU, GOAL 2/rl_only lower-role gap)
`cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-drramp-minloadlower-acq1`
(respec of the matched drramp-acq1 parent, `--cfg
safety.hold_min_load_apply_lower=1.0`, same 8M-step/dr=0.2/SAC budget,
NOT warm-started -- the termination changes the absorbing-state
landscape from step 0, so a from-scratch run answers "does training
WITH this boundary present prevent the leg-park habit from forming at
all", the strongest form of the test). Gate: composed direct-arm
`lower_ok` (same n=18x2-seed `eval_lifecycle_handoff_rlonly.py`
protocol) should improve over the matched parent's own 24/36 (s0) /
16/36 (s1), AND the resulting over_current traces' CORROBORATED_STALL
count (via this item's own `stall_classification`) should drop versus
the parent's 5/37 (ideally 0 on L1 hip), without `hold_min_load`
becoming a chronic new failure mode on otherwise-fine episodes
(eyeball strips/video, not just the count). FAIL if `lower_ok` doesn't
improve and/or CORROBORATED_STALL doesn't drop, or if `hold_min_load`
over-triggers on legitimate gait variance -- would mean the hold
recipe's floor/grace values don't transfer to the lower task's own
dynamics and a lower-specific retune (not a new mechanism) is the next
lever.

Evidence: `current_trace_{s0,s1}_seed{0,100}/*.json` (qpos_trace_rad/
contact_trace/joint_limit_rad fields), `s{0,1}_seed{0,100}.log`.
