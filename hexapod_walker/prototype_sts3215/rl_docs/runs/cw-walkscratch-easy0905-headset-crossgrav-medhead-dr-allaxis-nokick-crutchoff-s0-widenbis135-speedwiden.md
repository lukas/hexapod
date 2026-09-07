# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis135-speedwiden

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T12:31:11+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis135

**wandb_id**: v9a5r2xq

**hypothesis**: Plain English: two realism axes on this crutch-off full-DR composite have now EACH been independently validated on seed 0 -- base5+135 heading widening (widenbis135, ACQ PASS 21/24) and command speed-band widening (speedwiden, ACQ PASS 21/24, closed 3/3) -- but never together. Does combining them (6-way heading INCLUDING +135, plus the 0.03-0.12 m/s dynamic-cap speed range) still hold, or is there an interaction (e.g. the wider heading set makes the policy more sensitive to a wider commanded speed, or vice versa) that neither single-axis test could reveal? Warm-started from s0's own widenbis135 checkpoint (already has the heading axis baked in), adding ONLY the speedwiden cfg on top -- same pattern as every other single-axis-addition arm in this campaign. Prediction-if-true (composable): gait_valid stays near s0-widenbis135's own 21/24, 0 falls, no new chronic sacrifice beyond the walk_startjitter/sto leg0/leg5 flag both single axes already share -- both axes can be adopted together into item(1)'s next composite champion. Prediction-if-false: a new chronic sacrifice or fall appears that neither single-axis arm showed alone -- an interaction exists and the composite needs to be built as its own item, not assumed from independent single-axis passes.

**gate**: PASS if gait_valid>=18/24 (near s0-widenbis135's own 21/24) with 0 falls/24 and no new chronic sacrifice beyond walk_startjitter/sto leg0/leg5. FAIL if a new chronic leg-pair sacrifice or fall appears that neither speedwiden nor widenbis135 alone showed.

