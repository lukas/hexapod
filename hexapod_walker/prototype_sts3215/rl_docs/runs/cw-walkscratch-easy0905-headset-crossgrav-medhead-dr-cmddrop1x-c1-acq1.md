# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:55:40+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1

**hypothesis**: Does the campaign's PERFECT single-axis DR-restore canary (medhead-dr-cmddrop1x-c1: nominal cmd_drop_prob~=0.022, 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real acquisition-scale (40M) training budget on top of the 80M champion, matching the friction1x/mass1x precedent that individual-axis DR-restore canaries need their own ACQ confirmation, not just a 2M glance?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show even a PERFECT canary is not safe to assume durable.

