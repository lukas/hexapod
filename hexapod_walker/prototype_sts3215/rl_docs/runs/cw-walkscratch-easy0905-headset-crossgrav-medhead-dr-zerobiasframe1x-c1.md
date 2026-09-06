# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T06:20:03+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobias1x-c1

**hypothesis**: Harder variant of the in-flight zerobias1x arm (nominal joint_zero_bias_deg=1.0, sensor-readback-only): additionally set dr.zero_drift_cmd_frame=1 so the SAME per-joint zero-point error also shifts the commanded-position frame (a hardware-realistic coupling -- a physical set-zero calibration error moves BOTH what the encoder reports AND where a given command angle actually points the joint, not just the readback). Does the champion still tolerate its own nominal zero-bias when the error is not silently correctable via feedback alone? Independent of zerobias1x's own verdict (still training) -- this is a distinct, harder configuration of the same axis, not a duplicate.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates the harder frame-coupled zero-bias, not just the sensor-only version. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) relative to the sensor-only zerobias1x sibling -- shows the command-frame coupling (not just the bias magnitude) is the binding part of this axis.

**verdict**: Harder frame-coupled zero-bias (dr.zero_bias applied in the COMMAND frame, not just sensor-side) holds cleanly on the campaign's cleanest champion: 23/24 gait_valid, 0 falls/terminations across the full 24-episode 4-panel harness. Evidence: only flag is walk_startjitter/sto ep3 (sac=[0]), a single non-chronic leg, not the recurring leg[1,4] fingerprint. slip/m 3.3-5.2 (in line with every sibling DR-restore canary). contact_sheet.png video-confirmed clean upright six-leg cycling gait, no drag/skate/collapse. Matches the sensor-only zerobias1x sibling's own clean PASS -- the frame-coupling is NOT the binding part of this axis; the axis is free at nominal dose regardless of which frame the bias enters in. Next: this closes zerobiasframe as another clean single-axis DR-restore; no ACQ-scale (40M) durability read yet for this specific axis.

