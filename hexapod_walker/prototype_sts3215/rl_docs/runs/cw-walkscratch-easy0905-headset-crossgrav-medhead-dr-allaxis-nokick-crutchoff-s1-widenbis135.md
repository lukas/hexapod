# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widenbis135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T12:23:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

**wandb_id**: duvwg4h3

**hypothesis**: Plain English: does the +135deg-alone heading widen that EXONERATED seed 0 (base5+135, ACQ PASS, 21/24 gait_valid matching baseline) replicate on seed 1, or was s0 lucky? This campaign's own discipline requires 3-seed confirmation before calling any realism axis closed (every other axis here -- speedwiden, the original 5-way heading set, all named DR axes -- was seed-replicated before adoption); widenbis135 is s0-only so far. Same exact recipe as s0-widenbis135 (add ONLY +135deg to the 5-way heading set), warm-started from s1's OWN ACQ-passed crutchoff-s1-acq1 checkpoint instead of s0's, seed 3 to match s1's own convention. Prediction-if-true: gait_valid stays near s1-acq1's own 21/24 baseline, 0 falls, no new chronic sacrifice -- widenbis135 generalizes as safe. Prediction-if-false: a new chronic leg-pair sacrifice or fall appears -- s0's clean result was seed-specific, not a property of the +135 heading itself.

**gate**: PASS (heading exonerated, replicates s0) if 0 falls/24 AND gait_valid>=19/24 AND no chronic (<0.10 duty every flagged episode) single-leg or leg-pair sacrifice absent from s1-acq1's own clean panel. FAIL if a chronic sacrifice or fall appears that s1-acq1's own baseline does not show.

