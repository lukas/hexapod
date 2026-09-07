# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T05:37:19+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2

**wandb_id**: qrpb9skj

**hypothesis**: Plain English: crutchoff-s2's 2M canary CANARY PASSED (0 falls/24 eps, gait_valid 20/24), matching its s1 twin, on a seed that fell repeatedly with the 3x torque crutch ON. Second seed of the same acquisition-scale durability question: does crutch-off push-recovery robustness survive 40M of further training, not just a 2M canary?

**gate**: ACQUISITION: held-out gate (DR-0, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid stays >=18/24 (flat-or-better vs the 2M canary's 20/24) -- entrenchment/regression if falls reappear or gait_valid drops materially.

**verdict**: ACQ PASS: crutch-off (dr.torque_scale 3,3->1,1) fix HOLDS at real 40M acquisition budget on seed s2 -- 0 falls/terminations across all 24 held-out episodes (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 3/6), gait_valid 21/24, flat-or-better vs the 2M canary's own 20/24 (same startjitter/sto softening pattern, transient single-leg flags not chronic). Progress/slip both improved over the 2M canary (walk/det slip med 4.88, prog med 1.69). Frame strips (contact_sheet, walk_startjitter_sto_5) confirm a level upright body through push markers, no topple. This is the 2nd of 3 crutch-off seeds to confirm the fix survives full ACQ budget (matches s1-acq1's expected pattern; s0-acq1 still training). Closes the seed-2 slice of item(1)'s crutch-isolation question: removing the 3x torque assist is a real, budget-durable fix for the push-recovery fragility on this seed, not just a canary-depth artifact.

