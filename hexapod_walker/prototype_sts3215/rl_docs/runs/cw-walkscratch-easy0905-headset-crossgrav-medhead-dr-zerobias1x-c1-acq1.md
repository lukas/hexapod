# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobias1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T07:23:48+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobias1x-c1

**wandb_id**: r7b1feao

**hypothesis**: 3rd individual single-axis DR-restore ACQ-scale continuation this cycle-window (after friction1x-c1-acq1 by me and torquefade2x/mass1x/encnoise1x-c1-acq1 by concurrent cycles, same idea): does the campaign's PERFECT joint-zero-calibration-bias canary (medhead-dr-zerobias1x-c1: nominal 1deg/joint set_zero offset, 24/24 gait_valid, sac=[] every episode, 0 falls at 2M) hold up at acquisition-scale (40M) on top of the 80M champion, the same canary-vs-ACQ durability question the campaign's crossgrav/widen/irr composition axes have repeatedly answered NO to for roughly half of healthy-source canary-clean cases?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls -- shows joint-zero-bias realism is durable, not just canary-clean. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows even a PERFECT single-axis DR canary is not safe to assume durable at scale.

