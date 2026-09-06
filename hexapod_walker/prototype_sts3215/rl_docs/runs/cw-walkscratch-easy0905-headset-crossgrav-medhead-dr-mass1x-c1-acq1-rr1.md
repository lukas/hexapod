# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-06T06:53:38+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1

**hypothesis**: Plain English: does the real hardware's mass-manufacturing tolerance (0.85-1.20x global mass_scale + 0.10 per-leg jitter) stay a clean walk with real training, not just a 2M canary glance? mass1x-c1's own 2M canary was 23/24 (one non-chronic leg-4 flag) on the campaign's cleanest champion -- unlike the PERFECT-canary axes, this is a near-clean-but-imperfect canary, a second useful data point (after torquefade2x-c1-acq1) on whether canary cleanliness predicts ACQ-scale durability for bare DR-realism axes the way it does for irr/widen composition axes.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice (a repeat of the same non-chronic leg-4 blip is fine) and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears -- would show mass tolerance is a real hardening-rung item, not a free axis.

**failed_reason**: run never appeared as 'running' in W&B within 240s

