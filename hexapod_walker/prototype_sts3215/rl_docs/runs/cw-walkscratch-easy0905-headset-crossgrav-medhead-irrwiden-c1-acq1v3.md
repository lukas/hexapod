# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1v3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SELF_KILLED_OVER_CAP

**created**: 2026-09-06T05:58:31+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1

**wandb_id**: be6evk1a

**hypothesis**: The irr-then-widen composite (irr-timing jitter + 8-way heading, composed on medhead) holds at full 40M ACQ scale, matching its own 2M canary (23/24) and its widen-then-irr sibling's precedent.

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style or leg-2/5-worsening chronic sacrifice emerges.

**verdict**: Killed by the launching cycle itself within ~1 min of start (0 GPU memory used, no training progress lost): this was the cycle's 3rd 40M ACQ launch, pushing new-GPU-steps-this-cycle to 120M against the guardrails.yaml max_new_gpu_steps_per_cycle=80000000 hard cap (no operator exception in force for this cycle). Re-queued to backlog for a later cycle/drain to pick up honestly within its own cap; the hypothesis/gate are unchanged and still valid.

