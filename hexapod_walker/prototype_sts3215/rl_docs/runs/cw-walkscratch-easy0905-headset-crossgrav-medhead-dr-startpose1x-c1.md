# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-startpose1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T05:56:11+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: bp9r6xkj

**hypothesis**: Restore nominal (1x) START-POSE spread (placement_noise_deg per-joint hand-placement slop + bad_start_prob/max_joints/deg occasional badly-off joints, i.e. how a human actually sets the robot down) -- the easy0905 recipe has trained from an EXACTLY nominal start pose every episode (dr-scale=0.0 collapses these to 0 when not explicitly overridden), yet the eval harness's own walk_startjitter panel already exercises exactly this. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR start-pose spread without retraining collapse -- note this same bundled mechanism (placementjit) was already tried as a REPAIR lever on a different, already-compromised base(1g) family and CLOSED 8/8 FAIL there (regressed vs undosed twins); this arm asks the DISTINCT question of whether an already-CLEAN crossgrav-transferred champion also regresses under it, not whether it repairs anything.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- would extend the base(1g) placementjit-closure finding to the crossgrav family too and argue start-pose realism needs a real hardening-rung training budget everywhere, not just here.

