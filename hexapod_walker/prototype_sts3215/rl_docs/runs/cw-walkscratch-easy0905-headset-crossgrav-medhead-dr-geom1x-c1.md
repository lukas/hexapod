# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:45:31+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) GEOMETRY spread (link_len_scale_pct/link_len_leg_pct print+assembly leg-length error, com_offset_m chassis CoM shift) -- the easy0905 recipe has trained with every leg link and the chassis CoM at their EXACT nominal length/position every episode (dr-scale=0.0 collapses these magnitudes to 0 when not explicitly overridden), i.e. no print/CAD/assembly tolerance despite guardrails.yaml explicitly naming GEOMETRY as one of the per-world DR axes this stack is supposed to cover. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR geometry spread (+-2% global leg length, +-1.2% per-leg-segment, +-12mm CoM shift) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction/gain DR-restoration arms -- closes out GEOMETRY, the last untested category literally named in guardrails.yaml (mass/geometry/friction/compliance/gravity/gains). Retry of the identically-designed geom1x attempt from an earlier cycle that got mechanically REFUSED twice (pod races) and never actually trained.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the fixed-geometry idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows geometry realism is a binding constraint the DR-rung must budget real training time against, likely via IK foot-placement mismatch.

**refused_reason**: hexapod-mjx-train-4 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1 — GPU pods host exactly one run; pick a free GPU pod.

