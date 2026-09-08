# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T06:41:27+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont10m

**wandb_id**: xcn1obp9

**hypothesis**: Plain English: the corrected 12M read of the Cartesian foot-decode retrofit landed in its registered INTERMEDIATE band (ON/OFF mean-slip ratios 2.42/3.08/2.52/3.10 — neither <=1.5x promising nor >3x-in-3/4 failure), with all four held-out groups improving slip AND progress from 2M->12M and duration-normalized per-tick reward rising -0.44->-0.17; this run executes the gate's own one-extra-read clause: does slip keep converging toward the joint-decode control band with exactly 10M more steps, or is ~2.5-3x the control this parameterization's asymptote? Exact continuation of cartfoot-c1-cont10m from its OWN 12M checkpoint, RNG2, identical PPO/physics/reward/noise/motor cfg; only the 3 goal.walk_cart_foot_box_* keys differ from the matched control.

**gate**: FINAL one-extra-read (clause exhausted after this — no further automatic extensions): 24-ep walk/walk_startjitter det+sto exact gate at 22M cumulative vs matched cartfoot-offctrl-cont20m at equal depth, arithmetic MEAN slip_per_m per group. PROMISING = mean slip <=1.5x control in >=3/4 groups AND gait_valid >=18/24 AND 0 falls. FALSIFIES the retrofit = >3x control in >=3/4 groups OR gait_valid <18/24; any new fall or protected-behavior loss also blocks promotion and further continuation. Any remaining intermediate result = record unresolved-retrofit outcome and STOP automatic extensions — NOT a universal Cartesian class closure. If per-tick reward rises but held-out slip/progress stalls or worsens, route to the MISALIGNED audit branch instead of more same-recipe training. No new seeds, doses, torque, or reward changes.

