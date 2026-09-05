# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED - DUPLICATE

**created**: 2026-09-05T23:49:48+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

**wandb_id**: pbouoxbw

**hypothesis**: Plain English: widenirr-c1's 2M canary showed that composing the two independently-validated halfgrav rungs (widen2's heading-widen-from-medhead + irr's command-timing jitter, jitter applied on top of the widen2-c1 champion) is not just mechanism-healthy but actually BEATS the widen2-c1 champion's own clean canary numbers (23/24 vs 21/24 gait_valid, 0 falls, course-tracking not blown up by the added jitter). This is the acquisition-scale (40M) confirmation: does the composed widen+irr recipe hold a real course-tracking/gait advantage over plain widen2-c1-acq1 (already ACQ PASS, 21/24 gait_valid, this same cycle) at full budget, or does more training erode the composition edge the way it eroded the matched seed-2 sibling (widen2-c2b-acq1, ACQ FAIL, chronic leg-1) and widenirr-c2b (CANARY FAIL, same seed lineage)?

**gate**: ACQ PASS if gait_valid stays majority-valid (>=18/24) with 0 chronic single-leg entrenchment (no leg parked in >50% of episodes) and course/heading tracking (courserr, wrong_course_frac_1s) is flat-or-better vs this run's own 2M canary read and vs the plain widen2-c1-acq1 sibling; ACQ FAIL if gait_valid collapses into minority or a leg chronically parks, matching the widen2-c2b-acq1 entrenchment fingerprint.

**verdict**: Killed manually this cycle: this run and the watcher-drained cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1 (same init-from checkpoint, same hypothesis/gate, launched ~2min apart on train-7 and train-3) were an accidental duplicate -- my own respec --now landed on train-3 right as the watchers own continuous drain independently placed the identical backlog item on train-7. Killed the train-3 process (pid 2390147/2390148/2390153 + orphaned video/tracker children) to free the pod; the canonical acq1 run on train-7 continues as the sole ACQ arm. No training signal lost (both were <1M steps in, same checkpoint, same recipe).

