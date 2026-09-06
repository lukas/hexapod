# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T08:16:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1

**wandb_id**: 8w82uq33

**hypothesis**: This checkpoint's own 40M ACQ read was a borderline PASS-flagged-for-WATCH: gait_valid held majority (20/24) but the sacrifice fingerprint SHIFTED (canary's confined single leg-4 softening widened to a leg[2,4] pair at the same episodes, and leg-4 newly appeared in a previously-clean mode). Does +40M more steps (80M total) resolve this back toward the canary's confined pattern, hold flat, or entrench further toward the campaign's named leg[1,4] chronic-sacrifice failure mode?

**gate**: PASS/HOLDS if gait_valid stays majority (>=12/24) with the leg[2,4] pattern staying CONFINED to its current episodes/modes (no 3rd mode gaining the pattern, no leg's duty going to ~0/chronic-park) and 0 falls. FAIL/ENTRENCHES if the leg[2,4] pair spreads to a new mode, any leg's duty collapses toward 0 across a majority of episodes in any mode, or a fall appears -- would confirm this composition line is on an entrenchment trajectory, not just a noisy but flat borderline.

