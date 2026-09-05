# cw-walkscratch-easy0905-headset-base-s0c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:10:23+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: tm703vax

**hypothesis**: Plain English: n=3 seed check for the base-family heading canary (headset-base-c1, from base-s2, already CANARY PASSed: reward+v_along_cmd+ep_len all healthy). Does a SECOND base-family champion (base-s0-c1) also keep walking under the small discrete heading set {0,+45,-45} using the same unchanged freeprog reward? Same bank-proven recipe (test_walkscratch_easy_pilot.py EASY_HEADING, 22/22 green), same boundaries (no new reward keys, own-track warm start, not teacher/BC/motion-prior). Cheap 2M canary reusing idle GPU capacity while the base-c1/halfgrav-c1 40M acquisitions train.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-base-c1/headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live (env/v_along_cmd and/or reward_walk trending up across the 2M budget). FAIL only on flat reward/v_along or an immediate park recapture.

