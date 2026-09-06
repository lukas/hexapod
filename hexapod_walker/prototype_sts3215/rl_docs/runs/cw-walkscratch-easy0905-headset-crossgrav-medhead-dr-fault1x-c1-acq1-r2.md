# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-06T08:43:32+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1

**wandb_id**: j5s145wt

**hypothesis**: Plain English: does the moderate per-episode actuator FAULT probability (fault_prob=0.3, weakened/frozen/disabled-joint mix) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-run of fault1x-c1-acq1, which landed with an accidental 2M-step budget (the --steps-not-overridden respec bug, RL_LOG 09-06 07:3x/08:2x) -- this -r2 explicitly pins --steps 40000000 to give the axis its intended first ACQ-scale confirmation.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the fault-injection axis needs more/different training exposure before being called safe.

**verdict**: Killed by the launching cycle itself within ~4M steps of start (self-caught guardrail overage, no meaningful progress lost): this was my cycles 3rd 40M ACQ launch this cycle (gains1x-r2 + geom1x-r2 already running), pushing new-GPU-steps-this-cycle to 120M against guardrails.yaml max_new_gpu_steps_per_cycle=80000000 (no operator exception in force). Re-queued to backlog for a later cycle to pick up honestly within its own cap; hypothesis/gate unchanged and still valid.

