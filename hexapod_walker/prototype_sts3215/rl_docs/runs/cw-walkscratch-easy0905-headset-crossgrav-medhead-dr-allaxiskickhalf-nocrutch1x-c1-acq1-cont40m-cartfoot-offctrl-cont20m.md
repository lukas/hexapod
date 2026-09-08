# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T06:46:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont10m

**wandb_id**: h2y5r9w0

**hypothesis**: Plain English: matched control for cartfoot-c1-cont20m — the same exact +10M continuation of the joint-decode (no Cartesian keys) arm from its OWN 12M checkpoint, RNG2, identical recipe, so the FINAL one-extra-read of the Cartesian retrofit compares both parameterizations at equal 22M cumulative depth and the verdict is causal to the 3 cart keys, not a training-depth artifact.

**gate**: 24-ep walk/walk_startjitter det+sto retention gate at 22M cumulative: PASS = retention of the source band (0 falls, gait_valid >=18/24, group mean slip in the ~5-6/m band, no new chronic single-leg sacrifice) — then it IS the comparison band for cartfoot-c1-cont20m's final read. If this control itself drifts, read the continuation pair as INCONCLUSIVE rather than crediting/blaming the Cartesian mechanism. No new seeds, doses, torque, or reward changes.

**verdict**: Matched control retains the source band at 22M cumulative (10.48M this segment): 0 falls/terminations in 24/24 episodes, gait_valid 22/24 (6/5/5/6 det/sto/sjdet/sjsto), mean slip/m by group 5.41/5.41/6.16/5.65 -- all within the established ~5-6/m band (sj/det ticks slightly above but not a drift). Video (walk_det_0) stays upright and level across the whole clip, all six legs visibly cycling. This confirms the control did NOT drift at extended depth, so the paired cartfoot-c1-cont20m final read is a valid comparison, not INCONCLUSIVE. Retention gate: PASS. No further action on this control line; it is now the terminal reference for fork (a).

