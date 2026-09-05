# cw-walkscratch-easy0905-headset-base-medhead-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T18:11:53+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-c1

**wandb_id**: 8dtoak13

**hypothesis**: Plain English: the 2M medium-heading canary (headset-base-medhead-c1) already proved the heading-tracking gradient is live and mechanism-healthy on the 5-way quarter-turn set (v_along cleared the noise floor, full survival, no collapse) -- this gives it the full 40M acquisition budget to see if it actually learns to walk toward all 5 commanded headings (0,+-45,+-90deg) as cleanly as base-acq1 learned the 3-way set. Warm-started from headset-base-medhead-c1's own 2M checkpoint (own-track continuation, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at own physics + medium heading set: 20s held-out episodes across all 5 headings (0,+-45,+-90deg), >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than reflex-stop. PASS licenses re-attempting the full 8-way set as the next widening rung; FAIL (flat/non-tracking after 40M) means the quarter-turn-only rung itself needs decomposition (e.g. one direction pair at a time) before any wider set.

