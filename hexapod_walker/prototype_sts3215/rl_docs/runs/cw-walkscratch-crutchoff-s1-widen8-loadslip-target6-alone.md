# cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T15:34:32+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s1-widen8-legdutyratio-loadslip

**wandb_id**: n2k2b5jx

**hypothesis**: Plain English: seed1 twin of the s0 loadslip-isolation arm this same window. Every walk_leg_loadslip_ratio_charge arm tried so far was ALSO trained with walk_leg_duty_ratio_charge=150 active and warm-started from a checkpoint that already had duty-ratio-charge baked in, so the reward-quarters collapse blamed on loadslip is confounded with the already-accepted (CANARY PASS) duty-ratio-charge-alone collapse shape. This arm inits from the TRUE pre-duty-charge s1 checkpoint (widen8-acq1) with duty-ratio-charge=0 and ONLY the corrected loadslip-ratio charge (150/target=6.0) live, replicating the s0 isolation arm on a second seed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, isolation scope, seed1 replicate. PASS-worth-CONTINUE if >=3/4 of the 4 held-out groups jointly improve slip AND progress vs the plain s1 widen8-acq1 undosed baseline with 0 new falls, AND reward-quarters do not show the same order-of-magnitude collapse as the s1 duty-ratio-charge-alone canary. FAIL if <3/4 groups improve or a new fall appears. Read together with the s0 twin: 2/2 FAIL closes load-slip-ratio-charge as a standalone lever; a split result needs a 3rd-seed tie-break before either claim.

