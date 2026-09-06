# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T11:02:27+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1

**hypothesis**: Plain English: does the full ~30-axis realism composite, with kick at its proven-safe half dose (0.15) AND the 3x torque crutch fully removed (the real unassisted servo spec), hold up at real acquisition budget (40M) -- this is QUEUE AIM item (3)'s second composite-ACQ funding step, a DIFFERENT recipe from the parallel allaxis-nokick-c1-acq1 (which keeps the crutch ON and disables kick entirely). Single lever vs the canary: budget 2M->40M, otherwise byte-identical.

**gate**: ACQ gate (40M): aggregate gait_valid majority (>=18/24) sustained at ACQ scale (matching or improving the 21/24 canary), 0 falls/terminations, no NEW chronic single-leg sacrifice, slip/m recorded (expected higher than the crutch-ON composites, ~7-17/m at canary scale) but not itself gating. PASS -> confirms the full-realism-without-crutch composite is durable at acquisition scale, a stronger realism claim than allaxis-nokick-c1-acq1 alone (keeps the crutch). FAIL/entrenches -> the composite needs the torque crutch after all once trained longer, even though the 2M canary showed no such need.

