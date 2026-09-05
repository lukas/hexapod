# cw-walkscratch-easy0905-headset-base-s1c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:09:04+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: xors486s

**hypothesis**: Plain English: n=3 seed check (third base-family champion, base-s1-c1) for the heading canary, same design as headset-base-s0c1 (see that run for full rationale) -- reusing idle GPU capacity per the operator's full-fleet-utilization order rather than leaving it idle mid-campaign.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-base-c1): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

