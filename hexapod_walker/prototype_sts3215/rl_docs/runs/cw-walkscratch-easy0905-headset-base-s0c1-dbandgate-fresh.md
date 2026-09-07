# cw-walkscratch-easy0905-headset-base-s0c1-dbandgate-fresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T02:53:18+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgfresh

**wandb_id**: f3wp5pba

**hypothesis**: Both closed floor-only/count-only per-leg-utilization mechanisms (walk_duty_gate 9/9 FAIL, walk_swing_gate 5/5 FAIL) on this exact base(1g) family s0c1 leg-1/4 chronic-underuse pathology only ever priced ONE tail of contact duty (more duty good, or more swing-count good) -- CURRENT_TRUTHS 09-05 diagnosed BOTH closures' shared root cause as leaving the OTHER tail (freeze/vibrate for duty_gate; toe-tap-without-load for swing_gate) as the cheaper escape. New mechanism reward.walk_duty_band_gate (built+bank-proved this cycle, 13/13 test_walkscratch_easy_pilot.py green, formal bit-exact proof for the g=0 default path) prices BOTH tails of the SAME trailing contact-duty signal walk_duty_gate already used: MIN over support legs of a trapezoid membership in [duty_band_floor, duty_band_ceil], scoring 1.0 only for a genuinely alternating mid-range duty. This is the fresh-provenance arm: identical recipe/seed/init-from (base_s0_c1.zip, the same lightly-trained checkpoint dgfresh baked its (failed) duty_gate into) with ONLY the reward mechanism swapped, to test whether pricing BOTH tails from before the habit entrenches avoids the leg-1/4 marginal-underuse pattern the undosed s0c1-acq1 lineage develops.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M), same bar dgfresh/swinggate-fresh used: PASS if walk_startjitter/det leg duty is measurably higher (least-favored leg, not just factor movement) than the undosed twin's own landed report (cw_walkscratch_easy0905_headset_base_s0c1_gate/report.json: leg-4 duty 0.02-0.07 all 6 episodes, gait_valid 0/6) with walk/det+sto staying >=10/12 valid and no new falls -- evidence the two-sided band moves the mean where the one-sided floor/count gates could not. FAIL if leg duty is unchanged/worse vs the undosed twin (repeats the INERT-DOSE/toe-tap-without-load fingerprint a 3rd way) or det/sto validity regresses or falls appear -- closes duty_band_gate as a repair lever for this family too, forcing the next design pass toward a structural (curriculum/exploration-anneal) rather than reward-price mechanism.

**verdict**: CANARY FAIL - MECHANISM: two-sided duty-band pricing does not repair the leg-4 startjitter dropout from a fresh warm-start. Evidence: walk_startjitter/det leg-4 duty_cycle stays 0.03-0.07 (median 0.045) across all 6 episodes, essentially the same as the undosed twin's own landed 0.02-0.07 (median 0.045) -- leg 4 sacrificed 6/6 episodes both arms, gait_valid 0/6 both. Plain walk/det stays clean (6/6 valid, matches baseline) and no new falls appear (terms=0 both modes); frame strip looks like ordinary walking, not a new freeze/vibrate escape -- a plain inert dose. Why: this is the 3rd independent reward-price mechanism on this exact family (after walk_duty_gate 9/9 FAIL and walk_swing_gate 5/5 FAIL) to fail moving the metric even applied from a fresh checkpoint before any habit entrenches -- the two-sided band still leaves near-zero support-leg duty as a viable optimum under start-jitter resets. Next: per the pre-registered gate this closes duty_band_gate as a repair lever on fresh-provenance init; the leg-4 startjitter underuse needs a structural fix (curriculum/exploration-anneal on jittered starts), not a 4th reward-price variant.

