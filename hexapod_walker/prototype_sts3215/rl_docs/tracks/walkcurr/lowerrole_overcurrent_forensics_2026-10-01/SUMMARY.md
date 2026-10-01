# rl_only lower-role over_current FORENSICS (2026-10-01)

Scoped item: walkcurr/STATUS.md Next(1) -- "which joints trip, at what
point in the lower trajectory, from which walk-exit poses" for the
drramp composed-gate (rise->walk->lower) over_current failures.
Zero GPU spend (CPU MuJoCo eval only). Tool: `eval_lifecycle_handoff_
rlonly.py --current-trace-dir <dir>` (new flag, default off, this
cycle) + the new pure `trip_summary()`/`joint_label()` helpers
(mechanics-tested, `test_eval_lifecycle_handoff_rlonly.py`).

**Read this doc's `WRONG_BUS_PROFILE_pre_fix/` subfolder ONLY as a
cautionary artifact of a bug this cycle found and fixed -- its
numbers/conclusions are superseded by everything below.**

## Bug found+fixed en route: stance/lower envs silently ran under the
WRONG (post-09-27) actuator bus profile
First pass through this forensics item reproduced a clean story (one
joint, late-stage only) but the raw distances/pass-rates didn't match
the one historical comparable file on disk
(`logs/ckpt_eval/lifecycle_rlonly_lower_sac_s0_drramp_diagbaseline_
n12.json`, s0, same checkpoints/seed/protocol) despite THIS session
being perfectly deterministic run-to-run. Root cause: the operator's
2026-09-26 evening commit `f77d8e987` moved `config.yaml`'s
`bus.write_speed`/`write_acc` default from 400/20 (what every
checkpoint through 09-26 trained under) to 2000/80 (the robot's
scripted-gait contract since 09-01), and added `trained_profile.
pin_trained_bus_profile` to auto-restore the old value from each
checkpoint's `.training_complete.json` sidecar. Neither
`probe_currentcap29_flatonly.BASE_CFG_ARGS` (stance role) nor
`cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp.CFG_ARGS`
(lower role) pin `bus.write_speed`/`write_acc` explicitly, and NEITHER
checkpoint has a sidecar for the auto-pin to recover from (both
predate the sidecar feature) -- so `eval_lifecycle_handoff_rlonly.py`
was silently building both envs under today's 2000/80 default instead
of the 400/20 contract these checkpoints actually trained with. FIXED
this cycle: both recipe modules now pin `bus.write_speed=400`/
`write_acc=20` explicitly (same remediation already applied 2026-09-30
to `test_real_failed_checkpoint_ema_inert_disp_active` for an
analogous pre-09-27 checkpoint), with tests asserting the pin. The
WALK role (`slew_smooth_s0`) was never affected -- it already pins its
own `bus.write_speed=4096`/`write_acc=1000` explicitly.
This means ANY other eval of these two specific checkpoint families
run between 2026-09-27 and this fix (not just this tool) may also have
silently replayed them under the wrong bus contract; not audited
beyond this tool's own usage.

## Corrected protocol (held fixed across all 4 runs below, bus profile
now pinned): stance `currentcap29-s5-klrollback05-acq15m`, walk
`slew_smooth_s0`, lower `lowerrole-scratch-sac-s{0,1}-drramp-acq1`,
speed 0.06, heading 0, det, n=18 episodes/arm x 2 seeds (0, 100) per
checkpoint = 36 "direct" (composed rise->walk->lower) + 36 "plant"
(walk role's own clean reset -> lower, isolates walk-exit momentum)
episodes per checkpoint, 144 episodes total.

## Finding 1: over_current fails are REAL and multi-joint, not a
single-joint signature
Combined over 37 over_current terminations (both checkpoints, both
seeds, direct+plant arms): the responsible joint (by `trip_summary`'s
`final_joint`, matching the SafetyLayer's own `max(current_ids,
key=abs)` rule) is **L5 hip in 15/37 (41%)**, L2 knee 7/37, L2 hip
7/37, L1 hip 4/37, L0 knee 3/37, L5 knee 1/37 -- a leading joint (the
rearmost leg's hip) but NOT an exclusive single-joint mechanism; 6 of
18 joints appear. Current pins at the same ~2.46-2.64A hard ceiling
the joystick track's closed `k_walk_move_current` lever already names
(a recurring actuator-model saturation value, not unique to this
pathology). Onset phase-fraction through the 15s lower episode ranges
18%-99%, MEDIAN 37% -- i.e. typically mid-descent, not exclusively
late. Evidence: `current_trace_{s0,s1}_seed{0,100}/*_over_current.json`.

## Finding 2: s0 is more robust than s1, consistently, but neither is
clean
Direct-arm `lower_ok` over 2 independent seed draws (36 episodes
each): **s0 24/36 (66.7%)**, s1 16/36 (44.4%) -- s0 beats s1 in BOTH
individual seed draws (14/18 vs 9/18 at seed 0; 10/18 vs 7/18 at seed
100) and on the plant arm too (s0 28/36 vs s1 24/36). This replicates
the qualitative seed-asymmetry direction from the (buggy-profile) first
pass, but NOT its magnitude or its "s0 already clears the ceiling"
framing -- under the corrected protocol neither seed is close to a
zero-fall bar, and s1's own historical isolated-gate PASS numbers
(11/12, stronger than s0's own 9/12) do not predict its WORSE composed
performance here; composition-carried state matters more than either
role's isolated gate score.
Evidence: `s{0,1}_seed{0,100}_n18_report.json`.

## Conclusion / what a future stabilization mechanism must cite
This is a broad, moderate-severity, multi-joint over_current
vulnerability under composed (walk-exit-state-carried) and even
clean-reset ("plant") lower-role episodes alike, mildly worse for s1
than s0, NOT reducible to one joint or one phase of the descent. A
future fix should not target "fix L5 hip's late-stage stall" (the
original, now-superseded framing) -- it should target whatever makes
the lower-role policy occasionally drive an ARBITRARY leg's hip/knee
into sustained high torque across a wide range of descent phases,
e.g. revisiting the per-episode current-penalty shaping
(`reward.k_current_hot`/`current_hot_a=2.0`, already present in both
recipes) or the lower-episode's own entry-pose diversity (walk-exit
qpos spans a correspondingly wide range -- not analyzed per-leg here,
left as a next step, not a new mechanism to design from scratch).

## Recommendation for todaypolicy/walkcurr
Use s0 (not s1) as the lower-role component in any lifecycle_v2
composition work (directionally, consistently better both seeds/both
arms) but do NOT claim it clears a zero-fall or even a "better than
the historical 12/18,14/18 citation" bar -- that citation itself may
be stale (see the bus-profile bug above; unclear what profile produced
it) and should be re-verified, not assumed, before being cited again.
`bundle_rlonly_lifecycle_v2/transfer_manifest.json` reflects this
corrected, modest-evidence framing, not a GO claim.
