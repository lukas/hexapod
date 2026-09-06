# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T07:25:08+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1

**wandb_id**: np2kt3bf

**hypothesis**: Plain English: does the real actuator command-latency spread (previously OFF) stay a clean walk with real training, not just a 2M canary glance? latency1x-c1's own 2M canary was a PERFECT 24/24 (0 falls) on the campaign's cleanest champion -- a 3rd ACQ durability confirmation for a bare DR-realism axis (after torquefade2x-c1-acq1, mass1x-c1-acq1), picking the single most hardware-timing-critical axis in the sweep.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally near its own 24/24 canary) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

