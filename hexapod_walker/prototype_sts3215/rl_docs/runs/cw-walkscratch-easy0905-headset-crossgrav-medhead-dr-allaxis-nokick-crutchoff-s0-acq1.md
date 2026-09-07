# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T06:23:45+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0

**wandb_id**: 0r0p9nix

**hypothesis**: Plain English: crutchoff-s0's 2M canary CANARY PASSED (0 falls/24 eps, gait_valid 6/6+4/6+6/6+3/6=19/24), completing the 3-seed crutch-isolation set 3/3 clean. This is the ONE seed whose crutch-ON failure only showed up at 40M ACQ, not at 2M (2/24 tilt_roll falls at acq scale, 0/24 at its own 2M canary) -- so unlike s1/s2 (which fell with crutch ON at their own 2M canaries too), a clean crutch-off canary here is the WEAKEST prior evidence of the three. Does removing the crutch (dr.torque_scale 3,3->1,1) hold at the exact budget where this seed's crutch-ON fragility first appeared, completing the 3-seed ACQ picture alongside the already-running s1/s2-acq1?

**gate**: ACQUISITION: held-out gate (DR-0, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid stays >=18/24 (flat-or-better vs the 2M canary's 19/24) -- entrenchment/regression if falls reappear (the SAME failure mode crutch-ON already showed at this exact budget) or gait_valid drops materially.

