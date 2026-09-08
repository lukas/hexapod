# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T11:32:10+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: wcwrs8eq

**hypothesis**: 2nd seed of the swing-count-floor lever (see s0 sibling's hypothesis for the full mechanism rationale): does pairing the 0.30-target ratio charge with a >=2-swing/4s floor close the 'gait_valid recovers via worse slip' trade both dose escalations showed, reproducibly across seeds? One lever vs the exact matched 0.30-dose guardfix1 sibling, same seed/init-from/heading-set/DR/motor cfg.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, identical gate text to the s0 sibling: (a) post-grace ratio telemetry present/finite; (b) zero new falls vs the matched 0.30-dose s1 sibling; (c) >=3/4 groups jointly improve gait_valid AND slip/progress vs that sibling for CONTINUE; report whether the specific episode-level trade the 0.30/0.45 doses showed persists. Short 2M null does not close the lever alone.

