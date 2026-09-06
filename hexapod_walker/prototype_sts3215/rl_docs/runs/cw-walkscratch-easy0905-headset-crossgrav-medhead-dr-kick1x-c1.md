# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T05:18:09+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: ngh1u2od

**hypothesis**: Turn on the project's mid-walk roll-kick perturbation (a torso roll impulse, distinct from the base-torque push tested by the sibling push1x arm), currently OFF (dr.walk_kick_prob=0.0, zero kick events all campaign). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive a real chance (30%/episode, nominal dose 8-18deg peak roll over 0.5-1.2s) of a mid-walk lateral kick without retraining collapse? Isolated single-axis diagnostic, same template as the sibling push/mass/friction/latency/deadband/torque/noise DR-restoration arms; the 2nd half of the ladder's named 'DR/push hardening' rung.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from an occasional roll kick with zero retraining. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows kick recovery needs its own real training-budget hardening rung, not a free zero-shot add.

