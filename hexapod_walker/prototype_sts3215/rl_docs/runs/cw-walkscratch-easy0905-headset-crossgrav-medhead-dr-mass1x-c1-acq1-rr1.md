# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED_DUPLICATE

**created**: 2026-09-06T06:53:38+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1

**hypothesis**: Plain English: does the real hardware's mass-manufacturing tolerance (0.85-1.20x global mass_scale + 0.10 per-leg jitter) stay a clean walk with real training, not just a 2M canary glance? mass1x-c1's own 2M canary was 23/24 (one non-chronic leg-4 flag) on the campaign's cleanest champion -- unlike the PERFECT-canary axes, this is a near-clean-but-imperfect canary, a second useful data point (after torquefade2x-c1-acq1) on whether canary cleanliness predicts ACQ-scale durability for bare DR-realism axes the way it does for irr/widen composition axes.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice (a repeat of the same non-chronic leg-4 blip is fine) and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears -- would show mass tolerance is a real hardening-rung item, not a free axis.

**verdict**: Killed within ~1min of start: a backlog-queue race re-launched the SAME respec (mass1x-c1-acq1) as a true duplicate on train-3 after the original had already landed VERIFIED RUNNING on train-7 (a launcher-side experiments.json write got transiently truncated by a concurrent-write race mid-launch, which made the drain believe the first attempt had crashed and requeue an -rr1 retry -- the original process on train-7 was never actually dead, confirmed alive via live ps + launch_run.py status). Zero GPU-hours lost (killed at ~1 min, no checkpoint produced). The real arm continues as cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1 on train-7.

