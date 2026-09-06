# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:20:03+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobias1x-c1

**hypothesis**: Harder variant of the in-flight zerobias1x arm (nominal joint_zero_bias_deg=1.0, sensor-readback-only): additionally set dr.zero_drift_cmd_frame=1 so the SAME per-joint zero-point error also shifts the commanded-position frame (a hardware-realistic coupling -- a physical set-zero calibration error moves BOTH what the encoder reports AND where a given command angle actually points the joint, not just the readback). Does the champion still tolerate its own nominal zero-bias when the error is not silently correctable via feedback alone? Independent of zerobias1x's own verdict (still training) -- this is a distinct, harder configuration of the same axis, not a duplicate.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates the harder frame-coupled zero-bias, not just the sensor-only version. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) relative to the sensor-only zerobias1x sibling -- shows the command-frame coupling (not just the bias magnitude) is the binding part of this axis.

