# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T05:23:28+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: ni3kpon4

**hypothesis**: Restore nominal (1x) lost-SyncWrite / dropped-command probability (cmd_drop_prob_max) -- the easy0905 recipe has trained with ZERO dropped control ticks the whole campaign (dr-scale=0.0 collapses the RandRanges cmd_drop_prob_max magnitude to 0 when not explicitly overridden), i.e. every one of the 100Hz control ticks lands exactly as commanded, unlike the real bus which occasionally drops a SyncWrite. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR command-drop rate (up to 5% of ticks silently repeat the previous command) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates occasional dropped commands. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows the zero-drop idealization is load-bearing.

