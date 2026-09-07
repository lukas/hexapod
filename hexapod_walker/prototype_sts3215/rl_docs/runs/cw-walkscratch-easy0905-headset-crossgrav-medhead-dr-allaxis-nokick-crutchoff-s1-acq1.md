# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T05:33:50+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1

**wandb_id**: 0aq94iv4

**hypothesis**: Plain English: crutchoff-s1's 2M canary CANARY PASSED (0 falls/24 eps, gait_valid 6/6+5/6+6/6+3/6=20/24), on the SAME seed that fell repeatedly with the 3x torque crutch ON. Does removing the crutch keep working at real acquisition budget (40M), or does this seed re-develop the push-recovery fragility once training entrenches further (matching the pattern where s0's own crutch-ON failure only appeared at 40M, not at 2M)?

**gate**: ACQUISITION: held-out gate (DR-0, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid stays >=18/24 (flat-or-better vs the 2M canary's 20/24) -- entrenchment/regression if falls reappear or gait_valid drops materially.

**verdict**: ACQ PASS: crutch-off (dr.torque_scale 3,3->1,1) fix HOLDS at real 40M acquisition budget on seed s1 -- 0 falls/terminations across all 24 held-out episodes (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 3/6), gait_valid 21/24, flat-or-better vs the 2M canary's own 20/24 (same startjitter/sto softening pattern as canary and as the s2-acq1 sibling, transient single-leg flags not chronic). Progress/slip both improved over the 2M canary depth (walk/det slip med 4.67, prog med 1.77). Contact sheet confirms a level, upright body walking through push-perturbation markers with no topple. This is the 1st of 3 crutch-off seeds to confirm the fix survives full ACQ budget, and matches s2-acq1's identical numbers (21/24, same panel breakdown) landed the same cycle -- 2/2 ACQ seeds now clean, s0-acq1 still training. Closes the seed-1 slice of item(1)'s crutch-isolation question: removing the 3x torque assist is a real, budget-durable fix for the push-recovery fragility, not just a canary-depth artifact.

