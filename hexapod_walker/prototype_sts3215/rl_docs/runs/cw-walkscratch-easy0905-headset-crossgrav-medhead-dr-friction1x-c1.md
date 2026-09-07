# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:12:45+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) ground-friction randomization -- the easy0905 recipe has trained with contact friction_scale pinned at an exact fixed 1.0x (dr-scale=0.0 collapses the RandRanges friction_scale pair (0.6,1.4) to a single fixed point when not explicitly overridden), i.e. every episode sees the SAME foot/ground friction regardless of surface/print/wear spread, even though slip/m is this whole campaign's core tracked metric. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR friction range (0.6-1.4x) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass DR-restoration arms -- friction is arguably the most load-bearing untested axis given how heavily this track already scores slip.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls, and slip_per_m does not blow out far past the 2.6-3.4 champion-band -- shows the gait does not depend on the fixed-friction idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, falls appear, or slip/m spikes into a paddle/skate regime) -- shows friction realism is a binding constraint the DR-rung must budget real training time against.

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1 already exists on hexapod-mjx-train-1

