# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T11:04:02+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1

**hypothesis**: Plain English: does the full ~30-axis realism composite, with BOTH the kick-safe half dose (0.15, proven safe standalone and in the kick-off composite) AND the torque-assist crutch fully removed (torque_scale 1.0, the real unassisted servo spec), hold up at real acquisition budget (40M), not just a 2M canary? Single lever vs the allaxiskickhalf-nocrutch1x-c1 canary (21/24 gv, 0 falls): budget 2M->40M, otherwise byte-identical.

**gate**: ACQ gate (40M): aggregate gait_valid majority (>=18/24) sustained at ACQ scale (matching or improving the 21/24 canary), 0 falls/terminations, no NEW chronic single-leg sacrifice consolidating from the canary's scattered flags (legs 2/0+2/3 across 3 different modes). PASS -> closes QUEUE AIM item (3)'s composite-no-crutch half for real at acquisition scale -- the full-realism, no-crutch, kick-safe composite is durable. FAIL/entrenches -> the no-crutch removal needs more than the kick-safe dose alone; audit torque_scale interaction with the other ~28 axes at sustained training.

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1 already exists on hexapod-mjx-train-3

