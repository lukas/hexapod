# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gains1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T08:32:20+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gains1x-c1

**wandb_id**: cp1ai238

**hypothesis**: Plain English: does the nominal per-servo PD-gain spread (+-20% kp/+-25% kv) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-run of gains1x-c1-acq1, which landed with an accidental 2M-step budget (the --steps-not-overridden respec bug, RL_LOG 09-06 07:3x/08:2x) -- this -r2 explicitly pins --steps 40000000 to give the axis its intended first ACQ-scale confirmation. gains1x-c1's own 2M canary was 23/24 (0 falls, one non-chronic leg-4 flag).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the gains-spread axis needs more/different training exposure before being called safe.

