# cw-walkscratch-easy0905-headset-halfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:13:45+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: dd62ifib

**hypothesis**: Plain English: n=3 seed check for the halfgrav-family heading canary (headset-halfgrav-c2, from halfgrav-s2, already reads clean: monotonic reward quarters 25.9/53.5/64.0/98.8). Does a SECOND 0.5g champion (halfgrav-s1) also keep walking under the small discrete heading set {0,+45,-45} on the same unchanged freeprog reward? Same bank-proven recipe/boundaries as the base-family sibling canaries launched this cycle. Cheap 2M canary using idle GPU capacity.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

