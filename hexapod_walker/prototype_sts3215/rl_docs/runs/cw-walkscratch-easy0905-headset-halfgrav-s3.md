# cw-walkscratch-easy0905-headset-halfgrav-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:12:28+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: btkppya1

**hypothesis**: Plain English: n=3 seed check (third 0.5g champion, halfgrav-s3) for the heading canary, same design as headset-halfgrav-s1 (see that run for full rationale) -- reusing idle GPU capacity per the operator's full-fleet-utilization order.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

