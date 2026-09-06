# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gains1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:31:13+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) per-joint PD-gain spread (kp_scale_pct/kv_scale_pct) -- the easy0905 recipe has trained with EVERY joint's position/velocity gain pinned at the exact same fitted value every episode (dr-scale=0.0 collapses the RandRanges kp/kv_scale_pct magnitudes to 0 when not explicitly overridden), i.e. no per-servo gain spread despite 18 physically-distinct STS3215 units that will never share identical PD response on hardware. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR gain spread (+-20% kp / +-25% kv per joint) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates per-servo gain heterogeneity. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows uniform-gain idealization is load-bearing and the DR-rung must budget real training time against per-servo gain spread.

