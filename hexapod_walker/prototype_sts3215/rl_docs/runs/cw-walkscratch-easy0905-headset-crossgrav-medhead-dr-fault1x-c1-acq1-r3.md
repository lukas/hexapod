# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1-acq1-r3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T09:01:50+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1

**wandb_id**: 9nx4uk9j

**hypothesis**: Plain English: does the moderate per-episode actuator FAULT probability (fault_prob=0.3, weakened/frozen/disabled-joint mix) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-queue of fault1x-c1-acq1-r2, which this same cycle self-killed at ~4M steps purely to stay within the guardrails.yaml max_new_gpu_steps_per_cycle=80000000 cap (that cycle had already committed 80M via gains1x-r2+geom1x-r2) -- no behavioral concern, just budget bookkeeping. -r2 itself was a re-run of fault1x-c1-acq1, which landed with an accidental 2M-step budget (the --steps-not-overridden respec bug, RL_LOG 09-06 07:3x/08:2x).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the fault-injection axis needs more/different training exposure before being called safe.

