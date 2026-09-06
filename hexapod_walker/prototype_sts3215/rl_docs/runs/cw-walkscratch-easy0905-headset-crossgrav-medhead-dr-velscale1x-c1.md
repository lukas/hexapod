# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-velscale1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:22:07+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) per-joint max-velocity spread (vel_scale) -- the easy0905 recipe has trained with every servo's achievable slew rate pinned at the exact same fitted value every episode (dr-scale=0.0 collapses the RandRanges vel_scale pair (0.85,1.10) to a single fixed point when not explicitly overridden), i.e. no per-servo speed-capability spread despite real STS3215 units varying in max speed with wear/battery/unit. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR velocity-cap spread (0.85-1.10x) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates per-servo max-velocity heterogeneity. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows uniform-speed-cap idealization is load-bearing.

