# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T06:44:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont10m

**hypothesis**: Plain English: matched control for cartfoot-c1-cont20m — the same exact +10M continuation of the joint-decode (no Cartesian keys) arm from its OWN 12M checkpoint, RNG2, identical recipe, so the FINAL one-extra-read of the Cartesian retrofit compares both parameterizations at equal 22M cumulative depth and the verdict is causal to the 3 cart keys, not a training-depth artifact.

**gate**: 24-ep walk/walk_startjitter det+sto retention gate at 22M cumulative: PASS = retention of the source band (0 falls, gait_valid >=18/24, group mean slip in the ~5-6/m band, no new chronic single-leg sacrifice) — then it IS the comparison band for cartfoot-c1-cont20m's final read. If this control itself drifts, read the continuation pair as INCONCLUSIVE rather than crediting/blaming the Cartesian mechanism. No new seeds, doses, torque, or reward changes.

**refused_reason**: hexapod-mjx-train-0 code marker 6abf149bb013bf20002fd2c7961c3bcdfb2f0fb8 != local HEAD e74e248751ab7584b50d04c8b80dbc17cc28de41 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-0 (and snapshot/commit before that if the tree is dirty).

