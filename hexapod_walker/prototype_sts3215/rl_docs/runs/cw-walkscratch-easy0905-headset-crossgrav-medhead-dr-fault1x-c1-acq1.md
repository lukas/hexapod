# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SUPERSEDED

**created**: 2026-09-06T07:41:58+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1

**wandb_id**: etbc8q3h

**hypothesis**: Plain English: does tolerance of a real per-episode actuator fault (0.3 prob, weakened/frozen/disabled-leg mix) stay a clean walk with a real 40M training budget, not just a 2M canary glance? fault1x-c1's own 2M canary was 22/24 (0 falls, one flag directly explained by that episode's own injected dead joint) -- this is its first ACQ-scale confirmation, and the only remaining named DR axis without one besides gains1x/geom1x/extpush1x/actionnoise1x.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice beyond what's directly explained by injected faults, 0 unexplained falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg not explained by fault metadata, or an unexplained fall).

**verdict**: Mislabeled-budget duplicate, not a real ACQ read: same respec-steps-inheritance footgun as extpush1x/gains1x/geom1x -- landed at the source canary's 2M budget instead of 40M. Same information as the already-PASSed fault1x-c1 2M canary (one fault-explained leg-0 blip, non-chronic, 0 falls) -- no new evidence. Why: closing the ledger cleanly. What's next: the correctly-budgeted 40M read is running as fault1x-c1-acq1-r3 (wandb 9nx4uk9j, after -r2 was self-killed by a concurrent cycle's own cap correction) -- read and verdict that one.

