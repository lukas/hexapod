# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widenbis135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-07T12:26:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: nbcddvh2

**hypothesis**: Plain English: does the +135deg-alone heading widen that EXONERATED seed 0 (base5+135, ACQ PASS, 21/24 gait_valid matching baseline) replicate on seed 2, completing the 3-seed set? This campaign's own discipline requires 3-seed confirmation before calling any realism axis closed; widenbis135 is s0-only (s1 companion launched same cycle). Same exact recipe as s0-widenbis135 (add ONLY +135deg to the 5-way heading set), warm-started from s2's OWN ACQ-passed crutchoff-s2-acq1 checkpoint, seed 4 to match s2's own convention. Prediction-if-true: gait_valid stays near s2-acq1's own 21/24 baseline, 0 falls, no new chronic sacrifice -- widenbis135 generalizes 3/3. Prediction-if-false: a new chronic leg-pair sacrifice or fall appears -- s0's clean result does not generalize.

**gate**: PASS (heading exonerated, replicates s0) if 0 falls/24 AND gait_valid>=19/24 AND no chronic (<0.10 duty every flagged episode) single-leg or leg-pair sacrifice absent from s2-acq1's own clean panel. FAIL if a chronic sacrifice or fall appears that s2-acq1's own baseline does not show.

**verdict**: Heading-widen (base5+135deg) replicates on seed 2, completing the 3-seed set clean. gait_valid 21/24 (5/6,6/6,6/6,4/6), 0 falls/terms in all 24 held-out episodes, matching seed2's own crutchoff-s2-acq1 baseline (also 21/24: 6/6,6/6,6/6,3/6) almost exactly -- same two legs (0 and 5) flagged, no new chronic sacrifice, no fall. Slip/m similar range to baseline (not the axis under test). Closes widenbis135 3/3 ACQ PASS (s0, s1, s2 all clean) -- the +135deg heading-widen realism axis is proven on all 3 crutch-off seeds. Per the s0-widenbis135-speedwiden interaction FAIL (matched-fault control, RL_LOG 09-07 13:34), heading-widen and speed-widen (also 3/3 ACQ PASS) are adopted as two SEPARATE hardening lineages, not stacked, until a fault-robustness mitigation is designed. No further widenbis135 spend needed.

